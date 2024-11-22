# The wall height and aspect pre-processor can be used to identify wall pixels and their height from ground and building digital surface models (DSM) by using a filter 

"""
/***************************************************************************
 Helper class for doing matrix calculations
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
from __future__ import absolute_import
from builtins import range
import numpy as np
import scipy.ndimage.interpolation as sc
import math
from UMEP.WallHeight.wallalgorithms import get_ders
import linecache
import sys



class Worker():
    """
    This is a non-threaded version of the WallWorker class in UMEP.WallHeight
    Provides methods for calculating numpy array properties and doing matrix calculations.
    Refactored to better fit into an O-O design.
    A future task would be to make this threaded again, but there is no current pressing need.
    
    """

    def __init__(self, walls, scale, dsm, feedback):

        self.dsm = dsm
        self.scale = scale
        self.walls = walls
        self.feedback = feedback

    # May throw exceptions directly in this modified version
    # Creates a numpy array of the calculated wall aspect based on a DSM layer and Wall Height Raster
    def run(self):
        ret = None
        a = self.dsm
        scale = self.scale
        walls = self.walls

        # def filter1Goodwin_as_aspect_v3(walls, scale, a):

        row = a.shape[0]
        col = a.shape[1]

        filtersize = np.floor((scale + 0.0000000001) * 9)
        if filtersize <= 2:
            filtersize = 3
        else:
            if filtersize != 9:
                if filtersize % 2 == 0:
                    filtersize = filtersize + 1

        filthalveceil = int(np.ceil(filtersize / 2.))
        filthalvefloor = int(np.floor(filtersize / 2.))

        filtmatrix = np.zeros((int(filtersize), int(filtersize)))
        buildfilt = np.zeros((int(filtersize), int(filtersize)))

        filtmatrix[:, filthalveceil - 1] = 1
        buildfilt[filthalveceil - 1, 0:filthalvefloor] = 1
        buildfilt[filthalveceil - 1, filthalveceil: int(filtersize)] = 2

        y = np.zeros((row, col))  # final direction
        z = np.zeros((row, col))  # temporary direction
        x = np.zeros((row, col))  # building side
        walls[walls > 0] = 1

        for h in range(0, 180):  # =0:1:180 #%increased resolution to 1 deg 20140911
            if self.feedback.isCanceled():
                    break
            filtmatrix1temp = sc.rotate(filtmatrix, h, order=1, reshape=False, mode='nearest')  # bilinear
            filtmatrix1 = np.round(filtmatrix1temp)
            filtmatrixbuildtemp = sc.rotate(buildfilt, h, order=0, reshape=False, mode='nearest')  # Nearest neighbor
            filtmatrixbuild = np.round(filtmatrixbuildtemp)
            index = 270-h
            if h == 150:
                filtmatrixbuild[:, filtmatrix.shape[0] - 1] = 0
            if h == 30:
                filtmatrixbuild[:, filtmatrix.shape[0] - 1] = 0
            if index == 225:
                n = filtmatrix.shape[0] - 1
                filtmatrix1[0, 0] = 1
                filtmatrix1[n, n] = 1
            if index == 135:
                n = filtmatrix.shape[0] - 1
                filtmatrix1[0, n] = 1
                filtmatrix1[n, 0] = 1

            for i in range(int(filthalveceil)-1, row - int(filthalveceil) - 1):  #i=filthalveceil:sizey-filthalveceil
                for j in range(int(filthalveceil)-1, col - int(filthalveceil) - 1):  #(j=filthalveceil:sizex-filthalveceil
                    if walls[i, j] == 1:
                        wallscut = walls[i-filthalvefloor:i+filthalvefloor+1, j-filthalvefloor:j+filthalvefloor+1] * filtmatrix1
                        dsmcut = a[i-filthalvefloor:i+filthalvefloor+1, j-filthalvefloor:j+filthalvefloor+1]
                        if z[i, j] < wallscut.sum():  #sum(sum(wallscut))
                            z[i, j] = wallscut.sum()  #sum(sum(wallscut));
                            if np.sum(dsmcut[filtmatrixbuild == 1]) > np.sum(dsmcut[filtmatrixbuild == 2]):
                                x[i, j] = 1
                            else:
                                x[i, j] = 2

                            y[i, j] = index

            self.feedback.setProgress(int(h * 50/180)) # From 0 to 50% as this is the first half of processing

        y[(x == 1)] = y[(x == 1)] - 180
        y[(y < 0)] = y[(y < 0)] + 360

        grad, asp = get_ders(a, scale)

        y = y + ((walls == 1) * 1) * ((y == 0) * 1) * (asp / (math.pi / 180.))

        dirwalls = y

        return dirwalls


    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

