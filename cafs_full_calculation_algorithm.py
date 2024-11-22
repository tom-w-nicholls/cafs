# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CAfSFullCalculationAlgorithm
                                 A QGIS plugin
 Calls all of the other plugins in turn.
 An overarching plugin to run the entire suite of commands in one pass
        copyright            : (c) 2021 by Cumbria Action for Sustainability
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


class CAfSFullCalculationAlgorithm(QgsProcessingAlgorithm):
    """
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.


    BUILDINGS_LAYER = "BUILDINGS_LAYER"
    LOCAL_EXTENT = "LOCAL_EXTENT" 
    DATA_DIRECTORY = "DATA_DIRECTORY"   
    RESULTS_DIRECTORY = "RESULTS_DIRECTORY"   
    DTM_LAYER = "DTM_LAYER"
    DSM_LAYER = "DSM_LAYER"    
    METEOROLOGICAL_RAW="METEOROLOGICAL_DATA_FILE"
    CHECKBOX='USE_WIDE_AREA'
    WIDE_AREA = 'WIDE_LAYER'    
    
    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # Input layers:
        
        paths=SolarDirectoryPaths()
        dataPath = paths.dataDirectoryPath

        self.addParameter(
            QgsProcessingParameterString(
                self.DATA_DIRECTORY,
                self.tr(self.DATA_DIRECTORY),
                defaultValue=DATA_STRING
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.RESULTS_DIRECTORY,
                self.tr(self.RESULTS_DIRECTORY),
                defaultValue=RESULTS_STRING
            )
        )



        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LOCAL_EXTENT,
                self.tr('LOCAL_AREA'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=LOCAL_EXTENT_LAYER_NAME
            )
        )
        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.BUILDINGS_LAYER,
                self.tr('BUILDINGS_LAYER'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=FULL_AREA_BUILDINGS_LAYER_NAME
            )
        )

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DTM_LAYER,
            self.tr("DTM"), 
            self.DTM_LAYER, 
            False)
        )
        
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DSM_LAYER,
            self.tr("DSM"), 
            self.DSM_LAYER, 
            False)
        )

        self.addParameter(QgsProcessingParameterFile(
                self.METEOROLOGICAL_RAW,
                self.tr('METEOROLOGICAL_DATA_FILE'),
                extension="epw"
        ))

        self.addParameter(QgsProcessingParameterBoolean(self.CHECKBOX,
                                                        self.tr('Use Wide Area'),
                                                        defaultValue=False))

        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.WIDE_AREA,
                self.tr('WIDE_EXTENT_LAYER_NAME'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=PROCESSED_ROOF_PLANES_LAYER_NAME
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        
        dsmLayer = self.parameterAsRasterLayer(parameters, self.DSM_LAYER, context)
        dtmLayer = self.parameterAsRasterLayer(parameters, self.DTM_LAYER, context)
        buildingsLayer = self.parameterAsVectorLayer(parameters, self.BUILDINGS_LAYER, context)
        localExtentAreaLayer = self.parameterAsVectorLayer(parameters, self.LOCAL_EXTENT, context)

        dataString = self.parameterAsString(parameters, self.DATA_DIRECTORY, context)
        resultsString = self.parameterAsString(parameters, self.RESULTS_DIRECTORY, context)

        wideAreaHighResLayer = self.parameterAsVectorLayer(parameters, self.WIDE_AREA, context)
        useWideArea = self.parameterAsBool(parameters, self.CHECKBOX, context)
        meteorologicalDataRawFilePath = self.parameterAsFile(parameters, self.METEOROLOGICAL_RAW, context)

        log(f"Local_AREA is {str(localExtentAreaLayer)}")
        log(f"local area sourcename is {localExtentAreaLayer.sourceName()}")
        log(f"local area feature size is {localExtentAreaLayer.featureCount()}")
        log(f"Starting roofprocessor for DATA_DIRECTORY: {dataString}")
        parameters = {
            'DATA_DIRECTORY':dataString,
            'LOCAL_EXTENT':localExtentAreaLayer.source(),
            'BUILDINGS_LAYER':buildingsLayer,
            'DTM_LAYER':dtmLayer.source(),
            'DSM_LAYER':dsmLayer.source()
        }
        processing.run('CAFS:roofprocessor',parameters, context=context, feedback=feedback)

        log(f"Starting shadow for DATA_DIRECTORY: {dataString}")
        parameters = {
            'DATA_DIRECTORY':dataString,
            'DSM_LAYER':dsmLayer,
            'USE_WIDE_AREA':useWideArea,
            'WIDE_LAYER':wideAreaHighResLayer,
            'LOCAL_LAYER':localExtentAreaLayer,
            'DTM_LAYER':dtmLayer
        }
        processing.run('CAFS:shadow',parameters, context=context, feedback=feedback)

        log(f"Starting solar for DATA_DIRECTORY: {dataString}")
        parameters = {
            'DATA_DIRECTORY':dataString,
            'METEOROLOGICAL_DATA_FILE':meteorologicalDataRawFilePath
        }
        processing.run('CAFS:solar',parameters, context=context, feedback=feedback)

        log(f"Starting suitableroofs for DATA_DIRECTORY: {dataString}")
        parameters = {
            'DATA_DIRECTORY':dataString,
            'RESULTS_DIRECTORY':resultsString        
        }
        processing.run('CAFS:suitableroofs',parameters, context=context, feedback=feedback)
        log(f"Finished calculations. Results are in the following directory: {resultsString}")

        return {}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'calculate'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return 'calculate'

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
        return 'CAFS FULL'

    def shortHelpString(self):
        return self.tr("Runs all four algorithms of the CAFS series in order to calculate the roof areas suitable for Solar PV")

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CAfSFullCalculationAlgorithm()
