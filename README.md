# Multi-day Timelapse Video Editor

TODO:
- Add day count to frames
- Write README

## Frame preprocessing:

``` bash
python3 preprocess_frames.py /processed/frames/dir Europe/Belgrade /input/images/dir_1 /input/images/dir_2 --latitude 44.787197 --longitude 20.457273 --resize_to_width 1920 --fade_seconds 1800 --night_margin_seconds 3600 --ignore_daylight_savings_switch --worker_thread_count 20
```

## Video creation

``` bash
python3 create_video.py /processed/frames/dir /output/video/video.mp4
```
