/* -*- c++ -*-
 * Copyright (c) 2012-2017 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */
#include "galsim/Image.h"
#define BOOST_TEST_DYN_LINK

#include "galsim/IgnoreWarnings.h"

#define BOOST_NO_CXX11_SMART_PTR
#include <boost/test/unit_test.hpp>
#include <boost/test/test_case_template.hpp>
#include <boost/mpl/list.hpp>

BOOST_AUTO_TEST_SUITE(image_tests);

typedef boost::mpl::list<short, int, float, double, std::complex<double> > test_types;

BOOST_AUTO_TEST_CASE_TEMPLATE( TestImageBasic , T , test_types )
{
    // Tests are designed for these to be odd, but not necessarily equal
    const int ncol=7;  // x ranges from 1 .. ncol
    const int nrow=5;  // y ranges from 1 .. nrow
    T ref_array[nrow*ncol] = {
        // x  ->
        11, 21, 31, 41, 51, 61, 71,  // y
        12, 22, 32, 42, 52, 62, 72,  //
        13, 23, 33, 43, 53, 63, 73,  // |
        14, 24, 34, 44, 54, 64, 74,  // v
        15, 25, 35, 45, 55, 65, 75 };
    // Of course, when viewed as an image, the rows are generally drawn from bottom to top.

    // Check basic constructor from nrow,ncol
    galsim::ImageAlloc<T> im1(ncol,nrow);
    galsim::Bounds<int> bounds(1,ncol,1,nrow);

    BOOST_CHECK(im1.getXMin()==1);
    BOOST_CHECK(im1.getXMax()==ncol);
    BOOST_CHECK(im1.getYMin()==1);
    BOOST_CHECK(im1.getYMax()==nrow);
    BOOST_CHECK(im1.getBounds()==bounds);

    BOOST_CHECK(im1.getData() != NULL);
    BOOST_CHECK(im1.getStride() == ncol);

    // Check alternate constructor from bounds
    galsim::ImageAlloc<T> im2(bounds);
    galsim::ImageView<T> im2_view = im2;
    galsim::ConstImageView<T> im2_cview = im2;

    BOOST_CHECK(im2_view.getXMin()==1);
    BOOST_CHECK(im2_view.getXMax()==ncol);
    BOOST_CHECK(im2_view.getYMin()==1);
    BOOST_CHECK(im2_view.getYMax()==nrow);
    BOOST_CHECK(im2_view.getBounds()==bounds);

    BOOST_CHECK(im2_cview.getXMin()==1);
    BOOST_CHECK(im2_cview.getXMax()==ncol);
    BOOST_CHECK(im2_cview.getYMin()==1);
    BOOST_CHECK(im2_cview.getYMax()==nrow);
    BOOST_CHECK(im2_cview.getBounds()==bounds);

    BOOST_CHECK(im2.getData() != NULL);
    BOOST_CHECK(im2_view.getData() == im2.getData());
    BOOST_CHECK(im2_cview.getData() == im2.getData());
    BOOST_CHECK(im2.getStride() == ncol);
    BOOST_CHECK(im2_view.getStride() == ncol);
    BOOST_CHECK(im2_cview.getStride() == ncol);

    // Check various ways to set and get values
    for (int y=1; y<=nrow; ++y) {
        for (int x=1; x<=ncol; ++x) {
            im1(x,y) = 100 + 10*x + y;
            im2_view(x,y) = 100 + 10*x + y;
        }
    }
    for (int y=1; y<=nrow; ++y) {
        for (int x=1; x<=ncol; ++x) {
            BOOST_CHECK(im1.at(x,y) == T(100+10*x+y));
            BOOST_CHECK(im1.view().at(x,y) == T(100+10*x+y));
            BOOST_CHECK(im2.at(x,y) == T(100+10*x+y));
            BOOST_CHECK(im2_view.at(x,y) == T(100+10*x+y));
            BOOST_CHECK(im2_cview.at(x,y) == T(100+10*x+y));
            im1.setValue(x,y, T(10*x + y));
            im2.setValue(x,y, T(10*x + y));
            BOOST_CHECK(im1(x,y) == T(10*x+y));
            BOOST_CHECK(im1.view()(x,y) == T(10*x+y));
            BOOST_CHECK(im2(x,y) == T(10*x+y));
            BOOST_CHECK(im2_view(x,y) == T(10*x+y));
            BOOST_CHECK(im2_cview(x,y) == T(10*x+y));
        }
    }

    // Check view of given data
    // Note: Our array is on the stack, so we don't have any ownership to pass around.
    //       Hence, use a default shared_ptr constructor.
    galsim::ImageView<T> im3_view(ref_array, boost::shared_ptr<T>(), 1, ncol, bounds);
    galsim::ConstImageView<T> im3_cview(ref_array, boost::shared_ptr<T>(), 1, ncol, bounds);
    for (int y=1; y<=nrow; ++y) {
        for (int x=1; x<=ncol; ++x) {
            BOOST_CHECK(im3_view(x,y) == T(10*x+y));
            BOOST_CHECK(im3_cview(x,y) == T(10*x+y));
        }
    }

    // Check shift ops
    int dx = 31;
    int dy = 16;
    galsim::Position<int> delta(dx,dy);

    im1.shift(delta);
    im2_view.shift(delta);
    im3_cview.shift(delta);
    galsim::Bounds<int> shifted_bounds(1+dx, ncol+dx, 1+dy, nrow+dy);

    BOOST_CHECK(im1.getBounds() == shifted_bounds);
    BOOST_CHECK(im2_view.getBounds() == shifted_bounds);
    BOOST_CHECK(im3_cview.getBounds() == shifted_bounds);
    // Others shouldn't have changed.
    BOOST_CHECK(im2.getBounds() == bounds);
    BOOST_CHECK(im2_cview.getBounds() == bounds);
    BOOST_CHECK(im3_view.getBounds() == bounds);
    for (int y=1; y<=nrow; ++y) {
        for (int x=1; x<=ncol; ++x) {
            BOOST_CHECK(im1(x+dx,y+dy) == T(10*x+y));
            BOOST_CHECK(im2(x,y) == T(10*x+y));
            BOOST_CHECK(im2_view(x+dx,y+dy) == T(10*x+y));
            BOOST_CHECK(im2_cview(x,y) == T(10*x+y));
            BOOST_CHECK(im3_view(x,y) == T(10*x+y));
            BOOST_CHECK(im3_cview(x+dx,y+dy) == T(10*x+y));
        }
    }
}

