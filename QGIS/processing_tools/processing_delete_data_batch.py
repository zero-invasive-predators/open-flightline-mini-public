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
from datetime import datetime

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterFile,
                       QgsProject)
from qgis import processing
from open_flightline_mini import flightline_project
from open_flightline_mini import data_reader


class DeleteDataBatches(QgsProcessingAlgorithm):
    """
    Provides a list of data batches that can be deleted from the data.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_GPKG = 'PROJECT_GPKG'
    DATA_BATCHES = 'DATA_BATCHES'
    RESULTS = 'RESULTS'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Delete Data Batches', string)

    def createInstance(self):
        return DeleteDataBatches()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'delete_data_batches'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('7. Delete Data Batches')

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
        parameters and outputs associated with it.
        """
        return self.tr("Deletes data bathes from the gpkg data store")

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
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(self.PROJECT_FOLDER,
                                       "Project GPKG Location",
                                       extension='gpkg',
                                       defaultValue=project.project_gpkg
                                       ))

        self.addParameter(
            QgsProcessingParameterEnum(name=self.DATA_BATCHES,
                                       description='Data Batches',
                                       options=project.get_data_batches(),
                                       allowMultiple=True,
                                       usesStaticStrings=True
                                       )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        results = {}
        project_folder = self.parameterAsString(
            parameters, self.PROJECT_FOLDER, context)

        fl_project = flightline_project.FlightlineProject()
        fl_project.__set_project_folder__(project_folder)
        fl_project.read_from_json_config()

        data_batches = parameters['DATA_BATCHES']

        for batch in data_batches:
            feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Deleting data for batch: {batch}")
            for table in ['heli_bait_lines', 'heli_bait_lines_detailed', 'heli_bait_lines_buffered',
                          'heli_points', 'load_summary', 'flight_path']:
                feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Deleting data from: {table}")
                records_deleted = fl_project.delete_batch_id_data(batch, table)
                feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: {records_deleted} from table {table}")
            feedback.pushInfo(data_reader.archive_data_batch(fl_project.raw_data_folder, batch))

        return results
