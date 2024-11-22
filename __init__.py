# -*- coding: utf-8 -*-
"""
/***************************************************************************
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
# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Cafs class from file Cafs.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .cafs import CafsPlugin
    return CafsPlugin()
