# Copyright (c) 2012-2015 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#

import os
import galsim
import logging

# This file handles processing the input items according to the specifications in config['input'].
# This file includes the basic functionality, which is often sufficient for simple input types,
# but it has hooks to allow more customized behavior where necessary. See input_*.py for examples.

# This module-level dict will store all the registered input types.
# See the RegisterInputType function near the end of this file.
# The keys will be the (string) names of the extra output types, and the values will be
# builder classes that will perform the different processing functions.
# The keys will be the (string) names of the image types, and the values will be loaders
# that load the input object's class as well some other information we need to know to how to
# process the input object correctly.
valid_input_types = {}


def ProcessInput(config, file_num=0, logger=None, file_scope_only=False, safe_only=False):
    """
    Process the input field, reading in any specified input files or setting up
    any objects that need to be initialized.

    Each item registered as a valid input type will be built and available at the top level
    of config in config['input_objs'].  Since there is allowed to be more than one of each type
    of input object (e.g. multilpe catalogs or multiple dicts), these are actually lists.
    If there is only one e.g. catalog entry in config['input'], then this list will have one
    element.

    e.g. config['input_objs']['catalog'][0] holds the first catalog item defined in
    config['input']['catalog'] (if any).

    @param config           The configuration dict to process
    @param file_num         The file number being worked on currently [default: 0]
    @param logger           If given, a logger object to log progress. [default: None]
    @param file_scope_only  If True, only process the input items that are marked as being
                            possibly relevant for file- and image-level items. [default: False]
    @param safe_only        If True, only process the input items whose construction parameters
                            are not going to change every file, so it can be made once and
                            used by multiple processes if appropriate. [default: False]
    """
    config['index_key'] = 'file_num'
    config['file_num'] = file_num
    if logger:
        logger.debug('file %d: Start ProcessInput',file_num)
    # Process the input field (read any necessary input files)
    if 'input' in config:
        # We'll iterate through this list of keys a few times
        all_keys = [ k for k in valid_input_types.keys() if k in config['input'] ]

        # First, make sure all the input fields are lists.  If not, then we make them a
        # list with one element.
        for key in all_keys:
            if not isinstance(config['input'][key], list):
                config['input'][key] = [ config['input'][key] ]

        # The input items can be rather large.  Especially RealGalaxyCatalog.  So it is
        # unwieldy to copy them in the config file for each process.  Instead we use proxy
        # objects which are implemented using multiprocessing.BaseManager.  See
        #
        #     http://docs.python.org/2/library/multiprocessing.html
        #
        # The input manager keeps track of all the real objects for us.  We use it to put
        # a proxy object in the config dict, which is copyable to other processes.
        # The input manager itself should not be copied, so the function CopyConfig makes
        # sure to only keep that in the original config dict, not the one that gets passed
        # to other processed.
        # The proxy objects are  able to call public functions in the real object via
        # multiprocessing communication channels.  (A Pipe, I believe.)  The BaseManager
        # base class handles all the details.  We just need to register each class we need
        # with a name (called tag below) and then construct it by calling that tag function.

        # We don't need the manager stuff if we (a) are already in a multiprocessing Process, or
        # (b) we are only loading for file scope, or (c) both config.image.nproc and
        # config.output.nproc == 1.
        use_manager = (
                'current_nproc' not in config and
                not file_scope_only and
                ( ('image' in config and 'nproc' in config['image'] and
                   galsim.config.ParseValue(config['image'], 'nproc', config, int)[0] != 1) or
                  ('output' in config and 'nproc' in config['output'] and
                   galsim.config.ParseValue(config['output'], 'nproc', config, int)[0] != 1) ) )

        if use_manager and 'input_manager' not in config:
            from multiprocessing.managers import BaseManager
            class InputManager(BaseManager): pass

            # Register each input field with the InputManager class
            for key in all_keys:
                fields = config['input'][key]

                # Register this object with the manager
                for i in range(len(fields)):
                    field = fields[i]
                    tag = key + str(i)
                    InputManager.register(tag, valid_input_types[key].init_func)
            # Start up the input_manager
            config['input_manager'] = InputManager()
            config['input_manager'].start()

        if 'input_objs' not in config:
            config['input_objs'] = {}
            for key in all_keys:
                fields = config['input'][key]
                config['input_objs'][key] = [ None for i in range(len(fields)) ]
                config['input_objs'][key+'_safe'] = [ None for i in range(len(fields)) ]

        # Read all input fields provided and create the corresponding object
        # with the parameters given in the config file.
        for key in all_keys:
            loader = valid_input_types[key]

            # Skip this key if not relevant for file_scope_only run.
            if file_scope_only and not loader.file_scope: continue

            if logger:
                logger.debug('file %d: Process input key %s',file_num,key)
            fields = config['input'][key]

            for i in range(len(fields)):
                field = fields[i]
                input_objs = config['input_objs'][key]
                input_objs_safe = config['input_objs'][key+'_safe']
                if logger:
                    logger.debug('file %d: Current values for %s are %s, safe = %s',
                                 file_num, key, str(input_objs[i]), input_objs_safe[i])
                if input_objs[i] is not None and input_objs_safe[i]:
                    if logger:
                        logger.debug('file %d: Using %s already read in',file_num,key)
                else:
                    if logger:
                        logger.debug('file %d: Build input type %s',file_num,key)
                    try:
                        kwargs, safe = loader.getKwargs(field, config, logger)
                    except KeyboardInterrupt:
                        raise
                    except:
                        # If we get an exception here, then probably not safe.
                        # e.g. it might need an rng that we haven't made yet.
                        # So if we are doing the safe_only run, just consider this one unsafe
                        # and move on.
                        if safe_only:
                            input_objs[i] = None
                            input_objs_safe[i] = None
                            continue
                        raise

                    if safe_only and not safe:
                        if logger:
                            logger.debug('file %d: Skip %s %d, since not safe',file_num,key,i)
                        input_objs[i] = None
                        input_objs_safe[i] = None
                        continue

                    if logger:
                        logger.debug('file %d: %s kwargs = %s',file_num,key,kwargs)
                    if use_manager:
                        tag = key + str(i)
                        input_obj = getattr(config['input_manager'],tag)(**kwargs)
                    else:
                        input_obj = loader.init_func(**kwargs)

                    if logger:
                        logger.debug('file %d: Built input object %s %d',file_num,key,i)
                        if 'file_name' in kwargs:
                            logger.debug('file %d: file_name = %s',file_num,kwargs['file_name'])
                    if logger:
                        if loader.has_nobj:
                            logger.info('Read %d objects from %s',input_obj.getNObjects(),key)

                    # Store input_obj in the config for use by BuildGSObject function.
                    input_objs[i] = input_obj
                    input_objs_safe[i] = safe
                    # Invalidate any currently cached values that use this kind of input object:
                    # TODO: This isn't quite correct if there are multiple versions of this input
                    #       item.  e.g. you might want to invalidate dict0, but not dict1.
                    for value_type in loader.types:
                        galsim.config.RemoveCurrent(config, type=value_type)
                        if logger:
                            logger.debug('file %d: Cleared current_vals for items with type %s',
                                         file_num,value_type)

        # Check that there are no other attributes specified.
        valid_keys = valid_input_types.keys()
        galsim.config.CheckAllParams(config['input'], ignore=valid_keys)


