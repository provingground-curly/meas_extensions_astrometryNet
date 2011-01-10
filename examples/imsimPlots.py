from optparse import OptionParser
from math import hypot

import lsst.pex.policy as policy
import lsst.meas.astrom as measAstrom
import lsst.afw.image as afwImage
from lsst.pex.logging import Log
from lsst.afw.coord import DEGREES
import lsst.meas.algorithms.utils as maUtils

import wcsPlots
import imsimUtils

import numpy as np

def main():
    parser = OptionParser()
    imsimUtils.addOptions(parser)
    parser.add_option('--fixup', dest='fixup', action='store_true', default=False, help='Fix up problems with PT1.1-current outputs')
    parser.add_option('--photometry', '-P', dest='dophotometry', action='store_true', default=False, help='Make photometry plot?')
    parser.add_option('--corr', '-C', dest='docorr', action='store_true', default=False, help='Make correspondences plot?')
    parser.add_option('--distortion', '-D', dest='dodistortion', action='store_true', default=False, help='Make distortion plot?')
    parser.add_option('--matches', '-M', dest='domatches', action='store_true', default=False, help='Make matches plot?')
    (opt, args) = parser.parse_args()

    if (opt.dophotometry is False and
        opt.docorr       is False and
        opt.dodistortion is False and
        opt.domatches    is False):
        plots = None
    else:
        plots = []
        if opt.dophotometry:
            plots.append('photom')
        if opt.docorr:
            plots.append('corr')
        if opt.dodistortion:
            plots.append('distortion')
        if opt.domatches:
            plots.append('matches')
        
    inButler = imsimUtils.getInputButler(opt)

    allkeys = imsimUtils.getAllKeys(opt, inButler)

    for keys in allkeys:
        plotsForField(inButler, keys, opt.fixup, plots)


