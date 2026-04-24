import os
from enum import Enum

from typing_extensions import Iterable, Sized

from tests.hrdf_checker_tests.downloader.downloader import Downloader
from tests.hrdf_checker_tests.parser.csv_parser import CSVParser
from tests.hrdf_checker_tests.parser.hrdf_parser import HRDFParser, Language
from tests.hrdf_checker_tests.persister.persister import Persister
from tests.hrdf_checker_tests.utils.list_utils import convert_list_to_dict

from utilities.test_utilities import DataTest

THRESHOLDS = {
    "max_betreiber_fahreten_diviation_relative": 0.15
}


class LoggerLevelEnum(Enum):
    INFO = 1
    INFO_WITH_BANG = 2
    WARNING = 3
    ERROR = 4


def log_with_log_level(log_level: LoggerLevelEnum, message: str, data_test: DataTest):
    match log_level:
        case LoggerLevelEnum.INFO:
            data_test.log_info(message)
        case LoggerLevelEnum.INFO_WITH_BANG:
            data_test.log_info(message, True)
        case LoggerLevelEnum.WARNING:
            data_test.log_warning(message)
        case LoggerLevelEnum.ERROR:
            data_test.log_exception(message)


def log_list(list: Iterable | Sized, data_test: DataTest, list_message: str, element_message: str,
             log_element_level: LoggerLevelEnum = LoggerLevelEnum.INFO_WITH_BANG,
             log_level_at_attention: LoggerLevelEnum = LoggerLevelEnum.WARNING,
             attention_threshhold: int = 50,
             log_list_level: LoggerLevelEnum = LoggerLevelEnum.INFO,
             max_logging_length: int = 500,
             additional_object=None):
    """

    :param list: the list (or other collection) to be logged
    :param data_test: to log
    :param list_message: the message for the entire list is an f-string with acces to count and additional_object variable
    :param element_message: the message for one element of the list is an f-string with acces to element and additional_object variable
    :param log_element_level: the log level for the element log lines
    :param log_level_at_attention: the log level at "attention"
    :param attention_threshold: the minimum size indication "attention"
    :param log_list_level: the log level for the list_message
    :param max_logging_length: max length of the list to be logged list longer than this limit will not be logged per element
    :param additional_object: an additional object which can be used in the list_message and element_message f-strings (e.g. a dict with additional information for the element)
    :return: Nothing, uses log functions from data_test objects
    """
    count = len(list)  # used in eval
    list_message_str = eval(f'f"{list_message}"')
    if len(list) >= attention_threshhold:
        log_with_log_level(log_level_at_attention, list_message_str, data_test)
    else:
        log_with_log_level(log_list_level, list_message_str, data_test)
    if len(list) <= max_logging_length:
        for element in list:
            log_with_log_level(log_element_level, eval(f'f"{element_message}"'), data_test)
    else:
        log_with_log_level(log_list_level,
                           f"List length ({len(list)}) considered to be too long (threshold {max_logging_length}), refusing to log individual elements",
                           data_test)


def persist_file_sizes(hrdf_parser: HRDFParser, data_test: DataTest, persister: Persister,
                       fahrplan_bezeichnung: str):
    FILE_SIZE_FILE_NAME = "hrdf_file_sizes.json"
    persister.append_structured_data(FILE_SIZE_FILE_NAME, hrdf_parser.get_file_sizes(),
                                     fahrplan_bezeichnung)
    data_test.log_info(f"Persisted file sizes to {FILE_SIZE_FILE_NAME}")


