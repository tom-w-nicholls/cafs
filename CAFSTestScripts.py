# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CAFS Test Scripts - not part of the plugin; just used for testing code
                                 A QGIS plugin
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

# TODO - Project doesn't load NYRoad layer
# TODO - starting point for the client

processing.algorithmHelp("native:clip")

import inspect


dir(mps) # shows all classes within the module mps
dir(mps.MetdataProcessor) # shows all functions and members


##############  Run these lines on QGIS start up ##############

# We need the processing module, at least

from qgis.core import *
from math import pi
import sys, importlib
import os
import time
from UMEP.WallHeight import wall_height_modified as wallheightmod
from solarcalculator.SolarConstants  import *



# Set up some paths 

from pathlib import Path # Post python 3.4
projectPathString = QgsProject.instance().readPath("./")
projectPath = Path(projectPathString)
dataDirectoryPath = projectPath / 'DATA' 
	# - to DATA subdirectory (this is where we will store intermediate files)
shadowDirectoryPath = projectPath / 'DATA' / 'SHADOW'

# Create subdirectories if they don't exist already
if not os.path.exists(str(dataDirectoryPath)):
    os.makedirs(dataDirectoryPath)

if not os.path.exists(str(shadowDirectoryPath)):
    os.makedirs(shadowDirectoryPath)


	
#Functions to rename a layer
def renameSelectedLayer(newName, iface):
	for layer in iface.layerTreeView().selectedLayers():
		layer.setName(newName)

def renameLayer(oldName,newName,projectInstance):
	layerToRename = projectInstance.mapLayersByName(oldName)[0]
	layerToRename.setName(newName)
	
### Create a feedback object to examine problems in the processing module ####

class MyFeedBack(QgsProcessingFeedback):

    def reportError(self, error, fatalError=False):
        print(error)


LOCAL_EXTENT_BUILDINGS_LAYER_NAME="NY Building"  # TODO CHANGE THIS FILENAME FOR LIVE APP
LOCAL_EXTENT_LAYER_NAME='Ambleside Extent'
LOCAL_BUILDINGS_LAYER_NAME="Local-Buildings"
ASPECT_LAYER_NAME = 'Aspect'
SLOPE_LAYER_NAME = 'Slope'
DSM_MINUS_DTM_1M_LAYER_NAME = 'DSM-DTM_1m'
DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME = 'DSM-DTM_1m-clipped'
DSM_1M_LAYER_NAME = 'DSM_1m'
DSM_1M_CLIPPED_LAYER_NAME = 'DSM-1m-clipped'
DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME = 'DSM-DTM_2m'
ASPECT_2M_LAYER_NAME = "Aspect_2m"
SLOPE_2M_LAYER_NAME="Slope_2m"
SLOPE_RECLASSIFIED_LAYER_NAME="Slope-reclassified"
ASPECT_RECLASSIFIED_LAYER_NAME="Aspect-reclassified"
ASPECT_SIEVED_LAYER_NAME="Aspect-sieved"
SLOPE_SIEVED_LAYER_NAME="Slope-sieved"
ASPECT_SIN_LAYER_NAME="Aspect-sin"
ASPECT_COS_LAYER_NAME="Aspect-cos"
BUFFERED_BUILDINGS_LAYER_NAME="Buffered-buildings"
ROOF_ASPECT_LAYER_NAME="Roof-Aspect"
ROOF_SLOPE_LAYER_NAME="Roof-Slope"
ROOF_ASPECT_VECTOR_LAYER_NAME="Roof-Aspect-Vector"
ROOF_SLOPE_VECTOR_LAYER_NAME="Roof-Slope-Vector"
ROOF_SLOPE_VECTOR_FIXED_LAYER_NAME="Roof-Slope-Vector-Fixed"
ROOF_ASPECT_VECTOR_FIXED_LAYER_NAME="Roof-Aspect-Vector-Fixed"
ROOF_PLANES_LAYER_NAME="Roof-Planes"
DEBUFFERED_ROOF_PLANES_LAYER_NAME="De-Buffered-Roof-Planes"
REBUFFERED_ROOF_PLANES_LAYER_NAME="Re-Buffered-Roof-Planes"
SINGLEPART_ROOF_PLANES_LAYER_NAME="SinglePart-Roof-Planes"
BUFFERED_ROOF_PLANES_LAYER_NAME="Buffered-Roof-Planes"
PROCESSED_ROOF_PLANES_LAYER_NAME="Processed-Roof-Planes"
ROOF_PLANES_ATTRIBUTES_ADDED_LAYER_NAME="Roof-planes-attributes-added"
SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME="annual-solar-energy"

METEOROLOGICAL_FILE_RAW_FILE_NAME="tmy_54.430_-2.963_2006_2015.epw"
METEOROLOGICAL_FILE_PROCESSED_FILE_NAME="meteorological data processed.txt"
WALL_HEIGHT_FILE_NAME="Wall-Height"
WALL_ASPECT_FILE_NAME="Wall-Aspect"
# Hopefully these two will be temporary:
WALL_ASPECT_LAYER_NAME="wall_aspect"
WALL_HEIGHT_LAYER_NAME="wall_height"

MARCH_BINARY_LAYER_NAME="March-Binary"
JUNE_BINARY_LAYER_NAME="June-Binary"
SEPTEMBER_BINARY_LAYER_NAME="September-Binary"
DECEMBER_BINARY_LAYER_NAME="December-Binary"

SHADOW_BINARY_LAYER_NAME="shadow-binary"

_LAYER_NAME=""
_LAYER_NAME=""
_LAYER_NAME=""
_LAYER_NAME=""

ASPECT_FILE_NAME = ASPECT_LAYER_NAME + ".tif"

class FakeDialog:
  def __init__(self, progressBar):
    self.progressBar = progressBar

crs = QgsCoordinateReferenceSystem("EPSG:27700") # Hack

# FOR TESTING!
#LOCAL_EXTENT_LAYER_NAME="small-area-extent"



#  Need to add in steps 13 & 14 to allow the user to add their own DTM & DSM data
# and not assume that it's preloaded with the project?
#  Also step 15 to subtract the two layers



#### START OF PHASE ONE ####


# TODO: does this crash? Use cliprasterbyextent instead
# Extra Step 17.1 clip DSM-DTM by the area of interest to speed up calculations 
# (see note in step 35)


### TODO: THIS (step 17) MUST precede the solar calculation phase

DSM_Minus_DTM_clipped_File = dataDirectoryPath / 'DSM-DTM_1m-clipped.tif'
parameters = {
	'INPUT':DSM_MINUS_DTM_1M_LAYER_NAME,
	'PROJWIN':LOCAL_EXTENT_LAYER_NAME,
#	'NODATA':None, # leave as None to keep original nodata values
	'OPTIONS':'',
	'DATA_TYPE':0,
	'OUTPUT':str(DSM_Minus_DTM_clipped_File)}
