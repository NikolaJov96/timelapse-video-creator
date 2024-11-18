import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class FramePreprocessorOptions:
    """
    Struct that contains the options for the frame preprocessor.
    """
    # Paths
    output_dir: pathlib.Path
    input_dirs: list[pathlib.Path]

    # Video metadata
    timezone: str
    latitude: float | None
    longitude: float | None
    resize_to_width: int | None

    # Fading options
    fade_seconds: int
    night_margin_seconds: int

    # Other options
    ignore_daylight_savings_switch: bool
    render_date_and_time: bool

    # Execution options
    worker_thread_count: int
