# -*- coding: utf-8 -*-

"""
/***************************************************************************
 RoofEnergyCalculator
                                 A QGIS plugin
 Filters for suitable roofs and calculates Solar PV output for each one
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



class RoofEnergyCalculatorAlgorithm(QgsProcessingAlgorithm):
    """
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    ROOF_PLANES_OUTPUT = SUITABLE_ROOF_PLANES_LAYER_NAME # This will be the name of the layer in the QGIS interface
    INPUT = "INPUT"
    CSV_OUTPUT = 'CSV_OUTPUT'
    DATA_DIRECTORY = "DATA_DIRECTORY"   
    RESULTS_DIRECTORY = "RESULTS_DIRECTORY"   

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        paths=SolarDirectoryPaths()

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

    ######################################################################
    # This function represents steps 45 to 48 of Alex's methodology log
    # - to calculate the area of each feature and remove any with NULL area.
    # input layer is a QgsProcessingFeatureSource
    # output layer is a QgsProcessingFeatureSink
    # both defined in a dialog
    # We take features one by one from the input layer
    # We calculate the area of each feature
    # If it is null, we discard it
    # if it is non-null, we create a new feature
    # we define the fields in the new feature
    # we add a new field "area_plan"
    # we add the attributes
    # we clone the geometry
    # and we insert the new attribute "area_plan" as the calculated area of the feature.
    # We also calculate latitude and longitude as attributes for each feature.
    ###################################################################################
 
    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """


        # Create Paths to data and results directory dynamically, and create those dirs if they don't exist.
        paths=SolarDirectoryPaths()
        dataString = self.parameterAsString(parameters, self.DATA_DIRECTORY, context)
        dataPath = paths.projectPath / dataString
        dataPath.mkdir(parents=True, exist_ok=True)
        # source = self.parameterAsSource(parameters, self.INPUT, context)

        resultsString = self.parameterAsString(parameters, self.RESULTS_DIRECTORY, context)
        resultsPath = paths.projectPath / resultsString
        resultsPath.mkdir(parents=True, exist_ok=True)
        csvOutputFilePath = resultsPath / (CSV_OUTPUT_FILENAME + '.csv')

        processedRoofPlanesFilePath = dataPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')
        processedRoofPlanesLayer = QgsProcessingUtils.mapLayerFromString(str(processedRoofPlanesFilePath), context) 
        

        #  We need to supply a list of newFields
        # Rather than just recreating newFields from the source, I'll append a new field "area_plan"
        ID_ATTRIBUTE_NAME = "id"
        AREA_PLAN_ATTRIBUTE_NAME = "area_plan"
        AREA_TRUE_ATTRIBUTE_NAME = "area_true"
        LATITUDE_ATTRIBUTE_NAME = "latitude"
        LONGITUDE_ATTRIBUTE_NAME = "longitude"
        ASPECT_ATTRIBUTE_NAME = "Aspect_mean"
        COSINE_ATTRIBUTE_NAME = "C_mean"
        SINE_ATTRIBUTE_NAME = "S_mean"
        SLOPE_ATTRIBUTE_NAME = "Slope_mean"
        IRRADIATION_ATTRIBUTE_NAME = "Irrad_mean"
        SHADE_ATTRIBUTE_NAME = "Shade_mean"
        ROOF_OUTPUT_ATTRIBUTE_NAME = "Output_kwh"
        ROOF_IS_FLAT_ATTRIBUTE_NAME = "Roof_flat"
        NUMBER_OF_PANELS_ATTRIBUTE_NAME = "Num_panels"
        RADIANS_TO_DEGREES = 180 / pi
        PANEL_FIT_FACTOR = 0.7284 # This is Alex's estimated value - multiply this by the actual area to get the number of panels
        FLAT_PANEL_FIT_FACTOR = 0.7
        REAL_PANEL_AREA = 1.65 # square metres
        EFFECTIVE_PANEL_AREA = 1.75 # accounts for gaps between the panels
        PANEL_YIELD = 0.2 
        PANEL_EFFICIENCY = 0.789 # 21% energy loss
        
        # Panels smaller than 16 square metres are no use for installation of Solar PV
        MINIMUM_USEFUL_AREA = 16 # We should parameterize this for the end user
        # Also a slope above 60 aspectMean is useless
        MAXIMUM_USEFUL_SLOPE = 60 # ditto
         
        # Create the newFields for the new feature (only keep the ones we are interested in)
        originalFields = processedRoofPlanesLayer.fields()
        newFields = QgsFields() 
        newFields.append(QgsField(ID_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(LATITUDE_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(LONGITUDE_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(AREA_PLAN_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(AREA_TRUE_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(ASPECT_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(SLOPE_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(SHADE_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(IRRADIATION_ATTRIBUTE_NAME, QVariant.Double))
        newFields.append(QgsField(NUMBER_OF_PANELS_ATTRIBUTE_NAME, QVariant.Int))
        newFields.append(QgsField(ROOF_IS_FLAT_ATTRIBUTE_NAME, QVariant.String))
        newFields.append(QgsField(ROOF_OUTPUT_ATTRIBUTE_NAME, QVariant.Double))
        idxAreaPlan = originalFields.indexFromName(AREA_PLAN_ATTRIBUTE_NAME)
        idxAreaTrue = originalFields.indexFromName(AREA_TRUE_ATTRIBUTE_NAME)
        idxLatitude = originalFields.indexFromName(LATITUDE_ATTRIBUTE_NAME)
        idxLongitude = originalFields.indexFromName(LONGITUDE_ATTRIBUTE_NAME)
        idxAspectMean = originalFields.indexFromName(ASPECT_ATTRIBUTE_NAME)
        idxCosine = originalFields.indexFromName(COSINE_ATTRIBUTE_NAME)
        idxSine = originalFields.indexFromName(SINE_ATTRIBUTE_NAME)
        idxSlopeMean = originalFields.indexFromName(SLOPE_ATTRIBUTE_NAME)
        idxShadeMean = originalFields.indexFromName(SHADE_ATTRIBUTE_NAME)
        idxEnergyMean = originalFields.indexFromName(IRRADIATION_ATTRIBUTE_NAME)
        idxRoofOutput = originalFields.indexFromName(ROOF_OUTPUT_ATTRIBUTE_NAME)
        idxNumPanels = originalFields.indexFromName(NUMBER_OF_PANELS_ATTRIBUTE_NAME)
        idxRoofFlat = originalFields.indexFromName(ROOF_IS_FLAT_ATTRIBUTE_NAME)
 
        
       
        try:
            # Compute the number of steps to display within the progress bar and
            # get features from source
            total = 100.0 / processedRoofPlanesLayer.featureCount() if processedRoofPlanesLayer.featureCount() else 0
            features = processedRoofPlanesLayer.getFeatures()
            id=1 # Temporary counter to allow us to examine the first few rows and then exit (for testing)
            
            # Needed to transform National grid to latitude and longitude
            # 3857 is the same as WGS84, which is what google maps and open street map use
            # 27700 is British National Grid, which is coordinates that we are using.``
            sourceCrs = QgsCoordinateReferenceSystem(27700, QgsCoordinateReferenceSystem.EpsgCrsId)
            destinationCrs = QgsCoordinateReferenceSystem(3857, QgsCoordinateReferenceSystem.EpsgCrsId)
            coordTransform = QgsCoordinateTransform(sourceCrs, destinationCrs, QgsProject.instance())

            suitableRoofsPath = resultsPath / (SUITABLE_ROOF_PLANES_LAYER_NAME + '.shp')
            log(f"Suitable Roofs Path = {suitableRoofsPath}")

            writer = QgsVectorFileWriter(str(suitableRoofsPath), 
                                    getSystemEncoding(),
                                    newFields,
                                    QgsWkbTypes.Polygon, 
                                    sourceCrs,
                                    "ESRI Shapefile")
 
            
            # Find the existing source and iterate over its features (polygons)
            # We need to clone the original geometry (the points of the polygon - represented by the underlying AbstractGeometry object) 
            # and the new area attribute for each feature.    
            totalCalculatedOutput=0
            fieldNames = [field.name() for field in newFields]
            with open(csvOutputFilePath, 'w') as outputFile:
                
                # write header
                line = ','.join(name for name in fieldNames) + '\n'
                outputFile.write(line)
                
                for current, feature in enumerate(features):
                    # Stop the algorithm if cancel button has been clicked
                    if feedback.isCanceled():
                        break
        
                    # Update the progress bar
                    feedback.setProgress(int(current * total))
                    geom = feature.geometry()
                    if geom: # only if not null, otherwise don't include this feature in the new source
                        # Step 52: aspect in degrees
                        aspectInRadians=0
                        cMean=float(feature.attribute(idxCosine))
                        sMean=float(feature.attribute(idxSine))
                        arctanValue = atan(sMean / cMean)
                        if(cMean>0 and sMean>0):
                            aspectInRadians=arctanValue
                        elif(cMean<0):
                            aspectInRadians=arctanValue + pi
                        else:
                            aspectInRadians=arctanValue + pi*2
                        aspectMean = aspectInRadians * RADIANS_TO_DEGREES
                        # step 55: true area of the roof:
                        slopeMean=float(feature.attribute(idxSlopeMean))
                        areaTrue=float(geom.area())/cos(slopeMean/RADIANS_TO_DEGREES)
                        shadeMean=float(feature.attribute(idxShadeMean))
                        
                        #  Step 57: only add the feature to the new layer if area is greater than 16 square metres
                        #  Step 58: also ignore slope above 60 aspectMean
                        #  Step 59: Also filter by Aspect (if slope>10 and roof not essentially flat)
                        #  Step 76: Remove all roofs that are too shaded (i.e. have a shade_mean below 0.5)
                        aspectFilter=(slopeMean>10 and (aspectMean < 67.5 or aspectMean > 292.5)) # features to be deleted
                        if(areaTrue>MINIMUM_USEFUL_AREA and slopeMean <= 60 and (not aspectFilter) and shadeMean>=0.5):
                            abstractGeometry = geom.get().clone() # We have to clone geometry to avoid sharing references
                            newGeometry = QgsGeometry(abstractGeometry)
                            # Ensure that coordinates are in British National Grid rather than the 27700 CRS.
                            # newGeometry.transform(coordTransform)
                            newFeature=QgsFeature(newFields)  # Create a new empty feature which we will add to the sink layer
                            # Now create the newFields for the new feature, and copy over existing newFields (aspect-class and slope-class) from the 
                            # original feature before we add the area_plan field
                            newFeature.setGeometry(newGeometry)
                            # NEW - drop the coordination transformation as a test
                            point = newGeometry.centroid().asPoint()
    #                         newFeature.setAttribute(idxLatitude, point.x())
    #                         newFeature.setAttribute(idxLongitude, point.y())
    #                         newFeature.setAttribute(idxAspectMean, aspectMean)
    #                         newFeature.setAttribute(idxSlopeMean, slopeMean)
    #                         newFeature.setAttribute(idxAreaPlan, geom.area()) 
                            # Do the energy calculation and add the feature to the new layer
        #                     Step 84: Actual irradiation is 1.1x for flat roofs (i.e. if slope<10)
        #                     Step 90: Calculate the expected number of panels in each roof
        #                     Step 92: Find the energy output for each roof plane
        #                     Step 95: keep a running total of the total energy output for the entire area
                            energyOverThisRoof=feature.attribute(idxEnergyMean)
                            roofIsFlat = True if slopeMean < 10 else False
                            fitFactor = FLAT_PANEL_FIT_FACTOR if roofIsFlat else PANEL_FIT_FACTOR
                            integerNumberOfPanels = floor(areaTrue*fitFactor/EFFECTIVE_PANEL_AREA)
                            roofOutput = REAL_PANEL_AREA * integerNumberOfPanels * PANEL_YIELD * PANEL_EFFICIENCY * energyOverThisRoof
    #                         newFeature.setAttribute(idxRoofOutput, roofOutput)
    #                         newFeature.setAttribute(idxAreaTrue, areaTrue)
    #                         newFeature.setAttribute(idxEnergyMean, energyOverThisRoof)
    #                         newFeature.setAttribute(idxNumPanels, integerNumberOfPanels)
    #                         newFeature.setAttribute(idxRoofFlat, "Y" if roofIsFlat else "N")
    #                         newFeature.setAttribute(idxShadeMean, shadeMean)
                            newFeature[ID_ATTRIBUTE_NAME]=id
                            newFeature[LATITUDE_ATTRIBUTE_NAME]=point.x()
                            newFeature[LONGITUDE_ATTRIBUTE_NAME]=point.y()
                            newFeature[ASPECT_ATTRIBUTE_NAME]=aspectMean
                            newFeature[SLOPE_ATTRIBUTE_NAME]=slopeMean
                            newFeature[AREA_PLAN_ATTRIBUTE_NAME]=geom.area()
                            newFeature[AREA_TRUE_ATTRIBUTE_NAME]=areaTrue
                            newFeature[ROOF_OUTPUT_ATTRIBUTE_NAME]=roofOutput
                            newFeature[ROOF_IS_FLAT_ATTRIBUTE_NAME]="Y" if roofIsFlat else "N"
                            newFeature[IRRADIATION_ATTRIBUTE_NAME]=energyOverThisRoof
                            newFeature[NUMBER_OF_PANELS_ATTRIBUTE_NAME]=integerNumberOfPanels
                            newFeature[SHADE_ATTRIBUTE_NAME]=shadeMean
                            
                            if writer.addFeature(newFeature) == 0:
                                log("Failed to add feature")
                            
                            # Write this feature to the csv file
                            line = ','.join(str(newFeature[name]) for name in fieldNames) + '\n'
                            outputFile.write(line)
    
                            totalCalculatedOutput = totalCalculatedOutput + roofOutput
                            id=id+1
        #   Add these three lines in to do a sample data run of a few lines:                    
        #                 id=id+1
        #             if id>100:
        #                 break
                        
#                     TODO: Add in steps 82, 85, 90, 92, 95 here in the loop and find a total irradiation for the entire area
        except Exception as err:
            msg = "Exception encountered: " + str(err)
            QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
            raise QgsProcessingException(self.tr("Problem encountered during the processing :" + traceback.format_exc()))

        # Write the total energy output of all roofs to the Message Log:
        msg = "Total Energy Output of All Roofs = " + str(totalCalculatedOutput) + " kWh"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)


        # Return the results of the algorithm. In our case, no results so an empty dict.
        results = {}
        return results

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'suitableroofs'

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
        return 'CAFS 4'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        return self.tr("Fourth CAFS algorithm: Filter roofs to select for suitability for solar")

    def createInstance(self):
        return RoofEnergyCalculatorAlgorithm()