results = processing.run('gdal:cliprasterbyextent',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME) # IGNORE WARNINGS ABOUT CRS HERE
rlayer.setCrs(crs)
layer=QgsProject.instance().addMapLayer(rlayer) # Add it to the visual interface as a new layer

# Step 19  - calculate aspect - this is still needed for step 50!
# This calculates aspect with hard written file path (need to work out how to do relative paths)	
aspectFile = dataDirectoryPath / 'aspect.tif'
parameters = {
	'INPUT': DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME, 
	'BAND':1, 
	'COMPUTE_EDGES':True, 
	'OUTPUT':str(aspectFile)}
results = processing.run("gdal:aspect",parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)


# Step 20 - calculate slope, as per step 19
slopeFile = dataDirectoryPath / 'slope.tif'
parameters = {
	'INPUT':DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME, 
	'BAND':1, 
	'COMPUTE_EDGES':True, 
	'OUTPUT':str(slopeFile)}
results = processing.run("gdal:slope",parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SLOPE_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)



# Obtains the path of the current directory (I need this for saving temporary files)
# projectPathString = QgsProject.instance().readPath("./")

# So aspect calculation with a path relative to the project directory
# aspectFile = dataDirectoryPath / 'aspect.tif'
# parameters = {'INPUT':DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME, 'BAND':1, 'COMPUTE_EDGES':True, 'OUTPUT':str(aspectFile)}
# results = processing.runAndLoadResults("gdal:aspect",parameters)
# renameLayer('Aspect', ASPECT_2M_LAYER_NAME, QgsProject.instance())
# 
# #Similarly for slope
# 
# slopeFile = dataDirectoryPath / 'slope.tif'
# parameters = {'INPUT':DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME, 'COMPUTE_EDGES':True, 'BAND':1, 'OUTPUT':str(slopeFile)}
# results = processing.runAndLoadResults("gdal:slope",parameters)
# renameLayer('Slope', SLOPE_2M_LAYER_NAME, QgsProject.instance())



# Step 22 Reclassify by table  - to remove data below 2 metres from ground elevation

reclassifiedFile = dataDirectoryPath / 'DSM-DTM_2m.tif'
parameters = {
	'INPUT_RASTER':DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME,
	'RASTER_BAND':1,
	'TABLE':['',2,-9999],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,
	'OUTPUT':str(reclassifiedFile)}
