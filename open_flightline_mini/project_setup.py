# Open Flightline Mini

# Author: Nicholas Braaksma
# Date: 2023-11-02

# Description:
# Manages the setup of the Flightline project geopackage

import os

from osgeo import ogr
import re
from qgis import processing
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsField,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext)


# Generate in memory Tables/Layers
def generate_table_batch_load():
    """Creates an in memory batch_load table"""

    batch_load_table = QgsVectorLayer("NoGeometry", "batch_load", "memory")
    provider = batch_load_table.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('batch_load_id', QVariant.String),
                            QgsField('source_type', QVariant.String),
                            QgsField('datetime_loaded', QVariant.Double),
                            QgsField('dir_location', QVariant.String),
                            QgsField("helicopter_registartion", QVariant.String),
                            QgsField('additional_information', QVariant.Map)
                            ])
    batch_load_table.updateFields()
    return batch_load_table


def generate_table_consent():
    """Creates an in memory consent table"""
    consent_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "consent", "memory")
    provider = consent_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('consent_name', QVariant.String),
                            QgsField('consent_active', QVariant.Int),
                            QgsField('area_ha', QVariant.Double)])
    consent_lyr.updateFields()
    return consent_lyr


def generate_table_corridor():
    """Creates an in memory corridor table"""
    corridor_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "corridor", "memory")
    provider = corridor_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('corridor_name', QVariant.String),
                            QgsField('corridor_active', QVariant.Int),
                            QgsField('corridor_type', QVariant.String),
                            QgsField('area_ha', QVariant.Double)])
    corridor_lyr.updateFields()
    return corridor_lyr


def generate_table_drone_points():
    """Creates an in_memory drone_points table"""
    drone_point_lyr = QgsVectorLayer("Point?crs=EPSG:2193", "drone_points", "memory")
    provider = drone_point_lyr.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int),
                            QgsField('src_id', QVariant.Int),
                            QgsField("date_time", QVariant.DateTime),
                            QgsField("speed", QVariant.Double),
                            QgsField("heading", QVariant.Double),
                            QgsField("altitude", QVariant.Double),
                            QgsField("width", QVariant.Int),
                            QgsField("machine", QVariant.String),
                            QgsField("batch_id", QVariant.String),
                            QgsField("bucket_state", QVariant.Int, ),
                            QgsField("bucket_shutoff", QVariant.Int),
                            QgsField("hdop", QVariant.Int),
                            QgsField("vbat", QVariant.Double)])
    drone_point_lyr.updateFields()
    return drone_point_lyr


def generate_table_exclusion():
    """Creates an in memory exclusions table"""
    exclusions_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "exclusion", "memory")
    provider = exclusions_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('exclusions_name', QVariant.String),
                            QgsField('exclusion_active', QVariant.Int),
                            QgsField('area_ha', QVariant.Double)])
    exclusions_lyr.updateFields()
    return exclusions_lyr


def generate_table_flight_path():
    """Creates an in memory flight path table"""
    flight_path_lyr = QgsVectorLayer("MultiLinestring?crs=EPSG:2193", "flight_path", "memory")
    provider = flight_path_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('load_number', QVariant.Int),
                            QgsField('start_time', QVariant.DateTime),
                            QgsField('end_time', QVariant.DateTime),
                            QgsField('line_number', QVariant.Int),
                            QgsField("batch_id", QVariant.String)]
                           )
    flight_path_lyr.updateFields()
    return flight_path_lyr


def generate_table_heli_info():
    heli_info_lyr = QgsVectorLayer("NoGeometry", "heli_info", "memory")
    provider = heli_info_lyr.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int),
                            QgsField("helicopter_company", QVariant.String),
                            QgsField("machine_code", QVariant.String),
                            QgsField("pilot_name", QVariant.String),
                            QgsField('default_bucket_size', QVariant.Int),
                            QgsField('target_sow_rate', QVariant.Double),
                            QgsField("bucket_id", QVariant.String),
                            QgsField("swath_translation", QVariant.Map),
                            QgsField("machine_active", QVariant.Int),
                            QgsField("source_type")])
    heli_info_lyr.updateFields()
    return heli_info_lyr