def plotsForField(inButler, keys, fixup, plots=None):
    if plots is None:
        plots = ['photom','matches','corr','distortion']
        
    filters = inButler.queryMetadata('raw', 'filter', **keys)
    print 'Filters:', filters
    filterName = filters[0]

    psources = inButler.get('icSrc', **keys)
    # since the butler does lazy evaluation, we don't know if it fails until...
    try:
        print 'Got sources', psources
    except:
        print '"icSrc" not found.  Trying "src" instead.'
        psources = inButler.get('src', **keys)
        print 'Got sources', psources
        
    pmatches = inButler.get('icMatch', **keys)
    print 'Got matches', pmatches
    matchmeta = pmatches.getSourceMatchMetadata()
    matches = pmatches.getSourceMatches()
    print 'Match metadata:', matchmeta
    sources = psources.getSources()
    
    calexp = inButler.get('calexp', **keys)
    print 'Got calexp', calexp
    wcs = calexp.getWcs()
    print 'Got wcs', wcs
    print wcs.getFitsMetadata().toString()
    wcs = afwImage.cast_TanWcs(wcs)
    print 'After cast:', wcs

    photocal = calexp.getCalib()
    zp = photocal.getMagnitude(1.)
    print 'Zeropoint is', zp

    # ref sources
    W,H = calexp.getWidth(), calexp.getHeight()
    xc,yc = W/2., H/2.
    radec = wcs.pixelToSky(xc, yc)
    ra = radec.getLongitude(DEGREES)
    dec = radec.getLatitude(DEGREES)
    radius = wcs.pixelScale() * hypot(xc, yc) * 1.1
    print 'Image W,H', W,H
    print 'Image center RA,Dec', ra, dec
    print 'Searching radius', radius, 'arcsec'
    log = Log.getDefaultLog()
    log.setThreshold(Log.DEBUG);
    pol = policy.Policy()
    pol.set('matchThreshold', 30)
    solver = measAstrom.createSolver(pol, log)
    idName = 'id'
    # could get this from matchlist meta...
    anid = matchmeta.getInt('ANINDID')
    print 'Searching index with ID', anid
    print 'Using ID column name', idName
    print 'Using filter column name', filterName
    X = solver.getCatalogue(ra, dec, radius, filterName, idName, anid)
    ref = X.refsources
    inds = X.inds
    indexid = X.indexid
    assert(anid == indexid)
    print 'Got', len(ref), 'reference catalog sources'

    print 'False is', False

    #print ref
    #for r in ref:
    #    print r
    #for i in xrange(len(ref)):
    #    print ref[i]

    import gc
    #gc.set_debug(gc.DEBUG_LEAK)
    gc.collect()

    print 'before addTagAlongValues... False is', False

    measAstrom.addTagAlongValuesToReferenceSources(solver, pol, log, ref, indexid, inds, filterName)

    print 'after addTagAlongValues... False is', False

    print 'gc...'
    gc.collect()
    print '(done)'
    
    if True:
        fdict = maUtils.getDetectionFlags()
        starflag = int(fdict["STAR"])

        stargal = []
        referrs = []
        for i in xrange(len(ref)):
            print 'False is', False
            print 'flag:', ref[i].getFlagForDetection()
            print 'starflag:', starflag
            print 'and:', (int(ref[i].getFlagForDetection()) & starflag)
            sg = bool((int(ref[i].getFlagForDetection()) & starflag) > 0)
            print 'sg', i, 'is', sg
            stargal.append(sg)
            #stargal.append(bool((ref[i].getFlagForDetection() & starflag) > 0))
            referrs.append(float(ref[i].getPsfFluxErr() / ref[i].getPsfFlux() * 2.5 / -np.log(10)))

        print 'gc...'
        gc.collect()
        print '(done)'

        #stargal = [bool(r.getFlagForDetection() & starflag > 0)
        #           for r in ref]
        #referrs = [float(r.getPsfFluxErr() / r.getPsfFlux() * 2.5 / -np.log(10))
        #           for r in ref]
        print 'reference errs:', referrs
        print 'star/gals:', stargal

    else:
        print 'Tag-along columns:'
        cols = solver.getTagAlongColumns(anid)
        print cols
        for c in cols:
            print 'column: ', c.name, c.fitstype, c.ctype, c.units, c.arraysize
        colnames = [c.name for c in cols]

        col = filterName + '_err'
        if col in colnames:
            referrs = solver.getTagAlongDouble(anid, col, inds)
        else:
            referrs = None

        col = 'starnotgal'
        if col in colnames:
            stargal1 = solver.getTagAlongBool(anid, col, inds)
            # This nutty-looking stanza converts stargal to a real Python list;
            # for reasons I now don't remember, leaving it as a vector<bool> caused
            # problems when we make cuts below...
            stargal = []
            for i in range(len(stargal1)):
                stargal.append(stargal1[i])
        else:
            stargal = None

    gc.collect()


    keepref = []
    keepi = []
    for i in xrange(len(ref)):
        #print ref[i].getXAstrom(), ref[i].getYAstrom(), ref[i].getRa(), ref[i].getDec()
        x,y = wcs.skyToPixel(ref[i].getRa(), ref[i].getDec())
        if x < 0 or y < 0 or x > W or y > H:
            continue
        ref[i].setXAstrom(x)
        ref[i].setYAstrom(y)
        keepref.append(ref[i])
        keepi.append(i)
    print 'Kept', len(keepref), 'reference sources'
    ref = keepref

    if referrs is not None:
        referrs = [referrs[i] for i in keepi]
    if stargal is not None:
        stargal = [stargal[i] for i in keepi]

    gc.collect()

    print 'reference errs:', referrs
    print 'star/gals:', stargal

    gc.collect()

    if False:
        m0 = matches[0]
        f,s = m0.first, m0.second
        print 'match 0: ref %i, source %i' % (f.getSourceId(), s.getSourceId())
        print '  ref x,y,flux = (%.1f, %.1f, %.1f)' % (f.getXAstrom(), f.getYAstrom(), f.getPsfFlux())
        print '  src x,y,flux = (%.1f, %.1f, %.1f)' % (s.getXAstrom(), s.getYAstrom(), s.getPsfFlux())

    print 'join 1'
    measAstrom.joinMatchList(matches, ref, first=True, log=log)
    print '(done)'
    args = {}
    if fixup:
        # ugh, mask and offset req'd because source ids are assigned at write-time
        # and match list code made a deep copy before that.
        # (see svn+ssh://svn.lsstcorp.org/DMS/meas/astrom/tickets/1491-b r18027)
        args['mask'] = 0xffff
        args['offset'] = -1
    print 'join 2'
    measAstrom.joinMatchList(matches, sources, first=False, log=log, **args)
    print '(done)'

    visit = keys['visit']
    raft = keys['raft']
    sensor = keys['sensor']
    prefix = 'imsim-v%i-r%s-s%s' % (visit, raft.replace(',',''), sensor.replace(',',''))

    if 'photom' in plots:
        print 'photometry plots...'
        tt = 'LSST ImSim v%i r%s s%s' % (visit, raft.replace(',',''), sensor.replace(',',''))

        wcsPlots.plotPhotometry(sources, ref, matches, prefix, band=filterName, zp=zp, referrs=referrs, refstargal=stargal, title=tt)
        wcsPlots.plotPhotometry(sources, ref, matches, prefix, band=filterName, zp=zp, delta=True, referrs=referrs, refstargal=stargal, title=tt)

        # test w/ and w/o referrs and stargal.
        if False:
            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'A', band=filterName, zp=zp, title=tt)
            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'B', band=filterName, zp=zp, referrs=referrs, title=tt)
            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'C', band=filterName, zp=zp, refstargal=stargal, title=tt)

            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'A', band=filterName, zp=zp, delta=True, title=tt)
            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'B', band=filterName, zp=zp, delta=True, referrs=referrs, title=tt)
            wcsPlots.plotPhotometry(sources, ref, matches, prefix + 'C', band=filterName, zp=zp, delta=True,refstargal=stargal, title=tt)



    if 'matches' in plots:
        print 'matches...'
        wcsPlots.plotMatches(sources, ref, matches, wcs, W, H, prefix)

    if 'corr' in plots:
        #print 'corr...'
        # requires astrometry.libkd (not available in 0.30)
        #wcsPlots.plotCorrespondences2(sources, ref, matches, wcs, W, H, prefix)
        #print 'corr...'
        #wcsPlots.plotCorrespondences(sources, ref, matches, wcs, W, H, prefix)
        pass

    if 'distortion' in plots:
        print 'distortion...'
        wcsPlots.plotDistortion(wcs, W, H, 400, prefix,
                                'SIP Distortion (exaggerated x 10)', exaggerate=10.)
        print 'distortion...'
        wcsPlots.plotDistortion(wcs, W, H, 400, prefix,
                                'SIP Distortion (exaggerated x 100)', exaggerate=100.,
                                suffix='-distort2.')


if __name__ == '__main__':
    main()
