# Copyright (c) 2012-2017 by the GalSim developers team on GitHub
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

from __future__ import print_function

import galsim

# This file adds input type fits_header and value type FitsHeader.

# The FitsHeader doesn't need anything special other than registration as a valid input type.
from .input import RegisterInputType, InputLoader
RegisterInputType('fits_header', InputLoader(galsim.FitsHeader, file_scope=True))

def _GenerateFromFitsHeader(config, base, value_type):
    """@brief Return a value read from a FITS header
    """
    header = galsim.config.GetInputObj('fits_header', config, base, 'FitsHeader')

    req = { 'key' : str }
    opt = { 'num' : int }
    kwargs, safe = galsim.config.GetAllParams(config, base, req=req, opt=opt)
    key = kwargs['key']

    val = header.get(key)

    #print(base['file_num'],'Header: key = %s, val = %s'%(key,val))
    return val, safe

# Register this as a valid value type
from .value import RegisterValueType
RegisterValueType('FitsHeader', _GenerateFromFitsHeader, [ float, int, bool, str ],
                  input_type='fits_header')
