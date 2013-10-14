# Copyright 2012, 2013 The GalSim developers:
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
#
# GalSim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GalSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GalSim.  If not, see <http://www.gnu.org/licenses/>
#

import os
import time
import galsim

valid_input_types = { 
    # The values are tuples with:
    # - the class name to build.
    # - a list of keys to ignore on the initial creation (e.g. PowerSpectrum has values that are 
    #   used later).
    # - whether the class has a getNObjects method, in which case it also must have a constructor
    #   kwarg nobjects_only to efficiently do only enough to calculate nobjects.
    # See the des module for examples of how to extend this from a module.
    'catalog' : ('Catalog', [], True), 
    'dict' : ('Dict', [], False), 
    'real_catalog' : ('RealGalaxyCatalog', [], True),
    'nfw_halo' : ('NFWHalo', [], False),
    'power_spectrum' : ('PowerSpectrum',
                        # power_spectrum uses these extra parameters for buildGrid later.
                        ['grid_spacing', 'interpolant'], 
                        False),
    'fits_header' : ('FitsHeader', [], False), 
}

valid_output_types = { 
    # The values are tuples with:
    # - the build function to call
    # - a function that merely counts the number of objects that will be built by the function
    # - whether the Builder takes nproc.
    # - whether the Builder takes psf_file_name, weight_file_name, and badpix_file_name.
    # - whether the Builder takes psf_hdu, weight_hdu, and badpix_hdu.
    # See the des module for examples of how to extend this from a module.
    'Fits' : ('BuildFits', 'GetNObjForFits', False, True, True),
    'MultiFits' : ('BuildMultiFits', 'GetNObjForMultiFits', True, True, False),
    'DataCube' : ('BuildDataCube', 'GetNObjForDataCube', True, True, False),
}

def CopyConfig(config):
    """
    If you want to use a config dict for multiprocessing, you need to deep copy
    the gal, psf, and pix fields, since they get cache values that are not picklable.
    If you don't do the deep copy, then python balks when trying to send the updated
    config dict back to the root process.  We do this a few different times, so encapsulate
    the copy semantics once here.
    """
    import copy
    config1 = copy.copy(config)
    if 'gal' in config: config1['gal'] = copy.deepcopy(config['gal'])
    if 'psf' in config: config1['psf'] = copy.deepcopy(config['psf'])
    if 'pix' in config: config1['pix'] = copy.deepcopy(config['pix'])
    if 'image' in config: config1['image'] = copy.deepcopy(config['image'])
    return config1


def ProcessInput(config, file_num=0, logger=None):
    """
    Process the input field, reading in any specified input files or setting up
    any objects that need to be initialized.

    Each item in the above valid_input_types will be built and available at the top level
    of config.  e.g.;
        config['catalog'] = the catalog specified by config.input.catalog, if provided.
        config['real_catalog'] = the catalog specified by config.input.real_catalog, if provided.
        etc.
    """
    config['seq_index'] = file_num
    config['file_num'] = file_num
    # Process the input field (read any necessary input files)
    if 'input' in config:
        input = config['input']
        if not isinstance(input, dict):
            raise AttributeError("config.input is not a dict.")

        # Read all input fields provided and create the corresponding object
        # with the parameters given in the config file.
        #print 'valid_input_types = ',valid_input_types
        for key in [ k for k in valid_input_types.keys() if k in input ]:
            #print 'key = ',key
            fields = input[key]

            # If it's not currently a list, make it a list with one element.
            if not isinstance(fields, list): fields = [ fields ]

            config[key] = []
            for field in fields:
                #print 'field = ',field
                field['type'], ignore = valid_input_types[key][0:2]
                #print 'type, ignore = ',field['type'],ignore
                input_obj = galsim.config.gsobject._BuildSimple(field, key, config, ignore)[0]
                #print 'input_obj = ',input_obj
                if logger and  valid_input_types[key][2]:
                    logger.info('Read %d objects from %s',input_obj.getNObjects(),key)
                # Store input_obj in the config for use by BuildGSObject function.
                config[key].append(input_obj)

        # Check that there are no other attributes specified.
        valid_keys = valid_input_types.keys()
        galsim.config.CheckAllParams(input, 'input', ignore=valid_keys)