def ProcessInputNObjects(config, logger=None):
    """Process the input field, just enough to determine the number of objects.

    Some input items are relevant for determining the number of objects in a file or image.
    This means we need to have them processed before splitting up jobs over multiple processes
    (since the seed increments based on the number of objects).  So this function builds
    the input items that have a getNObjects() method using the _nobject_only construction
    argument and returns the number of objects.

    Caveat: This function tries each input type in galsim.config.valid_input_types in
            order and returns the nobjects for the first one that works.  If multiple input
            items have nobjects and they are inconsistent, this function may return a
            number of objects that isn't what you wanted.  In this case, you should explicitly
            set nobjects or nimages in the configuration dict, rather than relying on this
            galsim.config "magic".

    @param config       The configuration dict to process
    @param logger       If given, a logger object to log progress. [default: None]

    @returns the number of objects to use.
    """
    config['index_key'] = 'file_num'
    if 'input' in config:
        for key in valid_input_types:
            loader = valid_input_types[key]
            if key in config['input'] and loader.has_nobj:
                field = config['input'][key]

                if key in config['input_objs'] and config['input_objs'][key+'_safe'][0]:
                    input_obj = config['input_objs'][key][0]
                else:
                    # If it's a list, just use the first one.
                    if isinstance(field, list): field = field[0]

                    kwargs, safe = loader.getKwargs(field, config, logger)
                    kwargs['_nobjects_only'] = True
                    input_obj = loader.init_func(**kwargs)
                if logger:
                    logger.debug('file %d: Found nobjects = %d for %s',
                                 config['file_num'],input_obj.getNOjects(),key)
                return input_obj.getNObjects()
    # If didn't find anything, return None.
    return None


