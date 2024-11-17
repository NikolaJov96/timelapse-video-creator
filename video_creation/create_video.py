#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
import pathlib
import subprocess
import tempfile

import argcomplete


def parse_args() -> tuple[pathlib.Path, pathlib.Path]:
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('input_dir', type=pathlib.Path, help='Directory with input images, which may be in subdirectories')
    parser.add_argument('output_vide_path', type=pathlib.Path, help='Path to save the output video')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    return args.input_dir, args.output_vide_path


def main():
    input_dir, output_vide_path = parse_args()
    assert input_dir.is_dir(), f'Input directory {input_dir} does not exist'
    assert not output_vide_path.exists(), f'Output video {output_vide_path} already exists'

    with tempfile.TemporaryDirectory() as temp_dir:
        images_txt_path = pathlib.Path(temp_dir) / 'images.txt'
        extract_images_command = (
            f'find "{input_dir}" -type f -name *.jpg | sort | '
            f'sed "s/^/file \'/; s/$/\'/" > "{images_txt_path}"'
        )
        subprocess.run(extract_images_command, shell=True, check=True)

        assert images_txt_path.exists(), f'Images list file {images_txt_path} not successfully created'
        print(f'Images list file created at {images_txt_path}')

        generate_video_command = (
            f'ffmpeg -f concat -safe 0 -i "{images_txt_path}" -r 30 '
            f'-c:v libx264 -pix_fmt yuv420p "{output_vide_path}"'
        )
        subprocess.run(generate_video_command, shell=True, check=True)


if __name__ == '__main__':
    main()
