from dataclasses import dataclass
from datetime import datetime

import exifread
from exifread.exceptions import ExifNotFound


@dataclass(frozen=True)
class ExifData:
    """
    Struct that contains the EXIF data found in an image.
    Allows None values for missing data.
    """
    timestamp_s: int | None
    latitude: float | None
    longitude: float | None


class ExifReader:
    """
    Class that reads EXIF data from an image.
    """
    DATE_TIME_TAG = 'DateTimeOriginal'
    GPS_LAT_TAG = 'GPS GPSLatitude'
    GPS_LAT_REF_TAG = 'GPS GPSLatitudeRef'
    GPS_LON_TAG = 'GPS GPSLongitude'
    GPS_LON_REF_TAG = 'GPS GPSLongitudeRef'
    GPS_ALT_TAG = 'GPS GPSAltitude'

    @staticmethod
    def read_exif_data(image_path: str) -> ExifData:
        """
        Read EXIF data from an image.
        """
        with open(image_path, 'rb') as image_file:
            try:
                exif_data = exifread.process_file(image_file, details=False)
            except ExifNotFound:
                exif_data = {}

        timestamp_s: int | None = None
        corresponding_tags = [tag for tag in exif_data.keys() if ExifReader.DATE_TIME_TAG in tag]
        if len(corresponding_tags) > 0:
            date_time_tag = corresponding_tags[0]
            date_time_original = exif_data[date_time_tag].values
            date_time = datetime.strptime(date_time_original, '%Y:%m:%d %H:%M:%S')
            timestamp_s = int(date_time.timestamp())

        latitude, longitude = ExifReader.__parse_gps_data(exif_data)

        return ExifData(
            timestamp_s=timestamp_s,
            latitude=latitude,
            longitude=longitude)

    @staticmethod
    def __parse_gps_data(exif_data: dict) -> tuple[float | None, float | None]:
        """
        Parses GPS data from the EXIF data dictionary and returns latitude and longitude.
        """
        latitude: float | None = None
        if ExifReader.GPS_LAT_TAG in exif_data and ExifReader.GPS_LAT_REF_TAG in exif_data:
            latitude = ExifReader.__parse_coordinate(exif_data, ExifReader.GPS_LAT_TAG, ExifReader.GPS_LAT_REF_TAG)

        longitude: tuple[float, float, float] | None = None
        if ExifReader.GPS_LON_TAG in exif_data and ExifReader.GPS_LON_REF_TAG in exif_data:
            longitude = ExifReader.__parse_coordinate(exif_data, ExifReader.GPS_LON_TAG, ExifReader.GPS_LON_REF_TAG)

        return latitude, longitude

    @staticmethod
    def __parse_coordinate(exif_data: dict, coordinate_tag: str, ref_tag: str) -> float:
        """
        Parses a GPS coordinate from the EXIF data dictionary.
        """
        coordinate_values = exif_data[coordinate_tag].values
        assert isinstance(coordinate_values, list), 'GPS coordinate is not a list'
        assert len(coordinate_values) == 3, 'GPS coordinate does not have 3 values'
        gps_coordinate = (float(coordinate_values[0]), float(coordinate_values[1]), float(coordinate_values[2]))
        gps_coordinate_ref = exif_data[ref_tag].values
        return ExifReader.__convert_coordinate(gps_coordinate, gps_coordinate_ref)

    @staticmethod
    def __convert_coordinate(coordinates: tuple[float, float, float], ref: str) -> float:
        """
        Converts GPS coordinates from degrees, minutes, seconds to decimal.
        """
        degrees, minutes, seconds = coordinates
        sign = 1 if ref in ['N', 'E'] else -1
        return sign * (float(degrees) + float(minutes) / 60 + float(seconds) / 3600)
