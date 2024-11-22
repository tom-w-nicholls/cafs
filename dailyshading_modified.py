"""
/***************************************************************************
Based on some original open source code by Fredrik Lindberg.
 Adapted by Tom Nicholls for CAFS: Refactored to separate the calculation into a 
 more object-oriented design and to remove wall irradiation for speed.
                              -------------------
        copyright            : (c) 2021 by Cumbria Action for Sustainability
        original copyright   : 2015 by Fredrik Lindberg (fredrikl@gvc.gu.se)
        author               : Tom Nicholls
        email                : tom@codeclass.co.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""



import datetime as dt
from builtins import range
#from math import comb
from scipy.ndimage import zoom



from UMEP.Utilities import shadowingfunctions as shadow
from UMEP.Utilities.misc import *
from UMEP.Utilities.SEBESOLWEIGCommonFiles import sun_position as sp
from UMEP.Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_23 import shadowingfunction_wallheight_23
from qgis.core import *
from .SolarConstants  import *


def dailyshading(clippedHighResArray, lowResWideArray, lonlat, scale, scaleWide, 
            wideExtent, localExtent, 
            tv, UTC, timeInterval, onetime, dlg, dst, useWideArea):
    """
    Calculates solar shading based on landscape 3D profile and obstruction height/location
    We have two arrays - a high resolution "local" array that is our area of interest for calculating roof slopes,
    and a low resolution "wide area" array that is the area for which we are interested in "mountain shadows", and has been scaled down from a high res one.
    The absolute positions of these arrays in geographical coordinates are held in wideExtent and localExtent

    
    """
    # First log the arguments:
    if(isDebug()):
        log(str(locals()))
    # scaleFactor is the zoom factor between the low resolution and full resolution rasters
    # We make the assumption that the both rasters are at the same longitude and latitude
    lon = lonlat[0]
    lat = lonlat[1]
    year = tv[0]
    month = tv[1]
    day = tv[2]

    alt = np.median(clippedHighResArray)
    location = {'longitude': lon, 'latitude': lat, 'altitude': alt}

    shwidefinal = 0
   
    # We will calculate three averages and return these as the result of this function,
    # so set zero totals first
    # Note that numpy x and y are reversed in the zeros function
    shtot = np.zeros((localExtent.height, localExtent.width)) # total with wide area influence included
    shtotLocalOnly = np.zeros((localExtent.height, localExtent.width)) # total with wide area influence included

    if(useWideArea):
        shtotWideArea = np.zeros((lowResWideArray.shape[0], lowResWideArray.shape[1])) # average of the low resolution wide area rasters only

    clippedHighResWideAreaArray, highResWideZoomedArray = 0, 0 # only used in the case of a wide area shadow calculation

    if onetime == 1:
        itera = 1
    else:
        itera = int(1440 / timeInterval)  # number of iterations in 24 hours (timeInterval is in minutes)

    alt = np.zeros(itera)
    azi = np.zeros(itera)
    hour = int(0)
    index = 0
    time = dict()
    time['UTC'] = UTC


    for i in range(0, itera):  # calculate raster for each step in the interval (e.g. for hourly this is 24 steps in the day)
        year, month, day, hour, minu, ut_time = createTimeParameters(tv, timeInterval, onetime, dst, year, month, day, i)

        HHMMSS = dectime_to_timevec(ut_time)

        createTimeDict(year, month, day, time, HHMMSS)

        sun = sp.sun_position(time, location)
        alt[i] = 90. - sun['zenith']
        azi[i] = sun['azimuth']
        if(isDebug):
            log("Alt = " + str(alt[i]) + " Azi = " + str(azi[i]) + " Hour: " + str(hour) + " Min: " + str(minu) + " Sec: " + str(HHMMSS[2]) + " Day: " + str(day) + " Month: " + str(month) + " Year: " + str(year))

        # time_vector = dt.datetime(year, month, day, HHMMSS[0], HHMMSS[1], HHMMSS[2])

        if alt[i] > 0: # if the sun is above the horizon?
            if(isDebug):
                log("starting local shadow calculation")
            sh = shadow.shadowingfunctionglobalradiation(clippedHighResArray, azi[i], alt[i], scale, dlg, 0) # calculate shadow raster for this time of day
            if(isDebug):
                log("Finished Local Calculation")
            shtotLocalOnly = shtotLocalOnly + sh # total up shadow rasters
            index += 1 # keep track of how many for averages
            if(useWideArea):
                # Calculate the low resolution wide area shadow raster
                shLowResWideArea = shadow.shadowingfunctionglobalradiation(lowResWideArray, azi[i], alt[i], scaleWide, dlg, 0) # calculate shadow raster for this time of day
                
                if(isDebug):
                    log("Finished Wide Calculation")

                # We now have a large (low resolution) raster and a smaller high resolution one, both representing the wide area
                # First task is to "zoom" up the low res one to a higher one of full size (this is still the "wide" array)
                zoomHorizontalFactor = wideExtent.width / shLowResWideArea.shape[1]
                zoomVerticalFactor = wideExtent.height / shLowResWideArea.shape[0]
                highResWideZoomedArray = zoomResolutionArray(shLowResWideArea, zoomHorizontalFactor, zoomVerticalFactor)

                if(isDebug):
                    log(f"highResWideZoomedArray size horizontal: {highResWideZoomedArray.shape[1]}, size vertical: {highResWideZoomedArray.shape[0]}")

                # Now we need to clip this wide area shadow raster to the local region 
                # We can use numpy's array[x:y,a:b] to select a region
                
                
                xmin=localExtent.xmin-wideExtent.xmin
                xmax=localExtent.xmax-wideExtent.xmin
                ymin=wideExtent.ymax-localExtent.ymax
                ymax=wideExtent.ymax-localExtent.ymin
                
                if(isDebug):
                    log(f"xmin={xmin}, xmax={xmax}, ymin={ymin}, ymax={ymax}")

                # Note that x and y are reversed in numpy when it comes to accessing elements:
                clippedHighResWideAreaArray = highResWideZoomedArray[ymin:ymax, xmin:xmax]
                if(isDebug):    
                    log(f"Combining Rasters. sh size: {sh.shape[0]}, {sh.shape[1]}. clippedHighResWideAreaArray size: {clippedHighResWideAreaArray.shape[0]}, {clippedHighResWideAreaArray.shape[1]}")

                combinedRaster = sh * clippedHighResWideAreaArray * 1

                if(isDebug):
                    log(f"Finished combining rasters, result size: {combinedRaster.shape[0]}, {combinedRaster.shape[1]}")
               
                shtotWideArea=shtotWideArea + shLowResWideArea
                shtot=shtot+combinedRaster
                shtotLocalOnly=shtotLocalOnly+sh
            else:
                shtot=shtot+sh

    shfinal = shtot / index # find average of all the shadow rasters added up
    shlocalfinal = shtotLocalOnly / index # find average of all the local shadow rasters added up (not affected by wide area arrays)
    if(useWideArea):
        shwidefinal = shtotWideArea / index # find average of all the wide area low resolution shadow rasters added up
    shadowresult = {'shfinal': shfinal, 'shwide':shwidefinal, 'shlocal':shlocalfinal, 'shWideZoomedArray': highResWideZoomedArray, 'shWideClippedArray' : clippedHighResWideAreaArray}
    
    return shadowresult

def zoomResolutionArray(array, zoomHorizontalFactor, zoomVerticalFactor):
    # order is 3 for cubic, 1 for bilinear, 0 for nearest neighbour
    highResWideAreaArray = zoom(array, [zoomVerticalFactor, zoomHorizontalFactor], order=0) # nearest neighbour makes sense with 1s and 0s
    return highResWideAreaArray

def createTimeDict(year, month, day, time, HHMMSS):
    time['year'] = year
    time['month'] = month
    time['day'] = day
    time['hour'] = HHMMSS[0]
    time['min'] = HHMMSS[1]
    time['sec'] = HHMMSS[2]

def createTimeParameters(tv, timeInterval, onetime, dst, year, month, day, i):
    if onetime == 0:
        minu = int(timeInterval * i)
        # number of minutes after midnight in this stepif minu >= 60: # convert to hours and minutes
        hour = int(np.floor(minu / 60))
        minu = int(minu - hour * 60)
    else:
        minu = tv[4]
        hour = tv[3]
    doy = day_of_year(year, month, day)
    ut_time = doy - 1. + ((hour - dst) / 24.0) + (minu / (60. * 24.0)) + (0. / (60. * 60. * 24.0))
    if ut_time < 0:
        year = year - 1
        month = 12
        day = 31
        doy = day_of_year(year, month, day)
        ut_time = ut_time + doy - 1
    return year,month,day,hour,minu,ut_time

def day_of_year(yy, month, day):
    if (yy % 4) == 0:
        if (yy % 100) == 0:
            if (yy % 400) == 0:
                leapyear = 1
            else:
                leapyear = 0
        else:
            leapyear = 1
    else:
        leapyear = 0

    if leapyear == 1:
        dayspermonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    else:
        dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    doy = np.sum(dayspermonth[0:month-1]) + day

    return doy


def dectime_to_timevec(dectime):
    # This subroutine converts dectime to individual hours, minutes and seconds

    doy = np.floor(dectime)

    DH = dectime-doy
    HOURS = int(24 * DH)

    DM=24*DH - HOURS
    MINS=int(60 * DM)

    DS = 60 * DM - MINS
    SECS = int(60 * DS)

    return (HOURS, MINS, SECS)
