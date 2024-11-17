import pathlib
import shutil
from concurrent import futures
from dataclasses import dataclass
from datetime import date, datetime

import cv2
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

    def preprocess_frames(self):
        """
        """
        assert not self.__options.output_dir.exists(), f'Output directory {self.__options.output_dir} already exists'
        assert len(self.__options.input_dirs) > 0, 'No input directories provided'
        for input_dir in self.__options.input_dirs:
            assert input_dir.is_dir(), f'Input directory {input_dir} does not exist'
        assert len(self.__options.input_dirs) == len(set(self.__options.input_dirs)), 'Duplicate input directories'

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

    def __process_image(
            self,
            image_path: pathlib.Path,
            image_id: int,
            image_data: ImageData) -> None:
        """
        """
        fade_out_seconds = 30 * 60

        sun = SunTimes(
            longitude=image_data.longitude,
            latitude=image_data.latitude,
            altitude=0)
        sun_rise = sun.risewhere(date.fromtimestamp(image_data.timestamp_s), 'Europe/Belgrade')
        sun_set = sun.setwhere(date.fromtimestamp(image_data.timestamp_s), 'Europe/Belgrade')

        seconds_since_sunrise = image_data.timestamp_s - sun_rise.timestamp()
        seconds_until_sunset = sun_set.timestamp() - image_data.timestamp_s

        is_before_sunrise = seconds_since_sunrise < 0
        is_after_sunset = seconds_until_sunset < 0

        close_to_sunrise = abs(seconds_since_sunrise) < fade_out_seconds and is_before_sunrise
        close_to_sunset = abs(seconds_until_sunset) < fade_out_seconds and is_after_sunset

        if (is_before_sunrise or is_after_sunset) and not (close_to_sunrise or close_to_sunset):
            return

        image_id_str = f'{image_id:010d}'
        image_time_str = datetime.fromtimestamp(image_data.timestamp_s).strftime('%Y_%m_%d_%H_%M_%S')
        night_flag = ''
        if is_before_sunrise:
            night_flag = '_b'
        elif is_after_sunset:
            night_flag = '_a'
        new_image_name = f'{image_id_str}_{image_time_str}{night_flag}.jpg'
        subfolder_name = f'{image_id // self.MAX_IMAGES_PER_FOLDER:03d}'
        new_image_path = self.__options.output_dir / subfolder_name / new_image_name

        if close_to_sunrise or close_to_sunset:
            if close_to_sunrise:
                progress = 1 - abs(seconds_since_sunrise) / fade_out_seconds
            else:
                progress = 1 - abs(seconds_until_sunset) / fade_out_seconds
            assert 0 <= progress <= 1, f'Invalid progress value {progress}'

            image = cv2.imread(str(image_path))
            image = (image * progress).astype('uint8')
            self.__options.output_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(new_image_path), image)
        else:
            self.__options.output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(image_path, new_image_path)
