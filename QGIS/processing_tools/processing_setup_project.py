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
from qgis.core import (QgsProcessingParameterFile,
                       QgsProcessingParameterCrs,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFileDestination,
                       QgsCoordinateReferenceSystem,
                       QgsProcessingParameterBoolean)
from open_flightline_mini import flightline_project
from open_flightline_mini import project_setup


class SetupAerialProject(QgsProcessingAlgorithm):
    """
    This sets up an empty geopackage and configuration for
    an aerial operation.

    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECT_FOLDER = 'PROJECT_FOLDER'
    GPKG_LOCATION = 'GPKG_LOCATION'
    EXISTING_GPKG = 'EXISTING_GPKG'
    RAW_DATA_FOLDER = 'RAW_DATA_FOLDER'
    DATA_SOURCE_SRID = "DATA_SOURCE_SRID"
    DATA_STORE_SRID = "DATA_STORE_SRID"
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Project Management', string)

    def createInstance(self):
        return SetupAerialProject()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'setup_aerial_project'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('1. Setup Aerial Project')

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
        return self.tr("Creates a templated Geopackage and sets the project json")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT_FOLDER,
                "Project Folder",
                QgsProcessingParameterFile.Behavior(1)
            ))

        self.addParameter(
            QgsProcessingParameterFileDestination(self.GPKG_LOCATION,
                                                  "GPKG Location",
                                                  '.gpkg'
                                                  ))
        self.addParameter(
            QgsProcessingParameterBoolean(self.EXISTING_GPKG,
                                          "Refresh Existing GPKG"
                                          ))

        self.addParameter(
            QgsProcessingParameterFile(
                self.RAW_DATA_FOLDER,
                "Raw Data Folder",
                QgsProcessingParameterFile.Behavior(1)
            ))

        self.addParameter(
            QgsProcessingParameterCrs(self.DATA_SOURCE_SRID,
                                      "Data Source Coordinate System",
                                      defaultValue=QgsCoordinateReferenceSystem("EPSG:4326")
                                      ))

        self.addParameter(
            QgsProcessingParameterCrs(self.DATA_STORE_SRID,
                                      "Data Store Coordinate System",
                                      defaultValue=QgsCoordinateReferenceSystem("EPSG:2193")
                                      ))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        project_folder = self.parameterAsString(parameters, self.PROJECT_FOLDER, context)
        gpkg_location = self.parameterAsString(parameters, self.GPKG_LOCATION, context)
        existing_gpkg = self.parameterAsBoolean(parameters, self.EXISTING_GPKG, context)
        raw_data_folder = self.parameterAsString(parameters, self.RAW_DATA_FOLDER, context)
        data_source_srid = self.parameterAsCrs(parameters, self.DATA_SOURCE_SRID, context)
        data_store_srid = self.parameterAsCrs(parameters, self.DATA_STORE_SRID, context)

        project = flightline_project.FlightlineProject()
        project.__set_project_folder__(project_folder)
        project.__set_raw_data_folder__(raw_data_folder)
        project.__set_gpkg_path__(gpkg_location)

        project.data_source_srid = data_source_srid.authid()
        project.data_store_srid = data_store_srid.authid()
        setup = project_setup.GeopackageDataStore(project_folder, gpkg_location)

        # If GPKG is existing, then just refresh the working layers, otherwise
        # create a completely new or overwrite an existing gpkg
        if existing_gpkg:
            setup.create_gpkg_layers(setup.working_layers_generation)
        else:
            setup.create_empty_gpkg()
            setup.create_gpkg_layers(setup.static_layers_generation)
            setup.create_gpkg_layers(setup.working_layers_generation)

        feedback.pushInfo(f"Data Source SRID: {data_source_srid.authid()}")
        feedback.pushInfo(f"Data Store SRID: {data_store_srid.authid()}")

        project.write_to_config_json()
        return {self.OUTPUT: gpkg_location}
