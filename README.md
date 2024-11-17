# Multi-day Timelapse Video Editor

TODO:
- Add fade out duration option
- Refactor the frame preprocessor to look cleaner
- Write class and method documentation
- Write README

## Frame preprocessing:

``` bash
python3 preprocess_frames.py /processed/frames/dir Europe/Belgrade /input/images/dir_1 /input/images/dir_2 --worker_thread_count 20 --latitude 44.787197 --longitude 20.457273 --ignore_daylight_savings_switch --fade_seconds 900 --night_margin_seconds 3600
```

## Video creation

``` bash
python3 create_video.py /processed/frames/dir /output/video/video.mp4
```
