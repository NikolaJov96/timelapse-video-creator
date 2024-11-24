# Multi-day Timelapse Video Editor

A tool for the selection and preprocessing of timelapse images and the creation of a timelapse video. Designed to automate specific tasks for long, multi-day timelapse videos, where manual processing would be prohibitively time-consuming and result in inconsistent quality.

My motivation for creating this tool was a timelapse I was able to capture, of two pigeons hatching and growing up in a nest on my window. The issue was that there was not enough light at night to capture meaningful images, so I needed to filter out the night frames and create smooth transitions between days. An additional challenge was that the daylight savings time switch happened during the timelapse, which had to be accounted for automatically.

The tool includes two sections:
- Frame preprocessing: selection, preprocessing, and exporting of individual frames, so that they can be visually inspected before creating the video.
- Video creation: creating a timelapse video from the preprocessed frames.

## Frame preprocessing:

The main responsibilities of the frame preprocessing section are:
- Selection of daytime frames based on image timestamps and sunrise/sunset times for the specified GPS location (with some allowed margin for twilight).
- Applying a fade effect to the beginning and end of each day, to create smooth transitions between days.
- Resizing the frames to a specified width.

The reason why daylight savings time switch is a challenge is because (I suspect) the majority of cameras do not automatically adjust the time when the switch happens. This means that the timestamps of the images will be off by an hour, which would in this case result in incorrect sunrise/sunset times. The tool mitigates this by checking whether the first image was taken during daylight savings time and adjusts the timestamps of other images that are taken after the switch. This requires the user to specify the timezone alongside the GPS location.

## Video creation

Runs video creation on the frame preprocessing output directory. It uses FFmpeg to create a video from provided frames, so you will have to install it on your system if you don't have it already. Tested on FFmpeg version 4.4.2.

## Example usage

The following example shows how to install required Python libraries, run frame preprocessing, and create a video from the preprocessed frames.

``` bash
pip install -r requirements.txt

python3 frame_preprocessing/preprocess_frames.py \
 /processed/frames/output/dir \
    Europe/Belgrade \
 /input/images/dir_1 \
    /input/images/dir_2 \
 --latitude 44.787197 \
    --longitude 20.457273 \
 --resize_to_width 1920 \
    --fade_seconds 1800 \
 --night_margin_seconds 3600 \
    --ignore_daylight_savings_switch \
 --render_date_and_time \
    --worker_thread_count 20

python3 video_creation/create_video.py /processed/frames/dir /output/video/video.mp4
```
