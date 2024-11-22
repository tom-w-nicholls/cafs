# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Plugin for sorting solar roof results into an appropriate order for web output
                                 A QGIS plugin
 Calculates shadows of a geographical region based on obstructions
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

__author__ = 'Tom Nicholls'
__date__ = '2020-03-03'
__copyright__ = '(C) 2020 by Tom Nicholls'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import (QCoreApplication,
                              QVariant)
# from qgis.core import (QgsProcessing,
#                        QgsFeatureSink,
#                        QgsProcessingAlgorithm,
#                        QgsProcessingParameterFeatureSource,
#                        QgsProcessingParameterFeatureSink,
#                        QgsProject,
#                        QgsVectorLayer,
#                        QgsFields,
#                        QgsField)

from qgis.core import *
from math import pi, atan, cos, floor
from pathlib import Path # Post python 3.4
from pyproj import Proj, transform # For coordinate transformations
from .SolarConstants  import *
import traceback
from .SolarDirectoryPaths import SolarDirectoryPaths



class SortResultsAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a new layer from an existing vector layer
    Sorts features by the energy attribute ROOF_ENERGY_ATTRIBUTE_NAME
    The Id field will be reset to the (descending) order of energy output.
    tldr: just tidies up the layer ready for output.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    SORTED_SUITABLE_ROOF_PLANES_OUTPUT = "Sorted Suitable Roof Output Layer Name" # This will be the name of the input box as it appears in the QGIS interface
    INPUT = 'INPUT'
    CSV_OUTPUT = 'CSV_OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        paths=SolarDirectoryPaths()
        sortedSuitableRoofPlanesOutputDefault = paths.resultsDirectoryPath / (SORTED_SUITABLE_ROOF_PLANES_LAYER_NAME + '.shp')               
        mergedSuitablRoofPlanesInputDefault = paths.dataDirectoryPath / (MERGED_SUITABLE_ROOF_PLANES_LAYER_NAME + '.shp')               

        # Input layer is the set of merged vector features representing the roofs suitable for PV.
        # These need to be sorted and given appropriate IDs
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Merged Suitable Roof Layer'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=str(mergedSuitablRoofPlanesInputDefault)

            )
        )
        
        # User must define a CSV file for the final output
        csvOutputFilePath = paths.resultsDirectoryPath / (SORTED_CSV_OUTPUT_FILENAME + '.csv')
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.CSV_OUTPUT,
                self.tr('Sorted Suitable Roofs CSV'),
                'CSV files (*.csv)',
                defaultValue=str(csvOutputFilePath)
            )
        )


        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink (
            self.SORTED_SUITABLE_ROOF_PLANES_OUTPUT,
            self.tr(self.SORTED_SUITABLE_ROOF_PLANES_OUTPUT),
                defaultValue=str(sortedSuitableRoofPlanesOutputDefault)
            )
        )


    ######################################################################
    # An extra step for when we have multiple results sets
    # It takes a merged SUITABLE_ROOFS file and orders them by energy output
    # Recalculating the ID before output
    ###################################################################################
 
    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """


        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        paths=SolarDirectoryPaths()

        source = self.parameterAsSource(parameters, self.INPUT, context)
        
        ID_ATTRIBUTE_NAME = "id"
         
        # Create the newFields for the new feature (only keep the ones we are interested in)
        originalFields = source.fields()

        csvOutputFilePath = self.parameterAsFileOutput(parameters, self.CSV_OUTPUT, context)
       
        try:
            # Sink is a QgsProcessingParameterFeatureSink
            (sink, dest_id) = self.parameterAsSink(parameters, self.SORTED_SUITABLE_ROOF_PLANES_OUTPUT, context, originalFields, source.wkbType(), source.sourceCrs())

                        
            # Compute the number of steps to display within the progress bar and
            # get features from source
            total = 100.0 / source.featureCount() if source.featureCount() else 0
            features = source.getFeatures()
            id=1 # Counter to allow us to examine the first few rows and then exit (for testing)
            
            # # Needed to transform National grid to latitude and longitude
            # # 3857 is the same as WGS84, which is what google maps and open street map use
            # # 27700 is British National Grid, which is coordinates that we are using.``
            # sourceCrs = QgsCoordinateReferenceSystem(27700, QgsCoordinateReferenceSystem.EpsgCrsId)
            # destinationCrs = QgsCoordinateReferenceSystem(3857, QgsCoordinateReferenceSystem.EpsgCrsId)
            # coordTransform = QgsCoordinateTransform(sourceCrs, destinationCrs, QgsProject.instance())
            
    
            # SORT THE FEATURES IN THE INPUT LAYER, THEN OUTPUT THEM TO THE CSV FILE.

            # Create a sorted list of features. The `sorted` function
            # will read all features into a list and return a new list
            # sorted in this case by the features name value returned
            # by the `get_name` function
            sortedFeatures = sorted(features, key=getEnergy, reverse=True)
                   
            totalCalculatedOutput=0
            fieldNames = [field.name() for field in originalFields]
            with open(csvOutputFilePath, 'w') as outputFile:
                
                # write header
                line = ','.join(name for name in fieldNames) + '\n'
                outputFile.write(line)

                # Use the field names of the existing source layer (because some get truncated from their defaults:
                # e.g. "Aspect_Mean" becomes "Aspect_Mea")
                for feature in sortedFeatures:
                    feature[ID_ATTRIBUTE_NAME]=id
                    line = ','.join(str(feature[name]) for name in fieldNames) + '\n'
                    outputFile.write(line)                    
                    sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    log( f"id = {id}, Energy = {getEnergy(feature)}kwH" )
                    #totalCalculatedOutput = totalCalculatedOutput + roofOutput
                    id=id+1

        except Exception as err:
            msg = "Exception encountered: " + str(err)
            QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
            raise QgsProcessingException(self.tr("Problem encountered during the processing :" + traceback.format_exc()))

        results = {}
        results[self.SORTED_SUITABLE_ROOF_PLANES_OUTPUT] = dest_id
        results[self.CSV_OUTPUT] = csvOutputFilePath
        return results

                    


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'sort'

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
        return 'CAFS 5'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return SortResultsAlgorithm()


def getEnergy(f):
    return f[ROOF_ENERGY_ATTRIBUTE_NAME]
