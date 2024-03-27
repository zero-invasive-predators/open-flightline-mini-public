# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
import sys
from pathlib import Path
import os
repo_path = os.path.join(Path.home(), 'Documents', 'Github', 'open-flightline-mini')
sys.path.append(repo_path)

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterFolderDestination,
                       QgsProject,
                       QgsProcessingParameterFile)
from qgis import processing

from open_flightline_mini import flightline_project
from open_flightline_mini import project_setup


class CleanupBackupData(QgsProcessingAlgorithm):
    """
    This sets up an empty geopackage and configuration for
    an aerial operation.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_GPKG = 'PROJECT_GPKG'
    LAYERS_REMOVED = 'LAYERS REMOVED'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Project Management', string)

    def createInstance(self):
        return CleanupBackupData()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'cleanup_project_layers'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('3. Cleanup Project Layers')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Open Flightline Mini')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'open_flightline'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Cleans up backed up layers")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        project = flightline_project.FlightlineProject()
        project.__set_project_folder__(QgsProject.instance().absolutePath())
        # QGIS runs when intializing before the QgsProject folder is set
        if not QgsProject.instance().absolutePath():
            return
        project.read_from_json_config()

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.PROJECT_FOLDER,
                "Project Folder",
                defaultValue=project.project_folder
                ))

        self.addParameter(
            QgsProcessingParameterFile(self.PROJECT_GPKG,
                                       "Project GPKG Location",
                                       extension='gpkg',
                                       defaultValue=project.project_gpkg
                                       ))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        project_folder = self.parameterAsString(parameters, self.PROJECT_FOLDER, context)
        project_gpkg = self.parameterAsString(parameters, self.PROJECT_GPKG, context)

        project = flightline_project.FlightlineProject()
        project.__set_project_folder__(project_folder)
        project.read_from_json_config()
        project.__set_gpkg_path__(project_gpkg)

        setup = project_setup.GeopackageDataStore(project_folder, project_gpkg)
        layers_removed, errors = setup.cleanup_gpkg_copies()

        return {self.LAYERS_REMOVED: f"{layers_removed}"}
