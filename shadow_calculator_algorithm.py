# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ShadowCalculator
                                 A QGIS plugin
 Calculates shadows of a geographical region based on obstructions
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

__author__ = 'Tom'
__date__ = '2020-02-27'
__copyright__ = '(C) 2020 by Tom'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
# from qgis.core import (QgsProcessing,
#                        QgsFeatureSink,
#                        QgsProcessingAlgorithm,
#                        QgsProcessingParameterFeatureSource,
#                        QgsProcessingParameterFeatureSink)
# TODO: Fix Lazy * import
from qgis.core import *
from PyQt5.QtWidgets import QProgressBar # Need this for the QGIS plugin progress bar

from osgeo import gdal

from .SolarConstants  import *
from .shadow_generator_modified import ShadowGenerator
import numpy as np
from pathlib import Path # Post python 3.4
from .SolarDirectoryPaths import SolarDirectoryPaths

import processing


class ShadowCalculatorAlgorithm(QgsProcessingAlgorithm):
    """
    A QGIS plugin conforming to the QGIS plugin specification
    Calculates the solar shadow at a particular geographic location based on hillside elevation 
    and obstructions (buildings, trees etc)

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    DSM_CLIPPED='DSM_CLIPPED'
    ROOF_PLANES='ROOF_PLANES'
    SHADOW_BINARY=SHADOW_BINARY_LAYER_NAME

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        paths=SolarDirectoryPaths()

        # Input layers:
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DSM_CLIPPED,
            self.tr("DSM_CLIPPED"), DSM_1M_CLIPPED_LAYER_NAME, False))

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.ROOF_PLANES,
                self.tr('PROCESSED_ROOF_PLANES'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=PROCESSED_ROOF_PLANES_LAYER_NAME
            )
        )
        
        # Construct default filepath for raster height and aspect files so the user can avoid choosing if desired:
        shadowBinaryLayerFileName = SHADOW_BINARY_LAYER_NAME + '.tif'
        shadowBinaryRasterDefault = paths.shadowDirectoryPath / shadowBinaryLayerFileName


        self.addParameter(QgsProcessingParameterRasterDestination(
            self.SHADOW_BINARY,
            self.tr(self.SHADOW_BINARY),
            str(shadowBinaryRasterDefault), False))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        paths=SolarDirectoryPaths()

        dsmLayer = self.parameterAsRasterLayer(parameters, self.DSM_CLIPPED, context)
        processedRoofPlanesLayer = self.parameterAsVectorLayer(parameters, self.ROOF_PLANES, context)
        shadowBinaryFilePath = self.parameterAsOutputLayer(parameters, self.SHADOW_BINARY, context)
        results = {}
                
        
        # We just need to pass in a progressBar inside a "dlg" class to the shadowing methods just for consistency - it doesn't seem to do anything
        class FakeDialog:
            def __init__(self, progressBar):
                self.progressBar = progressBar

        progress = QProgressBar()
        dlg = FakeDialog(progress)
        
        hour=0
        min=0
        sec=0
        trans=0.03
        UTC=0
        loadRasterIntoCanvas=1
        timeInterval=60
        onetime=0
        
        shadowGenerator = ShadowGenerator()
        
        # March 20th 2020
        msg = "March 20th 2020"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        dst=0
        array200320 = shadowGenerator.calculateShadowRaster(dsmLayer, 2020, 3, 20, hour, min, sec, UTC, trans, timeInterval, dst, onetime, dlg) # step 65
        filepath200320 = paths.shadowDirectoryPath / '200320-shadow.tif'
        self.createRasterFromNumpyArray(array200320, -9999, filepath200320, shadowGenerator.geoTransform, shadowGenerator.projection)
        feedback.setProgress(20)
        
        
        # June 21st 2020 (daylight savings: dst=1)
        msg = "June 21st 2020"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        dst=1
        array200621 = shadowGenerator.calculateShadowRaster(dsmLayer, 2020, 6, 21, hour, min, sec, UTC, trans, timeInterval, dst, onetime, dlg) # step 66
        filepath200621 = paths.shadowDirectoryPath / '200621-shadow.tif'
        self.createRasterFromNumpyArray(array200621, -9999, filepath200621, shadowGenerator.geoTransform, shadowGenerator.projection)
        feedback.setProgress(40)
        
        # Sept 23rd 2020 (daylight savings: dst=1)
        msg = "Sept 23rd 2020"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)        
        dst=1
        array200923 = shadowGenerator.calculateShadowRaster(dsmLayer, 2020, 9, 23, hour, min, sec, UTC, trans, timeInterval, dst, onetime,  dlg) # step 67
        filepath200923 = paths.shadowDirectoryPath / '200923-shadow.tif'
        self.createRasterFromNumpyArray(array200923, -9999, filepath200923, shadowGenerator.geoTransform, shadowGenerator.projection)
        feedback.setProgress(60)

        # Dec 22nd 2020 
        msg = "Dec 22nd 2020"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)        
        dst=0
        array201222 = shadowGenerator.calculateShadowRaster(dsmLayer, 2020, 12, 22, hour, min, sec, UTC, trans, timeInterval, dst, onetime,  dlg) # step 67
        filepath201222 = paths.shadowDirectoryPath / '201222-shadow.tif'
        self.createRasterFromNumpyArray(array201222, -9999, filepath201222, shadowGenerator.geoTransform, shadowGenerator.projection)
        feedback.setProgress(80)
        
        #STEP 70 Reclassification to binary rasters
        outfilepath200320 = paths.shadowDirectoryPath / 'March-binary.tif'
        outfilepath200621 = paths.shadowDirectoryPath / 'June-binary.tif'
        outfilepath200923 = paths.shadowDirectoryPath / 'September-binary.tif'
        outfilepath201222 = paths.shadowDirectoryPath / 'December-binary.tif'
            
        parameters = {
            'INPUT_RASTER':str(filepath200320),
            'RASTER_BAND':1,
            'TABLE':[0,0.5,0,0.5,1,1],
            'NO_DATA':-9999,
            'RANGE_BOUNDARIES':0,
            'NODATA_FOR_MISSING':False,
            'DATA_TYPE':5,
            'OUTPUT':str(outfilepath200320)}
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        marchBinary= results['OUTPUT']
        feedback.setProgress(84)
        
        parameters['INPUT_RASTER']=str(filepath200621)
        parameters['OUTPUT']=str(outfilepath200621)
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        juneBinary= results['OUTPUT']
        feedback.setProgress(88)

        parameters['INPUT_RASTER']=str(filepath200923)
        parameters['OUTPUT']=str(outfilepath200923)
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        septemberBinary= results['OUTPUT']
        feedback.setProgress(92)

        parameters['INPUT_RASTER']=str(filepath201222)
        parameters['OUTPUT']=str(outfilepath201222)
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        decemberBinary= results['OUTPUT']
        feedback.setProgress(96)

        # STEP 73 Multiply all binary rasters together to produce the final shadow binary result:
        tempBinaryPath = paths.shadowDirectoryPath / 'binary-temp.tif'
        parameters = {
            'INPUT_A' : str(marchBinary),
            'BAND_A' : 1,
            'INPUT_B' : str(juneBinary),
            'BAND_B' : 1,
            'INPUT_C' : str(septemberBinary),
            'BAND_C' : 1,
            'INPUT_D' : str(decemberBinary),
            'BAND_D' : 1,
            'FORMULA' : 'A * B * C * D',   
            'OUTPUT':str(tempBinaryPath)}
        results = processing.run('gdal:rastercalculator',parameters, context=context, feedback=feedback)
        shadowBinaryLayer = fixLayerCrs(results['OUTPUT'], shadowBinaryFilePath, context, feedback)

        # STEP 75 Use zonal stats to calculate mean shade for each roof
        parameters = {
            'INPUT_RASTER':shadowBinaryLayer,
            'RASTER_BAND':1,
            'INPUT_VECTOR':processedRoofPlanesLayer,
            'COLUMN_PREFIX':'Shade_',
            'STATS':[2]}
        results = processing.run("qgis:zonalstatistics", parameters, context=context, feedback=feedback)

        # Set output
        
        results[self.SHADOW_BINARY] = shadowBinaryFilePath 

        return results


    def createRasterFromNumpyArray(self, sourceNumpyNDArray, noDataValue, filepath, geoTransform, projection):
        cols, rows = sourceNumpyNDArray.shape
        
        # Open up the raster file
        outputRaster = gdal.GetDriverByName('GTiff').Create(str(filepath),rows, cols, int(1) ,gdal.GDT_Float32)
        
        #writing output raster does the magic of converting array into raster!
        outputRaster.GetRasterBand(1).WriteArray( sourceNumpyNDArray ) 
        outputRaster.SetGeoTransform(geoTransform)
        outputRaster.SetProjection(projection)
        outputRaster.FlushCache()
        

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Shadow Calculator'

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
        return 'CAFS 2'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ShadowCalculatorAlgorithm()
    

