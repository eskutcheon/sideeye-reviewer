from dataclasses import dataclass, field, asdict
import os
from typing import Union


# TODO: greatly simplify all of this to easily allow users to make new basic data config files

@dataclass(frozen=True)
class GTLabels:
    """GTLabels class for storing the ground truth labels for the dataset.
    one hot encoding labels for the image mask, 0 to 3 divided by 255"""
    clean: float = 0
    transparent: float = 0.00392157
    semi_transparent: float = 0.00784314
    opaque: float = 0.01176471

@dataclass(frozen=True)
class CamLabels:
    """CamLabels class for storing the camera angle labels for the dataset."""
    FV: str = "Front Cam"
    RV: str = "Rear Cam"
    MVL: str = "Mirror Left Cam"
    MVR: str = "Mirror Right Cam"

@dataclass(frozen=True)
class ClassList:
    """ClassList class for storing the class list for the dataset."""
    clean: str = "clean"
    transparent: str = "transparent"
    semi_transparent: str = "semi-transparent"
    opaque: str = "opaque"

@dataclass(frozen=True)
class ClassDistribution:
    clean: float = 0.37369436584472654
    transparent: float = 0.12236318237304687
    semi_transparent: float = 0.20401020568847655
    opaque: float = 0.29993224609375

#NOTE: Color labels and color int labels may be able to be merged,
# need to check in code where both are called.
@dataclass(frozen=True)
class ColorLabels:
    """ColorLabels class for storing the color labels for the dataset."""
    clean: tuple = (0,0,0) # black
    transparent: tuple = (0,255,0) # green
    semi_transparent: tuple = (0,0,255) # blue
    opaque: tuple = (255,0,0) # red

@dataclass(frozen=True)
class ColorIntLabels:
    clean: int = 0
    transparent: int = 1
    semi_transparent: int = 2
    opaque: int = 3

@dataclass(frozen=True)
class DataSet:
    # URL for the dataset
    DATA_SOURCE = "https://drive.google.com/uc?export=download&id=1Id-K7SjwCqWkLwtIGJUj5Q0Dw0E_TP_9"
    CLASS_LIST: ClassList = ClassList()
    CAM_LABELS: CamLabels = CamLabels()
    COLOR_LABELS: ColorLabels = ColorLabels()
    COLOR_INT_LABELS: ColorIntLabels = ColorIntLabels()
    GT_LABELS: GTLabels = GTLabels()
    CLASS_DISTRIBUTION: ClassDistribution = ClassDistribution()


@dataclass(frozen=True)
class ClassDistribution:
    clean: float = 0.37369436584472654
    transparent: float = 0.12236318237304687
    semi_transparent: float = 0.20401020568847655
    opaque: float = 0.29993224609375