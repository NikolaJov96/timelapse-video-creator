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
        """
        frame_timestamp_s = image_data.timestamp_s
        if self.__options.ignore_daylight_savings_switch:
            is_frame_in_daylight_savings = DatetimeUtils.is_in_daylight_savings(
                frame_timestamp_s, self.__options.timezone)
            if self.__is_first_frame_in_daylight_savings and not is_frame_in_daylight_savings:
                frame_timestamp_s -= 60 * 60
            elif not self.__is_first_frame_in_daylight_savings and is_frame_in_daylight_savings:
                frame_timestamp_s += 60 * 60

        sun = SunTimes(
            longitude=image_data.longitude,
            latitude=image_data.latitude,
            altitude=0)
        sun_rise = sun.risewhere(date.fromtimestamp(frame_timestamp_s), self.__options.timezone)
        sun_set = sun.setwhere(date.fromtimestamp(frame_timestamp_s), self.__options.timezone)

        earliest_frame_timestamp_s = sun_rise.timestamp() - self.__options.night_margin_seconds
        latest_frame_timestamp_s = sun_set.timestamp() + self.__options.night_margin_seconds

        seconds_since_earliest_frame = frame_timestamp_s - earliest_frame_timestamp_s
        seconds_until_latest_frame = latest_frame_timestamp_s - frame_timestamp_s

        if seconds_since_earliest_frame < 0 or seconds_until_latest_frame < 0:
            return

        close_to_earliest_frame = 0 <= seconds_since_earliest_frame <= self.__options.fade_seconds
        close_to_latest_frame = 0 <= seconds_until_latest_frame <= self.__options.fade_seconds

        image_id_str = f'{image_id:010d}'
        image_time_str = datetime.fromtimestamp(frame_timestamp_s).strftime('%Y_%m_%d_%H_%M_%S')
        night_flag = self.__get_night_flag(frame_timestamp_s, sun_rise, sun_set)
        daylight_savings_flag = '_d' if frame_timestamp_s != image_data.timestamp_s else ''
        new_image_name = f'{image_id_str}_{image_time_str}{night_flag}{daylight_savings_flag}.jpg'
        subfolder_path = self.__options.output_dir / f'{image_id // self.MAX_IMAGES_PER_FOLDER:03d}'
        new_image_path = subfolder_path / new_image_name

        if close_to_earliest_frame or close_to_latest_frame:
            if close_to_earliest_frame:
                progress = seconds_since_earliest_frame / self.__options.fade_seconds
            else:
                progress = seconds_until_latest_frame / self.__options.fade_seconds
            assert 0 <= progress <= 1, f'Invalid progress value {progress}'

            image = cv2.imread(str(image_path))
            image = (image * progress).astype('uint8')
            subfolder_path.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(new_image_path), image)
        else:
            subfolder_path.mkdir(parents=True, exist_ok=True)
            shutil.copy(image_path, new_image_path)

    def __get_night_flag(self, timestamp_s: int, sun_rise: datetime, sun_set: datetime) -> str:
        """
        """
        seconds_since_sunrise = timestamp_s - sun_rise.timestamp()
        seconds_until_sunset = sun_set.timestamp() - timestamp_s

        is_before_sunrise = seconds_since_sunrise < 0
        is_after_sunset = seconds_until_sunset < 0

        if is_before_sunrise:
            return '_b'
        elif is_after_sunset:
            return '_a'
        else:
            return ''
