from dataclasses import dataclass


@dataclass(frozen=True)
class ImageData:
    """
    """
    timestamp_s: int
    latitude: float
    longitude: float
