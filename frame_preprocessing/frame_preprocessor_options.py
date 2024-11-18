import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class FramePreprocessorOptions:
    """
    Struct that contains the options for the frame preprocessor.
    """
    output_dir: pathlib.Path
    timezone: str
    input_dirs: list[pathlib.Path]
    worker_thread_count: int
    latitude: float | None
    longitude: float | None
    ignore_daylight_savings_switch: bool
    fade_seconds: int
    night_margin_seconds: int
