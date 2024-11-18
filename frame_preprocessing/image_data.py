from dataclasses import dataclass


@dataclass(frozen=True)
class ImageData:
    """
    Struct that contains the metadata of an image.
    Requires all fields to be present.
    """
    timestamp_s: int
    latitude: float
    longitude: float
