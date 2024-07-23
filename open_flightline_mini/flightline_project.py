# Open Flightline Mini

# Author: Nicholas Braaksma
# Date: 2023-11-02

# Description:
# Manages the Flightline Project

import os.path
import json
from statistics import mean

from qgis import processing

from qgis.core import (QgsVectorLayer,
                       QgsFeature,
                       QgsProject,
                       QgsFeatureRequest,
                       QgsExpression,
                       QgsGeometry)

from datetime import datetime
from pathlib import Path


def get_project_config_json(project_path=None):
    if not project_path:
        project_path = QgsProject.instance().absolutePath()
    config_json = os.path.join(project_path, 'project_config.json')
    return Path(config_json).as_posix()


#
def get_helicopter_list_from_project_folder(project_path):
    fp = FlightlineProject()
    fp.__set_project_folder__(project_path)
    fp.read_from_json_config()
    return fp.machine_code_list


def get_last_tracmap_data_source(project_path):
    fp = FlightlineProject()
    fp.__set_project_folder__(project_path)
    fp.read_from_json_config()
    return fp.last_tracmap_data_source_location


def get_op_day(project_path):
    fp = FlightlineProject()
    fp.__set_project_folder__(project_path)
    fp.read_from_json_config()
    return fp.operation_day


class FlightlineProject:

    def __init__(self):
        self.project_folder = None
        self.raw_data_folder = None
        self.project_gpkg = None
        self.op_day = None
        self.last_data_source_location = None
        self.data_source_srid = None
        self.data_store_srid = None
        self.load_site_ceiling = 50

    @property
    def operation_day(self):
        if not self.op_day:
            return 1
        return self.op_day

    @property
    def maximum_load_number(self):
        load_numbers = ([i['load_number'] for i in self.gpkg_layer('load_summary').getFeatures()])
        if not load_numbers:
            return 0
        else:
            return max(load_numbers)

    @property
    def last_tracmap_data_source_location(self):
        if not self.last_data_source_location:
            return r'E:\Tracmap'
        return self.last_data_source_location

    @property
    def project_config_json(self):
        return get_project_config_json(self.project_folder)

    @property
    def gpkg_name(self):
        return os.path.basename(self.project_gpkg)

    @property
    def project_config_json_exists(self):
        return os.path.exists(self.project_config_json)

    @property
    def machine_code_list(self):
        """Returns the machine code list from the heli_info table"""
        gpkg_layer = QgsVectorLayer(self.gpkg_layer_path('heli_info'))
        return sorted([i['machine_code'] for i in gpkg_layer.getFeatures()])

    @property
    def all_load_numbers_list(self):
        """Returns a list of available load numbers from the load summary table"""
        load_summary_lyr = self.gpkg_layer('load_summary')
        load_numbers = [i['load_number'] for i in load_summary_lyr.getFeatures()]

        return sorted(set(load_numbers))

    def get_machine_swath_translation(self, machine_code):
        """Uses the heli_info table to translate the tracmap width into the
        buckets effective swath. ZIP uses a combination of point sowing,  trickle, 10% overlap,
        50% overlap, full sow, 6gram and 12gram bait sizes."""

        heli_info_lyr = self.gpkg_layer('heli_info')
        features = [i['swath_translation'] for i in heli_info_lyr.getFeatures()
                    if all([i['machine_code'] == machine_code, i['machine_active'] == 1])]
        if len(features) == 0:
            return {}
        return features[0]

    def gpkg_layer(self, layer_name):
        return QgsVectorLayer(self.gpkg_layer_path(layer_name), layer_name, 'ogr')

    def gpkg_layer_path(self, layer_name):
        return f"{self.project_gpkg}|layername={layer_name}"

    def __set_gpkg_path__(self, gpkg_location):
        self.project_gpkg = gpkg_location

    def __set_project_folder__(self, project_folder):
        self.project_folder = Path(project_folder).as_posix()

    def __set_raw_data_folder__(self, raw_data_folder):
        self.raw_data_folder = Path(raw_data_folder).as_posix()
        # else:
        #     raise NotADirectoryError(f"{raw_data_folder} does not exist")

    def set_op_day(self, op_day):
        self.op_day = op_day

    def write_to_config_json(self):
        """
        Writes the project settings to the project_config.json file
        which should exist in the project folder
        :return:
        """
        json_string = json.dumps(self.__dict__, indent=4)
        with open(self.project_config_json, "w") as openfile:
            openfile.write(json_string)
        print('Successfully wrote json config')
        return True

    def read_from_json_config(self):
        # Only reads if there is a valid project_config
        if not self.project_config_json_exists:
            return
        with open(self.project_config_json, "r") as openfile:
            json_object = json.load(openfile)

        for k, v in json_object.items():
            self.__setattr__(k, v)
        print('Successfully read json config')
        return True

    def get_data_batches(self):
        """
        Looks at the load summary table and provides list of the batch ids
        :return:
        """
        batch_ids = []
        load_summary_lyr = self.gpkg_layer('load_summary')
        for batch in load_summary_lyr.getFeatures():
            batch_ids.append(batch['batch_id'])
        return sorted(list(set(batch_ids)))

    def get_current_machine_load_number(self, machine_code):
        """
        Looks at the heli points table and gets the machine load number
        :param machine_code:
        :return:
        """

        heli_pnts_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"machine_code ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        load_numbers = [i['load_number'] for i in heli_pnts_lyr.getFeatures(request)]
        if len(load_numbers) == 0:
            return 0
        return max(load_numbers)

    def heli_load_list(self, machine_code):
        """Returns the machine code list from the heli_info table"""
        heli_pnts_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"machine_code ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        load_numbers = [i['load_number'] for i in heli_pnts_lyr.getFeatures(request)]
        return list(set(load_numbers))

    def get_default_machine_bucket_size(self, machine_code):
        """
        Looks in the heli_info table to get a machines default bucket size.
        :param machine_code:
        :return: int<default_bucket_size>
        """

        heli_info_lyr = self.gpkg_layer('heli_info')
        expression = QgsExpression(f"machine_code ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        for feat in heli_info_lyr.getFeatures(request=request):
            return feat['default_bucket_size']

    def get_default_machine_sow_rate(self, machine_code):
        """
        Looks in the heli_info table to get a machines default bucket size.
        :param machine_code:
        :return: int<default_bucket_size>
        """

        heli_info_lyr = self.gpkg_layer('heli_info')
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        for feat in heli_info_lyr.getFeatures(request=request):
            return feat['target_sow_rate']

    def get_heli_points_ids(self, machine_code):
        """
        Gets a list of src_ids for a helicopter
        :param machine_code:
        :return: list<src_ids>
        """

        heli_points_src_ids = []
        heli_points_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        request.setFlags(QgsFeatureRequest.NoGeometry)
        request.setSubsetOfAttributes(['src_id'], heli_points_lyr.fields())

        for feat in heli_points_lyr.getFeatures(request):
            heli_points_src_ids.append(feat['src_id'])
        return heli_points_src_ids

    def combine_loads_for_heli_points(self, machine_code, load_numbers, bucket_size):
        """
        Updates the load numbers in the heli_points table using the first load
        number from the provided list
        :param machine_code: str
        :param load_numbers: list<int>
        :return:
        """

        new_load_number = min(load_numbers)
        heli_points_lyr = self.gpkg_layer('heli_points')
        if len(load_numbers) > 1:
            expression = QgsExpression(
                f"\"machine_code\" ILIKE '{machine_code}' and \"load_number\" in {tuple(load_numbers)}")
        else:
            expression = QgsExpression(
                f"\"machine_code\" ILIKE '{machine_code}' and \"load_number\" like {load_numbers[0]}")
        request = QgsFeatureRequest(expression)
        clause = QgsFeatureRequest.OrderByClause('load_number', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        request.setOrderBy(orderby)

        heli_points_lyr.startEditing()
        batch_id = None
        for feat in heli_points_lyr.getFeatures(request):
            # Set the batch id to the first record
            if not batch_id: batch_id = feat['batch_id']
            feat.setAttribute('load_number', new_load_number)
            feat.setAttribute('batch_id', batch_id)
            if bucket_size > 0:
                feat.setAttribute('bucket_size', bucket_size)
            heli_points_lyr.updateFeature(feat)

        heli_points_lyr.commitChanges()
        return

    def combine_loads_for_flight_path(self, machine_code, load_numbers):
        """
        Updates the load numbers in the flight_path table using the first load
        number from the provided list
        :param machine_code: str
        :param load_numbers: list<int>
        :return:
        """

        new_load_number = min(load_numbers)
        flight_path_lyr = self.gpkg_layer('flight_path')
        expression = QgsExpression(
            f"\"machine_code\" ILIKE '{machine_code}' and \"load_number\" in {tuple(load_numbers)}")
        request = QgsFeatureRequest(expression)
        clause = QgsFeatureRequest.OrderByClause('load_number', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        request.setOrderBy(orderby)

        flight_path_lyr.startEditing()
        batch_id = None
        for feat in flight_path_lyr.getFeatures(request):
            # Set the batch id to the first record
            if not batch_id: batch_id = feat['batch_id']
            feat.setAttribute('load_number', new_load_number)
            feat.setAttribute('batch_id', batch_id)
            flight_path_lyr.updateFeature(feat)

        flight_path_lyr.commitChanges()
        return

    def load_data_batch_into_heli_points(self, data_batch):
        """
        Loads the secondary points from the data batch into the heli_points table
        :param data_batch: data_reader.TracmapDataBatch()
        :return:
        """

        default_bucket_size = self.get_default_machine_bucket_size(data_batch.machine_code)

        counter = 0
        for batch_lyr in data_batch.layers.keys():
            if batch_lyr.endswith('secondary'):
                heli_points_lyr = self.gpkg_layer('heli_points')
                heli_points_lyr.startEditing()
                heli_points_field_names = [i.name() for i in heli_points_lyr.fields()]
                heli_points_src_ids = self.get_heli_points_ids(data_batch.machine_code)
                for id, feat in data_batch.layers[batch_lyr].items():
                    if id in heli_points_src_ids:
                        continue  # Already have the data, do not need to reload.
                    batch_field_names = [i.name() for i in feat.fields()]
                    new_feat = QgsFeature(heli_points_lyr.fields())
                    [new_feat.setAttribute(i, feat[i]) for i in heli_points_field_names if i in batch_field_names]
                    new_feat.setAttribute('date_time', datetime.strftime(new_feat['date_time'], '%Y-%m-%dT%H:%M:%S'))
                    new_feat.setAttribute('bucket_size', default_bucket_size)
                    new_feat.setGeometry(feat.geometry())
                    heli_points_lyr.dataProvider().addFeature(new_feat)
                    counter += 1
                heli_points_lyr.commitChanges()
        return counter

    def join_heli_points_to_load_site_by_machine(self, machine_code):
        """
        Spatial Joins load site features to heli points for a given machine
        :param machine_code:
        :return:
        """
        # Spatially join heli points to load site polygons
        # First, filter active load sites and machine data
        load_site_lyr_path = self.gpkg_layer_path('load_site')
        heli_points_lyr_path = self.gpkg_layer_path('heli_points')

        heli_points_output = processing.run("native:extractbyexpression", {
            'INPUT': heli_points_lyr_path,
            'EXPRESSION': f'"machine_code" ILIKE \'{machine_code}\'',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        load_site_output = processing.run("native:extractbyexpression", {
            'INPUT': load_site_lyr_path,
            'EXPRESSION': f'"load_site_active" = 1',
            'OUTPUT': 'TEMPORARY_OUTPUT'})
        s_heli_points_lyr = heli_points_output['OUTPUT']
        s_load_sites_lyr = load_site_output['OUTPUT']

        heli_load_site_sj_output = processing.run("native:joinattributesbylocation", {
            'INPUT': s_heli_points_lyr,
            'PREDICATE': [0],
            'JOIN': s_load_sites_lyr,
            'JOIN_FIELDS': [],
            'METHOD': 0,
            'DISCARD NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })

        return heli_load_site_sj_output['OUTPUT']

    def delete_batch_id_data(self, batch_id, table_name):
        """ Deletes data batches from the gpkg
        :param batch_id: <str>
        :param table_name: <str>
        """

        gpkg_lyr = self.gpkg_layer(table_name)
        expression = QgsExpression(f"\"batch_id\" ILIKE '{batch_id}'")
        request = QgsFeatureRequest(expression)

        counter = 0
        gpkg_lyr.startEditing()
        for f in gpkg_lyr.getFeatures(request=request):
            gpkg_lyr.deleteFeature(f.id())
            counter += 1

        gpkg_lyr.commitChanges()
        return counter

    def delete_machine_load_data(self, machine_code, load_number, table_name):
        """
        Sets an expression on the provided table and deletes the records
        :param machine_code:
        :param load_number:
        :param table_name:
        :return:
        """

        gpkg_lyr = self.gpkg_layer(table_name)
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' and \"load_number\" = '{load_number}' ")
        request = QgsFeatureRequest(expression)

        counter = 0
        gpkg_lyr.startEditing()
        for f in gpkg_lyr.getFeatures(request=request):
            gpkg_lyr.deleteFeature(f.id())
            counter += 1

        gpkg_lyr.commitChanges()
        return counter

    def delete_machine_data(self, machine_code, table_name):
        """
        Deletes data for the given machine out of a table
        :param machine_code:
        :param table_name:
        :return:
        """
        gpkg_lyr = self.gpkg_layer(table_name)
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)

        counter = 0
        gpkg_lyr.startEditing()
        for f in gpkg_lyr.getFeatures(request=request):
            gpkg_lyr.deleteFeature(f.id())
            counter += 1
        gpkg_lyr.commitChanges()
        return counter

    def clear_machine_load_numbers(self, machine_code):
        """
        For a given machine, resets the load number to Null
        :param machine_code:
        :return:
        """

        heli_points_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        request.setFlags(QgsFeatureRequest.NoGeometry)

        counter = 0
        heli_points_lyr.startEditing()
        load_number_i = heli_points_lyr.fields().names().index('load_number')
        for feat in heli_points_lyr.getFeatures(request=request):
            heli_points_lyr.changeAttributeValue(feat.id(), load_number_i, None)
            counter += 1
        heli_points_lyr.commitChanges()

        return counter

    def calculate_load_number_by_machine(self, machine_code):
        """
        Orders the point data by date and time and increments the load number
        when the machine flies into the load at less than 50m from the load
        site elevation.
        :param machine_code:
        :return: list of load numbers that were updated

        """

        heli_load_site_sj_lyr = self.join_heli_points_to_load_site_by_machine(machine_code)

        request = QgsFeatureRequest()
        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        request.setOrderBy(orderby)

        load_counter = 0
        feature_store = {}
        sown_out_of_load_site = False
        in_load_site = False
        features = [i for i in heli_load_site_sj_lyr.getFeatures(request)]
        checked_current_load = False

        for f in range(len(features)):
            current_feat = features[f]
            if current_feat['load_site_active']:
                in_load_site = current_feat['altitude'] <= current_feat['elevation_trigger']
            else:
                in_load_site = False
            if f == 0:
                lag_in_load_site = in_load_site
                if not isinstance(current_feat['load_number'], int):
                    feature_store[current_feat['src_id']] = load_counter
                continue
            # If a load number has already been calculated then do not recalculate
            if isinstance(current_feat['load_number'], int):
                load_counter = current_feat['load_number']
                lag_in_load_site = in_load_site
                continue

            # Was in Load site and has now left load site
            if lag_in_load_site is True and in_load_site is False:
                # Check if any sowing occurs in current load
                if checked_current_load is False:
                    for lead_f in range(f, len(features) - 1):
                        lead_feat = features[lead_f]
                        checked_current_load = True
                        if lead_feat['bucket_state'] == 1:
                            sown_out_of_load_site = True
                            break
                        if lead_feat['load_site_active']:
                            if lead_feat['altitude'] <= lead_feat['elevation_trigger']:
                                sown_out_of_load_site = False
                                break
                if sown_out_of_load_site is True:
                    load_counter += 1

            # Returned from load to load site
            if lag_in_load_site is False and in_load_site is True:
                sown_out_of_load_site = False
                checked_current_load = False

            feature_store[current_feat['src_id']] = load_counter
            lag_in_load_site = in_load_site

        # Update the load number
        heli_points_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"machine_code ILIKE '{machine_code}'")
        request = QgsFeatureRequest(expression)
        request.setFlags(QgsFeatureRequest.NoGeometry)
        request.setSubsetOfAttributes(['src_id', 'load_number'], heli_points_lyr.fields())

        load_number_i = heli_points_lyr.fields().names().index('load_number')
        heli_points_lyr.startEditing()
        for feat in heli_points_lyr.getFeatures():
            if feature_store.get(feat['src_id']) is not None:
                heli_points_lyr.changeAttributeValue(feat.id(), load_number_i, feature_store.get(feat['src_id']))
        heli_points_lyr.commitChanges()

        return list(set([i for i in feature_store.values()]))

    def calculate_detailed_bait_lines_by_machine_and_load(self, machine_code, load_number):
        """
        Calculates the coverage rate by machine and load for each sow point
        :param machine_code: list['PBX', 'PBY']
        :param load_number: list[1,2,3,4]
        :return:
        """

        # Coverage Calculation
        # bucket_kg / total_load_sowing_seconds = kg/second
        # ( pnt_pair_distance * swath ) / 10000 = ha/second
        # kg/second / ha/second = kg/hectare
        # Tabula defines sowing as points with bucket_state = 1, and draws a line
        # to match the bucket_state = 1 pnts together.

        # Check if the detailed and bait lines tables already have data
        # for this machine and load_number. If they do then delete them out first
        self.delete_machine_load_data(machine_code, load_number, 'heli_bait_lines_detailed')

        heli_bait_lines_detailed = self.gpkg_layer('heli_bait_lines_detailed')

        heli_points_lyr = self.gpkg_layer('heli_points')
        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' AND \"load_number\" LIKE '{load_number}'")
        request = QgsFeatureRequest(expression)
        request.setOrderBy(orderby)

        features = [i for i in heli_points_lyr.getFeatures(request)]
        total_seconds_sowing = len([i for i in features if i['bucket_state'] == 1])
        if not total_seconds_sowing:
            return 'No sow data for this load number'

        bucket_size = features[0]['bucket_size']
        load_kg_second = float(bucket_size) / float(total_seconds_sowing)
        line_number = 0
        sow_rates = []
        previous_bucket_state = features[0]['bucket_state']
        heli_bait_lines_detailed.startEditing()

        # Construct a line that is halfway between the previous point and the next point
        for i in range(len(features)):
            feat = features[i]
            current_bucket_state = feat['bucket_state']
            if current_bucket_state == 0:
                previous_bucket_state = current_bucket_state
                continue  # Only want to know about active sowing lines.
            if i == 0:
                tmp_geom = QgsGeometry.fromPolylineXY([features[i].geometry().asPoint(),
                                                       features[i + 1].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([features[i].geometry().asPoint(),
                                                          tmp_geom.centroid().asPoint()])
                time_delta = feat['date_time'].toPyDateTime() - features[i + 1]['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2
            elif i == len(features) - 1:
                tmp_geom = QgsGeometry.fromPolylineXY([features[i - 1].geometry().asPoint(),
                                                       features[i].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([tmp_geom.centroid().asPoint(),
                                                          features[i].geometry().asPoint()])
                time_delta = features[i - 1]['date_time'].toPyDateTime() - feat['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2
            else:
                line1 = QgsGeometry.fromPolylineXY(
                    [features[i - 1].geometry().asPoint(), features[i].geometry().asPoint()])
                line2 = QgsGeometry.fromPolylineXY(
                    [features[i + 1].geometry().asPoint(), features[i].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([line1.centroid().asPoint(),
                                                          features[i].geometry().asPoint(),
                                                          line2.centroid().asPoint()])
                time_delta = features[i + 1]['date_time'].toPyDateTime() - features[i - 1]['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2

            # Determine if a new line number needs to be created
            if previous_bucket_state == 0 and current_bucket_state == 1:
                line_number += 1

            distance = line_string.length()
            hectares = distance * feat['width'] / 10000
            sow_rate = load_kg_second / hectares
            speed = (seconds * distance) * 1.94384  # m/s to knots conversion
            sow_rates.append(sow_rate)

            new_feat = QgsFeature(heli_bait_lines_detailed.fields())
            new_feat.setAttribute('src_id', feat['src_id'])
            new_feat.setAttribute('date_time', feat['date_time'])
            new_feat.setAttribute('speed', speed)
            new_feat.setAttribute('heading', feat['heading'])
            new_feat.setAttribute('altitude', feat['altitude'])
            new_feat.setAttribute('width', feat['width'])
            new_feat.setAttribute('machine_code', machine_code)
            new_feat.setAttribute('bucket_size', bucket_size)
            new_feat.setAttribute('load_number', feat['load_number'])
            new_feat.setAttribute('coverage_rate', sow_rate)
            new_feat.setAttribute('hectares', hectares)
            new_feat.setAttribute('distance', distance)
            new_feat.setAttribute('seconds', seconds)
            new_feat.setAttribute('line_number', line_number)
            new_feat.setAttribute('batch_id', feat['batch_id'])
            new_feat.setAttribute('bucket_state', feat['bucket_state'])
            new_feat.setGeometry(line_string)
            heli_bait_lines_detailed.addFeature(new_feat)

            previous_bucket_state = current_bucket_state
        heli_bait_lines_detailed.commitChanges()

    def calculate_bait_lines_by_machine_and_load(self, machine_code, load_number):
        """
        Calculates the coverage rate by machine and load for each sow point
        :param machine_code: list['PBX', 'PBY']
        :param load_number: list[1,2,3,4]
        :return:
        """

        self.delete_machine_load_data(machine_code, load_number, 'heli_bait_lines')

        heli_bait_lines_detailed = self.gpkg_layer('heli_bait_lines_detailed')
        heli_bait_lines = self.gpkg_layer('heli_bait_lines')

        # Update the bait_lines table
        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' AND \"load_number\" LIKE '{load_number}'")
        request = QgsFeatureRequest(expression)
        request.setOrderBy(orderby)

        features = [f for f in heli_bait_lines_detailed.getFeatures(request)]
        if not features:
            return 'No sow data for this load number'

        bucket_size = features[0]['bucket_size']

        # Set First Feature
        first_feat = features[0]
        geom = first_feat.geometry()
        distance = first_feat['distance']
        hectares = first_feat['hectares']
        speeds = [first_feat['speed']]
        seconds = first_feat['seconds']
        altitudes = [first_feat['altitude']]
        coverage_rates = [first_feat['coverage_rate']]
        src_id = first_feat['src_id']
        batch_id = first_feat['batch_id']
        line_number = first_feat['line_number']
        date_time = first_feat['date_time']

        heli_bait_lines.startEditing()
        for i in range(1, len(features)):
            feat = features[i]

            # New Line number
            if features[i - 1]['line_number'] != feat['line_number']:
                write_record = True
                new_record = True
                append_record = False
                last_write_record = False
            else:
                write_record = False
                new_record = False
                append_record = True
                last_write_record = False

            if i == len(features) - 1 and write_record:
                new_record = False
                append_record = False
                write_record = True
                last_write_record = True

            if i == len(features) - 1 and not write_record:
                append_record = True
                write_record = True
                new_record = False
                last_write_record = False

            if append_record:
                distance += feat['distance']
                hectares += feat['hectares']
                speeds.append(feat['speed'])
                seconds += feat['seconds']
                altitudes.append(feat['altitude'])
                coverage_rates.append(feat['coverage_rate'])
                geom = geom.combine(feat.geometry())

            if write_record:
                # Write the current feature to table
                speed = sum(speeds) / len(speeds)
                altitude = sum(altitudes) / len(altitudes)
                coverage_rate = sum(coverage_rates) / len(coverage_rates)
                new_feat = QgsFeature(heli_bait_lines.fields())
                new_feat.setAttribute('distance', distance)
                new_feat.setAttribute('seconds', seconds)
                new_feat.setAttribute('hectares', hectares)
                new_feat.setAttribute('speed', speed)
                new_feat.setAttribute('altitude', altitude)
                new_feat.setAttribute('coverage_rate', coverage_rate)
                new_feat.setAttribute('date_time', date_time)
                new_feat.setAttribute('batch_id', batch_id)
                new_feat.setAttribute('src_id', src_id)
                new_feat.setAttribute('bucket_size', bucket_size)
                new_feat.setAttribute('width', feat['width'])
                new_feat.setAttribute('bucket_state', 1)
                new_feat.setAttribute('line_number', line_number)
                new_feat.setAttribute('load_number', feat['load_number'])
                new_feat.setAttribute('machine_code', machine_code)
                new_feat.setGeometry(geom)
                heli_bait_lines.addFeature(new_feat)

            # There are occasions where the last sow point is a singleton, this means adding the current line
            # and creating a new record for the last point.
            if last_write_record:
                new_feat = QgsFeature(heli_bait_lines.fields())
                new_feat.setAttribute('distance', feat['distance'])
                new_feat.setAttribute('seconds', seconds)
                new_feat.setAttribute('hectares', feat['hectares'])
                new_feat.setAttribute('speed', feat['speed'])
                new_feat.setAttribute('altitude', feat['altitude'])
                new_feat.setAttribute('coverage_rate', feat['coverage_rate'])
                new_feat.setAttribute('date_time', feat['date_time'])
                new_feat.setAttribute('batch_id', feat['batch_id'])
                new_feat.setAttribute('src_id', feat['src_id'])
                new_feat.setAttribute('bucket_size', feat['bucket_size'])
                new_feat.setAttribute('width', feat['width'])
                new_feat.setAttribute('bucket_state', 1)
                new_feat.setAttribute('line_number', feat['line_number'])
                new_feat.setAttribute('load_number', feat['load_number'])
                new_feat.setAttribute('machine_code', machine_code)
                new_feat.setGeometry(feat.geometry())
                heli_bait_lines.addFeature(new_feat)

            if new_record:
                geom = feat.geometry()
                distance = feat['distance']
                hectares = feat['hectares']
                speeds = [feat['speed']]
                seconds = feat['seconds']
                altitudes = [feat['altitude']]
                coverage_rates = [feat['coverage_rate']]
                batch_id = feat['batch_id']
                src_id = feat['src_id']
                date_time = feat['date_time']
                line_number = feat['line_number']

        heli_bait_lines.commitChanges()

        return

    def calculate_sq_buffer_bait_lines_by_machine_and_load(self, machine_code, load_number):
        """
        Uses the bait lines layer to calculate a square buffer
        :param machine_code:
        :param load_number:
        :return:
        """

        self.delete_machine_load_data(machine_code, load_number, 'heli_bait_lines_buffered')
        heli_bait_lines = self.gpkg_layer('heli_bait_lines')
        heli_bait_lines_buffered = self.gpkg_layer('heli_bait_lines_buffered')

        # Update the bait_lines table
        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' AND \"load_number\" LIKE '{load_number}'")
        request = QgsFeatureRequest(expression)
        request.setOrderBy(orderby)

        features = [f for f in heli_bait_lines.getFeatures(request)]
        if not features:
            return 'No sow data for this load number'

        swath_translation = self.get_machine_swath_translation(machine_code)
        heli_bait_lines_buffered.startEditing()
        for feat in features:
            width = feat['width']
            if swath_translation.get(width):
                width = swath_translation.get(width)
            new_feat = QgsFeature(heli_bait_lines_buffered.fields())
            new_feat.setAttribute('src_id', feat['src_id'])
            new_feat.setAttribute('date_time', feat['date_time'])
            new_feat.setAttribute('speed', feat['speed'])
            new_feat.setAttribute('heading', feat['heading'])
            new_feat.setAttribute('altitude', feat['altitude'])
            new_feat.setAttribute('width', width)
            new_feat.setAttribute('machine_code', machine_code)
            new_feat.setAttribute('bucket_size', feat['bucket_size'])
            new_feat.setAttribute('load_number', feat['load_number'])
            new_feat.setAttribute('coverage_rate', feat['coverage_rate'])
            new_feat.setAttribute('hectares', feat['hectares'])
            new_feat.setAttribute('distance', feat['distance'])
            new_feat.setAttribute('seconds', feat['seconds'])
            new_feat.setAttribute('line_number', feat['line_number'])
            new_feat.setAttribute('batch_id', feat['batch_id'])
            new_feat.setAttribute('bucket_state', 1)
            new_feat.setGeometry(
                feat.geometry().buffer(width / 2, 6, QgsGeometry.EndCapStyle(2), QgsGeometry.JoinStyleMiter, 2))
            heli_bait_lines_buffered.addFeature(new_feat)

        heli_bait_lines_buffered.commitChanges()
        return

    def calculate_flight_path(self, machine_code, load_number):
        """Creates a line path from the non sowing points
        :param machine_code: str
        :param load_number: int
        """

        self.delete_machine_load_data(machine_code, load_number, 'flight_path')

        flight_path_lyr = self.gpkg_layer('flight_path')
        heli_points_lyr = self.gpkg_layer('heli_points')
        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' AND \"load_number\" LIKE '{load_number}'")
        request = QgsFeatureRequest(expression)
        request.setOrderBy(orderby)

        features = [i for i in heli_points_lyr.getFeatures(request)]

        line_number = 0
        previous_bucket_state = features[0]['bucket_state']
        batch_id = features[0]['batch_id']
        feature_store = {line_number: {'geoms': [],
                                       'start_time': features[0]['date_time']}}

        # Construct a line that is halfway between the previous point and the next point
        # Store the features, then aggregate based on the line_number
        for i in range(len(features)):
            feat = features[i]
            current_bucket_state = feat['bucket_state']
            if current_bucket_state == 1:
                previous_bucket_state = current_bucket_state
                continue  # Only want to know about non sowing lines.
            if i == 0:
                tmp_geom = QgsGeometry.fromPolylineXY([features[i].geometry().asPoint(),
                                                       features[i + 1].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([features[i].geometry().asPoint(),
                                                          tmp_geom.centroid().asPoint()])
                time_delta = feat['date_time'].toPyDateTime() - features[i + 1]['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2
            elif i == len(features) - 1:
                tmp_geom = QgsGeometry.fromPolylineXY([features[i - 1].geometry().asPoint(),
                                                       features[i].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([tmp_geom.centroid().asPoint(),
                                                          features[i].geometry().asPoint()])
                time_delta = features[i - 1]['date_time'].toPyDateTime() - feat['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2
            else:
                line1 = QgsGeometry.fromPolylineXY(
                    [features[i - 1].geometry().asPoint(), features[i].geometry().asPoint()])
                line2 = QgsGeometry.fromPolylineXY(
                    [features[i + 1].geometry().asPoint(), features[i].geometry().asPoint()])
                line_string = QgsGeometry.fromPolylineXY([line1.centroid().asPoint(),
                                                          features[i].geometry().asPoint(),
                                                          line2.centroid().asPoint()])
                time_delta = features[i + 1]['date_time'].toPyDateTime() - features[i - 1]['date_time'].toPyDateTime()
                seconds = time_delta.total_seconds() / 2

            # Determine if a new line number needs to be created
            if previous_bucket_state == 1 and current_bucket_state == 0:
                line_number += 1
                feature_store[line_number] = {'geoms': [],
                                              'start_time': feat['date_time'],
                                              'end_time': feat['date_time']}

            feature_store[line_number]['geoms'].append(line_string)
            feature_store[line_number]['end_time'] = feat['date_time']
            previous_bucket_state = current_bucket_state

        # Aggregate the non sowing lines
        flight_path_lyr.startEditing()
        for key, value in dict(sorted(feature_store.items())).items():
            if not value['geoms']:
                continue  # For loads where the first point is sowing.
            geom = value['geoms'][0]
            if len(value['geoms']) > 1:
                for i in range(1, len(value['geoms'])):
                    next_geom = value['geoms'][i]
                    geom = geom.combine(next_geom)

            new_feat = QgsFeature(flight_path_lyr.fields())
            new_feat.setAttribute('machine_code', machine_code)
            new_feat.setAttribute('load_number', load_number)
            new_feat.setAttribute('batch_id', batch_id)
            new_feat.setAttribute('line_number', key)
            new_feat.setAttribute('start_time', value['start_time'])
            new_feat.setAttribute('end_time', value['end_time'])
            new_feat.setGeometry(geom)
            flight_path_lyr.addFeature(new_feat)
        flight_path_lyr.commitChanges()

        return

    def calculate_summary_for_load_machine(self, machine_code, load_number):
        """
        Summarizes bait_lines_detailed table for a given load number and machine.
        :param machine_code: str
        :param load_number: int
        :return:
        """

        load_summary_lyr = self.gpkg_layer('load_summary')
        bait_lines_detailed = self.gpkg_layer('heli_bait_lines_detailed')
        existing_feature = [i for i in load_summary_lyr.getFeatures()
                            if i['machine_code'] == machine_code and i['load_number'] == load_number]

        clause = QgsFeatureRequest.OrderByClause('date_time', ascending=True)
        orderby = QgsFeatureRequest.OrderBy([clause])
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' AND \"load_number\" LIKE '{load_number}'")
        request = QgsFeatureRequest(expression)
        request.setOrderBy(orderby)

        machine_sow_rate = self.get_default_machine_sow_rate(machine_code)
        # If record for machine and load already exists, then delete it first
        # then insert a new record
        features = [i for i in bait_lines_detailed.getFeatures(request)]
        load_summary_lyr.startEditing()
        if len(features) == 0:
            return 'No sow data for this load number'
        if len(existing_feature) == 1:
            new_feat = existing_feature[0]
        else:
            new_feat = QgsFeature(load_summary_lyr.fields())
        new_feat.setAttribute('machine_code', machine_code)
        new_feat.setAttribute('batch_id', features[0]['batch_id'])
        new_feat.setAttribute('start_time', min([i['date_time'] for i in features]))
        new_feat.setAttribute('end_time', max([i['date_time'] for i in features]))
        new_feat.setAttribute('load_number', load_number)
        new_feat.setAttribute('bucket_size', features[0]['bucket_size'])
        new_feat.setAttribute('sum_hectares_square', sum([i['hectares'] for i in features]))
        new_feat.setAttribute('coverage_rate', mean([i['coverage_rate'] for i in features]))
        new_feat.setAttribute('average_speed', mean([i['speed'] for i in features]))
        new_feat.setAttribute('runout_time', sum([i['seconds'] for i in features]))
        new_feat.setAttribute('distance_spreading', sum([i['distance'] for i in features]))
        new_feat.setAttribute('dir_location', os.path.join(self.raw_data_folder, machine_code, features[0]['batch_id']))

        kg_second = sum([i['seconds'] for i in features]) / features[0]['bucket_size']
        target_ha = features[0]['bucket_size'] / machine_sow_rate
        target_distance = (target_ha * 10000.00) / features[0]['width']
        target_seconds = target_ha * (kg_second + 1)
        target_speed = (target_distance / target_seconds) * 1.94384  # m/s to knots conversion

        new_feat.setAttribute('target_speed', target_speed)
        load_summary_lyr.addFeature(new_feat)

        load_summary_lyr.commitChanges()

        return new_feat.attributes()

    def zoom_to_flight_data_extent(self, machine_code, load_numbers):
        """
        Calculates the extent of the heli point data for the provided machine
        and load numbers.
        :param machine_code: str
        :param load_numbers: list<int,int>
        :return: extent
        """

        heli_points_lyr = self.gpkg_layer('heli_points')
        expression = QgsExpression(f"\"machine_code\" ILIKE '{machine_code}' and \"load_number\" in {tuple(load_numbers)}")
        request = QgsFeatureRequest(expression)

        counter = 0
        extent = {'xmin':10000000, 'ymin':10000000, 'xmax':0, 'ymax':0}

        for feat in heli_points_lyr.getFeatures(request=request):
            x = feat.geometry().asPoint().x()
            y = feat.geometry().asPoint().y()
            if x > extent['xmax']: extent['xmax'] = x
            if x < extent['xmin']: extent['xmin'] = x
            if y > extent['ymax']: extent['ymax'] = y
            if y < extent['ymin']: extent['ymin'] = y

        if extent == {'xmin':10000000, 'ymin':10000000, 'xmax':0, 'ymax':0}:
            return None

        return extent



