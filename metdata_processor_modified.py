# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MetdataProcessor
                                 A QGIS plugin
 Process metadata to be used in CAFS processor
                              -------------------
        begin                : 2015-06-06
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
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
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog
from UMEP.MetdataProcessor.metdata_processor_dialog import MetdataProcessorDialog
import os.path
import numpy as np
import webbrowser
# from solar_exception import SolarException

# TODO - move this file into the Solar Plugin Directory

class MetdataProcessor(object):
    """QGIS Plugin Implementation."""

    def __init__(self):
        """Constructor.

        """
        # Save reference to the QGIS interface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MetdataProcessor_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MetdataProcessor', message)


    # Extracted method allowing us to do the import as a method call directly
    # Can throw an exception of file fails to import or format is wrong
    # @author Tom - Lancaster University 
    def importFileFromFilePath(self, filePath):
        self.data = np.genfromtxt(filePath, skip_header=8, delimiter=',', filling_values=99999)
        returnMessage = "EPW file imported", "No time or meteorological variables need to be specified. "\
        "Press 'Export data' to continue to generate an UMEP-formatted text-file."

    def import_file(self):
        if self.dlg.checkBoxEPW.isChecked():
            result = self.fileDialog.exec_()
            self.dlg.pushButtonExport.setEnabled(True)
            self.folderPath = self.fileDialog.selectedFiles()
            filePath = self.folderPath[0]
            self.dlg.textInput.setText(filePath)
            if result == 1:
                try:
                    self.importFileFromFilePath(filePath)
                    QMessageBox.information(self.dlg, "EPW file imported",
                                            "No time or meteorological variables need to be specified. "
                                            "Press 'Export data' to continue to generate an UMEP-formatted text-file.")
                except Exception as e:
                    QMessageBox.critical(self.dlg, "Error: Check the number of columns in each line", str(e))
                    return

    def epw2umep(self, met_old):
        met_new = np.zeros((met_old.shape[0], 24)) - 999

        # yyyy
        met_new[:, 0] = 1985
        met_new[met_old.shape[0] - 1, 0] = 1986

        # hour
        met_new[:, 2] = met_old[:, 3]
        test = met_new[:, 2] == 24
        met_new[test, 2] = 0

        # day of year
        mm = met_old[:, 1]
        dd = met_old[:, 2]
        rownum = met_old.shape[0]
        for i in range(0, rownum):
            yy = int(met_new[i, 0])
            if (yy % 4) == 0:
                if (yy % 100) == 0:
                    if (yy % 400) == 0:
                        leapyear = 1
                    else:
                        leapyear = 0
                else:
                    leapyear = 1
            else:
                leapyear = 0
            if leapyear == 1:
                dayspermonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            else:
                dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            met_new[i, 1] = sum(dayspermonth[0:int(mm[i] - 1)]) + dd[i]

        test2 = np.where(met_new[:, 2] == 0)
        met_new[np.where(met_new[:, 2] == 0), 1] = met_new[np.where(met_new[:, 2] == 0), 1] + 1
        met_new[met_old.shape[0] - 1, 1] = 1

        # minute
        met_new[:, 3] = 0

        # met variables
        met_new[:, 11] = met_old[:, 6]  # Ta
        met_new[:, 10] = met_old[:, 8]  # Rh
        met_new[:, 12] = met_old[:, 9] / 1000.  # P
        met_new[:, 16] = met_old[:, 12]  # Ldown
        met_new[:, 14] = met_old[:, 13]  # Kdown
        met_new[:, 22] = met_old[:, 14]  # Kdir
        met_new[:, 21] = met_old[:, 15]  # Kdiff
        met_new[:, 23] = met_old[:, 20]  # Wdir
        met_new[:, 9] = met_old[:, 21]  # Ws
        met_new[:, 13] = met_old[:, 33]  # Rain
        met_new[np.where(met_new[:, 13] == 999), 13] = 0

        return met_new


    def preprocessMetData(self, outputfile):
        if not outputfile:
            raise SolarException("Error", "An output text file (.txt) must be specified")
        met_old = self.data

#         self.dlg.progressBar.setRange(0, 23)
        met_new = self.epw2umep(met_old)
        norain = np.sum(met_new[:, 13])
        # we are not concerned with rain for our application - Tom
#         if norain == 0:
#             QMessageBox.critical(None, "Value error", "No precipitation found in EPW-file. Find alternative "
#                                                   "data source if raixn is required (e.g. SUEWS).")
    
        
                                                                      #
        header = '%iy  id  it imin   Q*      QH      QE      Qs      Qf    Wind    RH     Td     press   rain ' \
                 '   Kdn    snow    ldown   fcld    wuh     xsmd    lai_hr  Kdiff   Kdir    Wd'
        numformat = '%d %d %d %d %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f ' \
                    '%.2f %.2f %.2f %.2f %.2f %.2f %.2f'
        np.savetxt(outputfile, met_new, fmt=numformat, header=header, comments='')

