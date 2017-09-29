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

imgdir = os.path.join(".", "SBProfile_comparison_images") # Directory containing the reference
                                                          # images.

try:
    import galsim
except ImportError:
    path, filename = os.path.split(__file__)
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

# Some standard values for testing
test_flux = 1.8
test_hlr = 1.8
test_sigma = 1.8
test_scale = 1.8


@timer
def test_fourier_sqrt():
    """Test that the FourierSqrt operator is the inverse of auto-convolution.
    """
    dx = 0.4
    myImg1 = galsim.ImageF(80,80, scale=dx)
    myImg1.setCenter(0,0)
    myImg2 = galsim.ImageF(80,80, scale=dx)
    myImg2.setCenter(0,0)

    # Test trivial case, where we could (but don't) analytically collapse the
    # chain of profiles by recognizing that FourierSqrt is the inverse of
    # AutoConvolve.
    psf = galsim.Moffat(beta=3.8, fwhm=1.3, flux=5)
    psf.drawImage(myImg1, method='no_pixel')
    sqrt1 = galsim.FourierSqrt(psf)
    psf2 = galsim.AutoConvolve(sqrt1)
    np.testing.assert_almost_equal(psf.stepk, psf2.stepk)
    psf2.drawImage(myImg2, method='no_pixel')
    printval(myImg1, myImg2)
    np.testing.assert_array_almost_equal(
            myImg1.array, myImg2.array, 4,
            err_msg="Moffat sqrt convolved with self disagrees with original")

    check_basic(sqrt1, "FourierSqrt", do_x=False)

    # Test non-trivial case where we compare (in Fourier space) sqrt(a*a + b*b + 2*a*b) against (a + b)
    a = galsim.Moffat(beta=3.8, fwhm=1.3, flux=5)
    a.shift(dx=0.5, dy=-0.3)  # need nonzero centroid to test
    b = galsim.Moffat(beta=2.5, fwhm=1.6, flux=3)
    check = galsim.Sum([a, b])
    sqrt = galsim.FourierSqrt(
        galsim.Sum([
            galsim.AutoConvolve(a),
            galsim.AutoConvolve(b),
            2*galsim.Convolve([a, b])
        ])
    )
    np.testing.assert_almost_equal(check.stepk, sqrt.stepk)
    check.drawImage(myImg1, method='no_pixel')
    sqrt.drawImage(myImg2, method='no_pixel')
    np.testing.assert_almost_equal(check.centroid.x, sqrt.centroid.x)
    np.testing.assert_almost_equal(check.centroid.y, sqrt.centroid.y)
    np.testing.assert_almost_equal(check.flux, sqrt.flux)
    np.testing.assert_almost_equal(check.xValue(check.centroid), check.max_sb)
    print('check.max_sb = ',check.max_sb)
    print('sqrt.max_sb = ',sqrt.max_sb)
    # This isn't super accurate...
    np.testing.assert_allclose(check.max_sb, sqrt.max_sb, rtol=0.1)
    printval(myImg1, myImg2)
    np.testing.assert_array_almost_equal(
            myImg1.array, myImg2.array, 4,
            err_msg="Fourier square root of expanded square disagrees with original")

    # Check picklability
    do_pickle(sqrt1, lambda x: x.drawImage(method='no_pixel'))
    do_pickle(sqrt1)

    # Should raise an exception for invalid arguments
    try:
        np.testing.assert_raises(TypeError, galsim.FourierSqrt)
        np.testing.assert_raises(TypeError, galsim.FourierSqrt, myImg1)
        np.testing.assert_raises(TypeError, galsim.FourierSqrt, [psf])
        np.testing.assert_raises(TypeError, galsim.FourierSqrt, psf, psf)
        np.testing.assert_raises(TypeError, galsim.FourierSqrt, psf, real_space=False)
        np.testing.assert_raises(TypeError, galsim.FourierSqrtProfile)
        np.testing.assert_raises(TypeError, galsim.FourierSqrtProfile, myImg1)
        np.testing.assert_raises(TypeError, galsim.FourierSqrtProfile, [psf])
        np.testing.assert_raises(TypeError, galsim.FourierSqrtProfile, psf, psf)
        np.testing.assert_raises(TypeError, galsim.FourierSqrtProfile, psf, real_space=False)
    except ImportError:
        pass

if __name__ == "__main__":
    test_fourier_sqrt()