def ProcessInputNObjects(config):
    """Process the input field, just enough to determine the number of objects.
    """
    if 'input' in config:
        input = config['input']
        if not isinstance(input, dict):
            raise AttributeError("config.input is not a dict.")

        #print 'valid_input_types = ',valid_input_types
        for key in valid_input_types:
            #print 'key = ',key
            #print 'valid_input_types[key] = ',valid_input_types[key]
            has_nobjects = valid_input_types[key][2]
            if key in input and has_nobjects:
                field = input[key]

                # If it's a list, just use the first one.
                if isinstance(field, list): field = field[0]

                #print 'field = ',field
                type, ignore = valid_input_types[key][0:2]
                #print 'type, ignore = ',type,ignore
                if type in galsim.__dict__:
                    init_func = eval("galsim."+type)
                else:
                    init_func = eval(type)
                kwargs = galsim.config.GetAllParams(field, key, config,
                                                    req = init_func._req_params,
                                                    opt = init_func._opt_params,
                                                    single = init_func._single_params,
                                                    ignore = ignore)[0]
                kwargs['nobjects_only'] = True
                input_obj = init_func(**kwargs)
                #print 'Found nobjects = %d for %s'%(input_obj.getNOjects(),key)
                return input_obj.getNObjects()
    # If didn't find anything, return None.
    return None