def generate_table_helicopter_load():
    heli_load_lyr = QgsVectorLayer("NoGeometry", "heli_load", "memory")
    provider = heli_load_lyr.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int),
                            QgsField("machine_code", QVariant.String),
                            QgsField("load", QVariant.Int),
                            QgsField("bucket_size", QVariant.Int),
                            QgsField("sow_rate", QVariant.Double)])
    heli_load_lyr.updateFields()
    return heli_load_lyr


def generate_table_heli_bait_lines_detailed():
    """
    Creates an in memory helicopter_bait_lines_table that shows
    baiting coverage by pnt pairs
    """

    heli_bait_lines_detailed_lyr = QgsVectorLayer("Linestring?crs=EPSG:2193", "heli_bait_lines_detailed", "memory")
    provider = heli_bait_lines_detailed_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('src_id', QVariant.String),
                            QgsField('date_time', QVariant.DateTime),
                            QgsField('speed', QVariant.Double),
                            QgsField('heading', QVariant.Double),
                            QgsField('altitude', QVariant.Double),
                            QgsField('width', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('bucket_size', QVariant.Int),
                            QgsField('load_number', QVariant.Int),
                            QgsField('coverage_rate', QVariant.Double),
                            QgsField('hectares', QVariant.Double),
                            QgsField('distance', QVariant.Double),
                            QgsField('seconds', QVariant.Double),
                            QgsField('line_number', QVariant.Int),
                            QgsField('batch_id', QVariant.String),
                            QgsField('bucket_state', QVariant.Int)])
    heli_bait_lines_detailed_lyr.updateFields()
    return heli_bait_lines_detailed_lyr


def generate_table_heli_bait_lines():
    """
    Creates an in memory helicopter_bait_lines_table that shows
    baiting coverage by pnt pairs
    """

    heli_bait_lines_lyr = QgsVectorLayer("Linestring?crs=EPSG:2193", "heli_bait_lines", "memory")
    provider = heli_bait_lines_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('src_id', QVariant.String),
                            QgsField('date_time', QVariant.DateTime),
                            QgsField('speed', QVariant.Double),
                            QgsField('heading', QVariant.Double),
                            QgsField('altitude', QVariant.Double),
                            QgsField('width', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('bucket_size', QVariant.Int),
                            QgsField('load_number', QVariant.Int),
                            QgsField('coverage_rate', QVariant.Double),
                            QgsField('hectares', QVariant.Double),
                            QgsField('distance', QVariant.Double),
                            QgsField('seconds', QVariant.Double),
                            QgsField('line_number', QVariant.Int),
                            QgsField('batch_id', QVariant.String),
                            QgsField('bucket_state', QVariant.Int)])
    heli_bait_lines_lyr.updateFields()
    return heli_bait_lines_lyr


def generate_table_heli_bait_lines_buffered():
    """
    Creates an in memory helicopter_bait_lines_table that shows
    baiting coverage by pnt pairs
    """

    heli_bait_lines_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "heli_bait_lines_buffered", "memory")
    provider = heli_bait_lines_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('src_id', QVariant.String),
                            QgsField('date_time', QVariant.DateTime),
                            QgsField('speed', QVariant.Double),
                            QgsField('heading', QVariant.Double),
                            QgsField('altitude', QVariant.Double),
                            QgsField('width', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('bucket_size', QVariant.Int),
                            QgsField('load_number', QVariant.Int),
                            QgsField('coverage_rate', QVariant.Double),
                            QgsField('hectares', QVariant.Double),
                            QgsField('distance', QVariant.Double),
                            QgsField('seconds', QVariant.Double),
                            QgsField('line_number', QVariant.Int),
                            QgsField('batch_id', QVariant.String),
                            QgsField('bucket_state', QVariant.Int)])
    heli_bait_lines_lyr.updateFields()
    return heli_bait_lines_lyr


