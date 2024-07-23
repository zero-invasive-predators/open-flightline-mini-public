# Module to handle loading of data from the onboard flight recorder
# Intially  to load data from a Tracmap USB export
# Then to load data from Tracmap Online (Tabula) and Drone.

import os
import shutil
from datetime import datetime, timedelta

from qgis.core import (QgsVectorLayer,
                       QgsFeature,
                       QgsGeometry,
                       QgsPoint)

from open_flightline_mini import project_setup


def log_file_count(data_source):
    """
    returns the count of log files found
    :param data_source:
    :return: int
    """
    log_count = 0
    for dirpath, dirnames, filenames in os.walk(data_source):
        if 'log.shp' in filenames:
            log_count += 1
    return log_count


def get_shapefile_feature_count(full_path):
    shp_lyr = QgsVectorLayer(full_path, "shp_lyr", "ogr")
    if not shp_lyr.isValid():
        return 0
    return shp_lyr.featureCount()


def list_valid_tracmap_folders(src_folder):
    """
    Searches the src_folder for shapefiles that have data
    :return:
    """
    valid_folders = []
    for dirpath, dirnames, filenames in os.walk(src_folder):
        # Assume if log.shp in the folder then it is a tracmap job export
        if all(['log.shp' not in [i.lower() for i in filenames],
                'secondary.shp' not in [i.lower() for i in filenames]]):
            continue
        log_lyr_path = os.path.join(dirpath, 'log.shp')
        secondary_lyr_path = os.path.join(dirpath, 'secondary.shp')
        log_lyr_cnt = get_shapefile_feature_count(log_lyr_path)
        secondary_lyr_cnt = get_shapefile_feature_count(secondary_lyr_path)
        if all([log_lyr_cnt > 0, secondary_lyr_cnt > 0]):
            valid_folders.append(dirpath)
    return valid_folders


def match_heli_rego_from_folder_names(heli_list, data_source):
    """
    Searches the data_source tree to see if any of the machine codes are
    within the folder names. If no matches then returns 'UNK'
    :param heli_list: list<str>: ['PBX', 'PBY'...]
    :param data_source: str: 'E:/Tracmap'
    :return: str<heli_rego>
    """

    for dirpath, dirnames, filenames in os.walk(data_source):
        for machine_code in heli_list:
            if machine_code.upper() in dirpath:
                return machine_code.upper()
    return 'UNK'


def current_download_time():
    return datetime.strftime(datetime.now(), '%H%M')


def copy_usb_data(data_source, data_destination):
    """

    :param data_source:
    :param data_destination:
    :return:
    """
    # Check if folders exist
    if not os.path.exists(data_source):
        raise FileNotFoundError(f"Data Source: {data_source} does not exist")
    if os.path.exists(data_destination):
        raise FileExistsError(f"Data Destination: {data_destination} already exists, change download time")

    shutil.copytree(data_source, data_destination)

def archive_data_batch(raw_data_folder, batch_id):
    """
    :param raw_data_folder: <str>
    :param batch_id: <str>
    :return:
    """

    batch_parts = batch_id.split('_')
    machine_code = batch_parts[0]
    op_day = batch_parts[1]
    op_time = batch_parts[2]
    folder_name = f"{op_day}_{op_time}"
    source = os.path.join(raw_data_folder, machine_code, folder_name)
    dest = os.path.join(raw_data_folder, machine_code, f"deleted_{folder_name}")

    if os.path.exists(source):
        shutil.move(source, dest)
        return f"Folder: {source} renamed to {dest}"
    else:
        return f'Unable to find folder: {source}.\n Folder not deleted'



def data_destination_checks(raw_data, machine_code, operation_day, download_time):
    """
    Checks if the data can be copied and sets up the destination
    :param operation_day: int
    :param machine_code: str
    :param download_time: str with leading 0
    :param raw_data:
    :return: str: download_time
    """
    # If heli rego folder does not exist then create it
    if not os.path.exists(os.path.join(raw_data, machine_code.upper())):
        os.mkdir(os.path.join(raw_data, machine_code.upper()))

    for i in range(0, 60):
        check_folder = f"{operation_day}_{download_time}"
        if os.path.exists(os.path.join(raw_data, machine_code.upper(), check_folder)):
            download_time = str(int(download_time) + 1).zfill(4)
        else:
            break
    return download_time


