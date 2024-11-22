# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShadowGenerator
                                 A QGIS plugin
 Simulates casting shadows
                              -------------------
        copyright            : (c) 2020 by Cumbria Action for Sustainability
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
from __future__ import absolute_import
from builtins import str
from builtins import object
from osgeo import gdal, osr
import os.path
from .dailyshading_modified import dailyshading
import numpy as np
import webbrowser
from .SolarConstants import *


class ShadowGenerator(object):
    """
    Calculates a shadow raster - this is an image of the shadow cast
    on the landscape at a particular day of the year.
    Iterates through 24 hours at snapshots intervals specified by timeInterval
    Takes the daily shadow to be the weighted average of these shadows calculated at interval
    """

    def __init__(self):

        self.folderPath = 'None'
        self.timeInterval = 30
        

    # dsmlayer and dsmWideLayer are clipped versions of the Raster layer
    def calculateShadowRaster(self, dsmlayer, dsmWideLayer, useWideArea, wideExtent, localExtent, year, month, day, hour, minu, sec, UTC, timeInterval, dst, onetime, dlg):
        """
        Calculates a shadow raster - this is an image of the shadow cast
        on the landscape at a particular day of the year.
        Iterates through 24 hours at intervals specified by timeInterval 

        Attributes
        ----------
            dsmlayer : Numpy Array
                Input Digital Elevation Raster
            dsmWideLayer: Numpy Array
                Wide area DSM for shadow calculation (if using)
            useWideArea : boolean
                True if using Wide Area Array
            localExtent : Dict
                width and height of the local area DSM
            wideExtent : Dict
                width and height of the wide area DSM
            year : int
                year
            month : int
                month of year
            day : int
                day of month
            hour : int
                hour
            minu : int
                minute
            sec : int
                second
            UTC : int
                UTC offset in hours
            timeInterval:
                : interval between snapshots in minutes
            dst : Numpy Array
                Input Digital Elevation Raster (DST - ground level without trees/buildings etc)
            onetime : boolean
                0 in this case as we are always doing an interval
            dlg : null
                set to null
        Returns
        -------
            gdal_dsm: Numpy array
                Calculated shadow raster with size based on the input dsmlayer
        
        # lonlat, sizex, sizey: calculated above from the dsm layer
        # tv: an array of [year, month, day, hour, min, sec]
        # UTC: UTC offset in hours (0 in our case)
        # self.timeinterval: time interval in minutes between snapshots
        # onetime: 0 in our case as we are using intervals and not a single calculation
        # dlg=null
        # self.folderpath[0]: path to the output folder
        # gdal_dsm: dsm read as an array
        # trans: light transmission (0.03 in our case)
        # dst: 0 or 1 depending on whether it's in daylight savings time
        # So the  calculated values are gdal_dsm, lonlat, sizex, sizey - all based on the dsm layer
        """
        provider = dsmlayer.dataProvider()
        filepath_dsm = str(provider.dataSourceUri())
        gdal_dsm = gdal.Open(filepath_dsm)
        dsm = gdal_dsm.ReadAsArray().astype(np.float)
        scale, lonlat, horizontalSize, verticalSize, geoTransform = calculateScaleParameters(gdal_dsm, dsmlayer, dsm)
        msg = f"scale = {scale}, lonlat={lonlat}, sizex = {horizontalSize}, sizey = {verticalSize}, geoTransform = {geoTransform}"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)


        # Make available to the outside world:
        self.geoTransform = geoTransform
        self.projection = gdal_dsm.GetProjection()

        lowResWideArray, scaleWide, horizontalSizeWide, verticalSizeWide = 0, 0, 0, 0 # initialize to avoid error
         

        # Now repeat all of these for the wide raster:
        if(useWideArea):
            provider = dsmWideLayer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())
            gdal_dsm_wide = gdal.Open(filepath_dsm)
            lowResWideArray = gdal_dsm_wide.ReadAsArray().astype(np.float)

            scaleWide, lonlatWide, horizontalSizeWide, verticalSizeWide, geoTransformWide = calculateScaleParameters(gdal_dsm_wide, dsmWideLayer, lowResWideArray)
            msg = "ScaleWide: " + str(scaleWide)
            QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

            # Make available to the outside world:
            self.geoTransformWide = geoTransformWide
            self.projectionWide = gdal_dsm_wide.GetProjection()
    
            


        tv = [year, month, day, hour, minu, sec]
        # dsm: our layer
        # lonlat, sizex, sizey: calculated above from the dsm layer
        # tv: an array of [year, month, day, hour, min, sec]
        # UTC: UTC offset in hours (0 in our case)
        # self.timeinterval: time interval in minutes between snapshots
        # onetime: 0 in our case as we are using intervals and not a single calculation
        # dlg=null
        # self.folderpath[0]: path to the output folder
        # gdal_dsm: dsm read as an array
        # trans: light transmission (0.03 in our case)
        # dst: 0 or 1 depending on whether it's in daylight savings time
        # So the  calculated values are gdal_dsm, lonlat, sizex, sizey - all based on the dsm layer
        shadowresult = dailyshading(dsm, lowResWideArray, lonlat, scale, scaleWide, wideExtent, localExtent, tv, UTC, timeInterval, onetime, dlg, dst, useWideArea)
        return shadowresult # dictionary of numpy arrays

def calculateScaleParameters(gdal_dsm, dsmlayer, dsm):
    nd = gdal_dsm.GetRasterBand(1).GetNoDataValue()
    dsm[dsm == nd] = 0.
    if dsm.min() < 0:
        dsm = dsm + np.abs(dsm.min())
    sizex = dsm.shape[1]
    sizey = dsm.shape[0]
    old_cs = osr.SpatialReference()
    dsm_ref = dsmlayer.crs().toWkt()
    old_cs.ImportFromWkt(dsm_ref)
    new_cs = osr.SpatialReference()
    new_cs.ImportFromWkt(getWgs84_wkt())
    transform = osr.CoordinateTransformation(old_cs, new_cs)
    width = gdal_dsm.RasterXSize
    height = gdal_dsm.RasterYSize
    gt = gdal_dsm.GetGeoTransform()
    minx = gt[0]
    miny = gt[3] + width * gt[4] + height * gt[5]
    lonlat = transform.TransformPoint(minx, miny)
    # nasty - breaks encapsulation, but do this to make available to the outside world
    geoTransform = gdal_dsm.GetGeoTransform()
    scale = 1 / geoTransform[1]
    return scale, lonlat, sizex, sizey, geoTransform 


def getWgs84_wkt():
    wgs84_wkt = """
    
    GEOGCS["WGS 84",
    
        DATUM["WGS_1984",
    
            SPHEROID["WGS 84",6378137,298.257223563,
    
                AUTHORITY["EPSG","7030"]],
    
            AUTHORITY["EPSG","6326"]],
    
        PRIMEM["Greenwich",0,
    
            AUTHORITY["EPSG","8901"]],
    
        UNIT["degree",0.01745329251994328,
    
            AUTHORITY["EPSG","9122"]],
    
        AUTHORITY["EPSG","4326"]]"""
    return wgs84_wkt