def Process(config, logger=None):
    """
    Do all processing of the provided configuration dict.  In particular, this
    function handles processing the output field, calling other functions to
    build and write the specified files.  The input field is processed before
    building each file.
    """

    # If we don't have a root specified yet, we generate it from the current script.
    if 'root' not in config:
        import inspect
        script_name = os.path.basename(
            inspect.getfile(inspect.currentframe())) # script filename (usually with path)
        # Strip off a final suffix if present.
        config['root'] = os.path.splitext(script_name)[0]

    # Make config['output'] exist if it doesn't yet.
    if 'output' not in config:
        config['output'] = {}
    output = config['output']
    if not isinstance(output, dict):
        raise AttributeError("config.output is not a dict.")

    # Get the output type.  Default = Fits
    if 'type' not in output:
        output['type'] = 'Fits' 
    type = output['type']

    # Check that the type is valid
    if type not in valid_output_types:
        raise AttributeError("Invalid output.type=%s."%type)

    # build_func is the function we'll call to build each file.
    build_func = eval(valid_output_types[type][0])

    # nobj_func is the function that builds the nobj_per_file list
    nobj_func = eval(valid_output_types[type][1])

    # can_do_multiple says whether the function can in principal do multiple files
    can_do_multiple = valid_output_types[type][2]

    # extra_file_name says whether the function takes psf_file_name, etc.
    extra_file_name = valid_output_types[type][3]

    # extra_hdu says whether the function takes psf_hdu, etc.
    extra_hdu = valid_output_types[type][4]
    #print 'type = ',type
    #print 'extra_file_name = ',extra_file_name
    #print 'extra_hdu = ',extra_hdu

    # We need to know how many objects we'll need for each file (and each image within each file)
    # to get the indexing correct for any sequence items.  (e.g. random_seed)
    # If we use multiple processors and let the regular sequencing happen, 
    # it will get screwed up by the multi-processing potentially happening out of order.
    # Start with the number of files.
    if 'nfiles' in output:
        nfiles = galsim.config.ParseValue(output, 'nfiles', config, int)[0]
    else:
        nfiles = 1 
    #print 'nfiles = ',nfiles

    # Figure out how many processes we will use for building the files.
    # (If nfiles = 1, but nimages > 1, we'll do the multi-processing at the image stage.)
    if 'nproc' in output:
        nproc = galsim.config.ParseValue(output, 'nproc', config, int)[0]
    else:
        nproc = 1 

    # If set, nproc2 will be passed to the build function to be acted on at that level.
    nproc2 = None
    if nproc > nfiles:
        if nfiles == 1 and can_do_multiple:
            nproc2 = nproc 
            nproc = 1
        else:
            if logger:
                logger.warn(
                    "Trying to use more processes than files: output.nproc=%d, "%nproc +
                    "output.nfiles=%d.  Reducing nproc to %d."%(nfiles,nfiles))
            nproc = nfiles

    if nproc <= 0:
        # Try to figure out a good number of processes to use
        try:
            from multiprocessing import cpu_count
            ncpu = cpu_count()
            if nfiles == 1 and can_do_multiple:
                nproc2 = ncpu # Use this value in BuildImages rather than here.
                nproc = 1
                if logger:
                    logger.debug("ncpu = %d.",ncpu)
            else:
                if ncpu > nfiles:
                    nproc = nfiles
                else:
                    nproc = ncpu
                if logger:
                    logger.info("ncpu = %d.  Using %d processes",ncpu,nproc)
        except:
            if logger:
                logger.warn("config.output.nproc <= 0, but unable to determine number of cpus.")
            nproc = 1
            if logger:
                logger.info("Using %d processes",nproc)
    
    # Set up the multi-process worker function if we're going to need it.
    if nproc > 1:
        # NB: See the function BuildStamps for more verbose comments about how
        # the multiprocessing stuff works.
        from multiprocessing import Process, Queue, current_process

        def worker(input, output):
            import time
            for (kwargs, file_num, file_name) in iter(input.get, 'STOP'):
                #print current_process().name,': worker got: ',file_num,file_name,kwargs
                ProcessInput(kwargs['config'], file_num=file_num)
                #print current_process().name,': After ProcessInput for file ',file_num
                result = build_func(**kwargs)
                #print current_process().name,': result for ',file_num,' = ',result
                output.put( (result, file_num, file_name, current_process().name) )
                #print current_process().name,': put the result for ',file_num,' on output queue'

        # Set up the task list
        task_queue = Queue()

    # Now start working on the files.

    image_num = 0
    obj_num = 0

    extra_keys = [ 'psf', 'weight', 'badpix' ]
    last_file_name = {}
    for key in extra_keys:
        last_file_name[key] = None

    nfiles_use = nfiles
    for file_num in range(nfiles):
        #print 'file, image, obj = ',file_num, image_num, obj_num
        # Set the index for any sequences in the input or output parameters.
        # These sequences are indexed by the file_num.
        # (In image, they are indexed by image_num, and after that by obj_num.)
        config['seq_index'] = file_num
        config['file_num'] = file_num

        # Get the file_name
        if 'file_name' in output:
            SetDefaultExt(output['file_name'],'.fits')
            file_name = galsim.config.ParseValue(output, 'file_name', config, str)[0]
        elif 'root' in config:
            # If a file_name isn't specified, we use the name of the config file + '.fits'
            file_name = config['root'] + '.fits'
        else:
            raise AttributeError(
                "No output.file_name specified and unable to generate it automatically.")
        
        # Prepend a dir to the beginning of the filename if requested.
        if 'dir' in output:
            dir = galsim.config.ParseValue(output, 'dir', config, str)[0]
            if dir and not os.path.isdir(dir): os.makedirs(dir)
            file_name = os.path.join(dir,file_name)
        else:
            dir = None

        # Assign some of the kwargs we know now:
        kwargs = {
            'file_name' : file_name,
            'image_num' : image_num,
            'obj_num' : obj_num
        }
        if nproc2:
            kwargs['nproc'] = nproc2

        kwargs['config'] = CopyConfig(config)

        output = kwargs['config']['output']
        # This also updates nimages or nobjects as needed if they are being automatically
        # set from an input catalog.
        nobj = nobj_func(kwargs['config'],file_num,image_num)

        # nobj is a list of nobj for each image in that file.
        # So len(nobj) = nimages and sum(nobj) is the total number of objects
        # This gets the values of image_num and obj_num ready for the next loop.
        image_num += len(nobj)
        obj_num += sum(nobj)

        # Check if we ought to skip this file
        if ('skip' in output 
                and galsim.config.ParseValue(output, 'skip', config, bool)[0]):
            if logger:
                logger.info('Skipping file %d = %s because output.skip = True',file_num,file_name)
            nfiles_use -= 1
            continue
        if ('noclobber' in output 
                and galsim.config.ParseValue(output, 'noclobber', config, bool)[0]
                and os.path.isfile(file_name)):
            if logger:
                logger.info('Skipping file %d = %s because output.noclobber = True' +
                            ' and file exists',file_num,file_name)
            nfiles_use -= 1
            continue

        # Check if we need to build extra images for write out as well
        for extra_key in [ key for key in extra_keys if key in output ]:
            #print 'extra_key = ',extra_key
            output_extra = output[extra_key]

            output_extra['type'] = 'default'
            req = {}
            single = []
            opt = {}
            ignore = []
            if extra_file_name and extra_hdu:
                single += [ { 'file_name' : str, 'hdu' : int } ]
                opt['dir'] = str
            elif extra_file_name:
                req['file_name'] = str
                opt['dir'] = str
            elif extra_hdu:
                req['hdu'] = int

            if extra_key == 'psf': 
                ignore += ['real_space', 'signal_to_noise']
            if extra_key == 'weight': 
                ignore += ['include_obj_var']
            if 'file_name' in output_extra:
                SetDefaultExt(output_extra['file_name'],'.fits')
            params, safe = galsim.config.GetAllParams(output_extra,extra_key,kwargs['config'],
                                                      req=req, opt=opt, single=single,
                                                      ignore=ignore)

            if 'file_name' in params:
                f = params['file_name']
                if 'dir' in params:
                    dir = params['dir']
                    if dir and not os.path.isdir(dir): os.makedirs(dir)
                # else keep dir from above.
                if dir:
                    f = os.path.join(dir,f)
                # If we already wrote this file, skip it this time around.
                # (Typically this is applicable for psf, where we may only want 1 psf file.)
                #print 'last_file_name for ',key,' = ',last_file_name[key]
                #print 'f = ',f
                if last_file_name[key] == f:
                    #print 'skipping'
                    continue
                #print 'assigning this to kwargs'
                kwargs[ extra_key+'_file_name' ] = f
                last_file_name[key] = f
            elif 'hdu' in params:
                kwargs[ extra_key+'_hdu' ] = params['hdu']
    
        # This is where we actually build the file.
        # If we're doing multiprocessing, we send this information off to the task_queue.
        # Otherwise, we just call build_func.
        if nproc > 1:
            #print 'put task on the queue: ',file_num,file_name,kwargs
            task_queue.put( (kwargs, file_num, file_name) )
        else:
            ProcessInput(kwargs['config'], file_num=file_num, logger=logger)
            # Apparently the logger isn't picklable, so can't send that for nproc > 1
            kwargs['logger'] = logger 
            t = build_func(**kwargs)
            if logger:
                logger.warn('File %d = %s: time = %f sec', file_num, file_name, t)
    #print 'nfiles_use = ',nfiles_use

    # If we're doing multiprocessing, here is the machinery to run through the task_queue
    # and process the results.
    if nproc > 1:
        # Run the tasks
        done_queue = Queue()
        p_list = []
        for j in range(nproc):
            p = Process(target=worker, args=(task_queue, done_queue), name='Process-%d'%(j+1))
            p.start()
            p_list.append(p)

        # Log the results.
        for k in range(nfiles_use):
            t, file_num, file_name, proc = done_queue.get()
            #print 'received results for ',file_num,file_name,t,proc
            if logger:
                logger.warn('%s: File %d = %s: time = %f sec', proc, file_num, file_name, t)

        # Stop the processes
        for j in range(nproc):
            task_queue.put('STOP')
        for j in range(nproc):
            p_list[j].join()
        task_queue.close()

    if logger:
        logger.debug('Done building files')


