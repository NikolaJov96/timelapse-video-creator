import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class FramePreprocessorOptions:
    """
    """
    output_dir: pathlib.Path
    input_dirs: list[pathlib.Path]
    worker_thread_count: int
    latitude: float | None
    longitude: float | None
