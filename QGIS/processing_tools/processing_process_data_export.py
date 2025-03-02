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
from qgis.core import (QgsProcessingParameterString,
                       QgsProcessingParameterEnum,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterNumber,
                       QgsProject,
                       QgsProcessingParameterFile,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsRectangle)
from qgis.utils import iface

from qgis import processing
from open_flightline_mini import flightline_project
from open_flightline_mini import data_reader


class CopyTracmapDataUSB(QgsProcessingAlgorithm):
    """
    This sets up an empty geopackage and configuration for
    an aerial operation.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_GPKG = 'PROJECT_GPKG'
    TRACMAP_DATA_SOURCE = 'TRACMAP_DATA_SOURCE'
    MACHINE_CODE = 'MACHINE_CODE'
    DAY_NUMBER = 'DAY_NUMBER'
    DOWNLOAD_TIME = 'DOWNLOAD_TIME'
    RESULS = 'RESULTS'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Data Processing', string)

    def createInstance(self):
        return CopyTracmapDataUSB()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'copy_tracmap_data_usb'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('4. Copy Tracmap Data USB')

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
        return self.tr("Copies data from a Tracmap USB Export")

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
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                "Project Folder",
                QgsProcessingParameterFile.Behavior(1),
                defaultValue=project.project_folder
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(self.PROJECT_GPKG,
                                       "Project GPKG Location",
                                       extension='gpkg',
                                       defaultValue=project.project_gpkg
                                       ))

        self.addParameter(
            QgsProcessingParameterFile(
                self.TRACMAP_DATA_SOURCE,
                "Tracmap Data",
                QgsProcessingParameterFile.Behavior(1),
                defaultValue=flightline_project.get_last_tracmap_data_source(
                    QgsProject().instance().absolutePath())
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(self.MACHINE_CODE,
                                       'Machine Code',
                                       flightline_project.get_helicopter_list_from_project_folder(
                                           QgsProject().instance().absolutePath()),
                                       allowMultiple=False,
                                       usesStaticStrings=True
                                       )
        )

        self.addParameter(
            QgsProcessingParameterNumber(self.DAY_NUMBER,
                                         'Day Number',
                                         defaultValue=flightline_project.get_op_day(
                                             QgsProject().instance().absolutePath())
                                         )
        )

        self.addParameter(
            QgsProcessingParameterString(self.DOWNLOAD_TIME,
                                         "Download Time",
                                         defaultValue=data_reader.current_download_time()
                                         )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.

        if not QgsProject.instance().absolutePath():
            return
        feedback.pushInfo(QgsProject.instance().absolutePath())

        project_folder = self.parameterAsString(parameters, self.PROJECT_FOLDER, context)
        project_gpkg = self.parameterAsString(parameters, self.PROJECT_GPKG, context)
        tracmap_data_source = self.parameterAsString(parameters, self.TRACMAP_DATA_SOURCE, context)
        machine_code = parameters['MACHINE_CODE']
        operation_day = self.parameterAsString(parameters, self.DAY_NUMBER,context)
        download_time = self.parameterAsString(parameters, self.DOWNLOAD_TIME, context)


        feedback.pushInfo(f"Parameters:\n Machine Code: {machine_code}\n Operation Day: {operation_day}")
        feedback.pushInfo(f"Download Time: {download_time}")
        feedback.pushInfo(f"Data Source: {tracmap_data_source}")

        fl_project = flightline_project.FlightlineProject()
        fl_project.__set_project_folder__(project_folder)
        fl_project.read_from_json_config()
        fl_project.__set_gpkg_path__(project_gpkg)
        coordinate_transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(fl_project.data_source_srid),
                                                      QgsCoordinateReferenceSystem(fl_project.data_store_srid),
                                                      QgsProject().instance())

        fl_project.op_day = operation_day
        fl_project.last_data_source_location = tracmap_data_source
        valid_download_time = data_reader.data_destination_checks(fl_project.raw_data_folder,
                                                                  machine_code,
                                                                  fl_project.op_day,
                                                                  download_time)
        if valid_download_time != download_time:
            feedback.pushWarning(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Folder for download time\
             {download_time} already exits, using {valid_download_time}")

        data_destination = os.path.join(fl_project.raw_data_folder,
                                        machine_code,
                                        f"{operation_day}_{valid_download_time}")

        data_reader.copy_usb_data(tracmap_data_source, data_destination)

        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Tracmap Data Source: {tracmap_data_source}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Machine Code: {machine_code}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Day Number: {operation_day}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Download Time: {download_time}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Save Destination: {data_destination}")

        new_valid_folders = data_reader.list_valid_tracmap_folders(data_destination)
        if not new_valid_folders:
            feedback.pushWarning("{datetime.now()}: None of the copied folders have data")
            return {self.RESULS: 'No Folders with data'}
        data_sorce_type = data_reader.data_source_type(new_valid_folders[0])
        batch_id = f"{machine_code}_{operation_day}_{download_time}"

        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Data Source Type: {data_sorce_type}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Valid Folders: {new_valid_folders}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Machine Code: {machine_code}")
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Batch ID: {batch_id}")

        swath_translation = fl_project.get_machine_swath_translation(machine_code=machine_code)

        transfer_data = data_reader.TracmapDataBatch(src_paths=new_valid_folders,
                                                     src_type=data_sorce_type,
                                                     coordinate_transform=coordinate_transform,
                                                     machine_code=machine_code,
                                                     batch_id=batch_id,
                                                     swath_translation=swath_translation)

        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Data Source Read")
        transfer_data.read_datasource()

        fl_project.load_data_batch_into_heli_points(transfer_data)
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Data Source transferred into gpkg")
        load_numbers = fl_project.calculate_load_number_by_machine(machine_code)
        feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: New Load Numbers: {load_numbers}")
        # Iterate over load numbers and update the coverage rates and bait line tables
        for load in load_numbers:
            feedback.pushInfo('\n')
            result = fl_project.calculate_detailed_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_sq_buffer_bait_lines_by_machine_and_load(machine_code, load)
            fl_project.calculate_flight_path(machine_code, load)
            feedback.pushInfo('Created flight path')
            feedback.pushInfo(f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Coverage Rate Details for load {load}\n{result}")
            summary = fl_project.calculate_summary_for_load_machine(machine_code, load)
            feedback.pushInfo(
                f"{datetime.strftime(datetime.now(), '%H:%M:%S')}: Summary Details:{summary}")

        # Zoom the map canvas to the new data extent
        #extent = fl_project.zoom_to_flight_data_extent(machine_code=machine_code, load_numbers=load_numbers)
        #if extent:
            #canvas = iface.mapCanvas()
            #rectangle = QgsRectangle(extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax'])
            #canvas.setExtent(rectangle)
            #canvas.refresh()

        fl_project.write_to_config_json()
        return {self.RESULS: 'Finished'}