def BuildFits(file_name, config, logger=None, 
              image_num=0, obj_num=0,
              psf_file_name=None, psf_hdu=None,
              weight_file_name=None, weight_hdu=None,
              badpix_file_name=None, badpix_hdu=None):
    """
    Build a regular fits file as specified in config.
    
    @param file_name         The name of the output file.
    @param config            A configuration dict.
    @param logger            If given, a logger object to log progress.
    @param image_num         If given, the current image_num (default = 0)
    @param obj_num           If given, the current obj_num (default = 0)
    @param psf_file_name     If given, write a psf image to this file
    @param psf_hdu           If given, write a psf image to this hdu in file_name
    @param weight_file_name  If given, write a weight image to this file
    @param weight_hdu        If given, write a weight image to this hdu in file_name
    @param badpix_file_name  If given, write a badpix image to this file
    @param badpix_hdu        If given, write a badpix image to this hdu in file_name

    @return time      Time taken to build file
    """
    t1 = time.time()

    # hdus is a dict with hdus[i] = the item in all_images to put in the i-th hdu.
    hdus = {}
    # The primary hdu is always the main image.
    hdus[0] = 0

    if psf_file_name or psf_hdu:
        make_psf_image = True
        if psf_hdu: 
            if psf_hdu <= 0 or psf_hdu in hdus.keys():
                raise ValueError("psf_hdu = %d is invalid or a duplicate."%pdf_hdu)
            hdus[psf_hdu] = 1
    else:
        make_psf_image = False

    if weight_file_name or weight_hdu:
        make_weight_image = True
        if weight_hdu: 
            if weight_hdu <= 0 or weight_hdu in hdus.keys():
                raise ValueError("weight_hdu = %d is invalid or a duplicate."&weight_hdu)
            hdus[weight_hdu] = 2
    else:
        make_weight_image = False

    if badpix_file_name or badpix_hdu:
        make_badpix_image = True
        if badpix_hdu: 
            if badpix_hdu <= 0 or badpix_hdu in hdus.keys():
                raise ValueError("badpix_hdu = %d is invalid or a duplicate."&badpix_hdu)
            hdus[badpix_hdu] = 3
    else:
        make_badpix_image = False

    for h in range(len(hdus.keys())):
        if h not in hdus.keys():
            raise ValueError("Image for hdu %d not found.  Cannot skip hdus."%h)

    all_images = galsim.config.BuildImage(
            config=config, logger=logger, image_num=image_num, obj_num=obj_num,
            make_psf_image=make_psf_image,
            make_weight_image=make_weight_image,
            make_badpix_image=make_badpix_image)
    # returns a tuple ( main_image, psf_image, weight_image, badpix_image )

    hdulist = []
    for h in range(len(hdus.keys())):
        assert h in hdus.keys()  # Checked for this above.
        hdulist.append(all_images[hdus[h]])
        #print 'Add allimages[%d] to hdulist'%hdus[h]

    # This next line is ok even if the main image is the only one in the list.
    galsim.fits.writeMulti(hdulist, file_name)
    if logger:
        if len(hdus.keys()) == 1:
            logger.debug('Wrote image to fits file %r',file_name)
        else:
            logger.debug('Wrote image (with extra hdus) to multi-extension fits file %r',file_name)

    if psf_file_name:
        all_images[1].write(psf_file_name)
        if logger:
            logger.debug('Wrote psf image to fits file %r',psf_file_name)

    if weight_file_name:
        all_images[2].write(weight_file_name)
        if logger:
            logger.debug('Wrote weight image to fits file %r',weight_file_name)

    if badpix_file_name:
        all_images[3].write(badpix_file_name)
        if logger:
            logger.debug('Wrote badpix image to fits file %r',badpix_file_name)

    t2 = time.time()
    return t2-t1


