# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Plugin for calculating solar irradiation of a landscape
                                 A QGIS plugin
 Calculates shadows of a geographical region based on obstructions
        copyright            : (c) 2020-21 by Cumbria Action for Sustainability
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


__author__ = 'Tom'
__date__ = '2020-02-27'
__copyright__ = '(C) 2020 by Tom'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import (QCoreApplication,
                              QVariant)

# TODO: Expand lazy import statement
from qgis.core import *

from UMEP.WallHeight import wallalgorithms
from .WallworkerModified import Worker as WallWorker
from .SolarConstants  import *
from osgeo import gdal
import numpy as np
from pathlib import Path # Post python 3.4
from .metdata_processor_modified import MetdataProcessor # TODO move file here
from .sebe_modified import SEBE  as sebe # TODO move file here
from .sebeworker_modified import Worker as SebeWorker
from .SolarDirectoryPaths import SolarDirectoryPaths



class SolarCalculatorAlgorithm(QgsProcessingAlgorithm):
    """
    A QGIS plugin conforming to the QGIS plugin specification
    Calculates the solar irradiation at a particular geographic location based on hillside elevation 
    and obstructions (buildings, trees etc)

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """


    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    METEOROLOGICAL_RAW="METEOROLOGICAL_DATA_FILE"
    DATA_DIRECTORY = "DATA_DIRECTORY"   
 
    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterString(
                self.DATA_DIRECTORY,
                self.tr(self.DATA_DIRECTORY),
                defaultValue=DATA_STRING
            )
        )
        self.addParameter(QgsProcessingParameterFile(
                self.METEOROLOGICAL_RAW,
                self.tr('METEOROLOGICAL_DATA_FILE'),
                extension="epw"
        ))


    def calculateWallHeightParameters(self, dsmlayer):
        provider = dsmlayer.dataProvider()
        filepath_dsm = str(provider.dataSourceUri())
        self.gdal_dsm = gdal.Open(filepath_dsm)
        self.dsm = self.gdal_dsm.ReadAsArray().astype(np.float)
        self.geoTransform = self.gdal_dsm.GetGeoTransform()
        self.scale = 1 / self.geoTransform[1]
        self.projection = self.gdal_dsm.GetProjection()
        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        paths=SolarDirectoryPaths()
        dataString = self.parameterAsString(parameters, self.DATA_DIRECTORY, context)
        dataPath = SolarDirectoryPaths().projectPath / dataString
        dataPath.mkdir(parents=True, exist_ok=True)
        solarRasterFilePath = dataPath / 'annual-solar-energy.tif'
        meteorologicalDataRawFilePath = self.parameterAsFile(parameters, self.METEOROLOGICAL_RAW, context)
        
        results = {}

        # Step 79 - Meteorological data file
        msg = "Starting Step 79 - Process meteorological data"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        metdataProcessor=MetdataProcessor()             
        metdataProcessor.importFileFromFilePath(meteorologicalDataRawFilePath)        
        # Construct a file path to the processed Meteorological Data file (to be calculated):
        meteorologicalDataProcessedFilePath = paths.dataDirectoryPath / METEOROLOGICAL_FILE_PROCESSED_FILE_NAME
        metdataProcessor.preprocessMetData(meteorologicalDataProcessedFilePath)
        
        # Step 80 - Wall Height and Wall Aspect Rasters
        msg = "Starting Step 80 - calculate wall height and aspect rasters"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        dsmMinusDtmFilePath = dataPath / (DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME + '.tif')
        dsmMinusDtmClippedLayer = QgsProcessingUtils.mapLayerFromString(str(dsmMinusDtmFilePath), context) 

        self.calculateWallHeightParameters(dsmMinusDtmClippedLayer)
        wallHeightArray = wallalgorithms.findwalls(self.dsm, WALL_LIMIT)
 
        worker = WallWorker(wallHeightArray, self.scale, self.dsm, feedback)
        wallAspectArray = worker.run()
        # TODO replace -9999 with constant

        
        # TODO - consider removing wall aspect and wall height as layers and files to speed up calculation.  We already have the numpy arrays from the calculation.
        
        # Final Step 81 - Solar Raster Calculation
        msg = "Starting Step 81 - calculate the energy raster - amount of sunlight falling on roofs"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        solarEnergyCalculator = sebe(feedback)

        msg = "(81a) - reading meteorological data..."
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        solarEnergyCalculator.readMeteorologicalData(meteorologicalDataProcessedFilePath)
        
        msg = "(81b) - initialise Solar parameters..."
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        # Calculates starting parameters for the calculation including turning the dsm raster into a numpy array
        dsmFilePath = dataPath / (DSM_1M_CLIPPED_LAYER_NAME + '.tif')
        dsmLayer = QgsProcessingUtils.mapLayerFromString(str(dsmFilePath), context) 

        building_slope, building_aspect, scale, voxelheight, sizey, sizex, radmatI, radmatD, radmatR, calc_month, dsmArray = solarEnergyCalculator.calculateSebeParameters(dsmLayer, UTC_OFFSET, ALBEDO)

        msg = "(81c) - starting the final solar roof calculation"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        sebeWorker = SebeWorker(dsmArray, scale, building_slope,building_aspect, voxelheight, sizey, sizex, wallHeightArray, wallAspectArray, ALBEDO, PSI, radmatI, radmatD, radmatR, calc_month, feedback)
        solarEnergyArray = sebeWorker.run()
        solarEnergyRaster=self.createRasterFromNumpyArray(solarEnergyArray, -9999, solarRasterFilePath)
        
        msg = "Step 81 completed successfully - see the layers panel for results"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        
        processedRoofPlanesFilePath = dataPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')
        
        #log(f"solarRasterFilePath is {solarRasterFilePath}")
        # STEP 83 - Finally, calculate mean irradiation over each roof
        msg = "Starting step 83 - calculating irradiation across each roof..."
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        parameters = {
            'INPUT_RASTER':str(solarRasterFilePath),
            'RASTER_BAND':1,
            'INPUT_VECTOR':str(processedRoofPlanesFilePath),
            'COLUMN_PREFIX':'Irrad_',
            'STATS':[2]}
        results = processing.run("qgis:zonalstatistics", parameters, context=context, feedback=feedback)       
      
        return results # Include the raster layers for wall aspect and wall height here
    
    # Create a raster from the numpy array by writing the data out to a file
    # I cannot find any other method of doing this!
    def createRasterFromNumpyArray(self, sourceNumpyNDArray, noDataValue, filepath):
        # Construct a file path to the temporary file in the data directory:
        cols, rows = sourceNumpyNDArray.shape
        
        # Open up the raster file
        outputRaster = gdal.GetDriverByName('GTiff').Create(str(filepath),rows, cols, int(1) ,gdal.GDT_Float32)

        #writing output raster does the magic of converting array into raster!
        outputRaster.GetRasterBand(1).WriteArray( sourceNumpyNDArray ) 
        outputRaster.SetGeoTransform(self.geoTransform)
        outputRaster.SetProjection(self.projection)
        outputRaster.FlushCache()
        return outputRaster

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'solar'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'CAFS 3'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        return self.tr("Third CAFS algorithm: produce a solar energy raster for the local area and calculate zonal statistics for each roof")

    def createInstance(self):
        return SolarCalculatorAlgorithm()