def SetupInputsForImage(config, logger):
    """Do any necessary setup of the input items at the start of an image.

    @param config       The configuration dict to process
    @param logger       If given, a logger object to log progress. [default: None]
    """
    if 'input' in config:
        for key in valid_input_types.keys():
            loader = valid_input_types[key]
            if key in config['input']:
                fields = config['input'][key]
                if not isinstance(fields, list):
                    fields = [ fields ]
                input_objs = config['input_objs'][key]

                for i in range(len(fields)):
                    field = fields[i]
                    input_obj = input_objs[i]
                    loader.setupImage(input_obj, field, config, logger)


# A helper function for getting the input object needed for generating a value or building
# a gsobject.
def GetInputObj(input_type, config, base, param_name):
    """Get the input object needed for generating a particular value

    @param input_type   The type of input object to get
    @param config       The config dict for this input item
    @param base         The base config dict
    @param param_name   The type of value that we are trying to construct (only used for
                        error messages).
    """
    if input_type not in base['input_objs']:
        raise ValueError("No input %s available for type = %s"%(input_type,param_name))

    if 'num' in config:
        num = galsim.config.ParseValue(config, 'num', base, int)[0]
    else:
        num = 0

    if num < 0:
        raise ValueError("Invalid num < 0 supplied for %s: num = %d"%(param_name,num))
    if num >= len(base['input_objs'][input_type]):
        raise ValueError("Invalid num supplied for %s (too large): num = %d"%(param_name,num))

    return base['input_objs'][input_type][num]


class InputLoader(object):
    """Define how to load a particular input type.

    The base class is often sufficient for simple types, but you may derive from it and
    override some of the functions to deal with special handling requirements.

    The loader object defines a few attributes that will be used by the processing framework,
    so any derived class should make sure to define them as well.

        init_func   The class or function that will be used to build the input object.

        types       A list of value or object types that use this input type.  These items will
                    have their "current" values invalidated when the input object changes.

        has_nobj    Whether the object can be used to automatically determine the number of
                    objects to build for a given file or image.  For example, a galsim.Catalog has
                    a specific number of rows in it.  In many cases, you will just want to run
                    through the whole catalog for each output file.  So the number of objects to
                    build will just be the number of objects in the input catalog. [default: False]

                    If this is True, the constructed input object must have a `getNObjects()`
                    method.  It must also take a construction kwarg, `_nobjects_only` that tells
                    it to only do enough initialization to efficiently determine nobjects.

        file_scope  Whether the input object might be relevant at file scope when the file and
                    image is initially being set up. [default: False]

                    If this is False, then the input object won't be loaded until after the
                    initial file setup.  For example, you might store the file names you want
                    to use for the output files in a YAML file, which you plan to read in as a
                    dict input object. Thus, dict is our canonical example of an input type for
                    which this parameter should be True.
    """
    def __init__(self, init_func, types, has_nobj=False, file_scope=False):
        self.init_func = init_func
        self.types = types
        self.has_nobj = has_nobj
        self.file_scope = file_scope

    def getKwargs(self, config, base, logger):
        """Parse the config dict and return the kwargs needed to build the input object.

        The default implementation looks for special class attributes called:

            _req_params     A dict of required parameters and their types.
            _opt_params     A dict of optional parameters and their types.
            _single_params  A list of dicts of parameters such that one and only one of
                            parameter in each dict is required.
            _takes_rng      A bool value saying whether an rng object is required.

        See galsim.Catalog for an example of a class that sets these attributes.

        In addition to the kwargs, we also return a bool value, safe, that indicates whether
        the constructed object will be safe to keep around for multiple files (True) of if
        it will need to be rebuilt for each output file (False).

        @param config       The config dict for this input item
        @param base         The base config dict
        @param logger       If given, a logger object to log progress. [default: None]

        @returns kwargs, safe
        """
        req = self.init_func._req_params
        opt = self.init_func._opt_params
        single = self.init_func._single_params
        kwargs, safe = galsim.config.GetAllParams(config, base, req=req, opt=opt, single=single)
        if self.init_func._takes_rng:
            if 'rng' not in config:
                raise ValueError("No config['rng'] available for %s.type"%key)
            kwargs['rng'] = config['rng']
            safe = False
        return kwargs, safe

    def setupImage(self, input_obj, config, base, logger):
        """Do any necessary setup at the start of each image.

        In the base class, this function does not do anything.  But see PowerSpectrumLoader
        for an example that does require some setup at the start of each image.

        @param input_obj    The input object to use
        @param config       The configuration dict for the input type
        @param base         The base configuration dict.
        @param logger       If given, a logger object to log progress.  [default: None]
        """
        pass