def BuildMultiFits(file_name, config, nproc=1, logger=None,
                   image_num=0, obj_num=0,
                   psf_file_name=None, weight_file_name=None, badpix_file_name=None):
    """
    Build a multi-extension fits file as specified in config.
    
    @param file_name         The name of the output file.
    @param config            A configuration dict.
    @param nproc             How many processes to use.
    @param logger            If given, a logger object to log progress.
    @param image_num         If given, the current image_num (default = 0)
    @param obj_num           If given, the current obj_num (default = 0)
    @param psf_file_name     If given, write a psf image to this file
    @param weight_file_name  If given, write a weight image to this file
    @param badpix_file_name  If given, write a badpix image to this file

    @return time      Time taken to build file
    """
    t1 = time.time()

    if psf_file_name:
        make_psf_image = True
    else:
        make_psf_image = False

    if weight_file_name:
        make_weight_image = True
    else:
        make_weight_image = False

    if badpix_file_name:
        make_badpix_image = True
    else:
        make_badpix_image = False

    if 'output' not in config or 'nimages' not in config['output']:
        raise AttributeError("Attribute output.nimages is required for output.type = MultiFits")
    nimages = galsim.config.ParseValue(config['output'],'nimages',config,int)[0]

    if nproc > nimages:
        # Only warn if nproc was specifically set, not if it is -1.
        if (logger and
            not ('nproc' in config['output'] and 
                 galsim.config.ParseValue(config['output'],'nproc',config,int)[0] == -1)):
            logger.warn(
                "Trying to use more processes than images: output.nproc=%d, "%nproc +
                "nimages=%d.  Reducing nproc to %d."%(nimages,nimages))
        nproc = nimages

    all_images = galsim.config.BuildImages(
        nimages, config=config, nproc=nproc, logger=logger,
        image_num=image_num, obj_num=obj_num,
        make_psf_image=make_psf_image, 
        make_weight_image=make_weight_image,
        make_badpix_image=make_badpix_image)

    main_images = all_images[0]
    psf_images = all_images[1]
    weight_images = all_images[2]
    badpix_images = all_images[3]

    galsim.fits.writeMulti(main_images, file_name)
    if logger:
        logger.debug('Wrote images to multi-extension fits file %r',file_name)

    if psf_file_name:
        galsim.fits.writeMulti(psf_images, psf_file_name)
        if logger:
            logger.debug('Wrote psf images to multi-extension fits file %r',psf_file_name)

    if weight_file_name:
        galsim.fits.writeMulti(weight_images, weight_file_name)
        if logger:
            logger.debug('Wrote weight images to multi-extension fits file %r',weight_file_name)

    if badpix_file_name:
        galsim.fits.writeMulti(badpix_images, badpix_file_name)
        if logger:
            logger.debug('Wrote badpix images to multi-extension fits file %r',badpix_file_name)


    t2 = time.time()
    return t2-t1


