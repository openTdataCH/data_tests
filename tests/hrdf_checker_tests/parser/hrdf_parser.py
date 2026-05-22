"""
A module to parse HRDF Files
"""
import datetime
import os
import re
import shutil
import tempfile
import zipfile
from enum import Enum
from typing import List, TypeVar
from utilities.test_utilities import DataTest

from typing_extensions import TypedDict, Callable

def has_bom(seq: bytes):
    return "BOM" if seq[0:3] == b'\xef\xbb\xbf' else "NO BOM"

class Bahnhof(TypedDict):
    nummer: int
    offizielleBezeichnung: str
    langeBezeichnung: str
    abkuerzung: str
    alternativeBezeichungen: list[str]


class BahnhofKoordWGS(TypedDict):
    nummer: int
    xKoordinate: float
    yKoordinate: float
    zKoordinate: int


class Richtung(TypedDict):
    richtungsschluessel: str
    richtungsangabe: str


class ZZeile(TypedDict):
    fahrtnummer: int
    verwaltung: str
    variante: int


class RZeile(TypedDict):
    richungskennung: str
    richtungsschluessel: str
    nummerAb: int | None
    nummerBis: int | None


class IZeile(TypedDict):
    textCode: str
    nummerAb: int | None
    nummerBis: int | None
    bitfeldNumber: int | None
    textNumber: int


class FPlanEntry(TypedDict):
    zZeile: ZZeile
    rZeile: List[RZeile]
    iZeilen: List[IZeile]


class FileSize(TypedDict):
    filename: str
    minSize: int | None
    maxSize: int | None
    actualSize: int


class Language(Enum):
    DE = "DE"
    EN = "EN"
    FR = "FR"
    IT = "IT"


class InfoText(TypedDict):
    nummer: int
    text: str


class Eckdaten(TypedDict):
    fahrplanStart: datetime.date
    fahrplanEnd: datetime.date
    fahrplanBezeichnung: str


class Zugart(TypedDict):
    gattungscode: str
    produktklasse: int
    tarifgruppe: str | None
    ausgabesteuerung: int
    gattungsbezeichnung: str
    zuschlag: int
    flags: str | None
    iZeilen: List[IZeile]


T = TypeVar("T")


def none_if_empty_or_value(value: str, converter: Callable[[str], T] = str) -> T | None:
    return None if value.isspace() else converter(value)


