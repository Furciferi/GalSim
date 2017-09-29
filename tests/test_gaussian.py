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
import numpy as np
import os
import sys

from galsim_test_helpers import *

path, filename = os.path.split(__file__)
imgdir = os.path.join(path, "SBProfile_comparison_images") # Directory containing the reference
                                                           # images.

try:
    import galsim
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim


# These are the default GSParams used when unspecified.  We'll check that specifying
# these explicitly produces the same results.
default_params = galsim.GSParams(
        minimum_fft_size = 128,
        maximum_fft_size = 4096,
        folding_threshold = 5.e-3,
        maxk_threshold = 1.e-3,
        kvalue_accuracy = 1.e-5,
        xvalue_accuracy = 1.e-5,
        shoot_accuracy = 1.e-5,
        realspace_relerr = 1.e-4,
        realspace_abserr = 1.e-6,
        integration_relerr = 1.e-6,
        integration_abserr = 1.e-8)


@timer
def test_gaussian():
    """Test the generation of a specific Gaussian profile against a known result.
    """
    savedImg = galsim.fits.read(os.path.join(imgdir, "gauss_1.fits"))
    savedImg.setCenter(0,0)
    dx = 0.2
    myImg = galsim.ImageF(savedImg.bounds, scale=dx)
    myImg.setCenter(0,0)

    gauss = galsim.Gaussian(flux=1, sigma=1)
    # Reference images were made with old centering, which is equivalent to use_true_center=False.
    myImg = gauss.drawImage(myImg, scale=dx, method="sb", use_true_center=False)
    np.testing.assert_array_almost_equal(
            myImg.array, savedImg.array, 5,
            err_msg="Using GSObject Gaussian disagrees with expected result")
    np.testing.assert_almost_equal(
            myImg.array.sum(dtype=float) *dx**2, myImg.added_flux, 5,
            err_msg="Gaussian profile GSObject::draw returned wrong added_flux")

    # Check a non-square image
    print(myImg.bounds)
    recImg = galsim.ImageF(45,66)
    recImg.setCenter(0,0)
    recImg = gauss.drawImage(recImg, scale=dx, method="sb", use_true_center=False)
    np.testing.assert_array_almost_equal(
            recImg[savedImg.bounds].array, savedImg.array, 5,
            err_msg="Drawing Gaussian on non-square image disagrees with expected result")
    np.testing.assert_almost_equal(
            recImg.array.sum(dtype=float) *dx**2, recImg.added_flux, 5,
            err_msg="Gaussian profile GSObject::draw on non-square image returned wrong added_flux")

    # Check with default_params
    gauss = galsim.Gaussian(flux=1, sigma=1, gsparams=default_params)
    gauss.drawImage(myImg,scale=0.2, method="sb", use_true_center=False)
    np.testing.assert_array_almost_equal(
            myImg.array, savedImg.array, 5,
            err_msg="Using GSObject Gaussian with default_params disagrees with expected result")
    gauss = galsim.Gaussian(flux=1, sigma=1, gsparams=galsim.GSParams())
    gauss.drawImage(myImg,scale=0.2, method="sb", use_true_center=False)
    np.testing.assert_array_almost_equal(
            myImg.array, savedImg.array, 5,
            err_msg="Using GSObject Gaussian with GSParams() disagrees with expected result")

    # Use non-unity values.
    gauss = galsim.Gaussian(flux=1.7, sigma=2.3)
    check_basic(gauss, "Gaussian")

    # Test photon shooting.
    do_shoot(gauss,myImg,"Gaussian")

    # Test kvalues
    do_kvalue(gauss,myImg,"Gaussian")

    # Check picklability
    do_pickle(galsim.GSParams())  # Check GSParams explicitly here too.
    do_pickle(galsim.GSParams(
        minimum_fft_size = 12,
        maximum_fft_size = 40,
        folding_threshold = 1.e-1,
        maxk_threshold = 2.e-1,
        kvalue_accuracy = 3.e-1,
        xvalue_accuracy = 4.e-1,
        shoot_accuracy = 5.e-1,
        realspace_relerr = 6.e-1,
        realspace_abserr = 7.e-1,
        integration_relerr = 8.e-1,
        integration_abserr = 9.e-1))
    do_pickle(gauss, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(gauss)

    # Should raise an exception if >=2 radii are provided.
    try:
        np.testing.assert_raises(TypeError, galsim.Gaussian, sigma=3, half_light_radius=1, fwhm=2)
        np.testing.assert_raises(TypeError, galsim.Gaussian, half_light_radius=1, fwhm=2)
        np.testing.assert_raises(TypeError, galsim.Gaussian, sigma=3, fwhm=2)
        np.testing.assert_raises(TypeError, galsim.Gaussian, sigma=3, half_light_radius=1)
    except ImportError:
        pass

    # Finally, test the noise property for things that don't have any noise set.
    assert gauss.noise is None
    # And accessing the attribute from the class should indicate that it is a lazyproperty
    assert 'lazy_property' in str(galsim.GSObject.noise)


@timer
def test_gaussian_properties():
    """Test some basic properties of the Gaussian profile.
    """
    test_flux = 17.9
    test_sigma = 1.8
    gauss = galsim.Gaussian(flux=test_flux, sigma=test_sigma)
    # Check that we are centered on (0, 0)
    cen = galsim.PositionD(0, 0)
    np.testing.assert_equal(gauss.centroid(), cen)
    # Check Fourier properties
    np.testing.assert_almost_equal(gauss.maxK(), 3.7169221888498383 / test_sigma)
    np.testing.assert_almost_equal(gauss.stepK(), 0.533644625664 / test_sigma)
    np.testing.assert_almost_equal(gauss.kValue(cen), (1+0j) * test_flux)
    np.testing.assert_almost_equal(gauss.flux, test_flux)
    import math
    np.testing.assert_almost_equal(gauss.xValue(cen), 1./(2.*math.pi) * test_flux / test_sigma**2)
    np.testing.assert_almost_equal(gauss.xValue(cen), gauss.maxSB())
    # Check input flux vs output flux
    for inFlux in np.logspace(-2, 2, 10):
        gauss = galsim.Gaussian(flux=inFlux, sigma=2.)
        outFlux = gauss.flux
        np.testing.assert_almost_equal(outFlux, inFlux)


@timer
def test_gaussian_radii():
    """Test initialization of Gaussian with different types of radius specification.
    """
    import math
    test_hlr = 1.8
    test_fwhm = 1.8
    test_sigma = 1.8
    test_flux = 1.8

    # Test constructor using half-light-radius:
    test_gal = galsim.Gaussian(flux = 1., half_light_radius = test_hlr)
    hlr_sum = radial_integrate(test_gal, 0., test_hlr)
    print('hlr_sum = ',hlr_sum)
    np.testing.assert_almost_equal(
            hlr_sum, 0.5, decimal=4,
            err_msg="Error in Gaussian constructor with half-light radius")

    # test that fwhm provides correct FWHM
    got_fwhm = test_gal.fwhm
    test_fwhm_ratio = (test_gal.xValue(galsim.PositionD(.5 * got_fwhm, 0.)) /
                       test_gal.xValue(galsim.PositionD(0., 0.)))
    print('fwhm ratio = ', test_fwhm_ratio)
    np.testing.assert_almost_equal(
            test_fwhm_ratio, 0.5, decimal=4,
            err_msg="Error in FWHM for Gaussian initialized with half-light radius")
    np.testing.assert_equal(
            test_gal.fwhm, got_fwhm,
            err_msg="Gaussian fwhm not equivalent to fwhm")

    # test that sigma provides correct sigma
    got_sigma = test_gal.sigma
    test_sigma_ratio = (test_gal.xValue(galsim.PositionD(got_sigma, 0.)) /
                        test_gal.xValue(galsim.PositionD(0., 0.)))
    print('sigma ratio = ', test_sigma_ratio)
    np.testing.assert_almost_equal(
            test_sigma_ratio, math.exp(-0.5), decimal=4,
            err_msg="Error in sigma for Gaussian initialized with half-light radius")
    np.testing.assert_equal(
            test_gal.sigma, got_sigma,
            err_msg="Gaussian sigma not equivalent to sigma property")

    # Test constructor using sigma:
    test_gal = galsim.Gaussian(flux = 1., sigma = test_sigma)
    center = test_gal.xValue(galsim.PositionD(0,0))
    ratio = test_gal.xValue(galsim.PositionD(test_sigma,0)) / center
    print('sigma ratio = ',ratio)
    np.testing.assert_almost_equal(
            ratio, np.exp(-0.5), decimal=4,
            err_msg="Error in Gaussian constructor with sigma")

    # then test that image indeed has the correct HLR properties when radially integrated
    got_hlr = test_gal.half_light_radius
    hlr_sum = radial_integrate(test_gal, 0., got_hlr)
    print('hlr_sum (profile initialized with sigma) = ',hlr_sum)
    np.testing.assert_almost_equal(
            hlr_sum, 0.5, decimal=4,
            err_msg="Error in half light radius for Gaussian initialized with sigma.")
    np.testing.assert_equal(
            test_gal.half_light_radius, got_hlr,
            err_msg="Gaussian half_light_radius not equivalent to half_light_radius property")

    # test that fwhm method provides correct FWHM
    got_fwhm = test_gal.fwhm
    test_fwhm_ratio = (test_gal.xValue(galsim.PositionD(.5 * got_fwhm, 0.)) /
                       test_gal.xValue(galsim.PositionD(0., 0.)))
    print('fwhm ratio = ', test_fwhm_ratio)
    np.testing.assert_almost_equal(
            test_fwhm_ratio, 0.5, decimal=4,
            err_msg="Error in FWHM for Gaussian initialized with sigma.")
    np.testing.assert_equal(
            test_gal.fwhm, got_fwhm,
            err_msg="Gaussian fwhm not equivalent to fwhm property")

    # Test constructor using FWHM:
    test_gal = galsim.Gaussian(flux = 1., fwhm = test_fwhm)
    center = test_gal.xValue(galsim.PositionD(0,0))
    ratio = test_gal.xValue(galsim.PositionD(test_fwhm/2.,0)) / center
    print('fwhm ratio = ',ratio)
    np.testing.assert_almost_equal(
            ratio, 0.5, decimal=4,
            err_msg="Error in Gaussian constructor with fwhm")

    # then test that image indeed has the correct HLR properties when radially integrated
    got_hlr = test_gal.half_light_radius
    hlr_sum = radial_integrate(test_gal, 0., got_hlr)
    print('hlr_sum (profile initialized with fwhm) = ',hlr_sum)
    np.testing.assert_almost_equal(
            hlr_sum, 0.5, decimal=4,
            err_msg="Error in half light radius for Gaussian initialized with FWHM.")
    np.testing.assert_equal(
            test_gal.half_light_radius, got_hlr,
            err_msg="Gaussian half_light_radius not equivalent to half_light_radius property")

    # test that sigma provides correct sigma
    got_sigma = test_gal.sigma
    test_sigma_ratio = (test_gal.xValue(galsim.PositionD(got_sigma, 0.)) /
                        test_gal.xValue(galsim.PositionD(0., 0.)))
    print('sigma ratio = ', test_sigma_ratio)
    np.testing.assert_almost_equal(
            test_sigma_ratio, math.exp(-0.5), decimal=4,
            err_msg="Error in sigma for Gaussian initialized with FWHM.")

    # Check that the getters don't work after modifying the original.
    # Note: I test all the modifiers here.  For the rest of the profile types, I'll
    # just confirm that it is true of shear.  I don't think that has any chance
    # of missing anything.
    test_gal_flux1 = test_gal * 3.
    try:
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux1, "fwhm")
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux1, "half_light_radius")
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux1, "sigma")
    except ImportError:
        # assert_raises requires nose, which we don't want to force people to install.
        # So if they are running this without nose, we just skip these tests.
        pass

    test_gal_flux2 = test_gal.withFlux(3.)
    try:
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux2, "fwhm")
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux2, "half_light_radius")
        np.testing.assert_raises(AttributeError, getattr, test_gal_flux2, "sigma")
    except ImportError:
        pass

    test_gal_shear = test_gal.shear(g1=0.3, g2=0.1)
    try:
        np.testing.assert_raises(AttributeError, getattr, test_gal_shear, "fwhm")
        np.testing.assert_raises(AttributeError, getattr, test_gal_shear, "half_light_radius")
        np.testing.assert_raises(AttributeError, getattr, test_gal_shear, "sigma")
    except ImportError:
        pass

    test_gal_rot = test_gal.rotate(theta = 0.5 * galsim.radians)
    try:
        np.testing.assert_raises(AttributeError, getattr, test_gal_rot, "fwhm")
        np.testing.assert_raises(AttributeError, getattr, test_gal_rot, "half_light_radius")
        np.testing.assert_raises(AttributeError, getattr, test_gal_rot, "sigma")
    except ImportError:
        pass

    test_gal_shift = test_gal.shift(dx=0.11, dy=0.04)
    try:
        np.testing.assert_raises(AttributeError, getattr, test_gal_shift, "fwhm")
        np.testing.assert_raises(AttributeError, getattr, test_gal_shift, "half_light_radius")
        np.testing.assert_raises(AttributeError, getattr, test_gal_shift, "sigma")
    except ImportError:
        pass


