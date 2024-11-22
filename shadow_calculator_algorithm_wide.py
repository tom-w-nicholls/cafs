# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ShadowCalculator
                                 A QGIS plugin
 Calculates shadows of a geographical region based on obstructions
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

__author__ = 'Tom Nicholls, CAFS'
__date__ = '2021-03-31'
__copyright__ = '(C) 2021 by Cumbria Action for Sustainability'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import *
from PyQt5.QtWidgets import QProgressBar # Need this for the QGIS plugin progress bar

from osgeo import gdal

from .SolarConstants  import *
from .shadow_generator_modified import ShadowGenerator
import numpy as np
from pathlib import Path # Post python 3.4
from .SolarDirectoryPaths import SolarDirectoryPaths

import processing

class ShadowCalculatorAlgorithmWide(QgsProcessingAlgorithm):
    """
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    DSM='DSM_LAYER'
    WIDE_AREA = 'WIDE_LAYER'    
    LOCAL_AREA = 'LOCAL_LAYER'    
    # DSM_CLIPPED='DSM_CLIPPED'
    DATA_DIRECTORY = "DATA_DIRECTORY"   
    CHECKBOX='USE_WIDE_AREA'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        paths=SolarDirectoryPaths()

        # Input layers:

        dataPath = paths.dataDirectoryPath
        self.addParameter(
            QgsProcessingParameterString(
                self.DATA_DIRECTORY,
                self.tr(self.DATA_DIRECTORY),
                defaultValue=DATA_STRING
            )
        )
        

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DSM,
            self.tr("DSM"), DSM_1M_LAYER_NAME, False))

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

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LOCAL_AREA,
                self.tr('LOCAL_EXTENT'),
                [QgsProcessing.TypeVectorAnyGeometry],
                defaultValue=LOCAL_EXTENT_LAYER_NAME
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        paths=SolarDirectoryPaths()

        dataString = self.parameterAsString(parameters, self.DATA_DIRECTORY, context)
        dataPath = SolarDirectoryPaths().projectPath / dataString
        dataPath.mkdir(parents=True, exist_ok=True)

        # The results of shadow calculations are stored in a directory under the data directory
        shadowPath = dataPath / "SHADOW"
        shadowPath.mkdir(parents=True, exist_ok=True)
      

        dsmLayer = self.parameterAsRasterLayer(parameters, self.DSM, context)
        wideAreaHighResLayer = self.parameterAsVectorLayer(parameters, self.WIDE_AREA, context)
        localAreaLayer = self.parameterAsVectorLayer(parameters, self.LOCAL_AREA, context)
        shadowBinaryFilePath =  dataPath / "SHADOW" / (SHADOW_BINARY_LAYER_NAME + '.tif')
        useWideArea = self.parameterAsBool(parameters, self.CHECKBOX, context)
                
        
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
        wideExtent, localExtent = 0,0
        wideAreaDSMLayer=0
        lowResWideAreaRaster=0
        highResWideLayer, lowResMergedWideLayer = 0, 0

        
        shadowGenerator = ShadowGenerator()

        # Load a layer from a file
        dsmClippedFilePath = dataPath / (DSM_1M_CLIPPED_LAYER_NAME + '.tif')
        dsmClippedLayer = QgsProcessingUtils.mapLayerFromString(str(dsmClippedFilePath), context) 

        # Set up the wide area parameters, if the checkbox is ticked
        if useWideArea is True:

            # 1. Clip the DSM by the wide area polygon
            tempResultOutputPath = dataPath / 'wide_area_dsm_clipped.tif'
            parameters = {
                'INPUT':dsmLayer,
                'PROJWIN':wideAreaHighResLayer,
                'NODATA':-9999,
                'OPTIONS':'',
                'DATA_TYPE':0,
                '--overwrite': True,
                'OUTPUT':str(tempResultOutputPath)}
            results = processing.run('gdal:cliprasterbyextent',parameters, context=context, feedback=feedback)
            # CRS is wrong for above output, so we now have to fix this!
            wideAreaDSMLayer = fixLayerCrs(results['OUTPUT'], tempResultOutputPath, context, feedback)
            highResWideLayer = QgsProcessingUtils.mapLayerFromString(results['OUTPUT'], context) # Load the layer from the filepath into the context
            msg = "WideAreaDSMLayer = " + str(wideAreaDSMLayer)
            log(msg)


            # 2. Reduce the resolution:
            tempResultOutputPath = dataPath / 'resampled-wide-area-dsm-clipped.tif'
            parameters = {
                'INPUT':wideAreaDSMLayer,
                'TARGET_CRS':'EPSG:27700',
                'RESAMPLING':2,  # 2 for cubic method
                'TARGET_RESOLUTION':SCALE_FACTOR,  # resample up to 10 metres
                'DATA_TYPE':6, # Float32
                'OUTPUT':str(tempResultOutputPath)}
            results = processing.run('gdal:warpreproject',parameters, context=context, feedback=feedback)
            lowResWideAreaRaster = results['OUTPUT']


            # 3. Find the maximum value of the DSM (local area)
            provider = dsmClippedLayer.dataProvider()
            stats = provider.bandStatistics(1, QgsRasterBandStats.All)
            maximumValueOfLocalAreaDSM = stats.maximumValue

            # 4. Create a raster of constant value:
            tempResultOutputPath = dataPath / 'constant-raster.tif'
            parameters = {
                'EXTENT': localAreaLayer,
                'PIXEL_SIZE': 10,
                'NUMBER': maximumValueOfLocalAreaDSM,
                'TARGET_CRS':'EPSG:27700',
                'OUTPUT':str(tempResultOutputPath)}
            results = processing.run('qgis:createconstantrasterlayer',parameters, context=context, feedback=feedback)
            constantRaster = results['OUTPUT']

            # 5. Merge constant layer over the reduced resolution layer:
            tempResultOutputPath = dataPath / 'low-res-wide-area-merged.tif'
            parameters = {
                'INPUT':[lowResWideAreaRaster, constantRaster],
                'DATA_TYPE':6, # Float32
                'OUTPUT':str(tempResultOutputPath)}
            results = processing.run('gdal:merge',parameters, context=context, feedback=feedback)
            lowResMergedRaster = results['OUTPUT']
            lowResMergedWideLayer = QgsProcessingUtils.mapLayerFromString(results['OUTPUT'], context) # Load the layer from the filepath into the context
            # Note: wideLayer is now a low-resolution merge between the low res raster and the flat constant local region raster

            msg = "dsmClippedLayer is: " + str(dsmClippedLayer.source())
            log(msg)
            msg = "wideAreaDSMLayer is: " + str(wideAreaDSMLayer)
            log(msg)

            # Calculate the x and y offsets between the two rasters dsmClippedLayer and wideAreaDsmLayer:

            wideExtent = Extent(highResWideLayer)
            log("Wide Extent: + str(wideExtent)")
            
        localExtent = Extent(dsmClippedLayer)
        log("Local Extent + str(localExtent)")


        # March 20th 2020
        msg = "March 20th 2020"
        log(msg)
        dst=0
        shadowResult = shadowGenerator.calculateShadowRaster(dsmClippedLayer, lowResMergedWideLayer, useWideArea, 
                                         wideExtent, localExtent, 
                                         2020, 3, 20, hour, min, sec, UTC, timeInterval, dst, onetime, dlg) # step 65

        array200320, local200320, wide200320 = shadowResult["shfinal"], shadowResult["shlocal"], shadowResult["shwide"] # numpy arrays
        filepath200320 = shadowPath / '200320-shadow.tif'
        self.createRasterFromNumpyArray(array200320, -9999, filepath200320, shadowGenerator.geoTransform, shadowGenerator.projection)
        if(useWideArea and isDebug()):
            filepathWide200320 = shadowPath / '200320-wide.tif'
            self.createRasterFromNumpyArray(wide200320, -9999, filepathWide200320, shadowGenerator.geoTransformWide, shadowGenerator.projectionWide)
 
        feedback.setProgress(20)
        msg = "Finished March Raster"
        log(msg)
        
        
        # June 21st 2020 (daylight savings: dst=1)
        msg = "June 21st 2020"
        log(msg)
        dst=1
        shadowResult = shadowGenerator.calculateShadowRaster(dsmClippedLayer, lowResMergedWideLayer, useWideArea, 
                                         wideExtent, localExtent, 
                                         2020, 6, 21, hour, min, sec, UTC, timeInterval, dst, onetime, dlg) # step 66

        array200621, local200621, wide200621 = shadowResult["shfinal"], shadowResult["shlocal"], shadowResult["shwide"] # numpy arrays
        filepath200621 = shadowPath / '200621-shadow.tif'
        self.createRasterFromNumpyArray(array200621, -9999, filepath200621, shadowGenerator.geoTransform, shadowGenerator.projection)
        if(useWideArea and isDebug()):
            filepathWide200621 = shadowPath / '200621-wide.tif'
            self.createRasterFromNumpyArray(wide200621, -9999, filepathWide200621, shadowGenerator.geoTransformWide, shadowGenerator.projectionWide)
        feedback.setProgress(40)
        msg = "Finished June Raster"
        log(msg)
        
       
        # Sept 23rd 2020 (daylight savings: dst=1)
        msg = "Sept 23rd 2020"
        log(msg)        
        dst=1
        shadowResult = shadowGenerator.calculateShadowRaster(dsmClippedLayer, lowResMergedWideLayer, useWideArea, 
                                         wideExtent, localExtent, 
                                         2020, 9, 23, hour, min, sec, UTC, timeInterval, dst, onetime, dlg) # step 66

        array200923, local200923, wide200923 = shadowResult["shfinal"], shadowResult["shlocal"], shadowResult["shwide"] # numpy arrays
        filepath200923 = shadowPath / '200923-shadow.tif'
        self.createRasterFromNumpyArray(array200923, -9999, filepath200923, shadowGenerator.geoTransform, shadowGenerator.projection)
        if(useWideArea and isDebug()):
            filepathWide200923 = shadowPath / '200923-wide.tif'
            self.createRasterFromNumpyArray(wide200923, -9999, filepathWide200923, shadowGenerator.geoTransformWide, shadowGenerator.projectionWide)
        feedback.setProgress(60)
        msg = "Finished September Raster"
        log(msg)

        # Dec 22nd 2020 
        msg = "Dec 22nd 2020"
        log(msg)        
        dst=0
        shadowResult = shadowGenerator.calculateShadowRaster(dsmClippedLayer, lowResMergedWideLayer, useWideArea, 
                                         wideExtent, localExtent, 
                                         2020, 12, 22, hour, min, sec, UTC, timeInterval, dst, onetime, dlg) # step 66

        array201222, local201222, wide201222 = shadowResult["shfinal"], shadowResult["shlocal"], shadowResult["shwide"] # numpy arrays
        filepath201222 = shadowPath / '201222-shadow.tif'
        self.createRasterFromNumpyArray(array201222, -9999, filepath201222, shadowGenerator.geoTransform, shadowGenerator.projection)
        if(useWideArea and isDebug()):
            filepathWide201222 = shadowPath / '201222-wide.tif'
            self.createRasterFromNumpyArray(wide201222 -9999, filepathWide201222, shadowGenerator.geoTransformWide, shadowGenerator.projectionWide)
        feedback.setProgress(80)
        msg = "Finished December Raster"
        log(msg)       
        
       
        # #STEP 70 Reclassification to binary rasters
        outfilepath200320 = shadowPath / 'March-binary.tif'
        outfilepath200621 = shadowPath / 'June-binary.tif'
        outfilepath200923 = shadowPath / 'September-binary.tif'
        outfilepath201222 = shadowPath / 'December-binary.tif'
            
        # Note Bugfix - threshold for March and September is 0.5, for June is 0.6 and for December is 0.4
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

        parameters['INPUT_RASTER']=str(filepath200923)
        parameters['OUTPUT']=str(outfilepath200923)
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        septemberBinary= results['OUTPUT']
        feedback.setProgress(88)

        parameters['INPUT_RASTER']=str(filepath200621)
        parameters['OUTPUT']=str(outfilepath200621)
        parameters['TABLE']=[0,0.6,0,0.6,1,1]
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        juneBinary= results['OUTPUT']
        feedback.setProgress(92)

        parameters['INPUT_RASTER']=str(filepath201222)
        parameters['OUTPUT']=str(outfilepath201222)
        parameters['TABLE']=[0,0.4,0,0.4,1,1]
        results = processing.run('native:reclassifybytable',parameters, context=context, feedback=feedback)
        decemberBinary= results['OUTPUT']
        feedback.setProgress(96)

        # STEP 73 Multiply all binary rasters together to produce the final shadow binary result:
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
            'OUTPUT':str(shadowBinaryFilePath)}
        results = processing.run('gdal:rastercalculator',parameters, context=context, feedback=feedback)
        shadowBinaryLayer = fixLayerCrs(results['OUTPUT'], shadowBinaryFilePath, context, feedback)

        processedRoofPlanesFilePath = dataPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')
        processedRoofPlanesLayer = QgsProcessingUtils.mapLayerFromString(str(processedRoofPlanesFilePath), context) 

        # STEP 75 Use zonal stats to calculate mean shade for each roof
        parameters = {
            'INPUT_RASTER':shadowBinaryLayer,
            'RASTER_BAND':1,
            'INPUT_VECTOR':processedRoofPlanesLayer,
            'COLUMN_PREFIX':'Shade_',
            'STATS':[2]}
        results = processing.run("qgis:zonalstatistics", parameters, context=context, feedback=feedback)

        # Set output
        
        # results[self.SHADOW_BINARY] = shadowBinaryFilePath 

        return {}

    def findExtent(self, rasterLayer):
        ext = rasterLayer.extent()
        xMin = ext.xMinimum()
        yMin = ext.yMinimum()
        xMax= ext.xMaximum()
        yMax = ext.yMaximum()
        msg=f"layer: {rasterLayer.source()} xMin:{xMin}, yMin:{yMin}, xMax:{xMax}, yMax:{yMax}"
        log(msg)
        return xMin, yMin, xMax, yMax


    def createRasterFromNumpyArray(self, sourceNumpyNDArray, noDataValue, filepath, geoTransform, projection):
        cols, rows = sourceNumpyNDArray.shape
        
        # Open up the raster file
        outputRaster = gdal.GetDriverByName('GTiff').Create(str(filepath),rows, cols, int(1) ,gdal.GDT_Float32)
        
        #writing output raster does the magic of converting array into raster!
        outputRaster.GetRasterBand(1).WriteArray( sourceNumpyNDArray ) 
        outputRaster.SetGeoTransform(geoTransform)
        outputRaster.SetProjection(projection)
        outputRaster.FlushCache()

    # Debugging function to demonstrate how gdal transforms rasters into numpy arrays.
    def createFakeRasterFromNumpyArray(self, noDataValue, filepath, geoTransform, projection):
        import numpy as np
        size=256
        x = range(256*256)
        x = np.reshape(x,(size,size))
        log(str(x))
        self.createRasterFromNumpyArray(x, noDataValue, filepath, geoTransform, projection)


        

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'shadow'

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
        return 'CAFS 2 Wide'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        return self.tr("Second CAFS algorithm: produce a shadow raster for the local area and calculate zonal statistics for each roof")

    def createInstance(self):
        return ShadowCalculatorAlgorithmWide()
    

