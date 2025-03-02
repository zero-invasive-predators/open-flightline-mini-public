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


class RecalculateMachineData(QgsProcessingAlgorithm):
    """
    This sets up an empty geopackage and configuration for
    an aerial operation.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_GPKG = 'PROJECT_GPKG'
    MACHINE_CODE = 'MACHINE_CODE'
    RESULTS = 'RESULTS'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Project Management', string)

    def createInstance(self):
        return RecalculateMachineData()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'a_combine_load_numbers'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('6. Recalculate Machine Data')

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
        return self.tr("Resets the load number in the heli_points table and recalculates the subesequent layers")

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
                defaultValue=project.project_folder))

        self.addParameter(
            QgsProcessingParameterFile(self.PROJECT_GPKG,
                                       "Project GPKG Location",
                                       extension='gpkg',
                                       defaultValue=project.project_gpkg
                                       ))

        self.addParameter(
            QgsProcessingParameterEnum(name=self.MACHINE_CODE,
                                       description='Machine Code',
                                       options=project.machine_code_list,
                                       allowMultiple=False,
                                       usesStaticStrings=True))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        results = {}

        project_folder = self.parameterAsString(parameters, self.PROJECT_FOLDER, context)
        project_gpkg = self.parameterAsString(parameters, self.PROJECT_GPKG, context)
        machine_code = self.parameterAsString(parameters, self.MACHINE_CODE, context)

        fl_project = flightline_project.FlightlineProject()
        fl_project.__set_project_folder__(project_folder)
        fl_project.read_from_json_config()
        fl_project.__set_gpkg_path__(project_gpkg)

        # Reset the load number in the heli points table
        feedback.pushInfo(f"Reseting the load number for {machine_code} in the heli_points table")
        record_count = fl_project.clear_machine_load_numbers(machine_code)
        feedback.pushInfo(f"{record_count} records cleared")

        # Delete data for the selected loads out of the other tables and recalculate
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Removing downstream data for Machine: {machine_code}")
        for table in ['heli_bait_lines_detailed', 'heli_bait_lines', 'heli_bait_lines_buffered',
                      'load_summary', 'flight_path']:
            records_removed = fl_project.delete_machine_data(machine_code, table)
            feedback.pushInfo(
                f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Removed {records_removed} records from Table: {table}")


        # Recalculate the load numbers
        feedback.pushInfo(f"Recalculating the load numbers for machine: {machine_code}")
        load_numbers = fl_project.calculate_load_number_by_machine(machine_code)
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Load Numbers: {load_numbers}")

        # Recalculate downstream data
        feedback.pushInfo(f"Recalculating downstream data from Heli points table")
        # Iterate over load numbers and update the coverage rates and bait line tables
        for load in load_numbers:
            feedback.pushInfo('\n')
            result = fl_project.calculate_detailed_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_sq_buffer_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_flight_path(machine_code, load)
            feedback.pushInfo('Created flight path')
            feedback.pushInfo(
                f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Coverage Rate Details for load {load}\n{result}")
            summary = fl_project.calculate_summary_for_load_machine(machine_code, load)
            feedback.pushInfo(
                f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Summary Details:{summary}")

        fl_project.write_to_config_json()
        return {self.RESULTS: 'Finished'}