def RegisterInputType(input_type, loader):
    """Register an input type for use by the config apparatus.

    @param input_type       The name of the type in config['input']
    @param loader           A loader object to use for loading in the input object.
                            It should be an instance of InputLoader or a subclass thereof.
    """
    valid_input_types[input_type] = loader

# We define in this file two simple input types: catalog and dict, which read in a Catalog
# or Dict from a file and then can use that to generate values.
RegisterInputType('catalog', InputLoader(galsim.Catalog, ['Catalog'], has_nobj=True))
RegisterInputType('dict', InputLoader(galsim.Dict, ['Dict'], file_scope=True))



# Now define the value generators connected to the catalog and dict input types.
def _GenerateFromCatalog(config, base, value_type):
    """@brief Return a value read from an input catalog
    """
    input_cat = GetInputObj('catalog', config, base, 'Catalog')

    # Setup the indexing sequence if it hasn't been specified.
    # The normal thing with a Catalog is to just use each object in order,
    # so we don't require the user to specify that by hand.  We can do it for them.
    galsim.config.SetDefaultIndex(config, input_cat.getNObjects())

    # Coding note: the and/or bit is equivalent to a C ternary operator:
    #     input_cat.isFits() ? str : int
    # which of course doesn't exist in python.  This does the same thing (so long as the
    # middle item evaluates to true).
    req = { 'col' : input_cat.isFits() and str or int , 'index' : int }
    opt = { 'num' : int }
    kwargs, safe = galsim.config.GetAllParams(config, base, req=req, opt=opt)
    col = kwargs['col']
    index = kwargs['index']

    if value_type is str:
        val = input_cat.get(index, col)
    elif value_type is float:
        val = input_cat.getFloat(index, col)
    elif value_type is int:
        val = input_cat.getInt(index, col)
    elif value_type is bool:
        val = galsim.config.value._GetBoolValue(input_cat.get(index, col))

    #print base['file_num'],'Catalog: col = %s, index = %s, val = %s'%(col, index, val)
    return val, safe


def _GenerateFromDict(config, base, value_type):
    """@brief Return a value read from an input dict.
    """
    input_dict = GetInputObj('dict', config, base, 'Dict')

    req = { 'key' : str }
    opt = { 'num' : int }
    kwargs, safe = galsim.config.GetAllParams(config, base, req=req, opt=opt)
    key = kwargs['key']

    val = input_dict.get(key)

    #print base['file_num'],'Dict: key = %s, val = %s'%(key,val)
    return val, safe

# Register these as valid value types
from .value import RegisterValueType
RegisterValueType('Catalog', _GenerateFromCatalog, [ float, int, bool, str ])
RegisterValueType('Dict', _GenerateFromDict, [ float, int, bool, str ])