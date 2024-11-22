"""

/***************************************************************************

 SEBEworker - modified
                                 A QGIS plugin
 Based on some original open source code by Fredrik Lindberg.
 Adapted by Tom Nicholls for CAFS: Refactored to separate the calculation into a 
 more object-oriented design and to remove wall irradiation for speed.
                              -------------------
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

from __future__ import print_function
from builtins import range
import numpy as np
from UMEP.Utilities.SEBESOLWEIGCommonFiles.shadowingfunction_wallheight_13 import shadowingfunction_wallheight_13
import linecache
import sys

# Modified version of the UMEP SEBE Worker class which doesn't do the calculation for wall irradiation
# Also refactored to be more reusable
# @author Tom Nicholls Lancaster University CUSP project
# code written for CAFS

class Worker():


    def __init__(self, dsm, scale, building_slope, building_aspect, voxelheight, sizey, sizex,
                 wheight, waspect, albedo, psi, radmatI, radmatD, radmatR, calc_month, feedback):

        self.dsm = dsm
        self.scale = scale
        self.building_slope = building_slope
        self.building_aspect = building_aspect
        self.voxelheight = voxelheight
        self.sizey = sizey
        self.sizex = sizex
        self.wheight = wheight
        self.waspect = waspect
        self.albedo = albedo
        self.psi = psi
        self.radmatI = radmatI
        self.radmatD = radmatD
        self.radmatR = radmatR
        self.calc_month = calc_month
        self.feedback = feedback

    # Returns a numpy array of the solar energy pattern on roofs
    def run(self):
        a = self.dsm
        scale = self.scale
        slope = self.building_slope
        aspect = self.building_aspect
        voxelheight = self.voxelheight
        sizey = self.sizey
        sizex = self.sizex
        walls = self.wheight
        dirwalls = self.waspect
        albedo = self.albedo
        psi = self.psi
        radmatI = self.radmatI
        radmatD = self.radmatD
        radmatR = self.radmatR
        calc_month = self.calc_month

        # Parameters
        deg2rad = np.pi/180
        Knight = np.zeros((sizex, sizey))
        Energyyearroof = np.copy(Knight)

        # Main loop - Creating skyvault of patches of constant radians (Tregeneza and Sharples, 1993)
        skyvaultaltint = np.array([6, 18, 30, 42, 54, 66, 78, 90])
        aziinterval = np.array([30, 30, 24, 24, 18, 12, 6, 1])

        index = 0
        iRange = skyvaultaltint.size
        for i in range(iRange):
            
            jRange = aziinterval[i]
            for j in range(jRange):

                if self.feedback.isCanceled():
                    break


                #################### SOLAR RADIATION POSITIONS ###################
                #Solar Incidence angle (Roofs)
                suniroof = np.sin(slope) * np.cos(radmatI[index, 0] * deg2rad) * \
                           np.cos((radmatI[index, 1]*deg2rad)-aspect) + \
                           np.cos(slope) * np.sin((radmatI[index, 0] * deg2rad))

                suniroof[suniroof < 0] = 0

                sh, wallsh, wallsun, facesh, facesun = shadowingfunction_wallheight_13(a, radmatI[index, 1],
                                                            radmatI[index, 0], scale, walls, dirwalls * deg2rad)
                shadow = np.copy(sh)

                # roof irradiance calculation
                # direct radiation
                if radmatI[index, 2] > 0:
                    I = shadow * radmatI[index, 2] * suniroof
                else:
                    I = np.copy(Knight)

                # roof diffuse and reflected radiation
                D = radmatD[index, 2] * shadow
                R = radmatR[index, 2] * (shadow*-1 + 1)

                Energyyearroof = np.copy(Energyyearroof+D+R+I)

                index = index + 1

                self.feedback.setProgress(50 + int(50 * (((i + 1) / iRange) + ((j + 1) / (iRange * jRange))))) # From 50 to 100% as this is the second half of processing


        Energyyearroof /= 1000
        return Energyyearroof
    


