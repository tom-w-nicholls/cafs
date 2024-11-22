"""
List of default file paths defined for the Solar calculations
All CAFS Projects should conform to this filepath specification for ease of use
Overrides are possible in the plugin inputs
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
from qgis.core import *
from pathlib import Path # Post python 3.4
from .SolarConstants import *

class SolarDirectoryPaths():

    def __init__(self):
 
        self.projectPathString = QgsProject.instance().readPath("./")
        msg = "projectPathString = " + self.projectPathString
        QgsMessageLog.logMessage(msg, "CAFS", level=Qgis.Info)
        self.projectPath = Path(self.projectPathString)
        self.lidarDataDirectoryPath = self.projectPath / 'LIDAR' 
        self.resultsDirectoryPath = self.projectPath / 'RESULTS' 
        self.resultsAllDirectoryPath = self.projectPath / 'RESULTS_ALL' 
        self.dataDirectoryPath = self.projectPath / DATA_STRING
        self.shadowDirectoryPath = self.dataDirectoryPath / 'SHADOW'
        self.dataDirectoryPath.mkdir(parents=True, exist_ok=True)
        self.resultsAllDirectoryPath.mkdir(parents=True, exist_ok=True)
        self.resultsDirectoryPath.mkdir(parents=True, exist_ok=True)
        self.shadowDirectoryPath.mkdir(parents=True, exist_ok=True)

         
