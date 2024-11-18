import pathlib
from concurrent import futures

import pytz
from exif_reader import ExifReader
from tqdm import tqdm

from frame_preprocessing.datetime_utils import DatetimeUtils
from frame_preprocessing.frame_preprocessor_options import FramePreprocessorOptions
from frame_preprocessing.image_data import ImageData
from frame_preprocessing.single_frame_processor import SingleFrameProcessor


class FramePreprocessor:
    """
    The main class that preprocesses frames.

    It manages the whole process from aggregating the input data and
    loading image data to running the parallel image processing.
    """

    def __init__(self, options: FramePreprocessorOptions) -> None:
        self.__options = options
        self.__check_options()

    def preprocess_frames(self):
        """
        Executes the end-to-end frame preprocessing process.
        """
        self.__check_directories()

        image_paths = self.__get_image_paths()
        images_data = self.__get_images_data(image_paths)

        sorted_image_paths = sorted(image_paths, key=lambda x: images_data[x].timestamp_s)
        image_ids = {image_path: i for i, image_path in enumerate(sorted_image_paths)}

        self.__run_parallel_image_processing(sorted_image_paths, image_ids, images_data)

    def __check_options(self):
        """
        Checks the validity of the received options and raises an exception if they are invalid.
        """
        assert len(self.__options.input_dirs) > 0, 'No input directories provided'
        assert len(self.__options.input_dirs) == len(set(self.__options.input_dirs)), 'Duplicate input directories'

        assert self.__options.timezone in pytz.all_timezones, f'Invalid timezone {self.__options.timezone}'
        if self.__options.latitude is not None:
            assert -90 <= self.__options.latitude <= 90, f'Latitude {self.__options.latitude} out of range [-90, 90]'
        if self.__options.longitude is not None:
            assert -180 <= self.__options.longitude <= 180, f'Longitude {self.__options.longitude} out of range [-180, 180]'
        if self.__options.resize_to_width is not None:
            assert 0 < self.__options.resize_to_width <= 10000, f'Resize width {self.__options.resize_to_width} unsupported'

        assert 0 <= self.__options.fade_seconds <= 14400, f'Fade seconds {self.__options.fade_seconds} out of range [0, 14400]'
        assert 0 <= self.__options.night_margin_seconds <= 14400, \
            f'Night margin seconds {self.__options.night_margin_seconds} out of range [0, 14400]'

        assert self.__options.worker_thread_count > 0, f'Invalid worker thread count {self.__options.worker_thread_count}'

    def __check_directories(self):
        """
        Checks the validity of the input and output directories and raises an exception if they are invalid.
        """
        assert not self.__options.output_dir.exists(), f'Output directory {self.__options.output_dir} already exists'

        for input_dir in self.__options.input_dirs:
            assert input_dir.is_dir(), f'Input directory {input_dir} does not exist'

    def __get_image_paths(self) -> list[pathlib.Path]:
        """
        Returns a list of image paths found in the input directories.
        """
        image_paths: list[pathlib.Path] = []
        for input_dir in self.__options.input_dirs:
            image_paths.extend(
                f for f in input_dir.glob('./**/*.*')
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
            )

        assert len(image_paths) > 0, 'No images found in input directories'
        return image_paths

    def __get_images_data(self, image_paths: list[pathlib.Path]) -> dict[pathlib.Path, ImageData]:
        """
        Returns a dictionary of image data objects for each image path.
        Checks the image data validity along the way.
        """
        images_data: dict[pathlib.Path, ImageData] = {}
        for image_path in tqdm(image_paths, desc='Reading image data'):
            exif_data = ExifReader.read_exif_data(image_path)
            assert exif_data.timestamp_s is not None, f'No timestamp found for {image_path}'
            assert exif_data.latitude is not None or self.__options.latitude is not None, f'No latitude found for {image_path}'
            assert exif_data.longitude is not None or self.__options.longitude is not None, f'No longitude found for {image_path}'
            images_data[image_path] = ImageData(
                timestamp_s=exif_data.timestamp_s,
                latitude=exif_data.latitude if exif_data.latitude is not None else self.__options.latitude,
                longitude=exif_data.longitude if exif_data.longitude is not None else self.__options.longitude)

        return images_data

    def __run_parallel_image_processing(
            self,
            sorted_image_paths: list[pathlib.Path],
            image_ids: dict[pathlib.Path, int],
            images_data: dict[pathlib.Path, ImageData]) -> None:
        """
        Runs the parallel image processing on the aggregated images.
        """
        is_first_frame_in_daylight_savings = DatetimeUtils.is_in_daylight_savings(
            images_data[sorted_image_paths[0]].timestamp_s,
            self.__options.timezone)
        single_frame_processor = SingleFrameProcessor(self.__options, is_first_frame_in_daylight_savings)

        with futures.ThreadPoolExecutor(max_workers=self.__options.worker_thread_count) as executor:
            futures_list = [
                executor.submit(
                    single_frame_processor.process_frame,
                    image_path,
                    image_ids[image_path],
                    images_data[image_path])
                for image_path in sorted_image_paths
            ]
            for future in tqdm(futures.as_completed(futures_list), total=len(futures_list), desc='Processing images'):
                future.result()