results = processing.run('native:reclassifybytable',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# Step 23.1 - recalculate aspect with data over 2m only
# This calculates aspect with hard written file path (need to work out how to do relative paths)	
aspect2mFile = dataDirectoryPath / 'Aspect_2m.tif'
parameters = {
	'INPUT': DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME, 
	'BAND':1, 
	'COMPUTE_EDGES':True, 
	'OUTPUT':str(aspect2mFile)}
results = processing.run("gdal:aspect",parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_2M_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)


# Step 23.2 - recalculate slope with data over 2m only
slope2mFile = dataDirectoryPath / 'Slope_2m.tif'
parameters = {
	'INPUT':DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME, 
	'BAND':1, 
	'COMPUTE_EDGES':True, 
	'OUTPUT':str(slope2mFile)}
results = processing.run("gdal:slope",parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SLOPE_2M_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# Step 27 Reclassify aspect data into classes:1,2,3,4
aspectReclassifiedFile = dataDirectoryPath / 'aspect-reclassified.tif'
parameters = {
	'INPUT_RASTER':ASPECT_2M_LAYER_NAME,
	'RASTER_BAND':1,
	'TABLE':[0,45,1,45,135,2,135,225,3,225,315,4,315,360,1,"",0,-9999,360,"",-9999],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5, # Use Floating Point here to follow Alex's methodology
	'OUTPUT':str(aspectReclassifiedFile)}
results = processing.run('native:reclassifybytable', parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_RECLASSIFIED_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# Step 28 Reclassify slope data into classes:1,2,3
slopeReclassifiedFile = dataDirectoryPath / 'slope-reclassified.tif'
parameters = {
	'INPUT_RASTER':SLOPE_2M_LAYER_NAME,
	'RASTER_BAND':1,
	'TABLE':[0,20,1,20,40,2,40,60,3,"",0,-9999,60,"",-9999],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,  # Use Floating Point here to follow Alex's methodology
	'OUTPUT':str(slopeReclassifiedFile)}
results = processing.run('native:reclassifybytable', parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SLOPE_RECLASSIFIED_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# Sieve slope data - step 30/31
slopedSieveFile = dataDirectoryPath / 'slope-sieved.tif'
parameters = {
	'INPUT':SLOPE_RECLASSIFIED_LAYER_NAME,
	'THRESHOLD':12,
	'OUTPUT':str(slopedSieveFile)}
results = processing.run('gdal:sieve',parameters,  feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SLOPE_SIEVED_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)
provider=layer.dataProvider()
provider.setNoDataValue(1, -9999) # band = 1
layer.triggerRepaint()

# Sieve Aspect Data - step 30/31
aspectSieveFile = dataDirectoryPath / 'aspect-sieved.tif'
parameters = {
	'INPUT':ASPECT_RECLASSIFIED_LAYER_NAME,
	'THRESHOLD':2,
	'OUTPUT':str(aspectSieveFile)}
results = processing.run('gdal:sieve',parameters,  feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_SIEVED_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)
provider=layer.dataProvider()
provider.setNoDataValue(1, -9999) # band = 1
layer.triggerRepaint()

#  Step 50 - sin of raster aspect values
aspectSinFile = dataDirectoryPath / 'aspect_sin.tif'
parameters = {
	'INPUT_A' : ASPECT_LAYER_NAME,
    'BAND_A' : 1,
    'FORMULA' : 'sin(A * ' + str(pi) + ' / 180)',   
	'OUTPUT':str(aspectSinFile)}
results = processing.run('gdal:rastercalculator',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_SIN_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)


#  Step 51 - cosine of raster aspect values
aspectCosFile = dataDirectoryPath / 'aspect_cos.tif'
parameters = {
	'INPUT_A' : ASPECT_LAYER_NAME,
    'BAND_A' : 1,
    'FORMULA' : 'cos(A * ' + str(pi) + ' / 180)',   
	'OUTPUT':str(aspectCosFile)}
results = processing.run('gdal:rastercalculator',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ASPECT_COS_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)



#### END OF PHASE ONE ####


#### START OF PHASE TWO ####

# Step 7 		
# Clip the buildings layer with the Local extent, then rename it.
clippedBuildingsFile = dataDirectoryPath / 'Local-Buildings.shp'
parameters = {
	'INPUT':LOCAL_EXTENT_BUILDINGS_LAYER_NAME,
	'OVERLAY':LOCAL_EXTENT_LAYER_NAME,
	'OUTPUT':str(clippedBuildingsFile)}
results = processing.run("native:clip",parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], LOCAL_BUILDINGS_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

#  Step 33 - Buffer Buildings by 2 metres

bufferedBuildingsFile = dataDirectoryPath / 'Buffered-buildings.shp'
parameters = {
	'INPUT':LOCAL_BUILDINGS_LAYER_NAME,
	'DISTANCE':2,
	'SEGMENTS':5,
	'END_CAP_STYLE':0,
	'JOIN_STYLE':0,
	'MITER_LIMIT':2,
	'DISSOLVE':False,
	'OUTPUT':str(bufferedBuildingsFile)}
results = processing.run('native:buffer',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], BUFFERED_BUILDINGS_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# Step 34.1 - Clip Aspect by Buffered Buildings (clip raster by mask layer)

roofAspectFile = dataDirectoryPath / 'Roof-Aspect.tif'
parameters = {
	'INPUT': ASPECT_SIEVED_LAYER_NAME,
	'MASK':BUFFERED_BUILDINGS_LAYER_NAME,
	'NODATA':-9999,
	'ALPHA_BAND':False,
	'CROP_TO_CUTLINE':True,
	'KEEP_RESOLUTION':True,
	'OPTIONS':'',
	'DATA_TYPE':0,
	'OUTPUT':str(roofAspectFile)}
results = processing.run('gdal:cliprasterbymasklayer',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ROOF_ASPECT_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# Step 34.2 - Clip Slope by Buffered Buildings (clip raster by mask layer)
roofSlopeFile = dataDirectoryPath / 'Roof-Slope.tif'
parameters = {
	'INPUT':SLOPE_SIEVED_LAYER_NAME,
	'MASK':BUFFERED_BUILDINGS_LAYER_NAME,
	'NODATA':-9999.0,
	'ALPHA_BAND':False,
	'CROP_TO_CUTLINE':True,
	'KEEP_RESOLUTION':True,
	'OPTIONS':'',
	'DATA_TYPE':0,
	'OUTPUT':str(roofSlopeFile)}
results = processing.run('gdal:cliprasterbymasklayer',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], ROOF_SLOPE_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# 36.1 Areas with common roof and slope - Polygonize Aspect
roofAspectShapeFile = dataDirectoryPath / 'Roof-Aspect-Vector.shp'
parameters = {
	'INPUT' : ROOF_ASPECT_LAYER_NAME, 
	'BAND' : 1, 
	'EIGHT_CONNECTEDNESS' : False, 
	'FIELD' : 'ASPECT-CLASS', 
	'OUTPUT':str(roofAspectShapeFile)}
results = processing.run('gdal:polygonize',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], ROOF_ASPECT_VECTOR_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 36.2 Polygonize Slope
roofSlopeShapeFile = dataDirectoryPath / 'Roof-Slope-Vector.shp'
parameters = {
	'INPUT' : ROOF_SLOPE_LAYER_NAME, 
	'BAND' : 1, 
	'EIGHT_CONNECTEDNESS' : False, 
	'FIELD' : 'SLOPE-CLASS', 
	'OUTPUT':str(roofSlopeShapeFile)}
results = processing.run('gdal:polygonize',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], ROOF_SLOPE_VECTOR_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 37.1 Validate Geometries
roofAspectFixedFile = dataDirectoryPath / 'Roof-Aspect-Vector-Fixed.shp'
parameters = {
	'INPUT' : ROOF_ASPECT_VECTOR_LAYER_NAME, 
	'OUTPUT':str(roofAspectFixedFile)}
results=processing.run("native:fixgeometries",parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], ROOF_ASPECT_VECTOR_FIXED_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 37.2 Validate Geometries
roofSlopeFixedFile = dataDirectoryPath / 'Roof-Slope-Vector-Fixed.shp'
parameters = {
	'INPUT' : ROOF_SLOPE_VECTOR_LAYER_NAME, 
	'OUTPUT':str(roofSlopeFixedFile)}
results=processing.run("native:fixgeometries",parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], ROOF_SLOPE_VECTOR_FIXED_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

#38 - Intersection between aspect and slope... Takes a while for some reason

roofPlanesFile = dataDirectoryPath / 'Roof-Planes.shp'
parameters = {
	'INPUT' : ROOF_ASPECT_VECTOR_FIXED_LAYER_NAME, 
	'OVERLAY' : ROOF_SLOPE_VECTOR_FIXED_LAYER_NAME,
	'OUTPUT':str(roofPlanesFile)}
results=processing.run("native:intersection",parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 40 - Buffer Roof Planes by -0.8 metres

bufferedRoofPlanesFile = dataDirectoryPath / 'Roof-planes-debuffered.shp'
parameters = {
	'INPUT':ROOF_PLANES_LAYER_NAME,
	'DISTANCE':-0.8,
	'SEGMENTS':5,
	'END_CAP_STYLE':0,
	'JOIN_STYLE':0,
	'MITER_LIMIT':2,
	'DISSOLVE':False,
	'OUTPUT':str(bufferedRoofPlanesFile)}
results = processing.run('native:buffer',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], DEBUFFERED_ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)


# Step 41 - Buffer Roof Planes by 0.8 metres

reBufferedRoofPlanesFile = dataDirectoryPath / 'Roof-planes-rebuffered.shp'
parameters = {
	'INPUT':DEBUFFERED_ROOF_PLANES_LAYER_NAME,
	'DISTANCE':0.8,
	'SEGMENTS':5,
	'END_CAP_STYLE':0,
	'JOIN_STYLE':0,
	'MITER_LIMIT':2,
	'DISSOLVE':False,
	'OUTPUT':str(reBufferedRoofPlanesFile)}
results = processing.runAndLoadResults('native:buffer',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], REBUFFERED_ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

#42 - Run multipart to single part on the roof planes

singlepartRoofPlanesFile = dataDirectoryPath / 'SinglePart-Roof-Planes.shp'
parameters = {
	'INPUT' : REBUFFERED_ROOF_PLANES_LAYER_NAME, 
	'OUTPUT':str(singlepartRoofPlanesFile)}
results=processing.run("native:multiparttosingleparts",parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], SINGLEPART_ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 43.1 Buffer by +1 metres 

extrabufferedRoofPlanesFile = dataDirectoryPath / 'Buffered-Roof-Planes.shp'
parameters = {
	'INPUT' : SINGLEPART_ROOF_PLANES_LAYER_NAME, 
	'DISTANCE':1,
	'SEGMENTS':5,
	'END_CAP_STYLE':0,
	'JOIN_STYLE':0,
	'MITER_LIMIT':2,
	'DISSOLVE':False,
	'OUTPUT':str(extrabufferedRoofPlanesFile)}
results = processing.run('native:buffer',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], BUFFERED_ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# 43.2 DeBuffer by -1 metres, this time creating a layer file
processedRoofPlanesFile = dataDirectoryPath / 'Processed-Roof-Planes.shp'
parameters = {
	'INPUT' : BUFFERED_ROOF_PLANES_LAYER_NAME,  
	'DISTANCE':-1,
	'SEGMENTS':5,
	'END_CAP_STYLE':0,
	'JOIN_STYLE':0,
	'MITER_LIMIT':2,
	'DISSOLVE':False,
	'OUTPUT':str(processedRoofPlanesFile)}
results = processing.run('native:buffer',parameters, feedback=MyFeedBack())
vlayer = QgsVectorLayer(results['OUTPUT'], PROCESSED_ROOF_PLANES_LAYER_NAME) # This is a vector layer
layer=QgsProject.instance().addMapLayer(vlayer)

# Step 51.1 - Zonal Statistics for cosine - store as an attribute
parameters = {
	'INPUT_RASTER':ASPECT_COS_LAYER_NAME,
	'RASTER_BAND':1,
	'INPUT_VECTOR':PROCESSED_ROOF_PLANES_LAYER_NAME,
	'COLUMN_PREFIX':'C_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())

# Step 51.2 - Zonal Statistics for sine - store as an attribute
parameters = {
	'INPUT_RASTER':ASPECT_SIN_LAYER_NAME,
	'RASTER_BAND':1,
	'INPUT_VECTOR':PROCESSED_ROOF_PLANES_LAYER_NAME,
	'COLUMN_PREFIX':'S_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())

# Step 54 - Find the mean of the original slope and store as an attribute.  Ignore stdev for now.

parameters = {
	'INPUT_RASTER':SLOPE_LAYER_NAME,
	'RASTER_BAND':1,
	'INPUT_VECTOR':PROCESSED_ROOF_PLANES_LAYER_NAME,
	'COLUMN_PREFIX':'Slope_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())



	

	
#### END OF PHASE TWO ####

	
# areaCalcFile = dataDirectoryPath / 'Area-Calculated-Roof-Planes.shp'	
# error = QgsVectorFileWriter.writeAsVectorFormat(layer,
#                                                 str(areaCalcFile),
#                                                 "UTF-8",
#                                                 driverName="ESRI Shapefile")
# if error[0] == QgsVectorFileWriter.NoError:
#     print("Data written to file")
# 
# vlayer = iface.addVectorLayer(str(areaCalcFile), "calculated_area", "ogr")

##################################
	
# 45 attempt 2 -  Instead of deleting features from a layer, let's try creating a new layer from scratch and copying features across.

# First define the fields - just area for now, then add in aspect and slope classes later
# fields = QgsFields() #  This is the list of fields (or names for "attributes")
# fields.append(QgsField("area_plan", QVariant.Double)) # Just one field for now
# 
# areaCalcFile = dataDirectoryPath / 'Area-Calculated-Roof-Planes.shp'	# output file location
# writer = QgsVectorFileWriter(str(areaCalcFile), "UTF-8", fields, QgsWkbTypes.Polygon, driverName="ESRI Shapefile")
# 
# if writer.hasError() != QgsVectorFileWriter.NoError:
#     print("Error when creating shapefile: ",  w.errorMessage())
# 	
# # Find the existing layer and iterate over its features (polygons)
# # We need to copy the original geometry (the points of the polygon) and the new area attribute for each feature.
# layers = QgsProject.instance().mapLayersByName('Processed-Roof-Planes') 
# layer = layers[0] 
# features = layer.getFeatures()
# print("Features in original layer:")
# print(layer.featureCount())
# 
# loop_count = 0
# for feature in features:
# 	newfeature=QgsFeature()  # Create a new feature which we will add to the brand new layer
# 	geom = feature.geometry()
# 	if geom: # only if not null, otherwise don't include this feature in the new layer
# 		newfeature.setAttributes(["area_plan", geom.area()])
# 		newfeature.setGeometry(geom)
# 		# print("setting area to" + str(geom.area()))
# 		err=writer.addFeature(newfeature) # add the feature to the new layer
# 	loop_count=loop_count+1
# 	#if loop_count > 100:
# 	#	break
# 	if not loop_count%10000:
# 		print(loop_count) # Every 10000 times around the loop give an update
# 
# del writer  # delete the writer to flush features to disk
# 
# # Now load the layer back into the interface:
# 
# newLayer = QgsVectorLayer(str(areaCalcFile), "Calculated Area", "ogr")
# if not newLayer.isValid():
#     print("Layer failed to load!")
# layer=QgsProject.instance().addMapLayer(newLayer)




# Now load the layer into the interface:

#newLayer = QgsVectorLayer(str(areaCalcFile), "Calculated Area", "ogr")
#layer=QgsProject.instance().addMapLayer(newLayer)

#areaCalcFile = dataDirectoryPath / 'Area-Calculated-Roof-Planes.shp'	# output file location
#writer = QgsVectorFileWriter(str(areaCalcFile), "UTF-8", fields, QgsWkbTypes.Polygon, driverName="ESRI Shapefile")

#if writer.hasError() != QgsVectorFileWriter.NoError:
#    print("Error when creating shapefile: ",  w.errorMessage())



# # Step 62 clip by extent
# #  This uses the coordinates of the extent of the Ambleside-extent layer
# processing.run("gdal:cliprasterbymasklayer", {'INPUT':'C:/CAFS/Ambleside Project/DATA/DSM_1m_composite.vrt','MASK':'/vsizip/C:/CAFS/Ambleside Project/DATA/Ambleside Extent.zip','NODATA':None,'ALPHA_BAND':False,'CROP_TO_CUTLINE':False,'KEEP_RESOLUTION':False,'OPTIONS':'','DATA_TYPE':0,'OUTPUT':'C:/CAFS/Ambleside Project/DATA/DSM-Shadow-1m.vrt'})
# # Step 12 Build Virtual Raster
# processing.run("gdal:buildvirtualraster", {'INPUT':['C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3500_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3501_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3502_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3503_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3504_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3505_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3506_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3507_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3508_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3509_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3600_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3601_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3602_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3603_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3604_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3605_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3606_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3607_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3608_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3609_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3700_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3701_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3702_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3703_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3704_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3705_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3706_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3707_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3708_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3709_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3800_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3801_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3802_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3803_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3804_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3805_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3806_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3807_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3808_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3900_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3901_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3902_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3903_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3904_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3905_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3906_DSM_1M.asc','C:/CAFS/Ambleside Project/LIDAR data Cumbria/DSM/ny3907_DSM_1M.asc'],'RESOLUTION':1,'SEPARATE':False,'PROJ_DIFFERENCE':False,'ADD_ALPHA':False,'ASSIGN_CRS':None,'RESAMPLING':0,'SRC_NODATA':'','OUTPUT':'C:/CAFS/Ambleside Project/DATA/DSM_1m_composite.vrt'})

	
		


##############################

############### Example code ##################

# # Iterate over each feature in the layer.  Each feature should be a polygon.
# features = layer.getFeatures()
# a=0
# for feature in features:
# 	geom = feature.geometry()
# 	print (geom)
# 	if not geom:  ### The only way I can find to test for Null reference that works!
# 		print("It's Null")
# #	print (geom.area())
# 	a=a+1
# 	if a>100:
# 		raise StopIteration
# 
# # get field names
# for field in layer.fields():
#     print(field.name())
# 
# # get layer by name
# layers = QgsProject.instance().mapLayersByName('Ambleside Extent') 
# layer = layers[0] #
# 
# # get layer by name
# layers = QgsProject.instance().mapLayersByName('Roof-Aspect-Vector-Fixed') 
# layer = layers[0] #
# 
# # get layer by name
# layers = QgsProject.instance().mapLayersByName('Processed-Roof-Planes') 
# layer = layers[0] #
# 
# # delete a feature - might be faster to delete multiple features with deleteFeatures()
# # layer.startEditing()
# # layer.deleteFeatures([1,2,3]) # delete a (Python) set of features
# # layer.commitChanges()
# 
# # Documentation isn't too clear, but deleteFeatures needs a Python list rather than a set
# # Find a list of features that have null geometry
# # features = layer.getFeatures()
# # featuresToDelete = []
# # print(layer.featureCount())
# # for feature in features:
# # 	geom = feature.geometry()
# # 	if not geom:
# # 		featuresToDelete.append(feature.id())
# # 
# # layer.startEditing()
# # layer.deleteFeatures(featuresToDelete) # delete a (Python) set of features
# # layer.commitChanges()
# # layer.featureCount()
# 
# 
# layer = iface.activeLayer()
# for field in layer.fields():
# 	print(field.name(), field.typeName())
# 
# ### Saving to a memory layer (but I had problems):
# 
# parameters = {
# 	'INPUT' : 'xxx-existing-layer-xxx', 
# 	'DISTANCE':1,
# 	'SEGMENTS':5,
# 	'END_CAP_STYLE':0,
# 	'JOIN_STYLE':0,
# 	'MITER_LIMIT':2,
# 	'DISSOLVE':False,
# 	'OUTPUT':'memory:'}
# results = processing.run('<algorithm>',parameters)
# vlayer=QgsProject.instance().addMapLayer(results['OUTPUT']) # returns pointer to added memory layer
# vlayer.setName("new-name")
# 
# # Logging a message to the log console in QGIS:
# msg = "Geometry area for old feature:" + str(geom.area())
# QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)
# 
# #  Grab a raster layer by name:
# rlayer = QgsProject.instance().mapLayersByName('DSM-DTM_1m')[0]
# # Output its width & height:
# rlayer.width(), rlayer.height()
# #etc...




############  End of Example Code ###############


# ##########  EXPERMIOENTAL CODE ###################
# ################
# # 45 (TOO SLOW) attempt 1 - Calculate area for each polygon and delete null area polygons
# 
# # 45.1 Add in a new attribute
# layer.startEditing()
# layer.addAttribute(QgsField("area_plan", QVariant.Double))
# layer.commitChanges()
# print("Area_plan attribute added")
# 
# # 45.2 go through each feature (polygon) and calculate the area, also comling a list of NULL area features
# 
# layer.startEditing()
# features = layer.getFeatures()
# loop_count = 0
# featuresToDelete = []
# print(layer.featureCount())
# for feature in features:
# 	geom = feature.geometry()
# 	if not geom:
# 		featuresToDelete.append(feature.id())
# #		print("null geometry")
# 	else:
# 		feature.setAttributes(["area_plan", geom.area()])
# 		print("setting area to" + geom.area())
# 	loop_count=loop_count+1
# 	if loop_count > 1000:
# 		raise StopIteration
# 	if true: #not loop_count%10000:
# 		print(loop_count) # Every 10000 times around the loop give an update
# 		print(geom.area())
# 		
# layer.commitChanges()
# 
# 
# # feature.attributes() # returns the attributes for this feature
# 
# # 45.3 Now delete the NULL area features found in the previous step:
# 
# layer.featureCount()
# layer.startEditing()
# layer.deleteFeatures(featuresToDelete) # delete a (Python) set of features
# layer.commitChanges()
# layer.featureCount()
# 
# 
# # (45) Experimental code - this is now in the plugin ProcessingTest
# 
# newLayer = QgsVectorLayer("multipolygon","Calculated-area","memory")
# 
# with edit(newLayer):
# 	# First define the fields - just area for now, then add in aspect and slope classes later
# 	fields = QgsFields() #  This is the list of fields (or "attributes")
# 	fields.append(QgsField("area_plan", QVariant.Double)) # Just one field for now
# 	provider=newLayer.dataProvider()
# 	provider.addAttributes(fields)
# 	newLayer.updateFields() # fetch changes from the data provider
# 	print("fields:", len(provider.fields()))
# 		
# 	layers = QgsProject.instance().mapLayersByName('Processed-Roof-Planes') 
# 	layer = layers[0] 
# 	features = layer.getFeatures()
# 	print("Features in original layer:")
# 	print(layer.featureCount())
# 	loop_count=0
# 
# 	# Find the existing layer and iterate over its features (polygons)
# 	# We need to clone the original geometry (the points of the polygon - represented by the underlying AbstractGeometry object) 
# 	# and the new area attribute for each feature.
# 	
# 	for feature in features:
# 		newFeature=QgsFeature()  # Create a new feature which we will add to the brand new layer
# 		geom = feature.geometry()
# 		if geom: # only if not null, otherwise don't include this feature in the new layer
# 			newFeature.setAttributes(["area_plan", geom.area()])
# 			newFeature.setGeometry(geom)
# 			bool=newLayer.addFeatures([newFeature]) # Capture the value to prevent the console printing out the return value!
# 		loop_count=loop_count+1
# 		#if loop_count > 20:
# 		#	break
# 		if not loop_count%10000:
# 			print(loop_count) # Every 10000 times around the loop give an update
# 			
# 	newLayer.updateExtents() # fetch changes from data provider
# 	print("total features in new layer:")
# 	print(newLayer.featureCount())
# 	e = newLayer.extent()
# 	print("extent:", e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum())
# 
# 
# # Now check that everything in 45.3 worked:
# 
# # First check the attributes list:
# print("List of fields in New Layer:")
# count=newLayer.fields().count()
# for index in range(count):
# 	print(newLayer.fields().field(index))
# 	
# loop_count=0
# for feature in newLayer.getFeatures():
# 	loop_count=loop_count+1
# 	if loop_count > 20:
# 		break
# 	print(feature.geometry())
# 	print(feature.attribute("area_plan"))
# 	
# # Finally, add the layer to the legend:
# layer=QgsProject.instance().addMapLayer(newLayer)
# 	
####################   END OF 45 ######################################

##############








###################  START OF SOLAR CALCULATION PHASE ######################

### STEP 79 - Appears to work ###
# TODO HANDLE EXCEPTIONS PROPERLY - CONSISTENT USE OF SOLAREXCEPTION #
#importlib.reload(sys.modules['UMEP.MetdataProcessor.metdata_processor_modified'])


msg = "Starting Step 79 - Process meteorological data"
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

from UMEP.MetdataProcessor import metdata_processor_modified as mps
metdataProcessor=mps.MetdataProcessor()

# TODO - should we use the project path rather than the data path?
metereologicalDataPath = projectPath / METEOROLOGICAL_FILE_RAW_FILE_NAME
epwFileDataPath = dataDirectoryPath / METEOROLOGICAL_FILE_PROCESSED_FILE_NAME

metdataProcessor.importFileFromFilePath(metereologicalDataPath)
# metdataProcessor.preprocessMetData(epwFileDataPath)
### END OF STEP 79 ###



### STEP 80 - CALCULATE WALL HEIGHT AND ASPECT RASTERS - TESTED AND WORKS###

# importlib.reload(sys.modules['UMEP.WallHeight.wall_height_modified'])

msg = "Starting Step 80 - calculate wall height and aspect rasters"
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)
iface.messageBar().pushMessage("Info:", msg, level=Qgis.Info, duration=10)

wallHeightCalculator = wallheightmod.WallHeight(iface)

wallHeightFilePath = dataDirectoryPath / WALL_HEIGHT_FILE_NAME
wallAspectFilePath = dataDirectoryPath / WALL_ASPECT_FILE_NAME
wallLimit=2.0 # 2 metres minimum wall height

layers = QgsProject.instance().mapLayersByName(DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME) 
dsmMinusDtmLayer = layers[0] #

wallHeightCalculator.calculateWallHeightRaster(dsmMinusDtmLayer, wallLimit, str(wallHeightFilePath), str(wallAspectFilePath), WALL_HEIGHT_LAYER_NAME, WALL_ASPECT_LAYER_NAME, True, True)



# wallHeightRasterLayer.setName(WALL_HEIGHT_LAYER_NAME)
# wallAspectRasterLayer.setName(WALL_ASPECT_LAYER_NAME)


####### START OF STEP 81 - MOST IMPORTANT STEP #########
# WORKING VERSION OF CODE TO CREATE THE ENERGY raster!
# Relies on wall aspect and wall height already having been calculated
# Also needs meteorological data files to have been translated

# Reloading modules when they have changed!
# importlib.reload(sys.modules['UMEP.SEBE'])
# importlib.reload(sys.modules['UMEP.SEBE.sebeworker_modified'])
# importlib.reload(sys.modules['UMEP.SEBE.sebe_modified'])

msg = "Starting Step 81 - calculate the energy raster - amount of sunlight falling on roofs"
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

from UMEP.SEBE import sebe_modified as sm

sebe = sm.SEBE(iface)

UTC_OFFSET=0
ALBEDO=0.15
PSI=0.03 # 3% transmission
vegdsm=None
vegdsm2=None
usevegdem=0

metereologicalDataPath = dataDirectoryPath / METEOROLOGICAL_FILE_PROCESSED_FILE_NAME

layers = QgsProject.instance().mapLayersByName(WALL_HEIGHT_FILE_NAME) 
dsmlayer = layers[0] #

msg = "(81) - reading meteorological data..."
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

sebe.readMeteorologicalData(metereologicalDataPath)

msg = "(81) - initialise SEBE parameters..."
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

# Obtain these layers back again (as they were produced by threads, don't try to grab synchronously).
layers = QgsProject.instance().mapLayersByName(WALL_HEIGHT_LAYER_NAME) 
wallHeightRasterLayer = layers[0] #
layers = QgsProject.instance().mapLayersByName(WALL_ASPECT_LAYER_NAME) 
wallAspectRasterLayer = layers[0] #
layers = QgsProject.instance().mapLayersByName(DSM_1M_CLIPPED_LAYER_NAME) 
dsmLayer = layers[0] #


building_slope, building_aspect, scale, voxelheight, sizey, sizex, radmatI, radmatD, radmatR, calc_month, dSM, wHeight, wAspect = sebe.calculateSebeParameters(dsmLayer, wallHeightRasterLayer, wallAspectRasterLayer, UTC_OFFSET, ALBEDO, str(dataDirectoryPath))

msg = "(81) - starting the  SEBE calculation background thread..."
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

sebe.solarLayerName=SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME # the layer name of the final calculated raster
sebe.folderPath = [str(dataDirectoryPath)] # Add this code in appropriately:
sebe.startModifiedWorker(dSM, scale, building_slope, building_aspect, voxelheight, sizey, sizex, vegdsm, vegdsm2, wHeight, wAspect, ALBEDO, PSI, radmatI, radmatD, radmatR, usevegdem, calc_month)
### END OF STEP 81 ###

# STEP 83 - Finally, calculate mean irradiation over each roof
# BUT, because of the slightly altered order of calculations that we are using, 
# use PROCESSED_ROOF_PLANES rather than SUITABLE_ROOFS as the basis of our roof plan
# This will result in more calculations and more roofs areas being calculated, but will
# make our code easier to follow later.
# Use column STATS: [2] because we are calculating the mean

# Step 83 - Find the mean solar irradiation across each polygon and store as an attribute.  Ignore stdev for now.

# NB! WAIT for the solar calculation before doing this step:

msg = "(83) - calculating irradiation across each roof..."
QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)

layers = QgsProject.instance().mapLayersByName(SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME) 
solarLayer = layers[0] #
solarLayer.setCrs(crs)

parameters = {
	'INPUT_RASTER':SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME,
	'RASTER_BAND':1,
	'INPUT_VECTOR':PROCESSED_ROOF_PLANES_LAYER_NAME,
	'COLUMN_PREFIX':'Irrad_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())




###################  END OF SOLAR CALCULATION PHASE ######################


################### START OF SHADOW CALCULATION PHASE #####################

#For testing
#LOCAL_EXTENT_LAYER_NAME='small-area-extent'


# Step 64 - first clip the DSM so that we can perform shadow calculations
# (see note in step 35)
#  works but produces warnings about crs (we fix these by setting crs manually).  
# [for some reason cliprasterbymasklayer doesn't work at all]

DSM_clipped_File = dataDirectoryPath / 'DSM-1m-clipped.tif'
parameters = {
	'INPUT':DSM_1M_LAYER_NAME,
	'PROJWIN':LOCAL_EXTENT_LAYER_NAME,
	'NODATA':-9999,
	'OPTIONS':'',
	'DATA_TYPE':0,
	'OUTPUT':str(DSM_clipped_File)}
results = processing.run('gdal:cliprasterbyextent',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], DSM_1M_CLIPPED_LAYER_NAME) # IGNORE WARNINGS ABOUT CRS HERE
rlayer.setCrs(crs)
layer=QgsProject.instance().addMapLayer(rlayer) # Add it to the visual interface as a new layer



### STEPS 65-68 SHADOW CALCULATION ####
# NOTE "SHADOW" directory must exist!

# importlib.reload(sys.modules['UMEP.ShadowGenerator'])
# importlib.reload(sys.modules['UMEP.ShadowGenerator.shadow_generator_modified'])

from UMEP.ShadowGenerator import shadow_generator_modified as shadow_generator
sg = shadow_generator.ShadowGenerator(iface)


layers = QgsProject.instance().mapLayersByName(DSM_1M_CLIPPED_LAYER_NAME) 
dsmLayer = layers[0] #

progress = QProgressBar()
dlg = FakeDialog(progress)

hour=0
min=0
sec=0
trans=0.03
UTC=0
loadRasterIntoCanvas=1
usevegdem=0
timeInterval=60
onetime=0


# March 20th 2020
dst=0
sg.calculateShadowRaster(dsmLayer, 2020, 3, 20, hour, min, sec, UTC, trans, timeInterval, dst, onetime, loadRasterIntoCanvas, str(shadowDirectoryPath), None, None, usevegdem, dlg) # step 65
layer200320=sg.calculatedLayer
layer200320.setCrs(crs)

# June 21st 2020 (daylight savings: dst=1)
dst=1
sg.calculateShadowRaster(dsmLayer, 2020, 6, 21, hour, min, sec, UTC, trans, timeInterval, dst, onetime, loadRasterIntoCanvas, str(shadowDirectoryPath), None, None, usevegdem, dlg) # step 66
layer200621=sg.calculatedLayer
layer200621.setCrs(crs)

# Sept 23rd 2020 (daylight savings: dst=1)
dst=1
sg.calculateShadowRaster(dsmLayer, 2020, 9, 23, hour, min, sec, UTC, trans, timeInterval, dst, onetime, loadRasterIntoCanvas, str(shadowDirectoryPath), None, None, usevegdem, dlg) # step 67
layer200923=sg.calculatedLayer
layer200923.setCrs(crs)


# Dec 22nd 2020 
dst=0
sg.calculateShadowRaster(dsmLayer, 2020, 12, 22, hour, min, sec, UTC, trans, timeInterval, dst, onetime, loadRasterIntoCanvas, str(shadowDirectoryPath), None, None, usevegdem, dlg) # step 68
layer201222=sg.calculatedLayer
layer201222.setCrs(crs)

#	def calculateShadowRaster(iface, dsmlayer, year, month, day, hour, minu, sec, UTC, trans, intervalTime, dst, onetime, loadRasterIntoCanvas, folderPath, vegdsm, vegdsm2, usevegdem, dlg):

#STEP 70.1 March reclassification to a binary raster
reclassifiedFile = dataDirectoryPath / 'March-binary.tif'
parameters = {
	'INPUT_RASTER':layer200320,
	'RASTER_BAND':1,
	'TABLE':[0,0.5,0,0.5,1,1],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,
	'OUTPUT':str(reclassifiedFile)}
results = processing.run('native:reclassifybytable',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], MARCH_BINARY_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

#STEP 70.2 September reclassification to a binary raster
reclassifiedFile = dataDirectoryPath / 'September-binary.tif'
parameters = {
	'INPUT_RASTER':layer200923,
	'RASTER_BAND':1,
	'TABLE':[0,0.5,0,0.5,1,1],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,
	'OUTPUT':str(reclassifiedFile)}
results = processing.run('native:reclassifybytable',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SEPTEMBER_BINARY_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)


#STEP 71 June reclassification to a binary raster
reclassifiedFile = dataDirectoryPath / 'June-binary.tif'
parameters = {
	'INPUT_RASTER':layer200621,
	'RASTER_BAND':1,
	'TABLE':[0,0.6,0,0.6,1,1],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,
	'OUTPUT':str(reclassifiedFile)}
results = processing.run('native:reclassifybytable',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], JUNE_BINARY_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

#STEP 72 June reclassification to a binary raster
reclassifiedFile = dataDirectoryPath / 'December-binary.tif'
parameters = {
	'INPUT_RASTER':layer201222,
	'RASTER_BAND':1,
	'TABLE':[0,0.4,0,0.4,1,1],
	'NO_DATA':-9999,
	'RANGE_BOUNDARIES':0,
	'NODATA_FOR_MISSING':False,
	'DATA_TYPE':5,
	'OUTPUT':str(reclassifiedFile)}
results = processing.run('native:reclassifybytable',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], DECEMBER_BINARY_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)

# STEP 73 Multiply all binary rasters together to produce the final shadow binary result:
shadowBinaryFile = dataDirectoryPath / 'shadow-binary.tif'
parameters = {
	'INPUT_A' : MARCH_BINARY_LAYER_NAME,
    'BAND_A' : 1,
	'INPUT_B' : JUNE_BINARY_LAYER_NAME,
    'BAND_B' : 1,
	'INPUT_C' : SEPTEMBER_BINARY_LAYER_NAME,
    'BAND_C' : 1,
	'INPUT_D' : DECEMBER_BINARY_LAYER_NAME,
    'BAND_D' : 1,
    'FORMULA' : 'A * B * C * D',   
	'OUTPUT':str(shadowBinaryFile)}
results = processing.run('gdal:rastercalculator',parameters, feedback=MyFeedBack())
rlayer = QgsRasterLayer(results['OUTPUT'], SHADOW_BINARY_LAYER_NAME) # This is a raster layer
layer=QgsProject.instance().addMapLayer(rlayer)
layer.setCrs(crs)


# STEP 75 Use zonal stats to calculate mean shade for each roof
# BUT, because of the slightly altered order of calculations that we are using, 
# use PROCESSED_ROOF_PLANES rather than SUITABLE_ROOFS as the basis of our roof plan
# This will result in more calculations and more roofs areas being calculated, but will
# make our code easier to follow later.
# Use column STATS: [2] because we are calculating the mean

# MUST BE RUN ***AFTER*** THE SHADOW PHASE - both shadow binary & processed roof planes layers must exist 

parameters = {
	'INPUT_RASTER':SHADOW_BINARY_LAYER_NAME,
	'RASTER_BAND':1,
	'INPUT_VECTOR':PROCESSED_ROOF_PLANES_LAYER_NAME,
	'COLUMN_PREFIX':'Shade_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())




################### END OF SHADOW CALCULATION PHASE #####################



############### WORKING TEST OF CAFS:calculate script ##############


from qgis.core import *
from pathlib import Path # Post python 3.4
import os
from cafs import *
projectPathString = QgsProject.instance().readPath("./")
projectPath = Path(projectPathString)
dataDirectoryPath = projectPath / 'DATA' 
tempDataString = 'DATA3b'
resultsString = 'RESULTS3b'
tempDataDirectoryPath = projectPath / tempDataString 
resultsDirectoryPath = projectPath / resultsString
localExtentPath = projectPath / 'SMALL-AREAS' / 'alston-moor-3.shp'
meteorologicalPath = projectPath / 'tmy_54.430_-2.963_2006_2015.epw'
buildingsPath = projectPath / 'CUMBRIA_BUILDINGS.shp'
DSM_Path = dataDirectoryPath / 'DSM_1M.vrt'
DTM_Path = dataDirectoryPath / 'DTM_1M.vrt'

if not os.path.exists(str(dataDirectoryPath)):
    os.makedirs(dataDirectoryPath)

if not os.path.exists(str(tempDataDirectoryPath)):
    os.makedirs(tempDataDirectoryPath)

if not os.path.exists(str(resultsDirectoryPath)):
    os.makedirs(resultsDirectoryPath)

class MyFeedBack(QgsProcessingFeedback):

    def reportError(self, error, fatalError=False):
        print(error)

parameters = {
		'DATA_DIRECTORY':tempDataString,
		'LOCAL_EXTENT':str(localExtentPath),
		'BUILDINGS_LAYER':str(buildingsPath),
		'DTM_LAYER':str(DTM_Path),
		'DSM_LAYER':str(DSM_Path),
		'RESULTS_DIRECTORY':resultsString,
		'METEOROLOGICAL_DATA_FILE':str(meteorologicalPath),
		'USE_WIDE_AREA':0,
		'WIDE_LAYER':str(localExtentPath)
	}
processing.run('CAFS:calculate',parameters, feedback=MyFeedBack())



############## Alston Moor Re-calculations ####################
# Calculates roof areas and shadow rasters

from qgis.core import *
from pathlib import Path # Post python 3.4
import os
from cafs import *
from SolarConstants import *
projectPathString = QgsProject.instance().readPath("./")
projectPath = Path(projectPathString)
dataDirectoryPath = projectPath / 'DATA' 
smallAreasPath = projectPath / 'SMALL-AREAS' 
localExtentPath = smallAreasPath / 'alston-moor-18.shp'
meteorologicalPath = projectPath / 'tmy_54.430_-2.963_2006_2015.epw'
buildingsPath = projectPath / 'CUMBRIA_BUILDINGS.shp'
DSM_Path = dataDirectoryPath / 'DSM_1M.vrt'
DTM_Path = dataDirectoryPath / 'DTM_1M.vrt'
tempDataString = 'DATA1'
resultsString = 'RESULTS1'
tempDataDirectoryPath = projectPath / tempDataString 
resultsDirectoryPath = projectPath / resultsString

def cafsShadow(dataString, localExtentPath, DTM_Path, DSM_Path, useWideArea, wideAreaPath):
	log(f"Starting shadow for DATA_DIRECTORY: {dataString}")
	parameters = {
		'DATA_DIRECTORY':dataString,
		'DSM_LAYER':str(DSM_Path),
		'USE_WIDE_AREA':useWideArea,
		'WIDE_LAYER':str(wideAreaPath),
		'LOCAL_LAYER':str(localExtentPath),
		'DTM_LAYER':str(DTM_Path)
	}
	processing.run('CAFS:shadow',parameters, feedback=MyFeedBack())

def cafsRoofProcessor(dataString, localExtentPath, buildingsPath, DTM_Path, DSM_Path):
	log(f"Starting roofprocessor for DATA_DIRECTORY: {dataString}")
	parameters = {
		'DATA_DIRECTORY':dataString,
		'LOCAL_EXTENT':str(localExtentPath),
		'BUILDINGS_LAYER':str(buildingsPath),
		'DTM_LAYER':str(DTM_Path),
		'DSM_LAYER':str(DSM_Path)
	}
	processing.run('CAFS:roofprocessor',parameters, feedback=MyFeedBack())


class MyFeedBack(QgsProcessingFeedback):

    def reportError(self, error, fatalError=False):
        print(error)

def log(msg):
    QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)



if not os.path.exists(str(dataDirectoryPath)):
    os.makedirs(dataDirectoryPath)

if not os.path.exists(str(resultsDirectoryPath)):
    os.makedirs(resultsDirectoryPath)

if not os.path.exists(str(tempDataDirectoryPath)):
    os.makedirs(tempDataDirectoryPath)


tempDataString = 'DATA12'
if not os.path.exists(str(dataDirectoryPath)):
    os.makedirs(dataDirectoryPath)

localExtentPath = smallAreasPath / 'alston-moor-12.shp'
tempDataDirectoryPath = projectPath / tempDataString 

cafsRoofProcessor(tempDataString, localExtentPath, buildingsPath, DTM_Path, DSM_Path)
cafsShadow(tempDataString, localExtentPath, DTM_Path, DSM_Path, 0, localExtentPath)

tempDataString = 'DATA13'
if not os.path.exists(str(dataDirectoryPath)):
    os.makedirs(dataDirectoryPath)

localExtentPath = smallAreasPath / 'alston-moor-13.shp'
tempDataDirectoryPath = projectPath / tempDataString 

cafsRoofProcessor(tempDataString, localExtentPath, buildingsPath, DTM_Path, DSM_Path)
cafsShadow(tempDataString, localExtentPath, DTM_Path, DSM_Path, 0, localExtentPath)

# This bit is temporary. (Re)-calculate zonal statistics across each roof area for the solar raster
# (Due to the earlier miscalculation)


tempDataString = 'DATA15'
tempDataDirectoryPath = projectPath / tempDataString 

solarRasterPath = tempDataDirectoryPath / ('annual-solar-energy.tif')
processedRoofPlanesPath = tempDataDirectoryPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')

parameters = {
	'INPUT_RASTER':str(solarRasterPath),
	'RASTER_BAND':1,
	'INPUT_VECTOR':str(processedRoofPlanesPath),
	'COLUMN_PREFIX':'Irrad_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())


tempDataString = 'DATA16'
tempDataDirectoryPath = projectPath / tempDataString 

solarRasterPath = tempDataDirectoryPath / ('annual-solar-energy.tif')
processedRoofPlanesPath = tempDataDirectoryPath / (PROCESSED_ROOF_PLANES_LAYER_NAME + '.shp')

parameters = {
	'INPUT_RASTER':str(solarRasterPath),
	'RASTER_BAND':1,
	'INPUT_VECTOR':str(processedRoofPlanesPath),
	'COLUMN_PREFIX':'Irrad_',
	'STATS':[2]}
results = processing.run("qgis:zonalstatistics", parameters, feedback=MyFeedBack())

# Alston Moor - calculate the suitable roofs for each area

tempDataString = 'DATA18'
resultsString = 'RESULTS18'
tempDataDirectoryPath = projectPath / tempDataString 
resultsDirectoryPath = projectPath / resultsString

if not os.path.exists(str(resultsDirectoryPath)):
    os.makedirs(resultsDirectoryPath)

log(f"Starting suitableroofs for DATA_DIRECTORY: {str(tempDataDirectoryPath)}")
parameters = {
	'DATA_DIRECTORY':str(tempDataDirectoryPath),
	'RESULTS_DIRECTORY':str(resultsDirectoryPath)        
}
processing.run('CAFS:suitableroofs', parameters, feedback=MyFeedBack())


tempDataString = 'DATA19'
resultsString = 'RESULTS19'
tempDataDirectoryPath = projectPath / tempDataString 
resultsDirectoryPath = projectPath / resultsString

if not os.path.exists(str(resultsDirectoryPath)):
    os.makedirs(resultsDirectoryPath)

log(f"Starting suitableroofs for DATA_DIRECTORY: {str(tempDataDirectoryPath)}")
parameters = {
	'DATA_DIRECTORY':str(tempDataDirectoryPath),
	'RESULTS_DIRECTORY':str(resultsDirectoryPath)        
}
processing.run('CAFS:suitableroofs', parameters, feedback=MyFeedBack())



