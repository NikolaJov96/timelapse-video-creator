import pathlib
import shutil
from datetime import date, datetime

import cv2
from suntimes import SunTimes

from frame_preprocessing.datetime_utils import DatetimeUtils
from frame_preprocessing.frame_preprocessor_options import FramePreprocessorOptions
from frame_preprocessing.image_data import ImageData


class SingleFrameProcessor:
    """
    The class that handles the low-level logic of processing a single frame.
    """
    MAX_IMAGES_PER_FOLDER = 500

    def __init__(
            self,
            options: FramePreprocessorOptions,
            is_first_frame_in_daylight_savings: bool) -> None:
        self.__options = options
        self.__is_first_frame_in_daylight_savings = is_first_frame_in_daylight_savings

    def process_frame(
            self,
            image_path: pathlib.Path,
            image_id: int,
            image_data: ImageData) -> None:
        """
        Executes the processing of a single frame and saves the output image.
        """
        adjusted_timestamp_s = self.__get_daylight_savings_adjusted_timestamp(image_data.timestamp_s)
        sunrise, sunset = self.__get_sunrise_sunset(
            adjusted_timestamp_s, self.__options.latitude, self.__options.longitude)

        # The times of the earliest and the latest frame for the current day
        earliest_frame_timestamp_s = sunrise.timestamp() - self.__options.night_margin_seconds
        latest_frame_timestamp_s = sunset.timestamp() + self.__options.night_margin_seconds

        # How close the current frame is to the earliest and the latest frame in seconds
        seconds_since_earliest_frame = adjusted_timestamp_s - earliest_frame_timestamp_s
        seconds_until_latest_frame = latest_frame_timestamp_s - adjusted_timestamp_s

        # If the current frame is outside the range of the earliest and the latest frame, skip it
        if seconds_since_earliest_frame < 0 or seconds_until_latest_frame < 0:
            return

        # Check if the current frame is in the fade range of the earliest or the latest frame
        close_to_earliest_frame = 0 <= seconds_since_earliest_frame <= self.__options.fade_seconds
        close_to_latest_frame = 0 <= seconds_until_latest_frame <= self.__options.fade_seconds

        # Get output image path and create the parent directories if needed
        new_image_path = self.__generate_output_image_path(
            image_id, adjusted_timestamp_s, sunrise, sunset, image_data.timestamp_s)
        new_image_path.parent.mkdir(parents=True, exist_ok=True)

        if close_to_earliest_frame or close_to_latest_frame:
            # The frame is close to the earliest or the latest frame, apply the fade effect
            if close_to_earliest_frame:
                progress = seconds_since_earliest_frame / self.__options.fade_seconds
            else:
                progress = seconds_until_latest_frame / self.__options.fade_seconds
            assert 0 <= progress <= 1, f'Invalid progress value {progress}'

            image = cv2.imread(str(image_path))
            image = (image * progress).astype('uint8')
            cv2.imwrite(str(new_image_path), image)
        else:
            # The frame is not close to the earliest or the latest frame, just copy it
            shutil.copy(image_path, new_image_path)

    def __get_daylight_savings_adjusted_timestamp(self, timestamp_s: int) -> int:
        """
        Daylight savings time may switch during the time-lapse and the camera may not
        adjust for it. This method adjusts the timestamp to account for the daylight
        savings switch if the option is enabled.
        """
        adjusted_timestamp_s = timestamp_s
        if self.__options.ignore_daylight_savings_switch:
            is_frame_in_daylight_savings = DatetimeUtils.is_in_daylight_savings(
                adjusted_timestamp_s, self.__options.timezone)
            if self.__is_first_frame_in_daylight_savings and not is_frame_in_daylight_savings:
                adjusted_timestamp_s -= 60 * 60
            elif not self.__is_first_frame_in_daylight_savings and is_frame_in_daylight_savings:
                adjusted_timestamp_s += 60 * 60

        return adjusted_timestamp_s

    def __get_sunrise_sunset(self, timestamp_s: int, latitude: float, longitude: float) -> tuple[datetime, datetime]:
        """
        Get the sunrise and sunset datetime objects for the day of the given
        timestamp and the given timelapse geo-location.
        """
        sun = SunTimes(longitude=longitude, latitude=latitude, altitude=0)
        sunrise = sun.risewhere(date.fromtimestamp(timestamp_s), self.__options.timezone)
        sunset = sun.setwhere(date.fromtimestamp(timestamp_s), self.__options.timezone)

        return sunrise, sunset

    def __generate_output_image_path(
            self,
            image_id: int,
            frame_timestamp_s: int,
            sunrise: datetime,
            sunset: datetime,
            non_adjusted_timestamp_s: int) -> pathlib.Path:
        """
        Generate the path for the output image file based on the given parameters.

        Adds the following suffixes to the image name for easier troubleshooting:
        - _b if the frame is before sunrise
        - _a if the frame is after sunset
        - _d if the frame has a different daylight savings status than the first frame
        """
        image_id_str = f'{image_id:010d}'
        image_time_str = datetime.fromtimestamp(frame_timestamp_s).strftime('%Y_%m_%d_%H_%M_%S')
        before_sunrise_flag = '_b' if self.__is_before_sunrise(frame_timestamp_s, sunrise) else ''
        after_sunset_flag = '_a' if self.__is_after_sunset(frame_timestamp_s, sunset) else ''
        daylight_savings_flag = '_d' if frame_timestamp_s != non_adjusted_timestamp_s else ''

        new_image_name = (
            f'{image_id_str}_{image_time_str}'
            f'{before_sunrise_flag}{after_sunset_flag}{daylight_savings_flag}.jpg'
        )
        # Create subfolders with up to 500 images each to avoid having too many files in one directory
        subfolder_path = self.__options.output_dir / f'{image_id // self.MAX_IMAGES_PER_FOLDER:03d}'

        return subfolder_path / new_image_name

    def __is_before_sunrise(self, timestamp_s: int, sunrise: datetime) -> bool:
        """
        Check if the given timestamp is before the sunrise.
        """
        return timestamp_s - sunrise.timestamp() < 0

    def __is_after_sunset(self, timestamp_s: int, sunset: datetime) -> bool:
        """
        Check if the given timestamp is after the sunset.
        """
        return sunset.timestamp() - timestamp_s < 0
