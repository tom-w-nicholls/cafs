"""
List of global constants defined for the Solar calculations
/***************************************************************************
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

import processing

from qgis.core import *
from pathlib import Path # Post python 3.4
from qgis.PyQt.QtCore import QSettings

def isDebug():
    return False

DATA_STRING = "DATA"
RESULTS_STRING = "RESULTS"
FULL_AREA_BUILDINGS_LAYER_NAME="CUMBRIA_BUILDINGS"  
LOCAL_EXTENT_LAYER_NAME='Ambleside Extent'
LOCAL_BUILDINGS_LAYER_NAME="LOCAL_BUILDINGS"
ASPECT_LAYER_NAME = 'ASPECT'
SLOPE_LAYER_NAME = 'SLOPE'
DSM_MINUS_DTM_1M_LAYER_NAME = 'DSM-DTM'
DSM_MINUS_DTM_1M_CLIPPED_LAYER_NAME = 'DSM-DTM_CLIPPED'
DSM_1M_LAYER_NAME = 'DSM_1M'
DSM_1M_CLIPPED_LAYER_NAME = 'DSM_CLIPPED'
DTM_1M_LAYER_NAME = 'DTM_1M'
DTM_1M_CLIPPED_LAYER_NAME = 'DTM_CLIPPED'
DSM_WIDE_LAYER_NAME = 'DSM_WIDE'
WIDE_EXTENT_LAYER_NAME='WIDE_AREA'

DSM_MINUS_DTM_ABOVE_2M_LAYER_NAME = 'DSM-DTM_ABOVE_2M'
ASPECT_2M_LAYER_NAME = "ASPECT_2M"
SLOPE_2M_LAYER_NAME="SLOPE_2M"
SLOPE_RECLASSIFIED_LAYER_NAME="SLOPE_RECLASSIFIED"
ASPECT_RECLASSIFIED_LAYER_NAME="ASPECT_RECLASSIFIED"
ASPECT_SIEVED_LAYER_NAME="ASPECT_SIEVED"
SLOPE_SIEVED_LAYER_NAME="SLOPE_SIEVED"
ASPECT_SIN_LAYER_NAME="ASPECT_SIN"
ASPECT_COS_LAYER_NAME="ASPECT_COS"
BUFFERED_BUILDINGS_LAYER_NAME="BUFFERED_BUILDINGS"
ROOF_ASPECT_LAYER_NAME="ROOF_ASPECT"
ROOF_SLOPE_LAYER_NAME="ROOF_SLOPE"
ROOF_ASPECT_VECTOR_LAYER_NAME="ROOF_ASPECT_VECTOR"
ROOF_SLOPE_VECTOR_LAYER_NAME="ROOF_SLOPE_VECTOR"
ROOF_SLOPE_VECTOR_FIXED_LAYER_NAME="ROOF_SLOPE_VECTOR_FIXED"
ROOF_ASPECT_VECTOR_FIXED_LAYER_NAME="ROOF_ASPECT_VECTOR_FIXED"
ROOF_PLANES_LAYER_NAME="ROOF_PLANES"
DEBUFFERED_ROOF_PLANES_LAYER_NAME="DE_BUFFERED_ROOF_PLANES"
REBUFFERED_ROOF_PLANES_LAYER_NAME="RE_BUFFERED_ROOF_PLANES"
SINGLEPART_ROOF_PLANES_LAYER_NAME="SINGLEPART_ROOF_PLANES"
BUFFERED_ROOF_PLANES_LAYER_NAME="BUFFERED_ROOF_PLANES"
PROCESSED_ROOF_PLANES_LAYER_NAME="PROCESSED_ROOF_PLANES"
SUITABLE_ROOF_PLANES_LAYER_NAME="SUITABLE_ROOFS"
SHADOW_REJECTED_ROOFS_LAYER_NAME="SHADOW_ROOFS"
MERGED_SUITABLE_ROOF_PLANES_LAYER_NAME="SUITABLE_ROOFS_MERGED"
SORTED_SUITABLE_ROOF_PLANES_LAYER_NAME="SUITABLE_ROOFS_SORTED"
TRANSLATED_SUITABLE_ROOF_PLANES_LAYER_NAME="TRANSLATED_SUITABLE_ROOFS"
ROOF_PLANES_ATTRIBUTES_ADDED_LAYER_NAME="ROOF_PLANES_ATTRIBUTES_ADDED"
SOLAR_ENERGY_ROOF_CALCULATION_LAYER_NAME="ANNUAL_SOLAR_ENERGY"
WEB_LOCAL_BUILDINGS_LAYER_NAME="LOCAL_BUILDINGS_WEB"

ROOF_ENERGY_ATTRIBUTE_NAME = "Output_kwh"

METEOROLOGICAL_FILE_RAW_FILE_NAME="tmy_54.430_-2.963_2006_2015.epw"
METEOROLOGICAL_FILE_PROCESSED_FILE_NAME="meteorological data processed.txt"
WALL_HEIGHT_FILE_NAME="WALL_HEIGHT"
WALL_ASPECT_FILE_NAME="WALL_ASPECT"
# HOPEFULLY THESE TWO WILL BE TEMPORARY:
WALL_ASPECT_LAYER_NAME="WALL_ASPECT"
WALL_HEIGHT_LAYER_NAME="WALL_HEIGHT"
SORTED_CSV_OUTPUT_FILENAME="SORTED_SOLAR_PV_ROOF_ENERGY_OUTPUT"
CSV_OUTPUT_FILENAME="SOLAR_PV_ROOF_ENERGY_OUTPUT"
CSV_SHADOW_OUTPUT_FILENAME="REJECTED_SOLAR_ROOFS"

# TODO (low priority): Change this into a parameter in the dialog (with these defaults)
WALL_LIMIT = 3
UTC_OFFSET=0
ALBEDO=0.15
PSI=0.03 # 3% transmission

SCALE_FACTOR = 10 # used in wide area calculation, to reduce resolution of the raster

BRITISH_NATIONAL_GRID = QgsCoordinateReferenceSystem("EPSG:27700") # Hack to push layers into the correct Coordinate Reference System
# EPSG 27700 is British National Grid


MARCH_BINARY_LAYER_NAME="MARCH_BINARY"
JUNE_BINARY_LAYER_NAME="JUNE_BINARY"
SEPTEMBER_BINARY_LAYER_NAME="SEPTEMBER_BINARY"
DECEMBER_BINARY_LAYER_NAME="DECEMBER_BINARY"

SHADOW_BINARY_LAYER_NAME="SHADOW_BINARY"

CAFS_OUTPUT_LOG_NAME = "CAFS"

ASPECT_FILE_NAME = ASPECT_LAYER_NAME + ".tif"

# projectPathString = QgsProject.instance().readPath("./")
# projectPath = Path(projectPathString)
# lidarDataDirectoryPath = projectPath / 'LIDAR' 
# resultsDirectoryPath = projectPath / 'RESULTS' 
# dataDirectoryPath = projectPath / 'DATA' 
# shadowDirectoryPath = dataDirectoryPath / 'SHADOW'
# lidarDataDirectoryPath.mkdir(parents=True, exist_ok=True) # Create it to avoid crashing!
# dataDirectoryPath.mkdir(parents=True, exist_ok=True)
# resultsDirectoryPath.mkdir(parents=True, exist_ok=True)
# shadowDirectoryPath.mkdir(parents=True, exist_ok=True)


# Fix the Coordinate Reference System of the given layer
# e.g. sometimes our algorithms return a layer with the wrong CRS!
def fixLayerCrs(inputLayer, outputFilePath, context, feedback):
    parameters = {'INPUT':inputLayer, 
        'TARGET_CRS':BRITISH_NATIONAL_GRID, 
        'NODATA':-9999, 
        'COPY_SUBDATASETS':0, 
        'OPTIONS':'', 
        'DATA_TYPE':0, 
        'OUTPUT':str(outputFilePath)}
    results = processing.run('gdal:translate', parameters, context=context, feedback=feedback)
    dsmClippedLayer = results['OUTPUT']
    return dsmClippedLayer

def log(msg):
    QgsMessageLog.logMessage(msg, CAFS_OUTPUT_LOG_NAME, level=Qgis.Info)


#  convenience class to encapsulate integer values of the max and min coords of a raster layer
# Essentially a data class
class Extent():

    def __init__(self, rasterLayer):
        """
        Default constructor.
        """
        extent=rasterLayer.extent()
        self.xmin = int(extent.xMinimum())
        self.xmax = int(extent.xMaximum())
        self.ymin = int(extent.yMinimum())
        self.ymax = int(extent.yMaximum())
        self.width = self.xmax-self.xmin
        self.height = self.ymax - self.ymin
        
        def __str__(self):
            return f"layer: {rasterLayer.source()} xMin:{self.xmin}, yMin:{self.ymin}, xMax:{self.xmax}, yMax:{self.ymax}, width:{self.width}, height:{self.height}"

# Utility function
def getSystemEncoding():
        settings = QSettings()
        return settings.value('/UI/encoding', 'System')

