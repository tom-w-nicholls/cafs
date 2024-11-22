# -*- coding: utf-8 -*-

"""
/***************************************************************************
 WebMapPreparationAlgorithm
                                 A QGIS plugin
 Filters the full list of candidate roofs for roofs suitable for Solar PV
 and calculates Solar PV output for each one
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
__date__ = '2020-10-04'
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



class WebMapPreparationAlgorithm(QgsProcessingAlgorithm):
    """
    Transforms the output of the Solar Suitable Roofs Algorithm (CAFS 4)
    From One CRS to another
    From: 27700 (British National Grid) which is the working CRS For our project 
    To: 3857 (WGS84) which is what Google Maps and Open Street Map use
    Then finally reduces the attributes down to those needed for the Solar Web Map
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    SUITABLE_ROOFS_INPUT = 'INPUT'

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    ROOF_PLANES_OUTPUT = 'ROOFS_OUTPUT' # This will be the name of the layer in the QGIS interface
    LOCAL_BUILDINGS_OUTPUT = 'BUILDINGS_OUTPUT' 
    SUITABLE_ROOFS_INPUT = 'SUITABLE_ROOFS'
    BUILDINGS_INPUT = 'FULL_BUILDINGS' # Reused from earlier algorithm
    LOCAL_BOUNDARY_INPUT = 'LOCAL_BOUNDARY'


    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        paths=SolarDirectoryPaths()
        suitableRoofPlanesInputDefault = paths.resultsDirectoryPath / (SUITABLE_ROOF_PLANES_LAYER_NAME + '.shp')               
        translatedSuitableRoofPlanesInputDefault = paths.resultsDirectoryPath / (TRANSLATED_SUITABLE_ROOF_PLANES_LAYER_NAME + '.shp')               

        # Input layers:
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SUITABLE_ROOFS_INPUT,
                self.tr('SUITABLE_ROOFS'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=str(suitableRoofPlanesInputDefault)

            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LOCAL_BOUNDARY_INPUT,
                self.tr('LOCAL_AREA'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=LOCAL_EXTENT_LAYER_NAME
            )
        )
        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.BUILDINGS_INPUT,
                self.tr('FULL BUILDINGS'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=FULL_AREA_BUILDINGS_LAYER_NAME
            )
        )



        localBuildingsOutputVectorDefaultPath = paths.dataDirectoryPath / (WEB_LOCAL_BUILDINGS_LAYER_NAME + '.shp')               

        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.LOCAL_BUILDINGS_OUTPUT,
                self.tr(self.LOCAL_BUILDINGS_OUTPUT),
                defaultValue=str(localBuildingsOutputVectorDefaultPath)
            )
        )
        
        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink (
            self.ROOF_PLANES_OUTPUT,
            self.tr(self.ROOF_PLANES_OUTPUT),
                defaultValue=str(translatedSuitableRoofPlanesInputDefault)
            )
        )


    ######################################################################
    # This algorithm simply translates the SUITABLE_ROOFS layer to a different 
    # coordinate reference system so that it can be used in the QGIS2WEB output 
    # The new coordinate system is WGS 84 (EPSG:3857) as used in webmaps
    ###################################################################################
 
    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """


        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        paths=SolarDirectoryPaths()

        source = self.parameterAsSource(parameters, self.SUITABLE_ROOFS_INPUT, context)
        buildingsLayer = self.parameterAsVectorLayer(parameters, self.BUILDINGS_INPUT, context)
        localExtentAreaLayer = self.parameterAsVectorLayer(parameters, self.LOCAL_BOUNDARY_INPUT, context)

        
        #  We need to supply a list of newFields
        # Rather than just recreating newFields from the source, I'll append a new field "area_plan"
        ID_ATTRIBUTE_NAME = "id"
        LATITUDE_ATTRIBUTE_NAME = "latitude"
        LONGITUDE_ATTRIBUTE_NAME = "longitude"
        ROOF_OUTPUT_ATTRIBUTE_NAME = "Output_kwh"
        NUMBER_OF_PANELS_ATTRIBUTE_NAME = "Num_panels"
         
        # Create the newFields for the new feature (only keep the ones we are interested in)
        originalFields = source.fields()
        newFields = QgsFields() 
        newFields.append(QgsField(ID_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(LATITUDE_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(LONGITUDE_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(NUMBER_OF_PANELS_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(ROOF_OUTPUT_ATTRIBUTE_NAME, QVariant.Double))
        idxLatitude = originalFields.indexFromName(LATITUDE_ATTRIBUTE_NAME)
        idxLongitude = originalFields.indexFromName(LONGITUDE_ATTRIBUTE_NAME)
        idxRoofOutput = originalFields.indexFromName(ROOF_OUTPUT_ATTRIBUTE_NAME)
        idxNumPanels = originalFields.indexFromName(NUMBER_OF_PANELS_ATTRIBUTE_NAME)
       
        try:
            destinationCrs = QgsCoordinateReferenceSystem(3857, QgsCoordinateReferenceSystem.EpsgCrsId)
            sourceCrs = QgsCoordinateReferenceSystem(27700, QgsCoordinateReferenceSystem.EpsgCrsId)
            coordTransform = QgsCoordinateTransform(sourceCrs, destinationCrs, QgsProject.instance())

            # Sink is a QgsProcessingParameterFeatureSink
            # Note the change in CRS from the source!
            (sink, dest_id) = self.parameterAsSink(parameters, self.ROOF_PLANES_OUTPUT, context, newFields, source.wkbType(), destinationCrs)

                        
            # Compute the number of steps to display within the progress bar and
            # get features from source
            total = 100.0 / source.featureCount() if source.featureCount() else 0
            features = source.getFeatures()
            
            # Needed to transform National grid to WGS84
            # 3857 is the same as WGS84, which is what google maps and open street map use
            # 27700 is British National Grid, which is coordinates that we are using.
            
            # Find the existing source and iterate over its features (polygons)
            # We need to clone the original geometry (the points of the polygon - represented by the underlying AbstractGeometry object) 
            # and the new area attribute for each feature.    

                
            for current, feature in enumerate(features):
                # Stop the algorithm if cancel button has been clicked
                if feedback.isCanceled():
                    break
    
                # Update the progress bar
                feedback.setProgress(int(current * total))
                geom = feature.geometry()
                if geom: # only if not null, otherwise don't include this feature in the new source
                    # Step 52: aspect in degrees

                    abstractGeometry = geom.get().clone() # We have to clone geometry to avoid sharing references
                    newGeometry = QgsGeometry(abstractGeometry)
                    newFeature=QgsFeature(newFields)  # Create a new empty feature which we will add to the sink layer

                    # Now create the newFields for the new feature, and copy over existing newFields (aspect-class and slope-class) from the 
                    # original feature before we add the area_plan field

                    newGeometry.transform(coordTransform)
                    newFeature.setGeometry(newGeometry)

                    newFeature[ID_ATTRIBUTE_NAME]=feature[ID_ATTRIBUTE_NAME]
                    newFeature[LATITUDE_ATTRIBUTE_NAME]=int(feature[LATITUDE_ATTRIBUTE_NAME]) # integer values, throw away the rest
                    newFeature[LONGITUDE_ATTRIBUTE_NAME]=int(feature[LONGITUDE_ATTRIBUTE_NAME]) # integer values, throw away the rest
                    newFeature[ROOF_OUTPUT_ATTRIBUTE_NAME]=round_sig(feature[ROOF_OUTPUT_ATTRIBUTE_NAME])  # round to 2 significant figures
                    newFeature[NUMBER_OF_PANELS_ATTRIBUTE_NAME]=feature[NUMBER_OF_PANELS_ATTRIBUTE_NAME]
                    sink.addFeature(newFeature, QgsFeatureSink.FastInsert)
                    
                        
        except Exception as err:
            log("Exception encountered: " + str(err))
            raise QgsProcessingException(self.tr("Problem encountered during the processing :" + traceback.format_exc()))

        # Now, we need to clip the full buildings layer to output simply the buildings within the local boundary as we have defined it

        clippedBuildingsFilePath = self.parameterAsOutputLayer(parameters, self.LOCAL_BUILDINGS_OUTPUT, context)
        parameters = {
            'INPUT':buildingsLayer,
            'OVERLAY':localExtentAreaLayer,
            'OUTPUT':str(clippedBuildingsFilePath)}
        results = processing.run("native:clip",parameters, feedback=feedback)

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        results = {}
        results[self.LOCAL_BUILDINGS_OUTPUT] = clippedBuildingsFilePath 
        results[self.ROOF_PLANES_OUTPUT] = dest_id
        return results

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'webprepare'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Prepare Layer for QGIS2WEB')

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
        return 'CAFS 6'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return WebMapPreparationAlgorithm()

# Helper function to round to (2) significant digits
from math import log10, floor
def round_sig(x, sig=2):
	return round(x, sig-int(floor(log10(abs(x))))-1)
