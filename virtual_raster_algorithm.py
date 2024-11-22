# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Plugin for creating a composite raster from a series of smaller input ones
                                 A QGIS plugin
 Calculates shadows of a geographical region based on obstructions
        copyright            : (c) 2020-21 by Cumbria Action for Sustainability
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

from .SolarConstants  import *
from pathlib import Path # Post python 3.4
import processing
from math import pi
from .SolarDirectoryPaths import SolarDirectoryPaths


class VirtualRasterAlgorithm(QgsProcessingAlgorithm):
    """
    A QGIS plugin which combines several smaller rasters to a larger output one
    Convenience function as a precursor to the main solar calculations

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.


    DSM_RASTER_FOLDER = 'DSM_FOLDER'
    DTM_RASTER_FOLDER = 'DTM_FOLDER'
    DSM_RASTER_OUTPUT = 'DSM_OUTPUT'
    DTM_RASTER_OUTPUT = 'DTM_OUTPUT'
    
    
    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        paths=SolarDirectoryPaths()

        dsmRasterFileLocationDefault = paths.lidarDataDirectoryPath / 'DSM'
        dtmRasterFileLocationDefault = paths.lidarDataDirectoryPath / 'DTM'


        # Input layers:
        self.addParameter(
            QgsProcessingParameterFile(
                self.DSM_RASTER_FOLDER,
                self.tr('FOLDER LOCATION FOR *DSM* RASTERS'),
                behavior=QgsProcessingParameterFile.Folder,
                extension='asc',
                defaultValue=str(dsmRasterFileLocationDefault)
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.DTM_RASTER_FOLDER,
                self.tr('FOLDER LOCATION FOR *DTM* RASTERS'),
                behavior=QgsProcessingParameterFile.Folder,
                extension='asc',
                defaultValue=str(dtmRasterFileLocationDefault)
            )
        )

 
        dsmRasterDefault = paths.dataDirectoryPath / (DSM_1M_LAYER_NAME + '.vrt')
        dtmRasterDefault = paths.dataDirectoryPath / (DTM_1M_LAYER_NAME + '.vrt')

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.DSM_RASTER_OUTPUT,
            self.tr(DSM_1M_LAYER_NAME),
            str(dsmRasterDefault), 
            False)
        )
        
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.DTM_RASTER_OUTPUT,
            self.tr(DTM_1M_LAYER_NAME),
            str(dtmRasterDefault), 
            False)
        )

 

#     # Fix the Coordinate Reference System of the given layer
#     # e.g. sometimes our algorithms return a layer with the wrong CRS!
#     def fixLayerCrs(self, inputLayer, outputFilePath, context, feedback):
#         parameters = {'INPUT':inputLayer, 
#             'TARGET_CRS':BRITISH_NATIONAL_GRID, 
#             'NODATA':-9999, 
#             'COPY_SUBDATASETS':0, 
#             'OPTIONS':'', 
#             'DATA_TYPE':0, 
#             'OUTPUT':str(outputFilePath)}
#         results = processing.run('gdal:translate', parameters, context=context, feedback=feedback)
#         dsmClippedLayer = results['OUTPUT']
#         return dsmClippedLayer


    def createVirtualRaster(self, inputRasterDirectory, virtualRasterOutputFilePath, context, feedback):
        # Order of steps:
    # 1 - Create a list of file paths from the directory
    # 2 - Call the "gdal:buildvirtualraster" algorithm, including this list
    # 3 - Rename the layer
        rasterDirectoryPath = Path(inputRasterDirectory) # Make a list of strings which are filenames of raster files within the raster directory
        fileNameList = [str(e) for e in rasterDirectoryPath.iterdir() if e.is_file()]
        msg = "Files = " + str(fileNameList)
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        parameters = {
            'INPUT':fileNameList, 
            'RESOLUTION':1, 
            'SEPARATE':False, 
            'ASSIGN_CRS':'EPSG:27700', # TODO: Make this a constant
            'SRC_NODATA':-9999, 
            'OUTPUT':str(virtualRasterOutputFilePath)}
        results = processing.run('gdal:buildvirtualraster', parameters, context=context, feedback=feedback)
        return results

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.

        paths=SolarDirectoryPaths()

        dsmRasterDirectory = self.parameterAsFile(parameters, self.DSM_RASTER_FOLDER, context)
        dtmRasterDirectory = self.parameterAsFile(parameters, self.DTM_RASTER_FOLDER, context)
        dsmRasterFilePath = self.parameterAsOutputLayer(parameters, self.DSM_RASTER_OUTPUT, context)
        dtmRasterFilePath = self.parameterAsOutputLayer(parameters, self.DTM_RASTER_OUTPUT, context)
        
#         (sink, dest_id) = self.parameterAsSink(parameters, self.ROOF_PLANES,
#                 context, source.fields(), source.wkbType(), source.sourceCrs())
        dsmVirtualRasterOutputFilePath = self.parameterAsOutputLayer(parameters, self.DSM_RASTER_OUTPUT, context)
        dtmVirtualRasterOutputFilePath = self.parameterAsOutputLayer(parameters, self.DTM_RASTER_OUTPUT, context)
        
        # Optional step to build rasters
        msg = "Starting - creating virtual rasters from raw data"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        
        dsmVirtualRaster=self.createVirtualRaster(dsmRasterDirectory, dsmVirtualRasterOutputFilePath, context, feedback) 
        dtmVirtualRaster=self.createVirtualRaster(dtmRasterDirectory, dtmVirtualRasterOutputFilePath, context, feedback) 
        
        results = {}
        results[DSM_1M_LAYER_NAME] = dsmVirtualRaster
        
        return results

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'virtualrasters'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return 'virtualrasters'

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
        return 'CAFS 0'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return VirtualRasterAlgorithm()
