"""
Tests mandatory fields and mandatory files in GTFS datasets.
"""

import requests
import zipfile
import csv
import io
import json
from utilities.test_utilities import DataTest

REQUIRED_GTFS_FILES = ["agency.txt", "calendar.txt", "calendar_dates.txt", "routes.txt", "stop_times.txt", "stops.txt", "trips.txt"]

OPTIONAL_GTFS_FILES = ["booking_rules.txt", "booking_rules_additional_messages.txt", "feed_info.txt",
                       "frequencies.txt", "location_group_stops.txt", "location_groups.txt",
                       "locations.geojson", "transfers.txt", "fare_attributes.txt", "fare_rules.txt", "timeframes.txt", "rider_categories.txt",
                       "fare_media.txt", "fare_products.txt", "fare_leg_rules.txt", "fare_leg_join_rules.txt", "fare_transfer_rules.txt",
                       "areas.txt", "stop_areas.txt", "networks.txt", "route_networks.txt", "shapes.txt",
                       "pathways.txt", "levels.txt", "translations.txt", "attributions.txt"]

GTFS_REQUIRED_FIELDS = {
    "agency.txt": ["agency_id", "agency_name", "agency_url", "agency_timezone"],
    "calendar.txt": ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
    "calendar_dates.txt": ["service_id", "date", "exception_type"],
    "routes.txt": ["route_id", "route_short_name", "route_long_name", "route_type"],
    "stop_times.txt": ["trip_id", "arrival_time", "departure_time", "stop_id"],
    "stops.txt": ["stop_id", "stop_name", "stop_lat", "stop_lon"],
    "trips.txt": ["route_id", "service_id", "trip_id"],
    "booking_rules.txt": ["booking_rule_id", "booking_type","info_url","message","phone_number","prior_notice_duration_max",
                          "prior_notice_duration_min"],
    "booking_rules_additional_messages.txt": ["booking_rule_id", "message_id", "message_type", "message"],
    "feed_info.txt": ["feed_publisher_name", "feed_publisher_url", "feed_lang"],
    "frequencies.txt": ["trip_id", "start_time", "end_time", "headway_secs"],
    "location_group_stops.txt": ["location_group_id", "stop_id"],
    "location_groups.txt": ["location_group_id", "location_group_name"],
    "locations.geojson": ["type", "features"],
    "transfers.txt": ["from_stop_id", "to_stop_id", "transfer_type"],
    "fare_attributes.txt": ["fare_id", "price", "currency_type", "payment_method", "transfers"],
    "fare_rules.txt": ["fare_id"],
    "timeframes.txt": ["timeframe_id", "start_time", "end_time"],
    "rider_categories.txt": ["rider_category_id", "rider_category_name", "is_default_fare_category"],
    "fare_media.txt": ["fare_media_id", "fare_media_type"],
    "fare_products.txt": ["fare_product_id", "amount"],
    "fare_leg_rules.txt": ["fare_product_id"],
    "fare_leg_join_rules.txt": ["from_network_id", "to_network_id"],
    "fare_transfer_rules.txt": ["fare_transfer_type"],
    "areas.txt": ["area_id"],
    "stop_areas.txt": ["stop_id", "area_id"],
    "networks.txt": ["network_name"],
    "route_networks.txt": ["route_id", "network_id"],
    "shapes.txt": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
    "pathways.txt": ["pathway_id", "from_stop_id", "to_stop_id", "pathway_mode", "is_bidirectional"],
    "levels.txt": ["level_id", "level_index"],
    "translations.txt": ["table_name", "field_name", "language", "translation"],
    "attributions.txt": ["organization_name"]
}

def check_gtfs(url: str, data_test=None):
    if data_test is None:
        data_test = DataTest(name="check_gtfs")
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            files_in_zip = z.namelist()

            for file in REQUIRED_GTFS_FILES:
                if file not in files_in_zip:
                    data_test.log_failure(f"Required file {file} missing!")
                else:
                    validate_fields(z, file, data_test)

            for file in OPTIONAL_GTFS_FILES:
                if file in files_in_zip:
                    validate_fields(z, file, data_test)

    except requests.exceptions.RequestException as e:
        data_test.log_failure(f"Request Error: {e}")
    except zipfile.BadZipFile:
        data_test.log_failure("Downloaded file is not a valid ZIP archive.")
    except Exception as e:
        data_test.log_failure(f"General Error: {e}")


def validate_fields(zip_handle, filename, data_test):
    if filename not in GTFS_REQUIRED_FIELDS:
        return

    with zip_handle.open(filename) as f:
        if filename.endswith(".geojson"):
            try:
                data = json.load(f)
                missing = [f for f in GTFS_REQUIRED_FIELDS[filename] if f not in data]
                if missing:
                    data_test.log_failure(f"Missing keys in {filename}: {missing}")
            except Exception as e:
                data_test.log_failure(f"Error parsing JSON in {filename}: {e}")
            return

        wrapper = io.TextIOWrapper(f, encoding='utf-8-sig')
        reader = csv.reader(wrapper)
        try:
            header = next(reader)
        except StopIteration:
            data_test.log_failure(f"{filename} is empty.")
            return

        missing = [f for f in GTFS_REQUIRED_FIELDS[filename] if f not in header]

        if missing:
            data_test.log_failure(f"Missing field(s) in {filename}: {missing}")