BOOST_AUTO_TEST_CASE_TEMPLATE( TestImageArith , T , test_types )
{
    const int ncol=7;
    const int nrow=5;
    T ref_array[nrow*ncol] = {
        11, 21, 31, 41, 51, 61, 71,
        12, 22, 32, 42, 52, 62, 72,
        13, 23, 33, 43, 53, 63, 73,
        14, 24, 34, 44, 54, 64, 74,
        15, 25, 35, 45, 55, 65, 75 };
    galsim::Bounds<int> bounds(1,ncol,1,nrow);

    galsim::ConstImageView<T> ref_im(ref_array, boost::shared_ptr<T>(), 1, ncol, bounds);

    galsim::ImageAlloc<T> im1 = ref_im;
    galsim::ImageAlloc<T> im2 = T(2) * ref_im;
    for (int y=1; y<=nrow; ++y) {
        for (int x=1; x<=ncol; ++x) {
            BOOST_CHECK(im2(x,y) == T(2) * ref_im(x,y));
        }
    }

    // Test image addition
    {
        galsim::ImageAlloc<T> im3 = im1 + im2;
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(3) * ref_im(x,y));
            }
        }
        im3.fill(0);
        im3.view() = im1 + im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(3) * ref_im(x,y));
            }
        }
        im3 += im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(5) * ref_im(x,y));
            }
        }
        im3.view() += im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(7) * ref_im(x,y));
            }
        }
    }

    // Test image subtraction
    {
        galsim::ImageAlloc<T> im3 = im1 - im2;
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == -ref_im(x,y));
            }
        }
        im3.fill(0);
        im3.view() = im1 - im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == -ref_im(x,y));
            }
        }
        im3 -= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(-3) * ref_im(x,y));
            }
        }
        im3.view() -= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(-5) * ref_im(x,y));
            }
        }
    }

    // Test binary multiplication
    {
        galsim::ImageAlloc<T> im3 = im1 * im2;
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(2) * ref_im(x,y) * ref_im(x,y));
            }
        }
        im3.fill(0);
        im3.view() = im1 * im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(2) * ref_im(x,y) * ref_im(x,y));
                im3(x,y) /= ref_im(x,y);
            }
        }
        im3 *= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(4) * ref_im(x,y) * ref_im(x,y));
                im3(x,y) /= T(2) * ref_im(x,y);
            }
        }
        im3.view() *= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                // Note: 8 * ref_im(x,y) * ref_im(x,y) exceeds the maximum value for short
                // but 4 * ref_im(x,y) * ref_im(x,y) is ok for ref_im(7,5) = 75
                BOOST_CHECK(im3(x,y) == T(4) * ref_im(x,y) * ref_im(x,y));
            }
        }
    }

    // Test binary division
    {
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                im1(x,y) = T(4) * ref_im(x,y) * ref_im(x,y);
            }
        }
        galsim::ImageAlloc<T> im3 = im1 / im2;
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(2) * ref_im(x,y));
            }
        }
        im3.fill(0);
        im3.view() = im1 / im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(2) * ref_im(x,y));
                im3(x,y) *= ref_im(x,y);
            }
        }
        im3 /= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y));
                im3(x,y) *= T(4) * ref_im(x,y);
            }
        }
        im3.view() /= im2;
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == T(2) * ref_im(x,y));
            }
        }
        im1 = ref_im;
    }

    // Test image scalar addition
    {
        galsim::ImageAlloc<T> im3 = im1 + T(3);
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) + T(3));
            }
        }
        im3.fill(0);
        im3.view() = im1 + T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) + T(3));
            }
        }
        im3 += T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) + T(6));
            }
        }
        im3.view() += T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) + T(9));
            }
        }
    }

    // Test image subtraction
    {
        galsim::ImageAlloc<T> im3 = im1 - T(3);
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) - T(3));
            }
        }
        im3.fill(0);
        im3.view() = im1 - T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) - T(3));
            }
        }
        im3 -= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) - T(6));
            }
        }
        im3.view() -= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) - T(9));
            }
        }
    }

    // Test binary multiplication
    {
        galsim::ImageAlloc<T> im3 = im1 * T(3);
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) * T(3));
            }
        }
        im3.fill(0);
        im3.view() = im1 * T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) * T(3));
            }
        }
        im3 *= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) * T(9));
            }
        }
        im3.view() *= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(im3(x,y) == ref_im(x,y) * T(27));
            }
        }
    }

    // Test binary division
    {
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                im1(x,y) = ref_im(x,y) * T(27);
            }
        }
        galsim::ImageAlloc<T> im3 = im1 / T(3);
        BOOST_CHECK(im3.getBounds() == bounds);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(std::abs(im3(x,y) - ref_im(x,y) * T(9)) < 0.0001);
            }
        }
        im3.fill(0);
        im3.view() = im1 / T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(std::abs(im3(x,y) - ref_im(x,y) * T(9)) < 0.0001);
            }
        }
        im3 /= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(std::abs(im3(x,y) - ref_im(x,y) * T(3)) < 0.0001);
            }
        }
        im3.view() /= T(3);
        for (int y=1; y<=nrow; ++y) {
            for (int x=1; x<=ncol; ++x) {
                BOOST_CHECK(std::abs(im3(x,y) - ref_im(x,y)) < 0.0001);
            }
        }
        im1 = ref_im;
    }
}


BOOST_AUTO_TEST_SUITE_END();