def generate_table_heli_points():
    """

    Creates an in memory helicopter_point_table
    :return:
    """

    heli_point_lyr = QgsVectorLayer("Point?crs=EPSG:2193", "heli_points", "memory")
    provider = heli_point_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('src_id', QVariant.String),
                            QgsField('date_time', QVariant.DateTime),
                            QgsField('speed', QVariant.Double),
                            QgsField('heading', QVariant.Double),
                            QgsField('altitude', QVariant.Double),
                            QgsField('width', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('bucket_size', QVariant.Int),
                            QgsField('load_number', QVariant.Int),
                            QgsField('batch_id', QVariant.String),
                            QgsField('bucket_state', QVariant.Int)])
    heli_point_lyr.updateFields()
    return heli_point_lyr


def generate_table_load_site():
    """Creates an in memory load_site table"""
    load_site_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "load_site", "memory")
    provider = load_site_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('load_site_name', QVariant.String),
                            QgsField('load_site_active', QVariant.Int),
                            QgsField('elevation_trigger', QVariant.Double)])
    load_site_lyr.updateFields()
    return load_site_lyr


def generate_table_load_summary():
    """Creates an in memory load_summary table"""
    load_summary_table = QgsVectorLayer("NoGeometry", "load_summary", "memory")
    provider = load_summary_table.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField("machine_code", QVariant.String),
                            QgsField('batch_id', QVariant.String),
                            QgsField("start_time", QVariant.DateTime),
                            QgsField("end_time", QVariant.DateTime),
                            QgsField("load_number", QVariant.Int),
                            QgsField("bucket_size", QVariant.Int),
                            QgsField("sum_hectares_round", QVariant.Double),
                            QgsField("sum_hectares_square", QVariant.Double),
                            QgsField("sum_hectares_nominal", QVariant.Double),
                            QgsField("coverage_rate", QVariant.Double),
                            QgsField("average_speed", QVariant.Double),
                            QgsField("runout_time", QVariant.Double),
                            QgsField("distance_spreading", QVariant.Double),
                            QgsField("datetime_loaded", QVariant.DateTime),
                            QgsField("dir_location", QVariant.String),
                            QgsField("target_speed", QVariant.Double), ])
    load_summary_table.updateFields()
    return load_summary_table


def generate_table_operational_areas():
    """Creates an in memory operational_areas_lyr table"""

    operational_areas_lyr = QgsVectorLayer("MultiPolygon?crs=EPSG:2193", "operational_areas", "memory")
    provider = operational_areas_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('area_name', QVariant.String),
                            QgsField('area_ha', QVariant.Double),
                            QgsField('area_rules', QVariant.Map),
                            QgsField('area_type', QVariant.String)
                            ])
    operational_areas_lyr.updateFields()
    return operational_areas_lyr


def generate_table_staging_drone_points():
    """Creates an in_memory drone_points table"""
    drone_point_lyr = QgsVectorLayer("Point?crs=EPSG:2193", "staging_drone_points", "memory")
    provider = drone_point_lyr.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int),
                            QgsField('src_id', QVariant.Int),
                            QgsField("date_time", QVariant.DateTime),
                            QgsField("speed", QVariant.Double),
                            QgsField("heading", QVariant.Double),
                            QgsField("altitude", QVariant.Double),
                            QgsField("width", QVariant.Int),
                            QgsField("machine", QVariant.String),
                            QgsField("batch_id", QVariant.String),
                            QgsField("bucket_state", QVariant.Int, ),
                            QgsField("bucket_shutoff", QVariant.Int),
                            QgsField("hdop", QVariant.Int),
                            QgsField("vbat", QVariant.Double),
                            QgsField('action', QVariant.String)])
    generate_table_drone_points().updateFields()
    return drone_point_lyr


def generate_table_staging_heli_points():
    """

    Creates an in memory staging heli_point_table
    :return:
    """

    statging_heli_point_lyr = QgsVectorLayer("Point?crs=EPSG:2193", "staging_heli_points", "memory")
    provider = statging_heli_point_lyr.dataProvider()
    provider.addAttributes([QgsField('id', QVariant.Int),
                            QgsField('src_id', QVariant.Int),
                            QgsField('date_time', QVariant.DateTime),
                            QgsField('lat', QVariant.Double),
                            QgsField('lon', QVariant.Double),
                            QgsField('speed', QVariant.Double),
                            QgsField('heading', QVariant.Double),
                            QgsField('altitude', QVariant.Double),
                            QgsField('width', QVariant.Int),
                            QgsField('machine_code', QVariant.String),
                            QgsField('batch_id', QVariant.String),
                            QgsField('bucket_state', QVariant.Int),
                            QgsField('action', QVariant.String)])
    statging_heli_point_lyr.updateFields()
    return statging_heli_point_lyr


