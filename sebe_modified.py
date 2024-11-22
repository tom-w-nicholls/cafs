# -*- coding: utf-8 -*-
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

from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
# from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QThread, QCoreApplication
# from qgis.PyQt.QtWidgets import QFileDialog, QAction, QMessageBox
# from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from qgis.gui import *
# from .sebe_dialog import SEBEDialog
import os.path
from UMEP.Utilities.misc import *
from osgeo import gdal, osr
import numpy as np
from .sebeworker_modified import Worker as ModifiedWorker
from UMEP.Utilities.SEBESOLWEIGCommonFiles.Solweig_v2015_metdata_noload import Solweig_2015a_metdata_noload
from UMEP.SEBE.SEBEfiles.sunmapcreator_2015a import sunmapcreator_2015a
import webbrowser
from UMEP.SEBE import WriteMetaDataSEBE
from .SolarConstants  import *


class SEBE(object):
    """QGIS Plugin Implementation."""

    def __init__(self, feedback):

        self.folderPath = None
        self.scale = None
        self.gdal_dsm = None
        self.dsm = None
        self.folderPathMetdata = None
        self.metdata = None
        self.radmatfile = None
        self.steps = 0
        self.solarLayerName=SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME
        self.feeback = feedback
    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SEBE', message)


    def readMeteorologicalData(self, inputFilePath):
        headernum = 1
        delim = ' '
        try:
            self.metdata = np.loadtxt(inputFilePath, skiprows=headernum, delimiter=delim)
        except:
            raise SolarException("Import Error", "Make sure format of meteorological file is correct. You can "
                "prepare your data by using 'Prepare Existing Data' in "
                "the Pre-processor")
        testwhere = np.where((self.metdata[:, 14] < 0.0) | (self.metdata[:, 14] > 1300.0))
        if testwhere[0].__len__() > 0:
            raise SolarException("Value error", "Meteorological Data - Kdown - beyond what is expected at line: \n" +
                                 str(testwhere[0] + 1))
        if self.metdata.shape[1] != 24:
            raise SolarException("Import Error", "Wrong number of columns in meteorological data. You can "
                "prepare your data by using 'Prepare Existing Data' in "
                "the Pre-processor")

    
    def calculateSebeParameters(self, dsmlayer, UTC, albedo):   
#         self.folderPath = [dataDirectoryFilePath] # hack this as an array     
        provider = dsmlayer.dataProvider()
        filepath_dsm = str(provider.dataSourceUri())
        # self.dsmpath = filepath_dsm
        self.gdal_dsm = gdal.Open(filepath_dsm)
        # dSM is a numpy array
        dSM = self.gdal_dsm.ReadAsArray().astype(np.float)
        self.dsm = dSM
        sizex = self.dsm.shape[0]
        sizey = self.dsm.shape[1]
        # response to issue #85
        nd = self.gdal_dsm.GetRasterBand(1).GetNoDataValue()
        self.dsm[self.dsm == nd] = 0.
        if self.dsm.min() < 0:
            self.dsm = self.dsm + np.abs(self.dsm.min())
        # Get latlon from grid coordinate system
        old_cs = osr.SpatialReference()
        dsm_ref = dsmlayer.crs().toWkt()
        old_cs.ImportFromWkt(dsm_ref)
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
        new_cs = osr.SpatialReference()
        new_cs.ImportFromWkt(wgs84_wkt)
        # Hack - don't forget     to read in met_data too
        transform = osr.CoordinateTransformation(old_cs, new_cs)
        width = self.gdal_dsm.RasterXSize
        height = self.gdal_dsm.RasterYSize
        geotransform = self.gdal_dsm.GetGeoTransform()
        minx = geotransform[0]
        miny = geotransform[3] + width * geotransform[4] + height * geotransform[5]
        lonlat = transform.TransformPoint(minx, miny)
        lon = lonlat[0]
        lat = lonlat[1]
        scale = 1 / geotransform[1]
        self.scale = scale
        trunkfile = 0
        trunkratio = 0
        # Hack - vegetation layer is not used, so we set these to zero.
        filePath_cdsm = None
        filePath_tdsm = None
        voxelheight = geotransform[1] # float
        #   Hack - Set only global to 0 as this box isn't checked in our case
        onlyglobal = 0
        output = {'energymonth':0, 'energyyear':1, 'suitmap':0}
    # wall height layer
        
        alt = np.median(self.dsm)
        if alt < 0:
            alt = 3
        location = {'longitude':lon, 'latitude':lat, 'altitude':alt}
        YYYY, altitude, azimuth, zen, jday, leafon, dectime, altmax = Solweig_2015a_metdata_noload(self.metdata, location, UTC)
        radmatI, radmatD, radmatR = sunmapcreator_2015a(self.metdata, altitude, azimuth, 
            onlyglobal, output, jday, albedo, location, zen)
            # Hack - save sky irradiance is always false
        building_slope, building_aspect = get_ders(self.dsm, self.scale)
        calc_month = False # TODO: Month not implemented
        return building_slope, building_aspect, scale, voxelheight, sizey, sizex, radmatI, radmatD, radmatR, calc_month, dSM
    
    
