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

import galsim

from . import _galsim
from .gsobject import GSObject


class Exponential(GSObject):
    """A class describing an exponential profile.

    Surface brightness profile with I(r) ~ exp[-r/scale_radius].  This is a special case of
    the Sersic profile, but is given a separate class since the Fourier transform has closed form
    and can be generated without lookup tables.

    Initialization
    --------------

    An Exponential can be initialized using one (and only one) of two possible size parameters:
    `scale_radius` or `half_light_radius`.  Exactly one of these two is required.

    @param half_light_radius  The half-light radius of the profile.  Typically given in arcsec.
                            [One of `scale_radius` or `half_light_radius` is required.]
    @param scale_radius     The scale radius of the profile.  Typically given in arcsec.
                            [One of `scale_radius` or `half_light_radius` is required.]
    @param flux             The flux (in photons/cm^2/s) of the profile. [default: 1]
    @param gsparams         An optional GSParams argument.  See the docstring for GSParams for
                            details. [default: None]

    Methods and Properties
    ----------------------

    In addition to the usual GSObject methods, Exponential has the following access properties:

        >>> r0 = exp_obj.scale_radius
        >>> hlr = exp_obj.half_light_radius
    """
    _req_params = {}
    _opt_params = { "flux" : float }
    _single_params = [ { "scale_radius" : float , "half_light_radius" : float } ]
    _takes_rng = False

    # The half-light radius Factor is not analytic, but can be calculated by iterative solution
    # of the equation:
    #     (re / r0) = ln[(re / r0) + 1] + ln(2)
    _hlr_factor = 1.6783469900166605

    def __init__(self, half_light_radius=None, scale_radius=None, flux=1., gsparams=None):
        if half_light_radius is not None:
            if scale_radius is not None:
                raise TypeError(
                        "Only one of scale_radius and half_light_radius may be " +
                        "specified for Exponential")
            else:
                scale_radius = half_light_radius / Exponential._hlr_factor
        elif scale_radius is None:
                raise TypeError(
                        "Either scale_radius or half_light_radius must be " +
                        "specified for Exponential")
        self._gsparams = galsim.GSParams.check(gsparams)
        self._sbp = _galsim.SBExponential(scale_radius, flux, self.gsparams._gsp)

    @property
    def scale_radius(self): return self._sbp.getScaleRadius()
    @property
    def half_light_radius(self): return self.scale_radius * Exponential._hlr_factor

    def __eq__(self, other):
        return (isinstance(other, galsim.Exponential) and
                self.scale_radius == other.scale_radius and
                self.flux == other.flux and
                self.gsparams == other.gsparams)

    def __hash__(self):
        return hash(("galsim.Exponential", self.scale_radius, self.flux, self.gsparams))

    def __repr__(self):
        return 'galsim.Exponential(scale_radius=%r, flux=%r, gsparams=%r)'%(
            self.scale_radius, self.flux, self.gsparams)

    def __str__(self):
        s = 'galsim.Exponential(scale_radius=%s'%self.scale_radius
        if self.flux != 1.0:
            s += ', flux=%s'%self.flux
        s += ')'
        return s

_galsim.SBExponential.__getinitargs__ = lambda self: (
        self.getScaleRadius(), self.getFlux(), self.getGSParams())
