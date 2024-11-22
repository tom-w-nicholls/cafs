# CAFS QGIS Plugin
<h1> A Quick Demonstration of a simple Django/React/Leaflet project running in Docker</h1>

This plugin performs a survey of available public data within a geographic map in order to find domestic and commercial roof spaces suitable for solar PV installations.

This is done in 4 steps:
1. Identify flat roof spaces within the local boundary using 3D satellite imagery and ordnance survey building location data - these are the candidate roof spaces
2. Eliminate roof spaces that are too small
3. Eliminate roof spaces that are oriented too north-facing
4. Elminate roofs with the wrong slope (e.g. more than 60 degree slope)
5. Eliminate roofs in too much shadow from other obstructions (hills, trees, buildings etc)

The remaining roof spaces are the suitable roofs to perform a ground survey of data

A further processing algorithm is provided to convert this map of roofs to a map for displaying in a web browser and to output energy calculations as a CSV file.

Cumbria Action for Sustainability and other groups use this plugin to promote solar power generation to local communities

Tested to work as a plugin within QGIS version 3.14 only

Note: a lot of the solar calculations are extracted and refactored from the UMEP plugin written by Fredrik Lindberg.

The original manual process for Ambleside, as created by Alex Boyd, can be described in the following paper available from CAfS:
“Mapping Solar PV Potential in Ambleside” (joint report between CAfS and Lancaster University, 9th December 2019) available on request

See https://docs.qgis.org/3.4/en/docs/user_manual/plugins/plugins.html for how to install a plugin on this version of QGIS

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.                                   *