def BuildDataCube(file_name, config, nproc=1, logger=None, 
                  image_num=0, obj_num=0,
                  psf_file_name=None, weight_file_name=None, badpix_file_name=None):
    """
    Build a multi-image fits data cube as specified in config.
    
    @param file_name         The name of the output file.
    @param config            A configuration dict.
    @param nproc             How many processes to use.
    @param logger            If given, a logger object to log progress.
    @param image_num         If given, the current image_num (default = 0)
    @param obj_num           If given, the current obj_num (default = 0)
    @param psf_file_name     If given, write a psf image to this file
    @param weight_file_name  If given, write a weight image to this file
    @param badpix_file_name  If given, write a badpix image to this file

    @return time      Time taken to build file
    """
    t1 = time.time()

    if psf_file_name:
        make_psf_image = True
    else:
        make_psf_image = False

    if weight_file_name:
        make_weight_image = True
    else:
        make_weight_image = False

    if badpix_file_name:
        make_badpix_image = True
    else:
        make_badpix_image = False

    if 'output' not in config or 'nimages' not in config['output']:
        raise AttributeError("Attribute output.nimages is required for output.type = DataCube")
    nimages = galsim.config.ParseValue(config['output'],'nimages',config,int)[0]

    # All images need to be the same size for a data cube.
    # Enforce this by buliding the first image outside the below loop and setting
    # config['image_xsize'] and config['image_ysize'] to be the size of the first image.
    t2 = time.time()
    config1 = CopyConfig(config)
    all_images = galsim.config.BuildImage(
            config=config1, logger=logger, image_num=image_num, obj_num=obj_num,
            make_psf_image=make_psf_image, 
            make_weight_image=make_weight_image,
            make_badpix_image=make_badpix_image)
    obj_num += galsim.config.GetNObjForImage(config, image_num)
    t3 = time.time()
    if logger:
        # Note: numpy shape is y,x
        ys, xs = all_images[0].array.shape
        logger.info('Image %d: size = %d x %d, time = %f sec', image_num, xs, ys, t3-t2)

    # Note: numpy shape is y,x
    image_ysize, image_xsize = all_images[0].array.shape
    config['image_xsize'] = image_xsize
    config['image_ysize'] = image_ysize

    main_images = [ all_images[0] ]
    psf_images = [ all_images[1] ]
    weight_images = [ all_images[2] ]
    badpix_images = [ all_images[3] ]

    if nimages > 1:
        if nproc > nimages-1:
            # Only warn if nproc was specifically set, not if it is -1.
            if (logger and
                not ('nproc' in config['output'] and
                     galsim.config.ParseValue(config['output'],'nproc',config,int)[0] == -1)):
                logger.warn(
                    "Trying to use more processes than (nimages-1): output.nproc=%d, "%nproc +
                    "nimages=%d.  Reducing nproc to %d."%(nimages,nimages-1))
            nproc = nimages-1

        all_images = galsim.config.BuildImages(
            nimages-1, config=config, nproc=nproc, logger=logger,
            image_num=image_num+1, obj_num=obj_num,
            make_psf_image=make_psf_image,
            make_weight_image=make_weight_image,
            make_badpix_image=make_badpix_image)

        main_images += all_images[0]
        psf_images += all_images[1]
        weight_images += all_images[2]
        badpix_images += all_images[3]

    galsim.fits.writeCube(main_images, file_name)
    if logger:
        logger.debug('Wrote image to fits data cube %r',file_name)

    if psf_file_name:
        galsim.fits.writeCube(psf_images, psf_file_name)
        if logger:
            logger.debug('Wrote psf images to fits data cube %r',psf_file_name)

    if weight_file_name:
        galsim.fits.writeCube(weight_images, weight_file_name)
        if logger:
            logger.debug('Wrote weight images to fits data cube %r',weight_file_name)

    if badpix_file_name:
        galsim.fits.writeCube(badpix_images, badpix_file_name)
        if logger:
            logger.debug('Wrote badpix images to fits data cube %r',badpix_file_name)

    t4 = time.time()
    return t4-t1