def run(data_test: DataTest, static_mode=False):
    """
    This method runs the hrdf checker
    :argument static_mode: when true disables fetching and deletion of files to be checked, useful for debugging purposes, remember to set it to false before using it in production
    :argument data_test: the data test passed from the runner
    """

    """todo: change hardcoded urls below"""

    base_path = os.path.split(__file__)[0]
    files_path = os.path.join(base_path, "hrdf_files")
    hrdf_file_name = "hrdf.zip"
    dienststellen_file_name = "dienststellen.csv"
    if not static_mode:
        downloader_object = Downloader(files_path, data_test)
        downloader_object.fetch_file(
            "https://data.opentransportdata.swiss/dataset/timetable-54-2026-hrdf/permalink",
            hrdf_file_name, True)
        downloader_object.fetch_file(
            "https://data.opentransportdata.swiss/dataset/service-points-full/permalink",
            dienststellen_file_name, True)
        downloader_object.extract_zip_to_same_file_name(dienststellen_file_name)
    else:
        data_test.log_warning(f"Static mode has been enabled, the plugin will not fetch any data")
    hrdf_parser_object = HRDFParser(os.path.join(files_path,
                                                 hrdf_file_name), data_test)
    csv_parser_object = CSVParser(os.path.join(files_path,
                                               dienststellen_file_name), data_test)
    try:
        persister_object = Persister(files_path, data_test)
        soll_daten_bahnhof_list = csv_parser_object.read_as_dict()
        # missing files in hrdf
        set_of_missing_files = hrdf_parser_object.get_list_of_missing_files()
        log_list(set_of_missing_files, data_test, "{count} missing files in hrdf file",
                 "{element} is missing in hrdf file", attention_threshhold=1,
                 log_level_at_attention=LoggerLevelEnum.WARNING,
                 log_element_level=LoggerLevelEnum.WARNING)

        # excess files in hrdf
        set_of_excess_files = hrdf_parser_object.get_list_of_exess_fies()
        log_list(set_of_excess_files, data_test, "{count} excess files in hrdf file",
                 "{element} should not be in hrdf file", attention_threshhold=1,
                 log_level_at_attention=LoggerLevelEnum.WARNING,
                 log_element_level=LoggerLevelEnum.WARNING)

        # encoding
        hrdf_parser_object.test_file_encodings()
        soll_daten_bahnhof_dict = convert_list_to_dict(soll_daten_bahnhof_list,
                                                       lambda a: int(a['number']))
        hrdf_daten_fplan_bahnhof_numbers = hrdf_parser_object.get_bahnhof_numbers_from_fplan()
        hrdf_bahnhof_list = hrdf_parser_object.get_bahnhof()
        hrdf_bahnhof_dict = convert_list_to_dict(hrdf_bahnhof_list, lambda a: int(a['nummer']))
        hrdf_fplan_entries = hrdf_parser_object.get_fplan_entries()

        hrdf_betreiber_number_dict = convert_list_to_dict(hrdf_fplan_entries,
                                                          lambda a: a["zZeile"]["verwaltung"])
        fahrplan_bezeichnung = hrdf_parser_object.get_eckdaten()['fahrplanBezeichnung']
        # amount of fahrten comparison
        hrdf_betreiber_number_list = [x["zZeile"]["verwaltung"] for x in hrdf_fplan_entries]
        HRDF_ANZANHL_BETREIBER_FILE_NAME = "hrdf_anzahl_betreiber.json"
        for betreiber_number in hrdf_betreiber_number_dict.keys():
            hrdf_betreiber_number_dict[betreiber_number] = hrdf_betreiber_number_list.count(
                betreiber_number)
        try:
            loaded_hrdf_betrieber_number_dict = \
                persister_object.get_latest_structured_data(HRDF_ANZANHL_BETREIBER_FILE_NAME)[
                    'data']
            for betreiber_number in loaded_hrdf_betrieber_number_dict.keys():
                try:
                    factor = loaded_hrdf_betrieber_number_dict[betreiber_number] / \
                             hrdf_betreiber_number_dict[betreiber_number]
                    if THRESHOLDS[
                        "max_betreiber_fahreten_diviation_relative"] > factor or factor > 1 + \
                            THRESHOLDS["max_betreiber_fahreten_diviation_relative"]:
                        data_test.log_info(
                            f"Betreiber {betreiber_number} amount of fahrten (current: {hrdf_betreiber_number_dict[betreiber_number]} previous: {loaded_hrdf_betrieber_number_dict[betreiber_number]}) is outside of range (±{THRESHOLDS["max_betreiber_fahreten_diviation_relative"]:.2%}) with {factor:.2%}",
                            True)
                except KeyError as e:
                    data_test.log_warning(f"Betreiber number {e} not found")
                except ZeroDivisionError as e:
                    data_test.log_warning(
                        f"Betreiber {betreiber_number} has zero fahrten currently, this should never happen, because the betreibers are loaded from the fplan file")
        except FileNotFoundError:
            data_test.log_warning(
                f"No betreiber numbers found (at {os.path.join(persister_object.file_path, HRDF_ANZANHL_BETREIBER_FILE_NAME)}), you can ignore this warning if this is the first time running")
        persister_object.append_structured_data(HRDF_ANZANHL_BETREIBER_FILE_NAME,
                                                hrdf_betreiber_number_dict, fahrplan_bezeichnung)

        list_of_bfkoords = hrdf_parser_object.get_bfkoord_wgs()
        for bfkoord in list_of_bfkoords:
            if bfkoord["xKoordinate"] == 0 and bfkoord["yKoordinate"] == 0:
                data_test.log_info(
                    f"Koordinates for Bahnhof {bfkoord['nummer']} suspicious X {bfkoord['xKoordinate']} Y {bfkoord['yKoordinate']}",
                    True)

        set_of_bfkoords_bahnhof_numbers = set([x["nummer"] for x in list_of_bfkoords])

        set_of_bahnhof_numbers_without_koordinates = set(
            hrdf_bahnhof_dict.keys()) - set_of_bfkoords_bahnhof_numbers
        log_list(set_of_bahnhof_numbers_without_koordinates, data_test,
                 "{count} Bahnhofs without koordinates in bfkoords_wgs file",
                 "No koordinates for Bahnhof {element} found")

        # filter out the empty richtungs schlüssel because this is coverd by another test
        set_of_richtungsschluesel_from_fplan = set(
            [rZeile["richtungsschluessel"] for x in hrdf_fplan_entries for rZeile in x['rZeile'] if
             not rZeile['richtungsschluessel'].isspace()])
        list_of_richtung = hrdf_parser_object.get_richtung()
        set_of_richtungsschluesel_from_richtung = set(
            [x["richtungsschluessel"] for x in list_of_richtung])

        set_of_richtungsschluesel_not_in_richtung = set_of_richtungsschluesel_from_fplan - set_of_richtungsschluesel_from_richtung

        log_list(set_of_richtungsschluesel_not_in_richtung, data_test,
                 "{count} Richtungsschlüsel from fplan missing in richtung file",
                 "Richtungsschlüssel {element} from fplan is not present in richtung file")

        set_of_richtungsschluesel_not_in_fplan = set_of_richtungsschluesel_from_richtung - set_of_richtungsschluesel_from_fplan

        log_list(set_of_richtungsschluesel_not_in_fplan, data_test,
                 "{count} Richtungsschlüsel from richtung file unreferenced in fplan file",
                 "Richtungsschlüssel {element} from richtung file unreferenced in fplan file")

        list_of_fahrten_from_fplan_with_empty_richtungsschluesel = [x for x in hrdf_fplan_entries if
                                                                    x["rZeile"][0][
                                                                        "richtungsschluessel"].isspace()]
        log_list(list_of_fahrten_from_fplan_with_empty_richtungsschluesel, data_test,
                 "{count} Fahrten from fplan without richtungsschlüssel in *r Zeile",
                 "Fahrt with nummer {element['zZeile']['fahrtnummer']} (variante {element['zZeile']['variante']} betreiber {element['zZeile']['verwaltung']}) has empty richtungsschlüsel",
                 log_level_at_attention=LoggerLevelEnum.INFO_WITH_BANG)

        # check if files are within spec
        log_list(hrdf_parser_object.get_out_of_spec_file_sizes(), data_test,
                 "{count} Files too big or too small",
                 "File {element['filename']} too big or too small, min size: {element['minSize']/1000} KB max size: {element['maxSize']/1000} KB actual size: {element['actualSize']/1000} KB")

        # persist file sizes for future analysis
        try:
            persist_file_sizes(hrdf_parser_object, data_test, persister_object, fahrplan_bezeichnung)
        except Exception as e:
            data_test.log_exception(f"Failed to persist file sizes see: {e}", e)

        # check if info texts have the same keys in all languages
        dict_of_info_texts_de = convert_list_to_dict(hrdf_parser_object.get_infotexte(Language.DE),
                                                     lambda x: x['nummer'])
        dict_of_info_texts_fr = convert_list_to_dict(hrdf_parser_object.get_infotexte(Language.FR),
                                                     lambda x: x['nummer'])
        dict_of_info_texts_it = convert_list_to_dict(hrdf_parser_object.get_infotexte(Language.IT),
                                                     lambda x: x['nummer'])
        dict_of_info_texts_en = convert_list_to_dict(hrdf_parser_object.get_infotexte(Language.EN),
                                                     lambda x: x['nummer'])
        log_list(set(dict_of_info_texts_de.keys()) - set(dict_of_info_texts_fr.keys()), data_test,
                 "{count} Infotexte present which are in DE but not in FR",
                 "Infotext {element} not in FR")
        log_list(set(dict_of_info_texts_de.keys()) - set(dict_of_info_texts_it.keys()), data_test,
                 "{count} Infotexte present which are in DE but not in IT",
                 "Infotext {element} not in IT")
        log_list(set(dict_of_info_texts_de.keys()) - set(dict_of_info_texts_en.keys()), data_test,
                 "{count} Infotexte present which are in DE but not in EN",
                 "Infotext {element} not in EN")

        set_of_info_text_numbers_from_hrdf_fplan = set(
            info_text_number["textNummber"] for entrie in hrdf_fplan_entries for info_text_number in
            entrie["iZeilen"])

        list_of_zugart = hrdf_parser_object.get_zugart()

        set_of_info_text_numbers_from_zuagart = set(
            info_text_number["textNummber"] for entrie in list_of_zugart for info_text_number in
            entrie["iZeilen"])

        log_list(set_of_info_text_numbers_from_hrdf_fplan - set(dict_of_info_texts_de.keys()),
                 data_test,
                 "{count} Infotexte referenced in fplan file but not present in infotext file",
                 "Infotext {element} referenced in fplan but not present in infotext",
                 attention_threshhold=1)
        log_list(set_of_info_text_numbers_from_zuagart - set(dict_of_info_texts_de.keys()),
                 data_test,
                 "{count} Infotexte referenced in zugart file but not present in infotext file",
                 "Infotext {element} referenced in zugart but not present in infotext",
                 attention_threshhold=1)
        log_list(set(dict_of_info_texts_de.keys()) - (
                set_of_info_text_numbers_from_hrdf_fplan | set_of_info_text_numbers_from_zuagart),
                 data_test,
                 "{count} Infotexte present in infotext file but not referenced in fplan or zugart file",
                 "Infotext {element} (DE: {additional_object[element]['text']}) present in infotext but not referenced in fplan or zugart",
                 additional_object=dict_of_info_texts_de, attention_threshhold=100)

        set_of_missing_fplan_bahnhof_numbers = set(hrdf_daten_fplan_bahnhof_numbers).difference(
            set(soll_daten_bahnhof_dict.keys()))
        list_of_missing_fplan_bahnhof_numbers_possible_in_csv = [x for x in
                                                                 set_of_missing_fplan_bahnhof_numbers
                                                                 if
                                                                 110000 <= x < 150000 or 8500000 <= x < 8600000]
        log_list(list_of_missing_fplan_bahnhof_numbers_possible_in_csv, data_test,
                 "{count} missing Bahnhof in hrdf fplan file found (within 11-15, 85)",
                 "Bahnhof in hrdf fplan not found in service Points: {element}")

        set_of_unreferenced_bahnhof = set(hrdf_bahnhof_dict.keys()) - set(
            hrdf_daten_fplan_bahnhof_numbers)
        list_of_unreferenced_bahnhof_without_fake_bahnhof = [x for x in set_of_unreferenced_bahnhof
                                                             if
                                                             100000 < x]
        log_list(list_of_unreferenced_bahnhof_without_fake_bahnhof, data_test,
                 "{count} unreferenced bahnhof (from hrdf fplan) in hrdf bahnhof found",
                 "Bahnhof in hrdf bahnhof is unreferenced in fplan {element} {additional_object[element]['offizielleBezeichnung']}",
                 additional_object=hrdf_bahnhof_dict,
                 log_level_at_attention=LoggerLevelEnum.INFO_WITH_BANG)

        set_of_missing_bahnhof = set(hrdf_daten_fplan_bahnhof_numbers) - set(
            hrdf_bahnhof_dict.keys())
        log_list(set_of_missing_bahnhof, data_test,
                 "{count} bahnhof which are present in hrdf fplan but not in hrdf bahnhof",
                 "Bahnhof in hrdf fplan not found in hrdf bahnhof {element}")
    finally:
        hrdf_parser_object.close(not static_mode)
        csv_parser_object.close(not static_mode)
