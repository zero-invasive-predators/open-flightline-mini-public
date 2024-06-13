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
                       QgsProject,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterNumber)
from qgis import processing
from open_flightline_mini import flightline_project


class CombineAndChangeLoadSize(QgsProcessingAlgorithm):
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
    LOAD_NUMBERS = 'LOAD_NUMBERS'
    BUCKET_SIZE = 'BUCkET_SIZE'
    RESULTS = 'RESULTS'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Project Management', string)

    def createInstance(self):
        return CombineAndChangeLoadSize()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'combine_load_numbers'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('5. Combine and Change Loads')

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

        return self.tr("Combines Consecutive Load Numbers")

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

        self.addParameter(
            QgsProcessingParameterEnum(name=self.LOAD_NUMBERS,
                                       description="Load Numbers",
                                       options=[str(i) for i in project.all_load_numbers_list],
                                       allowMultiple=True,
                                       usesStaticStrings=True,))

        self.addParameter(
            QgsProcessingParameterNumber(name=self.BUCKET_SIZE,
                                         description="Bucket Size in Kg, leave as 0 if there is no change",
                                         defaultValue=0))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        results = {}

        project_folder = self.parameterAsString(
            parameters, self.PROJECT_FOLDER, context)

        project_gpkg = self.parameterAsString(
            parameters, self.PROJECT_GPKG, context)

        machine_code = self.parameterAsString(
            parameters, self.MACHINE_CODE, context)

        load_numbers = parameters['LOAD_NUMBERS']
        load_numbers_list = [int(i) for i in load_numbers]
        if len(load_numbers_list) == 0:
            feedback.pushWarning("No load numbers selected")
            return
        bucket_size = self.parameterAsInt(parameters, self.BUCKET_SIZE, context)

        fl_project = flightline_project.FlightlineProject()
        fl_project.__set_project_folder__(project_folder)
        fl_project.read_from_json_config()
        fl_project.__set_gpkg_path__(project_gpkg)

        # Check that the load numbers exist for that machine
        heli_load_numbers = fl_project.heli_load_list(machine_code)
        if not all([i in heli_load_numbers for i in load_numbers_list]):
            feedback.reportError(f'Please select available load numbers for Machine: {machine_code}\
            \nSelected Load Numbers:\ {load_numbers_list}\nAvailable Load Numbers: {heli_load_numbers}')
            return {}

        # Update the heli points dataset
        fl_project.combine_loads_for_heli_points(machine_code, load_numbers_list, bucket_size)
        fl_project.combine_loads_for_flight_path(machine_code, load_numbers_list)

        # Delete data for the selected loads out of the other tables and recalculate
        for load in load_numbers_list:
            feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Removing data for Load: {load}")
            for table in ['heli_bait_lines_detailed', 'heli_bait_lines', 'heli_bait_lines_buffered',
                'load_summary', 'flight_path']:
                feedback.pushInfo(
                    f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Removing data from Table: {table}")
                fl_project.delete_machine_load_data(machine_code, load, table)

        load = load_numbers_list[0]
        feedback.pushInfo(f"Recalculating data from Heli points table for load: {load}")
        result = fl_project.calculate_detailed_bait_lines_by_machine_and_load(machine_code, load)
        fl_project.calculate_bait_lines_by_machine_and_load(machine_code, load)
        fl_project.calculate_sq_buffer_bait_lines_by_machine_and_load(machine_code, load)
        fl_project.calculate_flight_path(machine_code, load)

        if len(load_numbers_list) > 1:
            feedback.pushInfo(f'Load Numbers: {load_numbers_list} have been combined into load {load}')
        else:
            feedback.pushInfo(f'Load Number: {load} bucket size has been changed to {bucket_size}')

        feedback.pushInfo(
            f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Coverage Rate Details for load {load}\n{result}")
        summary = fl_project.calculate_summary_for_load_machine(machine_code, load)
        feedback.pushInfo(
            f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Summary Details:{summary}")

        return {self.RESULTS: 'Finished'}
