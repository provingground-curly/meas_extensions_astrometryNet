#!/usr/bin/env python

"""
Tests of the GlobalAstrometrySolution interface, without actually trying to solve a field.
Solving a field can be slow, but these tests run quickly, so are easier to run to test
small bits of the class. For an end-to-end test, use testGAS.py
"""


import re
import os
import math
import sys
import unittest

import eups
import lsst.pex.policy as pexPolicy
import lsst.afw.image as afwImage
import lsst.meas.astrom.net as net
import lsst.utils.tests as utilsTests
import lsst.afw.image as afwImg
import lsst.afw.detection.detectionLib as detect
import lsst.pex.exceptions as pexExcept
try:
    type(verbose)
except NameError:
    verbose = 0

verbose=True


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def loadXYFromFile(filename):
    """Load a list of positions from a file"""
    f= open(filename)
    
    s1=detect.SourceSet()
    i=0
    for line in f:
        #Split the row into an array
        line = re.sub("^\s+", "", line)
        elts = re.split("\s+", line)
        
        #Swig requires floats, but elts is an array of strings
        x=float(elts[0])
        y=float(elts[1])
        flux=float(elts[2])

        source = detect.Source()

        source.setSourceId(i)
        source.setXAstrom(x); source.setXAstromErr(0.1)
        source.setYAstrom(y); source.setYAstromErr(0.1)
        source.setPsfFlux(flux)

        s1.append(source)
        
        i=i + 1
    f.close()
    
    return s1


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


class GlobalAstrometrySolutionTest(unittest.TestCase):
    """These tests work the interface to the class, but don't actually try to solve anything"""

    def setUp(self):
        eupsObj = eups.Eups()

        ok, version, reason = eupsObj.setup("astrometry_net_data", versionName="cfhttemplate")
        if not ok:
            raise ValueError("Couldn't set up cfht version of astrometry_net_data: %s" %(reason))
        
        metaFile = os.path.join(eups.productDir("astrometry_net_data"), "metadata.paf")
        
        self.gas = net.GlobalAstrometrySolution(metaFile)

    def tearDown(self):
        del self.gas

    
    def testSetStarlist(self):
        starlistFile = os.path.join(eups.productDir("meas_astrom"), "tests", "gd66.xy.txt")
        starlist = loadXYFromFile(starlistFile)
        
        starlist = starlist[:10]
        
        numStars = len(starlist)
        starlist[0].setXAstrom( float("nan"))   #Nan
        starlist[1].setYAstrom( float("nan"))   #Nan
        starlist[2].setPsfFlux( float("nan"))   #Nan

        starlist[3].setXAstrom( -1.)   #-ve
        starlist[4].setYAstrom( -1.)   #-ve
        starlist[5].setPsfFlux( -1. )   #-ve
        
        self.gas.setStarlist(starlist)
        
        #The first six objects should be skipped over, so this command should
        #raise an exception because we're setting the starlist to be too big.
        self.assertRaises(pexExcept.LsstCppException, 
                self.gas.setNumBrightObjects, (numStars-5))


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


def suite():
    """Returns a suite containing all the test cases in this module."""
    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(GlobalAstrometrySolutionTest)

    return unittest.TestSuite(suites)

def run(exit=False):
    """Run the tests"""
    utilsTests.run(suite(), exit)
 
if __name__ == "__main__":
    verbose = 3
    run(True)