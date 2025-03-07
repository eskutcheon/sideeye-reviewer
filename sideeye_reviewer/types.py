from typing import NewType, List, Dict, Any, Union, Callable, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    # matplotlib objects
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from matplotlib.image import AxesImage
    from matplotlib.animation import FuncAnimation
    # local imports
    from sideeye_reviewer.views.base_viewer import BaseReviewerView
    from sideeye_reviewer.views.unilabel_reviewer import SingleLabelReviewerView
    from sideeye_reviewer.views.multilabel_reviewer import MultiLabelReviewerView
    from sideeye_reviewer.views.slides_viewer import SlideshowViewerView
    from sideeye_reviewer.views.reviewer_button import ReviewerButton
    from sideeye_reviewer.models.data_manager import DataManager
    from sideeye_reviewer.models.sorter import BinManager
    from sideeye_reviewer.models.sorter import ImageSorter
    from sideeye_reviewer.controllers.review_controller import ReviewerController
    from sideeye_reviewer.controllers.base_controller import BaseReviewController
    from sideeye_reviewer.controllers.slides_controller import SlideshowController


# Custom types
ViewerLike = Union["BaseReviewerView", "SingleLabelReviewerView", "MultiLabelReviewerView", "SlideshowViewerView"]
DataManagerType = NewType("DataManagerType", "DataManager")
BinManagerType = NewType("BinManagerType", "BinManager")
ImageSorterType = NewType("ImageSorterType", "ImageSorter")
# TODO: might make this "ControllerLike" if I add another controller for the basic slideshow viewer
ControllerLike = Union["BaseReviewController", "ReviewerController", "SlideshowController"]
ReviewerButtonType = NewType("ReviewerButtonType", "ReviewerButton")



__all__ = [
    ViewerLike,
    DataManagerType,
    BinManagerType,
    ImageSorterType,
    ControllerLike,
    ReviewerButtonType,
]