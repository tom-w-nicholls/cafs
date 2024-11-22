# -*- coding: utf-8 -*-

"""
/***************************************************************************
Adds the individual algorithms in turn to the QGIS processing interface
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


__author__ = 'Tom Nicholls'
__date__ = '2020-03-09'
__copyright__ = '(C) 2020 by CAFS'
__revision__ = '$Format:%H$'

from .shadow_calculator_algorithm_wide import ShadowCalculatorAlgorithmWide
from .webMapPreparationAlgorithm import WebMapPreparationAlgorithm
from qgis.core import QgsProcessingProvider
from .roof_processor_algorithm import RoofProcessorAlgorithm
from .shadow_calculator_algorithm import ShadowCalculatorAlgorithm
from .solar_calculator_algorithm import SolarCalculatorAlgorithm
from .roof_energy_calculator_algorithm import RoofEnergyCalculatorAlgorithm
from .sort_results_algorithm import SortResultsAlgorithm
from .virtual_raster_algorithm import VirtualRasterAlgorithm
from .cafs_full_calculation_algorithm import CAfSFullCalculationAlgorithm
from .large_area_shadow_algorithm import LargeAreaShadowAlgorithm

class CafsProvider(QgsProcessingProvider):

    """ Adds the individual algorithms to the QGIS processing interface """

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    # This is important - where the cafs plugin loads in the four algorithms that are required
    
    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(VirtualRasterAlgorithm())
        self.addAlgorithm(RoofProcessorAlgorithm())
        #self.addAlgorithm(ShadowCalculatorAlgorithm())
        self.addAlgorithm(ShadowCalculatorAlgorithmWide())
        self.addAlgorithm(SolarCalculatorAlgorithm())
        self.addAlgorithm(RoofEnergyCalculatorAlgorithm())
        self.addAlgorithm(WebMapPreparationAlgorithm())
        self.addAlgorithm(SortResultsAlgorithm())
        self.addAlgorithm(CAfSFullCalculationAlgorithm())
        self.addAlgorithm(LargeAreaShadowAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'CAFS'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('CAFS')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can includeS
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
