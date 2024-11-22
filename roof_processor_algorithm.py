# -*- coding: utf-8 -*-

"""
/***************************************************************************
 RoofProcessor
                                 A QGIS plugin
 Finds all candidate roofs within the geographic area
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


class RoofProcessorAlgorithm(QgsProcessingAlgorithm):
    """
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.


    BUILDINGS_LAYER = "BUILDINGS_LAYER"
    LOCAL_AREA = "LOCAL_EXTENT" 
    DATA_DIRECTORY = "DATA_DIRECTORY"   
    DTM_LAYER = "DTM_LAYER"
    DSM_LAYER = "DSM_LAYER"
   
    
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
            QgsProcessingParameterVectorLayer(
                self.LOCAL_AREA,
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

        # Output layers: None
 
    def processAlgorithm(self, parameters, context, feedback):
        """
        Finds all candidate roofs based on known building locations and 3D profile of the landscapes
        regardless of their suitability for solar
        """

        paths=SolarDirectoryPaths()
        
        dsmLayer = self.parameterAsRasterLayer(parameters, self.DSM_LAYER, context)
        dtmLayer = self.parameterAsRasterLayer(parameters, self.DTM_LAYER, context)
        buildingsLayer = self.parameterAsVectorLayer(parameters, self.BUILDINGS_LAYER, context)
        localExtentAreaLayer = self.parameterAsVectorLayer(parameters, self.LOCAL_AREA, context)
        dataString = self.parameterAsString(parameters, self.DATA_DIRECTORY, context)
        dataPath = paths.projectPath / dataString
        dataPath.mkdir(parents=True, exist_ok=True)
        
        # Step 64 - clip DSM raster by local area extent
        msg = "Starting Step 64 - clip DSM layer by local extent"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        
        tempResultOutputPath = dataPath / 'clip-temp.tif'
        dsmClippedFilePath = dataPath / (DSM_1M_CLIPPED_LAYER_NAME + '.tif')
        parameters = {
            'INPUT':dsmLayer,
            'PROJWIN':localExtentAreaLayer,
            'NODATA':-9999,
            'OPTIONS':'',
            'DATA_TYPE':0,
            '--overwrite': True,
            'OUTPUT':str(tempResultOutputPath)}
        results = processing.run('gdal:cliprasterbyextent',parameters, context=context, feedback=feedback)
        # CRS is wrong for above output, so we now have to fix this!
        dsmClippedLayer = fixLayerCrs(results['OUTPUT'], dsmClippedFilePath, context, feedback)

        # Extra step 64b - clip DTM layer by local extent, to save on processing time
        msg = "Starting 64b - clip DTM layer by local extent"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        tempResultOutputPath2 = dataPath / 'clip-temp2.tif'
        parameters = {
            'INPUT':dtmLayer,
            'PROJWIN':localExtentAreaLayer,
            'NODATA':-9999,
            'OPTIONS':'',
            'DATA_TYPE':0,
            '--overwrite': True,
            'OUTPUT':str(tempResultOutputPath2)}
        results = processing.run('gdal:cliprasterbyextent',parameters, context=context, feedback=feedback)
        dtmClippedFilePath = dataPath / (DTM_1M_CLIPPED_LAYER_NAME + '.tif')
        dtmClippedLayer = fixLayerCrs(results['OUTPUT'], dtmClippedFilePath, context, feedback)

        
        # Step 15 - Subtract DTM from DSM but used clipped versions to save time:
        # we don't even bother to save the full DSM-DTM raster as it is no use to us
        msg = "Starting Step 15 - DSM - DTM clipped layer subtraction"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        
        tempResultOutputPath3 = dataPath / 'clip-temp3.tif'
        dsmMinusDtmClippedFilePath = dataPath / (DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME + '.tif')
        parameters = {
            'INPUT_A' : dsmClippedLayer,
            'BAND_A' : 1,
            'INPUT_B' : dtmClippedLayer,
            'BAND_B' : 1,
            'FORMULA' : 'A - B',   
#             '--overwrite': True,
            'NODATA':-9999,
            'OUTPUT':str(tempResultOutputPath3)}
        results = processing.run('gdal:rastercalculator',parameters, context=context, feedback=feedback)
        dsmMinusDtmClippedLayer = results['OUTPUT']
        dsmMinusDtmClippedLayer = fixLayerCrs(results['OUTPUT'], dsmMinusDtmClippedFilePath, context, feedback)

        
        # Step 19  - calculate aspect 
        msg = "Starting Step 19 - Aspect Calculation"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        
        aspect2mFilePath = dataPath / (ASPECT_LAYER_NAME +'.tif')
        parameters = {
            'INPUT': dsmMinusDtmClippedLayer, 
            'BAND':1, 
            'COMPUTE_EDGES':False, 
            '--overwrite': True,
            'OUTPUT':str(aspect2mFilePath)}
        results = processing.run("gdal:aspect", parameters, context=context, feedback=feedback)
        aspectLayer = results['OUTPUT']
#         aspectLayer.setCrs(BRITISH_NATIONAL_GRID)
       
        # Step 20 - calculate slope, as per step 19
        msg = "Starting Step 20 - Slope Calculation"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
        
        slope2mFilePath = dataPath / (SLOPE_LAYER_NAME + '.tif')
        parameters = {
            'INPUT':dsmMinusDtmClippedLayer, 
            'BAND':1, 
            'COMPUTE_EDGES':False, 
            '--overwrite': True,
            'OUTPUT':str(slope2mFilePath)}
        results = processing.run("gdal:slope", parameters, context=context, feedback=feedback)
        slopeLayer = results['OUTPUT']
        
        # Step 22 Reclassify by table  - to remove data below 2 metres from ground elevation
        msg = "Starting Step 22 - Remove data below 2 metres"
        QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)

        dsmMinusdtmAboveTwoMetresFile = dataPath / (DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME + '.tif')
        parameters = {
            'INPUT_RASTER':dsmMinusDtmClippedLayer,
            'RASTER_BAND':1,
            'TABLE':['',2,-9999],
            'NO_DATA':-9999,
            'RANGE_BOUNDARIES':0,
            'NODATA_FOR_MISSING':False,
            'DATA_TYPE':5,
            '--overwrite': True,
            'OUTPUT':str(dsmMinusdtmAboveTwoMetresFile)}
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        dsmMinusdtmAboveTwoMetresLayer = results['OUTPUT']

        # Step 23.1 - calculate aspect with data over 2m only
        aspect2mFilePath = dataPath / (ASPECT_2M_LAYER_NAME + '.tif')
        parameters = {
            'INPUT': dsmMinusdtmAboveTwoMetresLayer, 
            'BAND':1, 
            'COMPUTE_EDGES':True, 
            '--overwrite': True,
            'OUTPUT':str(aspect2mFilePath)}
        results = processing.run("gdal:aspect",parameters, context=context, feedback=feedback)
        aspect2mLayer = results['OUTPUT']


        slope2mFilePath = dataPath / (SLOPE_2M_LAYER_NAME + '.tif')
        parameters = {
            'INPUT':dsmMinusdtmAboveTwoMetresLayer, 
            'BAND':1, 
            'COMPUTE_EDGES':True, 
            '--overwrite': True,
            'OUTPUT':str(slope2mFilePath)}
        results = processing.run("gdal:slope", parameters, context=context, feedback=feedback)
        slope2mLayer = results['OUTPUT']
        
        # Step 27 Reclassify aspect data into classes:1,2,3,4

        aspectReclassifiedFilePath = dataPath / (ASPECT_RECLASSIFIED_LAYER_NAME + '.tif')
        parameters = {
            'INPUT_RASTER':aspect2mLayer,
            'RASTER_BAND':1,
            'TABLE':[0,45,1,45,135,2,135,225,3,225,315,4,315,360,1,"",0,-9999,360,"",-9999],
            'NO_DATA':-9999,
            'RANGE_BOUNDARIES':0,
            'NODATA_FOR_MISSING':False,
            'DATA_TYPE':5, # Use Floating Point here to follow Alex's methodology
            '--overwrite': True,
            'OUTPUT':str(aspectReclassifiedFilePath)}
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        aspectReclassifiedLayer = results['OUTPUT']

        # Step 28 Reclassify slope data into classes:1,2,3
        
        slopeReclassifiedFilePath = dataPath / (SLOPE_RECLASSIFIED_LAYER_NAME + '.tif')
        parameters = {
            'INPUT_RASTER':slope2mLayer,
            'RASTER_BAND':1,
            'TABLE':[0,20,1,20,40,2,40,60,3,"",0,-9999,60,"",-9999],
            'NO_DATA':-9999,
            'RANGE_BOUNDARIES':0,
            'NODATA_FOR_MISSING':False,
            'DATA_TYPE':5, # Use Floating Point here to follow Alex's methodology
            '--overwrite': True,
            'OUTPUT':str(slopeReclassifiedFilePath)}
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        slopeReclassifiedLayer = results['OUTPUT']
        
        
        # Sieve Aspect Data - step 30/31
        aspectSieveFilePath = dataPath / (ASPECT_SIEVED_LAYER_NAME + '.tif')
        parameters = {
            'INPUT':aspectReclassifiedLayer,
            'THRESHOLD':2,
            'OUTPUT':str(aspectSieveFilePath)}
        results = processing.run('gdal:sieve', parameters, context=context, feedback=feedback)
        aspectSieveLayer = results['OUTPUT']
        
        # Sieve slope data - step 30/31
        slopeSieveFilePath = dataPath / 'slope-sieved.tif'
        parameters = {
            'INPUT':slopeReclassifiedLayer,
            'THRESHOLD':12,
            'OUTPUT':str(slopeSieveFilePath)}
        results = processing.run('gdal:sieve', parameters, context=context, feedback=feedback)
        slopeSieveLayer = results['OUTPUT']


        #  Step 50 - sin of raster aspect values
        aspectSinFilePath = dataPath / 'aspect_sin.tif'
        parameters = {
            'INPUT_A' : aspectLayer,
            'BAND_A' : 1,
            'FORMULA' : 'sin(A * ' + str(pi) + ' / 180)',   
            'OUTPUT':str(aspectSinFilePath)}
        results = processing.run('gdal:rastercalculator', parameters, context=context, feedback=feedback)
        aspectSinLayer = results['OUTPUT']
 
        #  HACK!!! - TODO - fix this properly
        #  Answer as in here: https://gis.stackexchange.com/questions/307393/qgis-python-ignore-invalid-geometries
        # context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)
        
        #  Step 51 - cosine of raster aspect values
        aspectCosFilePath = dataPath / 'aspect_cos.tif'
        parameters = {
            'INPUT_A' : aspectLayer,
            'BAND_A' : 1,
            'FORMULA' : 'cos(A * ' + str(pi) + ' / 180)',   
            'OUTPUT':str(aspectCosFilePath)}
        results = processing.run('gdal:rastercalculator', parameters, context=context, feedback=feedback)
        aspectCosLayer = results['OUTPUT']
        
        # Step 7 - Clip the buildings layer with the Local extent
        clippedBuildingsFilePath = dataPath / 'Local-Buildings.shp'
        parameters = {
            'INPUT':buildingsLayer,
            'OVERLAY':localExtentAreaLayer,
            'OUTPUT':str(clippedBuildingsFilePath)}
        results = processing.run("native:clip", parameters, context=context, feedback=feedback)
        clippedBuildingsLayer = results['OUTPUT']

        #  Step 33 - Buffer Buildings by 2 metres

        bufferedBuildingsFilePath = dataPath / 'Buffered-buildings.shp'
        parameters = {
            'INPUT':clippedBuildingsLayer,
            'DISTANCE':2,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':str(bufferedBuildingsFilePath)}
        results = processing.run('native:buffer', parameters, context=context, feedback=feedback)
        bufferedBuildingsLayer = results['OUTPUT']

        # Note: Previous version using gdal:cliprasterbymasklayer crashes for Kendal

        # Step 34.1 - Clip Aspect by Buffered Buildings (clip raster by mask layer)

        # Extra step (November 2021): ensure that NODATA value is set properly in the ASPECT_SIEVED layer
        # Otherwise SAGA routines don't recognise the nodata and the result is a mess.
        correctedAspectSievePath = dataPath / 'aspect_sieved_corrected.tif'
        parameters = {'INPUT':aspectSieveLayer, 
            'TARGET_CRS':BRITISH_NATIONAL_GRID, 
            'NODATA':-9999, 
            'COPY_SUBDATASETS':0, 
            'OPTIONS':'', 
            'DATA_TYPE':0, 
            'OUTPUT':str(correctedAspectSievePath)}
        results = processing.run('gdal:translate', parameters, context=context, feedback=feedback)
        correctedAspectSieveLayer =  results['OUTPUT']
        
        # November 2021: Use SAGA routine instead of GDAL here as we have an issue with the validity of the data
        # in Kendal:

        roofAspectFilePath = dataPath / 'Roof-Aspect.sdat' # .sdat extension for SAGA routines
        parameters = {
            'INPUT': correctedAspectSieveLayer,
            'POLYGONS':bufferedBuildingsLayer,
            'OUTPUT':str(roofAspectFilePath)}
        results = processing.run('saga:cliprasterwithpolygon', parameters, context=context, feedback=feedback)
        roofAspectLayer =  results['OUTPUT']
        
        # 36.1 Polygonize Aspect
        roofAspectShapeFilePath = dataPath / 'Roof-Aspect-Vector.shp'
        parameters = {
            'INPUT' : roofAspectLayer, 
            'BAND' : 1, 
            'EIGHT_CONNECTEDNESS' : False, 
            'FIELD' : 'ASPECT-CLASS', 
            'OUTPUT':str(roofAspectShapeFilePath)}
        results = processing.run('gdal:polygonize', parameters, context=context, feedback=feedback)
        roofAspectVectorLayer =  results['OUTPUT']

        # November 2021: Perform the same changed steps for slope as for aspect
        correctedSlopeSievePath = dataPath / 'slope_sieved_corrected.tif'
        parameters = {'INPUT':slopeSieveLayer, 
            'TARGET_CRS':BRITISH_NATIONAL_GRID, 
            'NODATA':-9999, 
            'COPY_SUBDATASETS':0, 
            'OPTIONS':'', 
            'DATA_TYPE':0, 
            'OUTPUT':str(correctedSlopeSievePath)}
        results = processing.run('gdal:translate', parameters, context=context, feedback=feedback)
        correctedAspectSieveLayer =  results['OUTPUT']
 
        # Step 34.2 - Clip Slope by Buffered Buildings (clip raster by mask layer)
        roofSlopeFilePath = dataPath / 'Roof-Slope.sdat'
        parameters = {
            'INPUT':correctedAspectSieveLayer,
            'POLYGONS':bufferedBuildingsLayer,
            'OUTPUT':str(roofSlopeFilePath)}
        results = processing.run('saga:cliprasterwithpolygon', parameters, context=context, feedback=feedback)
        roofSlopeLayer =  results['OUTPUT']


        # 36.2 Polygonize Slope
        roofSlopeShapeFilePath = dataPath / 'Roof-Slope-Vector.shp'
        parameters = {
            'INPUT' : roofSlopeLayer, 
            'BAND' : 1, 
            'EIGHT_CONNECTEDNESS' : False, 
            'FIELD' : 'SLOPE-CLASS', 
            'OUTPUT':str(roofSlopeShapeFilePath)}
        results = processing.run('gdal:polygonize', parameters, context=context, feedback=feedback)
        roofSlopeVectorLayer =  results['OUTPUT']

        # 37.1 Validate Geometries - Aspect
        roofAspectFixedFilePath = dataPath / 'Roof-Aspect-Vector-Fixed.shp'
        parameters = {
            'INPUT' : roofAspectVectorLayer, 
            'OUTPUT':str(roofAspectFixedFilePath)}
        results = processing.run('native:fixgeometries', parameters, context=context, feedback=feedback)
        roofAspectFixedLayer =  results['OUTPUT']
        
        # 37.2 Validate Geometries - Slope
        roofSlopeFixedFilePath = dataPath / 'Roof-Slope-Vector-Fixed.shp'
        parameters = {
            'INPUT' : roofSlopeVectorLayer, 
            'OUTPUT':str(roofSlopeFixedFilePath)}
        results = processing.run('native:fixgeometries', parameters, context=context, feedback=feedback)
        roofSlopeFixedLayer =  results['OUTPUT']
        
        # Step 38 - Intersection between aspect and slope... Takes a while for some reason
        
        roofPlanesFilePath = dataPath / 'Roof-Planes.shp'
        parameters = {
            'INPUT' : roofAspectFixedLayer, 
            'OVERLAY' : roofSlopeFixedLayer,
            'OUTPUT':str(roofPlanesFilePath)}
        results = processing.run('native:intersection', parameters, context=context, feedback=feedback)
        roofPlanesLayer =  results['OUTPUT']
        
        # Step 40 - Buffer Roof Planes by -0.8 metres
        
        bufferedRoofPlanesFilePath = dataPath / 'Roof-planes-debuffered.shp'
        parameters = {
            'INPUT':roofPlanesLayer,
            'DISTANCE':-0.8,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':str(bufferedRoofPlanesFilePath)}
        results = processing.run('native:buffer', parameters, context=context, feedback=feedback)
        bufferedRoofPlanesLayer = results['OUTPUT']

        # Step 41 - Re-Buffer Roof Planes by 0.8 metres
        
        reBufferedRoofPlanesFilePath = dataPath / 'Roof-planes-rebuffered.shp'
        parameters = {
            'INPUT':bufferedRoofPlanesLayer,
            'DISTANCE':0.8,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':str(reBufferedRoofPlanesFilePath)}
        results = processing.run('native:buffer', parameters, context=context, feedback=feedback)
        rebufferedRoofPlanesLayer = results['OUTPUT']

        # Step 42 - Run multipart to single part on the roof planes
        
        singlepartRoofPlanesFilePath = dataPath / 'SinglePart-Roof-Planes.shp'
        parameters = {
            'INPUT' : rebufferedRoofPlanesLayer, 
            'OUTPUT':str(singlepartRoofPlanesFilePath)}
        results = processing.run('native:multiparttosingleparts', parameters, context=context, feedback=feedback)
        singlepartRoofPlanesLayer = results['OUTPUT']
        
        # 43.1 Buffer by +1 metres 

        extrabufferedRoofPlanesFilePath = dataPath / 'Buffered-Roof-Planes.shp'
        parameters = {
            'INPUT' : singlepartRoofPlanesLayer, 
            'DISTANCE':1,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':str(extrabufferedRoofPlanesFilePath)}
        results = processing.run('native:buffer', parameters, context=context, feedback=feedback)
        extrabufferedRoofPlanesLayer = results['OUTPUT']
        
        # 43.2 DeBuffer by -1 metres - giving us the processed roof planes layer!
        processedRoofPlanesFilePath = dataPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')
        parameters = {
            'INPUT' : extrabufferedRoofPlanesLayer,  
            'DISTANCE':-1,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'OUTPUT':str(processedRoofPlanesFilePath)}
        results = processing.run('native:buffer', parameters, context=context, feedback=feedback)
        processedRoofPlanesLayer = results['OUTPUT']

        # Step 51.1 - Zonal Statistics for cosine - store as an attribute
        parameters = {
            'INPUT_RASTER':aspectCosLayer,
            'RASTER_BAND':1,
            'INPUT_VECTOR':processedRoofPlanesLayer,
            'COLUMN_PREFIX':'C_',
            'STATS':[2]}
        results = processing.run('qgis:zonalstatistics', parameters, context=context, feedback=feedback)

        # Step 51.2 - Zonal Statistics for sine - store as an attribute
        parameters = {
            'INPUT_RASTER':aspectSinLayer,
            'RASTER_BAND':1,
            'INPUT_VECTOR':processedRoofPlanesLayer,
            'COLUMN_PREFIX':'S_',
            'STATS':[2]}
        results = processing.run('qgis:zonalstatistics', parameters, context=context, feedback=feedback)

        # Step 54 - Find the mean of the original slope and store as an attribute.  Ignore stdev for now.
        
        parameters = {
            'INPUT_RASTER':slopeLayer,
            'RASTER_BAND':1,
            'INPUT_VECTOR':processedRoofPlanesLayer,
            'COLUMN_PREFIX':'Slope_',
            'STATS':[2]}
        results = processing.run('qgis:zonalstatistics', parameters, context=context, feedback=feedback)
           

        return {}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'roofprocessor'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return 'roofprocessor'

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
        return 'CAFS 1'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        return self.tr("First CAFS algorithm: locate all flat roof spaces in the local area")

    def createInstance(self):
        return RoofProcessorAlgorithm()