class HRDFParser:
    MIN = "MIN"
    MAX = "MAX"
    BAHNHOF_FILE_NAME = "BAHNHOF"
    FPLAN_FILE_NAME = "FPLAN"
    BFKOORD_WGS_FILE_NAME = "BFKOORD_WGS"
    RICHTUNG_FILE_NAME = "RICHTUNG"
    INFOTEXT_PREFIX = "INFOTEXT_"
    INFOTEXT_DE_FILE_NAME = INFOTEXT_PREFIX + Language.DE.value
    INFOTEXT_EN_FILE_NAME = INFOTEXT_PREFIX + Language.EN.value
    INFOTEXT_FR_FILE_NAME = INFOTEXT_PREFIX + Language.FR.value
    INFOTEXT_IT_FILE_NAME = INFOTEXT_PREFIX + Language.IT.value
    ECKDATEN_FILE_NAME = "ECKDATEN"
    ZUGART_FILE_NAME = "ZUGART"
    LIST_OF_EXPECTED_FILES = ["ATTRIBUT", BAHNHOF_FILE_NAME, "BETRIEB_DE", "BETRIEB_EN",
                              "BETRIEB_FR", "BETRIEB_IT", "BFKOORD_LV95", BFKOORD_WGS_FILE_NAME,
                              "BFPRIOS", "BHFART", "BITFELD", "BITFIELD", "DURCHBI", ECKDATEN_FILE_NAME,
                              "FEIERTAG",
                              FPLAN_FILE_NAME, "GLEISE_LV95", "GLEISE_WGS", INFOTEXT_DE_FILE_NAME,
                              INFOTEXT_EN_FILE_NAME, INFOTEXT_FR_FILE_NAME, INFOTEXT_IT_FILE_NAME,
                              "KMINFO", "LINIE",
                              "METABHF", RICHTUNG_FILE_NAME, "UMSTEIGB", "UMSTEIGL", "UMSTEIGV",
                              "UMSTEIGZ", "ZEITVS", ZUGART_FILE_NAME]
    DICT_OF_EXPECTED_FILE_SIZES_IN_BYTES = {
        BAHNHOF_FILE_NAME: {
            MIN: 900_000,
            MAX: 2_000_000
        },
        FPLAN_FILE_NAME: {
            MIN: 500_000_000,
            MAX: 2_500_000_000
        },
        BFKOORD_WGS_FILE_NAME: {
            MIN: 1_500_000,
            MAX: 2_500_000
        },
        RICHTUNG_FILE_NAME: {
            MIN: 100_000,
            MAX: 250_000
        },
        INFOTEXT_DE_FILE_NAME: {
            MIN: 10_000_000,
            MAX: 60_000_000
        },
        INFOTEXT_EN_FILE_NAME: {
            MIN: 10_000_000,
            MAX: 60_000_000
        },
        INFOTEXT_FR_FILE_NAME: {
            MIN: 10_000_000,
            MAX: 60_000_000
        },
        INFOTEXT_IT_FILE_NAME: {
            MIN: 10_000_000,
            MAX: 60_000_000
        },
        ECKDATEN_FILE_NAME: {
            MIN: 40,
            MAX: 140
        },
        ZUGART_FILE_NAME: {
            MIN: 5_000,
            MAX: 15_000
        }
    }

    def __init__(self, hrdf_file_path, data_test: DataTest,
                 temporary_file_path=os.path.join(tempfile.gettempdir(), "hrdf")):
        self.hrdf_file_path = hrdf_file_path
        self.temporary_file_path = temporary_file_path
        self.data_test = data_test
        self.__extract_zip()

    def __extract_zip(self):
        zipfile.ZipFile(self.hrdf_file_path).extractall(self.temporary_file_path)
        self.data_test.log_info(
            f"Extracted HRDF file {self.hrdf_file_path} to temporary folder {self.temporary_file_path}")

    def get_bahnhof(self) -> list[Bahnhof]:
        bahnof_list: list[Bahnhof] = []
        with open(os.path.join(self.temporary_file_path, self.BAHNHOF_FILE_NAME), "r",
                  encoding="utf-8") as file:
            for line in file:
                nummer = int(line[:7])
                name_string = line[12:]
                alternative_bezeichungen = []
                offizielleBezeichnung = None
                langeBezeichnung = None
                abkrzung = None
                for match in re.finditer(r"(?P<value>[^$]*)\$<(?P<type>\d)>", name_string):
                    group_dict = match.groupdict()
                    match int(group_dict["type"]):
                        case 1:
                            offizielleBezeichnung = group_dict["value"]
                        case 2:
                            langeBezeichnung = group_dict["value"]
                        case 3:
                            abkrzung = group_dict["value"]
                        case 4:
                            alternative_bezeichungen.append(group_dict["value"])
                bahnof_list.append(
                    Bahnhof(nummer=nummer, alternativeBezeichungen=alternative_bezeichungen,
                            offizielleBezeichnung=offizielleBezeichnung,
                            langeBezeichnung=langeBezeichnung, abkuerzung=abkrzung))
        self.data_test.log_info(
            f"Successfully parsed {len(bahnof_list)} bahnhofs from {self.BAHNHOF_FILE_NAME}")
        return bahnof_list

    def get_bahnhof_numbers_from_fplan(self) -> list[int]:
        bahnhof_number_list = []
        with open(os.path.join(self.temporary_file_path, self.FPLAN_FILE_NAME), "r",
                  encoding="utf-8") as file:
            for line in file:
                if line[0] != '*':
                    bahnhof_number_list.append(int(line[:7]))
        self.data_test.log_info(
            f"Successfully parsed {len(bahnhof_number_list)} bahnhof numbers from {self.FPLAN_FILE_NAME}")
        return bahnhof_number_list

    def get_list_of_missing_files(self) -> set[str]:
        list_of_present_files = os.listdir(self.temporary_file_path)
        return set(self.LIST_OF_EXPECTED_FILES) - set(list_of_present_files)

    def get_list_of_exess_fies(self) -> set[str]:
        list_of_present_files = os.listdir(self.temporary_file_path)
        return set(list_of_present_files) - set(self.LIST_OF_EXPECTED_FILES)

    def get_bfkoord_wgs(self) -> list[BahnhofKoordWGS]:
        bfkoord_wgs_list = []
        with open(os.path.join(self.temporary_file_path, self.BFKOORD_WGS_FILE_NAME), "r",
                  encoding="utf-8") as file:
            for line in file:
                nummer = int(line[:7])
                x_koordinate = float(line[8:19])
                y_koordinate = float(line[20:31])
                z_koordinate = int(line[32:38])
                bfkoord_wgs_list.append(
                    BahnhofKoordWGS(nummer=nummer, xKoordinate=x_koordinate,
                                    yKoordinate=y_koordinate,
                                    zKoordinate=z_koordinate))
        self.data_test.log_info(
            f"Successfully parsed {len(bfkoord_wgs_list)} BahnhofKoordWGS from {self.BFKOORD_WGS_FILE_NAME}")
        return bfkoord_wgs_list

    def get_richtung(self) -> list[Richtung]:
        richtung_list = []
        with open(os.path.join(self.temporary_file_path, self.RICHTUNG_FILE_NAME), "r",
                  encoding="utf-8") as file:
            for line in file:
                richtungsschluessel = line[:7]
                richtungsangabe = line[8:].rstrip()
                richtung_list.append(
                    Richtung(richtungsschluessel=richtungsschluessel,
                             richtungsangabe=richtungsangabe))
        self.data_test.log_info(
            f"Successfully parsed {len(richtung_list)} richtung from {self.RICHTUNG_FILE_NAME}")
        return richtung_list

    def get_fplan_entries(self) -> list[FPlanEntry]:
        fplan_entries_list = []
        with open(os.path.join(self.temporary_file_path, self.FPLAN_FILE_NAME), "r",
                  encoding="utf-8") as file:
            z_zeile = None
            r_zeile = []
            i_zeilen = []
            in_information = False
            for line in file:
                # Assume end of meta information
                if line[0] != '*':
                    if in_information:
                        in_information = False
                        fplan_entries_list.append(
                            FPlanEntry(zZeile=z_zeile, rZeile=r_zeile, iZeilen=i_zeilen))
                        i_zeilen = []
                        r_zeile = []
                # Start of entrie
                elif line[:2] == "*Z":
                    in_information = True
                    fahrtnummer = int(line[3:9])
                    verwaltung = line[10:16]
                    variante = int(line[19:22])
                    z_zeile = ZZeile(fahrtnummer=fahrtnummer, verwaltung=verwaltung,
                                     variante=variante)
                # richtung information
                elif line[:2] == "*R":
                    richungskennung = line[3:4]
                    richtungsschluessel = line[5:12]
                    nummer_ab_r = none_if_empty_or_value(line[13:20], int)
                    nummer_bis_r = none_if_empty_or_value(line[21:28], int)
                    r_zeile.append(RZeile(richungskennung=richungskennung,
                                          richtungsschluessel=richtungsschluessel,
                                          nummerAb=nummer_ab_r,
                                          nummerBis=nummer_bis_r))
                # Infozeilen
                elif line[:2] == "*I":
                    text_code = line[3:5]
                    nummer_ab_i = none_if_empty_or_value(line[6:13], int)
                    nummer_bis_i = none_if_empty_or_value(line[14:21], int)
                    bitfeld_nummer = none_if_empty_or_value(line[22:28], int)
                    info_text_nummer = int(line[29:38])
                    i_zeilen.append(
                        IZeile(textCode=text_code, nummerAb=nummer_ab_i, nummerBis=nummer_bis_i,
                               bitfeldNummber=bitfeld_nummer, textNummber=info_text_nummer))
        self.data_test.log_info(
            f"Successfully parsed {len(fplan_entries_list)} FPlan entries from {self.FPLAN_FILE_NAME}")
        return fplan_entries_list

    def get_file_sizes(self):
        list_of_present_files = os.listdir(self.temporary_file_path)
        file_sizes_list = []
        for file in list_of_present_files:
            file_size = int(os.path.getsize(os.path.join(self.temporary_file_path, file)))
            min_size = None
            max_size = None
            try:
                min_size = self.DICT_OF_EXPECTED_FILE_SIZES_IN_BYTES[file][self.MIN]
                max_size = self.DICT_OF_EXPECTED_FILE_SIZES_IN_BYTES[file][self.MAX]
            except KeyError:
                pass
            file_sizes_list.append(
                FileSize(actualSize=file_size, minSize=min_size, maxSize=max_size, filename=file))
        self.data_test.log_info(f"Successfully got {len(file_sizes_list)} file sizes")
        return file_sizes_list

    def get_out_of_spec_file_sizes(self):
        all_file_sizes = self.get_file_sizes()
        return [x for x in all_file_sizes if
                x["minSize"] is not None and x["maxSize"] is not None and not x["minSize"] <= x[
                    "actualSize"] <= x["maxSize"]]

    def get_infotexte(self, language: Language):
        list_of_infotexte = []
        info_text_file_name = self.INFOTEXT_PREFIX + language.value
        with open(os.path.join(self.temporary_file_path, info_text_file_name), "r",
                  encoding="utf-8") as file:
            for line in file:
                nummer = int(line[:9])
                text = line[10:].rstrip()
                list_of_infotexte.append(InfoText(text=text, nummer=nummer))
        self.data_test.log_info(
            f"Successfully parsed {len(list_of_infotexte)} infotexte ({language.value}) from {info_text_file_name}")
        return list_of_infotexte

    def get_eckdaten(self):
        with open(os.path.join(self.temporary_file_path, self.ECKDATEN_FILE_NAME), "r",
                  encoding="utf-8") as file:
            lines = file.readlines()
            fahrplan_start = datetime.datetime.strptime(lines[0].strip(), "%d.%m.%Y")
            fahrplan_end = datetime.datetime.strptime(lines[1].strip(), "%d.%m.%Y")
            fahrplan_bezeichnung = lines[2].strip()
        self.data_test.log_info(
            f"Successfully parsed eckdaten ({fahrplan_bezeichnung}) from {self.ECKDATEN_FILE_NAME}")
        return Eckdaten(fahrplanStart=fahrplan_start, fahrplanEnd=fahrplan_end,
                        fahrplanBezeichnung=fahrplan_bezeichnung)

    def test_file_encodings(self):
        list_of_present_files = os.listdir(self.temporary_file_path)
        for file in list_of_present_files:
            opended_file = open(os.path.join(self.temporary_file_path, file), "r", encoding="utf-8")
            try:
                if has_bom(opended_file.read().encode(encoding="utf-8")) == "BOM":
                    self.data_test.log_warning(
                        f"File {file} has BOM, this may lead to unexpected behaviour")
            except UnicodeDecodeError as e:
                self.data_test.log_warning(
                    f"File {file} could not be read with utf-8 encoding, further checks will fail if file is used in checks")
            finally:
                opended_file.close()
        self.data_test.log_info(f"Successfully tested all file encodings")

    def get_zugart(self) -> List[Zugart]:
        zugart_entries_list = []
        with open(os.path.join(self.temporary_file_path, self.ZUGART_FILE_NAME), "r",
                  encoding="utf-8") as file:

            current_zugart = None

            for line in file:
                # Infozeilen
                if line[:2] == "*I":
                    text_code = line[3:5]
                    info_text_nummer = int(line[8:15])
                    current_zugart['iZeilen'].append(
                        IZeile(textCode=text_code, textNummber=info_text_nummer))
                # Start of second part of file, not parsed
                elif line[:6] == "<text>":
                    break
                else:
                    gattungscode = line[0:3]
                    produktklasse = int(line[4:6])
                    tarifgruppe = none_if_empty_or_value(line[7:8], str)
                    ausgabensteuerung = int(line[9:11])
                    gattungsbezeichnung = line[12:20]
                    zuschlag = int(line[21:22])
                    flags = none_if_empty_or_value(line[23:24], str)
                    current_zugart = Zugart(gattungscode=gattungscode,
                                            gattungsbezeichnung=gattungsbezeichnung,
                                            tarifgruppe=tarifgruppe, produktklasse=produktklasse,
                                            ausgabesteuerung=ausgabensteuerung, zuschlag=zuschlag,
                                            flags=flags, iZeilen=[])
                    zugart_entries_list.append(current_zugart)
        self.data_test.log_info(
            f"Succesfully parsed {len(zugart_entries_list)} Zugart from {self.ZUGART_FILE_NAME}")
        return zugart_entries_list

    def close(self, delete_hrdf_file: bool = True) -> None:
        if delete_hrdf_file:
            os.remove(self.hrdf_file_path)
            self.data_test.log_info(f"Removed hrdf file {self.hrdf_file_path}")
        shutil.rmtree(self.temporary_file_path)
        self.data_test.log_info(
            f"Closed HRDF parser and remove temporary folder {self.temporary_file_path}")
