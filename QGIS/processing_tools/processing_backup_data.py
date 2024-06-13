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
repo_path = os.path.join(Path.home(), 'Documents', 'Github', 'open-flightline-mini-public')
sys.path.append(repo_path)
from qgis import processing


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterFolderDestination,
                       QgsProject,
                       QgsProcessingParameterFile)

from open_flightline_mini import flightline_project
from open_flightline_mini import project_setup


class BackupGPKGData(QgsProcessingAlgorithm):
    """
    This sets up an empty geopackage and configuration for
    an aerial operation.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_GPKG = 'PROJECT_GPKG'
    RESULT = 'RESULT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Project Management', string)

    def createInstance(self):
        return BackupGPKGData()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'backup_aerial_data'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('2. Backup Aerial Data')

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
        return self.tr("Backs up and creates a fresh set of working layers")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        if not QgsProject.instance().absolutePath():
            return

        project = flightline_project.FlightlineProject()
        project.__set_project_folder__(QgsProject.instance().absolutePath())
        # QGIS runs when intializing before the QgsProject folder is set

        project.read_from_json_config()

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.PROJECT_FOLDER,
                "Project Folder",
                defaultValue=project.project_folder
            )
        )

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

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        project_folder = self.parameterAsString(
            parameters,
            self.PROJECT_FOLDER,
            context
        )

        gpkg_location = self.parameterAsString(
            parameters,
            self.PROJECT_GPKG,
            context
        )

        project = flightline_project.FlightlineProject()
        project.__set_project_folder__(project_folder)
        project.read_from_json_config()
        project.__set_gpkg_path__(gpkg_location)

        setup = project_setup.GeopackageDataStore(project_folder, gpkg_location)
        backup_number = setup.gpkg_backup_number
        setup.gpkg_backup_layers()
        setup.create_gpkg_layers(setup.working_layers_generation)

        return {self.RESULT: f"Backup Number: {backup_number + 1}"}