def GetNObjForFits(config, file_num, image_num):
    ignore = [ 'file_name', 'dir', 'nfiles', 'psf', 'weight', 'badpix', 'nproc',
               'skip', 'noclobber' ]
    galsim.config.CheckAllParams(config['output'], 'output', ignore=ignore)
    try : 
        nobj = [ galsim.config.GetNObjForImage(config, image_num) ]
    except ValueError : # (This may be raised if something needs the input stuff)
        ProcessInput(config, file_num=file_num)
        nobj = [ galsim.config.GetNObjForImage(config, image_num) ]
    return nobj
    
def GetNObjForMultiFits(config, file_num, image_num):
    ignore = [ 'file_name', 'dir', 'nfiles', 'psf', 'weight', 'badpix', 'nproc', 
               'skip', 'noclobber' ]
    req = { 'nimages' : int }
    # Allow nimages to be automatic based on input catalog if image type is Single
    if ( 'nimages' not in config['output'] and 
         ( 'image' not in config or 'type' not in config['image'] or 
           config['image']['type'] == 'Single' ) ):
        nobj = ProcessInputNObjects(config)
        if nobj:
            config['output']['nimages'] = ProcessInputNObjects(config)
    params = galsim.config.GetAllParams(config['output'],'output',config,ignore=ignore,req=req)[0]
    config['seq_index'] = file_num
    config['file_num'] = file_num
    nimages = params['nimages']
    try :
        nobj = [ galsim.config.GetNObjForImage(config, image_num+j) for j in range(nimages) ]
    except ValueError : # (This may be raised if something needs the input stuff)
        ProcessInput(config, file_num=file_num)
        nobj = [ galsim.config.GetNObjForImage(config, image_num+j) for j in range(nimages) ]
    return nobj

def GetNObjForDataCube(config, file_num, image_num):
    ignore = [ 'file_name', 'dir', 'nfiles', 'psf', 'weight', 'badpix', 'nproc',
               'skip', 'noclobber' ]
    req = { 'nimages' : int }
    # Allow nimages to be automatic based on input catalog if image type is Single
    if ( 'nimages' not in config['output'] and 
         ( 'image' not in config or 'type' not in config['image'] or 
           config['image']['type'] == 'Single' ) ):
        nobj = ProcessInputNObjects(config)
        if nobj:
            config['output']['nimages'] = ProcessInputNObjects(config)
    params = galsim.config.GetAllParams(config['output'],'output',config,ignore=ignore,req=req)[0]
    config['seq_index'] = file_num
    config['file_num'] = file_num
    nimages = params['nimages']
    try :
        nobj = [ galsim.config.GetNObjForImage(config, image_num+j) for j in range(nimages) ]
    except ValueError : # (This may be raised if something needs the input stuff)
        ProcessInput(config, file_num=file_num)
        nobj = [ galsim.config.GetNObjForImage(config, image_num+j) for j in range(nimages) ]
    return nobj
 
def SetDefaultExt(config, ext):
    """
    Some items have a default extension for a NumberedFile type.
    """
    if ( isinstance(config,dict) and 'type' in config and 
         config['type'] == 'NumberedFile' and 'ext' not in config ):
        config['ext'] = ext

