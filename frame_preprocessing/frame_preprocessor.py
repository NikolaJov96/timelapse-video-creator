import pathlib
import shutil
from concurrent import futures
from dataclasses import dataclass
from datetime import date, datetime

import cv2
import pytz
from exif_reader import ExifReader
from suntimes import SunTimes
from tqdm import tqdm

from frame_preprocessing.frame_preprocessor_options import FramePreprocessorOptions


@dataclass(frozen=True)
class ImageData:
    timestamp_s: int
    latitude: float
    longitude: float


class FramePreprocessor:
    """
    """
    MAX_IMAGES_PER_FOLDER = 500

    def __init__(self, options: FramePreprocessorOptions) -> None:
        self.__options = options

        self.__is_first_frame_in_daylight_savings: bool

    def preprocess_frames(self):
        """
        """
        self.__check_options()

        image_paths: list[pathlib.Path] = []
        for input_dir in self.__options.input_dirs:
            image_paths.extend(
                f for f in input_dir.glob('./**/*.*')
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
            )
        assert len(image_paths) > 0, 'No images found in input directories'

        images_data: dict[pathlib.Path, ImageData] = {}
        for image_path in tqdm(image_paths, desc='Reading image timestamps'):
            exif_data = ExifReader.read_exif_data(image_path)
            assert exif_data.timestamp_s is not None, f'No timestamp found for {image_path}'
            assert exif_data.latitude is not None or self.__options.latitude is not None, f'No latitude found for {image_path}'
            assert exif_data.longitude is not None or self.__options.longitude is not None, f'No longitude found for {image_path}'
            images_data[image_path] = ImageData(
                timestamp_s=exif_data.timestamp_s,
                latitude=exif_data.latitude if exif_data.latitude is not None else self.__options.latitude,
                longitude=exif_data.longitude if exif_data.longitude is not None else self.__options.longitude)

        # Sort images by timestamp
        sorted_image_paths = sorted(image_paths, key=lambda x: images_data[x].timestamp_s)
        # sorted_image_paths = [sorted_image_paths[0]]
        image_ids = {image_path: i for i, image_path in enumerate(sorted_image_paths)}

        self.__is_first_frame_in_daylight_savings = self.__is_daylight_savings(
            images_data[sorted_image_paths[0]].timestamp_s,
            'Europe/Belgrade')

        with futures.ThreadPoolExecutor(max_workers=self.__options.worker_thread_count) as executor:
            futures_list = [
                executor.submit(
                    self.__process_image,
                    image_path,
                    image_ids[image_path],
                    images_data[image_path])
                for image_path in sorted_image_paths
            ]
            for future in tqdm(futures.as_completed(futures_list), total=len(futures_list), desc='Processing images'):
                future.result()

    def __check_options(self):
        """
        """
        assert not self.__options.output_dir.exists(), f'Output directory {self.__options.output_dir} already exists'

        assert len(self.__options.input_dirs) > 0, 'No input directories provided'
        for input_dir in self.__options.input_dirs:
            assert input_dir.is_dir(), f'Input directory {input_dir} does not exist'
        assert len(self.__options.input_dirs) == len(set(self.__options.input_dirs)), 'Duplicate input directories'

        assert self.__options.worker_thread_count > 0, f'Invalid worker thread count {self.__options.worker_thread_count}'

        if self.__options.latitude is not None:
            assert -90 <= self.__options.latitude <= 90, f'Latitude {self.__options.latitude} out of range [-90, 90]'

        if self.__options.longitude is not None:
            assert -180 <= self.__options.longitude <= 180, f'Longitude {self.__options.longitude} out of range [-180, 180]'

    def __is_daylight_savings(self, timestamp_s: int, timezone: str) -> bool:
        """
        """
        timezone = pytz.timezone(timezone)
        date_time = datetime.fromtimestamp(timestamp_s)
        try:
            timezone_aware_date = timezone.localize(date_time, is_dst=None)
            return timezone_aware_date.tzinfo._dst.seconds != 0
        except pytz.exceptions.AmbiguousTimeError:
            # This happens in the exact hour when daylight savings switch occurs
            # We will consider these frames as not in daylight savings
            return False

    def __process_image(
            self,
            image_path: pathlib.Path,
            image_id: int,
            image_data: ImageData) -> None:
        """
        """
        fade_seconds = 30 * 60
        night_margin_seconds = 60 * 60

        frame_timestamp_s = image_data.timestamp_s
        if self.__options.ignore_daylight_savings_switch:
            is_frame_in_daylight_savings = self.__is_daylight_savings(frame_timestamp_s, 'Europe/Belgrade')
            if self.__is_first_frame_in_daylight_savings and not is_frame_in_daylight_savings:
                frame_timestamp_s -= 60 * 60
            elif not self.__is_first_frame_in_daylight_savings and is_frame_in_daylight_savings:
                frame_timestamp_s += 60 * 60

        sun = SunTimes(
            longitude=image_data.longitude,
            latitude=image_data.latitude,
            altitude=0)
        sun_rise = sun.risewhere(date.fromtimestamp(frame_timestamp_s), 'Europe/Belgrade')
        sun_set = sun.setwhere(date.fromtimestamp(frame_timestamp_s), 'Europe/Belgrade')

        earliest_frame_timestamp_s = sun_rise.timestamp() - night_margin_seconds
        latest_frame_timestamp_s = sun_set.timestamp() + night_margin_seconds

        seconds_since_earliest_frame = frame_timestamp_s - earliest_frame_timestamp_s
        seconds_until_latest_frame = latest_frame_timestamp_s - frame_timestamp_s

        if seconds_since_earliest_frame < 0 or seconds_until_latest_frame < 0:
            return

        close_to_earliest_frame = 0 <= seconds_since_earliest_frame <= fade_seconds
        close_to_latest_frame = 0 <= seconds_until_latest_frame <= fade_seconds

        image_id_str = f'{image_id:010d}'
        image_time_str = datetime.fromtimestamp(frame_timestamp_s).strftime('%Y_%m_%d_%H_%M_%S')
        night_flag = self.__get_night_flag(frame_timestamp_s, sun_rise, sun_set)
        daylight_savings_flag = '_d' if frame_timestamp_s != image_data.timestamp_s else ''
        new_image_name = f'{image_id_str}_{image_time_str}{night_flag}{daylight_savings_flag}.jpg'
        subfolder_path = self.__options.output_dir / f'{image_id // self.MAX_IMAGES_PER_FOLDER:03d}'
        new_image_path = subfolder_path / new_image_name

        if close_to_earliest_frame or close_to_latest_frame:
            if close_to_earliest_frame:
                progress = seconds_since_earliest_frame / fade_seconds
            else:
                progress = seconds_until_latest_frame / fade_seconds
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