def data_source_type(src_folder):
    """
    Checks what type of data source type the data is
    :param src_folder: str
    :return:
    """
    # Checking the secondary.shp for Tracmap Versions/1 Second Recording
    secondary_shp_path = os.path.join(src_folder, 'secondary.shp')
    if os.path.exists(secondary_shp_path):
        check_lyr = QgsVectorLayer(os.path.join(src_folder, 'secondary.shp'))
        check_lyr_fields = [i.name().lower() for i in check_lyr.fields()]
        if all([i in check_lyr_fields for i in ['date', 'time', 'lat', 'lon', 'speed', 'heading', 'gps alt',
                                                  'boomstate', 'targetrate', 'actualrate', 'width']]):
            return 'tabula_shapefile_baiting_points'
        elif all([i in check_lyr_fields for i in ['time', 'speed', 'heading', 'gps alt']]):
            return 'tracmap_shapefile_baiting_lines'
        elif all([i in check_lyr_fields for i in ['date', 'time', 'speed', 'heading', 'gps alt', 'boom state']]):
            return 'tracmap_shapefile_baiting_points'


    return 'Unrecognised Data Source'


class TracmapDataBatch:

    def __init__(self, src_paths, src_type, coordinate_transform, machine_code, batch_id,
                 swath_translation=None):
        self.src_paths = src_paths
        self.src_type = src_type
        self.coordinate_transform = coordinate_transform
        self.machine_code = machine_code
        self.batch_id = batch_id
        self.layers = {}
        self.swath_translation = swath_translation

    def translate_swath(self, swath_width):
        """
        The map/dictionary stored in the heli_info table is a dict of strings.
        Need to convert incoming values from tracmap data (usually floats) into
        strings so that they match.
        :param swath_width:
        :return:
        """
        if not self.swath_translation:
            return swath_width
        elif self.swath_translation.get(str(swath_width)):
            return float(self.swath_translation.get(str(swath_width)))
        else:
            return swath_width

    def read_datasource(self):
        self.__read_features__()

    def __read_features__(self):
        if self.src_type == 'tracmap_shapefile_baiting_lines':
            for dir_path in self.src_paths:
                self.__read_tracmap_shapefile_set_lines__(dir_path)
                self.__read_tracmap_summary_file__(dir_path)
        elif self.src_type == 'tracmap_shapefile_baiting_points':
            for dir_path in self.src_paths:
                self.__read_tracmap_shapefile_set_points__(dir_path)
                self.__read_tracmap_summary_file__(dir_path)
        elif self.src_type == 'tabula_shapefile_baiting_points':
            for dir_path in self.src_paths:
                self.__read_tabula_shapefile_set_points__(dir_path)
                self.__read_tracmap_summary_file__(dir_path)
        elif self.src_type == 'tracmap_cloud':
            self.__read_from_tracmap_cloud__()

    def __read_from_tracmap_cloud__(self):
        raise NotImplementedError("Not yet built")

    def __read_tracmap_shapefile_set_points__(self, dir_path):
        raise NotImplementedError("Not yet built")

    def __read_tracmap_shapefile_set_lines__(self, dir_path):
        print(dir_path)
        parent_folder = os.path.split(dir_path)[1]
        log_lyr_path = os.path.join(dir_path, "log.shp")
        secondary_lyr_path = os.path.join(dir_path, "secondary.shp")

        # log_lyr
        log_lyr = QgsVectorLayer(log_lyr_path, f"{parent_folder}_log", "ogr")
        secondary_lyr = QgsVectorLayer(secondary_lyr_path, f"{parent_folder}_secondary", "ogr")
        self.layers[secondary_lyr.name()] = {}
        template_layer = project_setup.generate_table_staging_heli_points()
        coordinate_transform = self.coordinate_transform
        for feat in log_lyr.getFeatures():
            swath_width = self.translate_swath(feat['width'])
            if feat['speed'] < 0 or feat['speed'] is None:
                continue

            point_time_tracker = datetime.strptime(feat['time'], '%Y-%m-%dT%H:%M:%S%z')
            # Turn line features to points
            feat_geom = feat.geometry()
            feat_geom.transform(coordinate_transform)

            # Turn baiting line feature into points and interpolate the time for each vertex
            for vert_set in feat_geom.asMultiPolyline():
                vertex_a = vert_set[0]
                for i in range(len(vert_set)):
                    new_feat = QgsFeature(template_layer.fields())
                    new_feat['speed'] = feat['Speed']
                    new_feat['width'] = swath_width
                    new_feat['altitude'] = feat['GPS Alt']
                    new_feat['machine_code'] = self.machine_code
                    new_feat['batch_id'] = self.batch_id
                    new_feat['bucket_state'] = 1
                    new_feat.setGeometry(QgsGeometry(QgsPoint(vertex_a)))
                    if i == 0:
                        new_feat['date_time'] = point_time_tracker
                    else:
                        distance = vertex_a.distance(vert_set[i])
                        seconds = distance / (feat['speed'] / 1.94384)
                        # The time resolution is seconds, so if the time between vertices is less than one second, then skip it
                        if not round(seconds, 0):
                            continue
                        time_delta = timedelta(seconds=seconds)
                        point_time_tracker += time_delta
                        new_feat['date_time'] = point_time_tracker
                        new_feat['src_id'] = f"{new_feat['date_time']}|{new_feat['speed']}"
                        vertex_a = vert_set[i]
                    self.layers[secondary_lyr.name()][new_feat['src_id']] = new_feat
                    # Last record to add in
                    if i + 1 == len(vert_set):
                        distance = vertex_a.distance(vert_set[i])
                        seconds = distance / (feat['speed'] / 1.94384)
                        time_delta = timedelta(seconds=seconds)
                        point_time_tracker += time_delta
                        new_feat['date_time'] = point_time_tracker
                        new_feat['src_id'] = f"{new_feat['date_time']}|{new_feat['speed']}"
                        new_feat.setGeometry(QgsGeometry(QgsPoint(vertex_a)))
                        self.layers[secondary_lyr.name()][new_feat['src_id']] = new_feat

        #TODO: Combine the log points and secondary points into the same set ordered by datetime.
        # secondary_lyr
        #self.layers[secondary_lyr.name()] = {}
        for feat in secondary_lyr.getFeatures():
            swath_width = self.translate_swath(feat['width'])
            new_geometry = feat.geometry()
            new_geometry.transform(coordinate_transform)
            new_feat = QgsFeature(template_layer.fields())
            new_feat['speed'] = feat['speed']
            new_feat['width'] = swath_width
            new_feat['heading'] = feat['heading']
            new_feat['altitude'] = feat['GPS Alt']
            new_feat['machine_code'] = self.machine_code
            new_feat['batch_id'] = self.batch_id
            new_feat['bucket_state'] = 0
            new_feat['date_time'] = datetime.strptime(feat['time'], '%Y-%m-%dT%H:%M:%S%z')
            new_feat['src_id'] = f"{new_feat['date_time']}_{new_feat['speed']}"
            new_feat.setGeometry(new_geometry)
            self.layers[secondary_lyr.name()][new_feat['src_id']] = new_feat

        return

    def __read_tracmap_summary_file__(self, dir_path):
        """
        Reads the tracmap summary txt file
        :param dir_path:
        :return:
        """
        summary_txt = os.path.join(dir_path, "summary.txt")
        parent_folder = os.path.split(dir_path)[1]
        self.layers[f"{parent_folder}_summary"] = {}
        with open(summary_txt, 'r') as txt_file:
            results = {}
            for line in txt_file.readlines():
                key, spacer, value = line.partition(':')
                if key:
                    self.layers[f"{parent_folder}_summary"][key] = value.strip()
        return

    def __read_tabula_shapefile_set_points__(self, dir_path):
        """
        Reads data that is exported by the tabula onboard tablet to a USB stick.
        The shape set should have a secondary shapefile of all flight points (baiting/non baiting)
        :param dir_path: str<path to the directory>
        :return: result
        """

        print(dir_path)
        parent_folder = os.path.split(dir_path)[1]
        secondary_lyr_path = os.path.join(dir_path, "secondary.shp")
        summary_txt = os.path.join(dir_path, "summary.txt")

        # Read Secondary layer features
        secondary_lyr = QgsVectorLayer(secondary_lyr_path, f"{parent_folder}_secondary", "ogr")
        self.layers[secondary_lyr.name()] = {}
        template_layer = project_setup.generate_table_heli_points()
        coordinate_transform = self.coordinate_transform
        for feat in secondary_lyr.getFeatures():
            swath_width = self.translate_swath(feat['width'])
            new_feat = QgsFeature(template_layer.fields())
            new_feat['date_time'] = datetime.strptime(f"{feat['Date']}T{feat['Time']}", '%Y-%m-%dT%H:%M:%S')
            new_feat['speed'] = feat['Speed']
            new_feat['heading'] = feat['Heading']
            new_feat['altitude'] = feat['GPS Alt']
            new_feat['width'] = swath_width
            new_feat['bucket_state'] = feat['BoomState']
            new_feat['machine_code'] = self.machine_code
            new_feat['batch_id'] = self.batch_id
            new_feat['src_id'] = f"{new_feat['date_time']}|{new_feat['speed']}"
            trans_geom = feat.geometry()
            trans_geom.transform(coordinate_transform)
            new_feat.setGeometry(trans_geom)

            self.layers[secondary_lyr.name()][new_feat['src_id']] = new_feat

        return