def generate_table_tracmap_summary():
    """
    Creates an in memory tracmap summary table
    :return:
    """
    tracmap_summary_lyr = QgsVectorLayer("NoGeometry", "tracmap_summary", "memory")
    provider = tracmap_summary_lyr.dataProvider()
    provider.addAttributes([QgsField("id", QVariant.Int),
                            QgsField("machine_code", QVariant.String),
                            QgsField("cumulative_tm_nominal_area", QVariant.Double),
                            QgsField("cumulative_tm_real_area", QVariant.Double),
                            QgsField("cumulative_tm_real_area", QVariant.Double),
                            QgsField("cumulative_tm_distance_travelled", QVariant.Double),
                            QgsField("cumulative_tm_distance_spreading", QVariant.Double),
                            QgsField("tm_nominal_area", QVariant.Double),
                            QgsField("tm_real_area", QVariant.Double),
                            QgsField("tm_distance_travelled", QVariant.Double),
                            QgsField("tm_distance_spreading", QVariant.Double),
                            QgsField("bacth_id", QVariant.String)])
    tracmap_summary_lyr.updateFields()
    return tracmap_summary_lyr


class GeopackageDataStore:

    def __init__(self, project_location, gpkg_path):
        self.project_location = project_location
        self.gpkg_name = os.path.basename(gpkg_path)
        self.gpkg_path = gpkg_path
        self.working_layers_list = ['batch_load', 'drone_points', 'heli_load', 'heli_points', 'load_summary',
                                    'staging_drone_points', 'staging_heli_points', 'tracmap_summary',
                                    'heli_bait_lines', 'heli_bait_lines_buffered', 'heli_bait_lines_detailed',
                                    'flight_path']
        self.static_layers_list = ['consent', 'corridor', 'exclusion', 'heli_info', 'load_site', 'operational_areas']
        self.working_layers_generation = [generate_table_batch_load(), generate_table_drone_points(),
                                          generate_table_flight_path(),
                                          generate_table_helicopter_load(), generate_table_heli_points(),
                                          generate_table_load_summary(), generate_table_staging_drone_points(),
                                          generate_table_staging_heli_points(), generate_table_tracmap_summary(),
                                          generate_table_heli_bait_lines(), generate_table_heli_bait_lines_buffered(),
                                          generate_table_heli_bait_lines_detailed()]
        self.static_layers_generation = [generate_table_consent(), generate_table_corridor(),
                                         generate_table_exclusion(),
                                         generate_table_heli_info(), generate_table_operational_areas(),
                                         generate_table_load_site()]

    @property
    def gpkg_backup_list(self):
        """
        Returns a list of gpkg layers that have a number at the end
        and are likely backups
        :return list <lyr_names>
        """
        backup_lyr_list = []
        for lyr in self.gpkg_layer_names_list_ogr:
            for base_lyr in self.working_layers_list:
                if base_lyr.lower() in lyr and re.search(r'\d{0,3}$', lyr).group():
                    backup_lyr_list.append(lyr)
        return backup_lyr_list

    @property
    def gpkg_backup_number(self):
        """
        Returns the next incremental backup number
        :return int
        """

        maximum_numbers = []
        for lyr in self.gpkg_layer_names_list_ogr:
            for base_lyr in self.working_layers_list:
                if base_lyr.lower() in lyr and re.search(r'\d{0,3}$', lyr).group():
                    maximum_numbers.append(re.search(r'\d{0,3}$', lyr).group())
        if not maximum_numbers:
            return 0
        else:
            return int(sorted(maximum_numbers, reverse=True)[0])

    @property
    def gpkg_layer_uri_list(self):
        """Checks if gpkg is populated with layers"""
        layers = []

        layer = QgsVectorLayer(self.gpkg_path, "test", "ogr")
        sub_layers = layer.dataProvider().subLayers()
        for subLayer in sub_layers:
            name = subLayer.split('!!::!!')[1]
            uri = "%s|layername=%s" % (self.gpkg_path, name,)
            layers.append(uri)
        return layers

    @property
    def gpkg_layer_names_list_ogr(self):
        """OGR version of getting gpkg layers"""
        gpkg_conn = ogr.Open(self.gpkg_path)
        layer_names = [i.GetName() for i in gpkg_conn]
        return layer_names

    @property
    def gpkg_layer_names_list(self):
        """
        QgsVectorLayer version of getting gpkg layers
        Not currently used, but leaving in as it is useful to have.
        """
        layer_names = []

        layer = QgsVectorLayer(self.gpkg_path, "test", "ogr")
        sub_layers = layer.dataProvider().subLayers()
        for subLayer in sub_layers:
            name = subLayer.split('!!::!!')[1]
            layer_names.append(name)
        return layer_names

    def gpkg_backup_layers(self):
        # Get list of layers,
        layer_list = self.gpkg_layer_names_list_ogr
        backup_number = self.gpkg_backup_number

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        transform_context = QgsProject.instance().transformContext()
        for lyr in [i for i in layer_list if i.lower() in self.working_layers_list]:
            orig_datasource = f"{self.gpkg_path}|layername={lyr}"
            dest_datasource = f"{self.gpkg_path}|layername={lyr}_{backup_number + 1}"
            original_layer = QgsVectorLayer(orig_datasource, lyr, 'ogr')

            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.layerName = f'{lyr}_{backup_number + 1}'
            save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

            transform_context = QgsProject.instance().transformContext()
            # Write to a GeoPackage (default)
            result = QgsVectorFileWriter.writeAsVectorFormatV3(original_layer,
                                                               self.gpkg_path,
                                                               transform_context,
                                                               save_options)
            print(f'Created Backup: {dest_datasource}')
        return

    def create_empty_gpkg(self):
        """
        Creates an empty gpkg with a tmp_layer
        :return: str gpkg location
        """

        # Create gpkg with a tmp layer
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        tmp_lyr = QgsVectorLayer("Point?crs=EPSG:2193", "tmp_pnt_lyr", "memory")
        provider = tmp_lyr.dataProvider()
        provider.addAttributes([QgsField('id', QVariant.Int), QgsField('name', QVariant.String)])
        tmp_lyr.updateFields()
        options.layerName = tmp_lyr.name()

        QgsVectorFileWriter.writeAsVectorFormatV3(layer=tmp_lyr, fileName=self.gpkg_path,
                                                  transformContext=QgsProject.instance().transformContext(),
                                                  options=options)
        print(f'Created GPKG: {self.gpkg_path}')
        return self.gpkg_path

    def create_gpkg_layers(self, layer_list):
        """
        Creates an in memory layers that can be exported
        to the project gpkg
        :param layer_list: list<functions>
        :return:
        """

        for lyr in layer_list:
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
            options.layerName = lyr.name()
            writer = QgsVectorFileWriter.create(self.gpkg_path,
                                                lyr.dataProvider().fields(),
                                                lyr.wkbType(),
                                                QgsCoordinateReferenceSystem("EPSG:2193"),
                                                QgsCoordinateTransformContext(),
                                                options)
            print(f'Created Layer: {lyr.name()}')
        del writer
        return True

    def cleanup_gpkg_copies(self):
        """
        Removes any of the working layers that have a number at the end.
        :return:
        """
        # The processing module runs within QGIS but not outside
        # Exclude from any out of QGIS testing
        layers_removed = []
        errors = []

        for gpkg_lyr_name in self.gpkg_backup_list:
            inputs = {"DATABASE": self.gpkg_path,
                      "SQL": f"DROP TABLE {gpkg_lyr_name}"}
            try:
                processing.run("native:spatialiteexecutesql", inputs)
                layers_removed.append(gpkg_lyr_name)
            except Exception as e:
                errors.append(e)
        return layers_removed, errors
