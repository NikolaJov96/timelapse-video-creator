#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import pathlib

import argcomplete

from frame_preprocessing.frame_preprocessor import FramePreprocessor
from frame_preprocessing.frame_preprocessor_options import FramePreprocessorOptions


def parse_args() -> FramePreprocessorOptions:
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('output_dir', type=pathlib.Path, help='Directory to save output video frames')
    parser.add_argument('timezone', type=str, help='Timezone of the input images location, as it was set on the camera')
    parser.add_argument('image_dirs', type=pathlib.Path, nargs='+', help='Directories with input images')
    parser.add_argument('--worker_thread_count', type=int, default=20, help='Number of worker threads')
    parser.add_argument('--latitude', type=float, default=None, help='Latitude of the video location, not required if all images have GPS data')  # noqa: E501
    parser.add_argument('--longitude', type=float, default=None, help='Longitude of the video location, not required if all images have GPS')  # noqa: E501
    parser.add_argument('--ignore_daylight_savings_switch', action='store_true', help='Ignore daylight savings switch')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    return FramePreprocessorOptions(
        output_dir=args.output_dir,
        timezone=args.timezone,
        input_dirs=args.image_dirs,
        worker_thread_count=args.worker_thread_count,
        latitude=args.latitude,
        longitude=args.longitude,
        ignore_daylight_savings_switch=args.ignore_daylight_savings_switch)


def main():
    options = parse_args()
    frame_preprocessor = FramePreprocessor(options)
    frame_preprocessor.preprocess_frames()


if __name__ == '__main__':
    main()
