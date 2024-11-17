from dataclasses import dataclass
from datetime import datetime

import exifread
from exifread.exceptions import ExifNotFound


@dataclass(frozen=True)
class ExifData:
    """
    """
    timestamp_s: int | None
    latitude: float | None
    longitude: float | None


class ExifReader:
    """
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
        """
        latitude: float | None = None
        if ExifReader.GPS_LAT_TAG in exif_data and ExifReader.GPS_LAT_REF_TAG in exif_data:
            latitude_values = exif_data[ExifReader.GPS_LAT_TAG].values
            assert isinstance(latitude_values, list), 'Latitude is not a list'
            assert len(latitude_values) == 3, 'Latitude does not have 3 values'
            gps_latitude = (float(latitude_values[0]), float(latitude_values[1]), float(latitude_values[2]))
            gps_latitude_ref = exif_data[ExifReader.GPS_LAT_REF_TAG].values
            latitude = ExifReader.__parse_coordinate(gps_latitude, gps_latitude_ref)

        longitude: tuple[float, float, float] | None = None
        if ExifReader.GPS_LON_TAG in exif_data and ExifReader.GPS_LON_REF_TAG in exif_data:
            longitude_values = exif_data[ExifReader.GPS_LON_TAG].values
            assert isinstance(longitude_values, list), 'Longitude is not a list'
            assert len(longitude_values) == 3, 'Longitude does not have 3 values'
            gps_longitude = (float(longitude_values[0]), float(longitude_values[1]), float(longitude_values[2]))
            gps_longitude_ref = exif_data[ExifReader.GPS_LON_REF_TAG].values
            longitude = ExifReader.__parse_coordinate(gps_longitude, gps_longitude_ref)

        return latitude, longitude

    @staticmethod
    def __parse_coordinate(coordinates: tuple[float, float, float], ref: str) -> float:
        """
        Parse a coordinate from a string.
        """
        degrees, minutes, seconds = coordinates
        sign = 1 if ref in ['N', 'E'] else -1
        return sign * (float(degrees) + float(minutes) / 60 + float(seconds) / 3600)