@timer
def test_gaussian_flux_scaling():
    """Test flux scaling for Gaussian.
    """
    # decimal point to go to for parameter value comparisons
    param_decimal = 12
    test_flux = 17.9
    test_sigma = 1.8

    # init with sigma and flux only (should be ok given last tests)
    obj = galsim.Gaussian(sigma=test_sigma, flux=test_flux)
    obj *= 2.
    np.testing.assert_almost_equal(
        obj.flux, test_flux * 2., decimal=param_decimal,
        err_msg="Flux param inconsistent after __imul__.")
    obj = galsim.Gaussian(sigma=test_sigma, flux=test_flux)
    obj /= 2.
    np.testing.assert_almost_equal(
        obj.flux, test_flux / 2., decimal=param_decimal,
        err_msg="Flux param inconsistent after __idiv__.")
    obj = galsim.Gaussian(sigma=test_sigma, flux=test_flux)
    obj2 = obj * 2.
    # First test that original obj is unharmed...
    np.testing.assert_almost_equal(
        obj.flux, test_flux, decimal=param_decimal,
        err_msg="Flux param inconsistent after __rmul__ (original).")
    # Then test new obj2 flux
    np.testing.assert_almost_equal(
        obj2.flux, test_flux * 2., decimal=param_decimal,
        err_msg="Flux param inconsistent after __rmul__ (result).")
    obj = galsim.Gaussian(sigma=test_sigma, flux=test_flux)
    obj2 = 2. * obj
    # First test that original obj is unharmed...
    np.testing.assert_almost_equal(
        obj.flux, test_flux, decimal=param_decimal,
        err_msg="Flux param inconsistent after __mul__ (original).")
    # Then test new obj2 flux
    np.testing.assert_almost_equal(
        obj2.flux, test_flux * 2., decimal=param_decimal,
        err_msg="Flux param inconsistent after __mul__ (result).")
    obj = galsim.Gaussian(sigma=test_sigma, flux=test_flux)
    obj2 = obj / 2.
    # First test that original obj is unharmed...
    np.testing.assert_almost_equal(
        obj.flux, test_flux, decimal=param_decimal,
        err_msg="Flux param inconsistent after __div__ (original).")
    # Then test new obj2 flux
    np.testing.assert_almost_equal(
        obj2.flux, test_flux / 2., decimal=param_decimal,
        err_msg="Flux param inconsistent after __div__ (result).")


@timer
def test_ne():
    """Test base.py GSObjects for not-equals."""
    # Define some universal gsps
    gsp = galsim.GSParams(maxk_threshold=1.1e-3, folding_threshold=5.1e-3)

    # The following should all test unequal:
    gals = [galsim.Gaussian(sigma=1.0),
            galsim.Gaussian(sigma=1.1),
            galsim.Gaussian(fwhm=1.0),
            galsim.Gaussian(half_light_radius=1.0),
            galsim.Gaussian(half_light_radius=1.1),
            galsim.Gaussian(sigma=1.2, flux=1.0),
            galsim.Gaussian(sigma=1.2, flux=1.1),
            galsim.Gaussian(sigma=1.2, gsparams=gsp)]
    # Check that setifying doesn't remove any duplicate items.
    all_obj_diff(gals)


if __name__ == "__main__":
    test_gaussian()
    test_gaussian_properties()
    test_gaussian_radii()
    test_gaussian_flux_scaling()
    test_ne()