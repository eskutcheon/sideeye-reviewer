import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable, Any
# local imports
from .utils import disable_all_axis_elements, measure_checkbox_labels, compute_button_positions
from .axes_wrappers import AxesData, ButtonAxesData, CheckboxAxesData, SummaryAxesData, LegendAxesData, ImageAxesData, PanelData
from .figure_defaults import ConstFigureDefaults, ConstAxesDefaults, SUPPORTED_PANEL_NAMES


class AxesCreationManager:
    """ Manages the creation and settings of axes in all of the figures subfigures
        meant to be a class member of FigureLayoutManager which calls to it to create and adjust axes
    """
    def __init__(self, used_axes_dict: Dict[str, bool]):
        self.fig_defaults = ConstFigureDefaults()
        self.used_axes_dict = used_axes_dict



    
    
    def create_image_axes(self, num_images: int, num_img_rows: int, num_img_cols: int, **kwargs) -> List[ImageAxesData]:
        pass

    #? NOTE: essentially the exact same logic as PaneledFigureWrapper.create_single_axes - could call this instead
    def set_axes_object(self, panel_data: PanelData, axes_data: AxesData):
        """ creates axes in the given panel of the figure using the provided AxesData """
        subfig = panel_data.subfigure
        if subfig is None:
            raise ValueError(f"Subfigure for panel '{panel_data.name}' is not yet initialized.")
        # create the axes in the subfigure using the provided AxesData
        ax = subfig.add_axes([axes_data.left, axes_data.bottom, axes_data.width, axes_data.height])
        # initialize the axes with the data from the AxesData object
        axes_data.initialize_axes(ax)

    def create_legend_axes(self, **kwargs) -> LegendAxesData:
        """Return a legend AxesData object."""
        return LegendAxesData(**kwargs)

    def create_summary_axes(self, **kwargs) -> SummaryAxesData:
        """Return a summary AxesData object."""
        return SummaryAxesData(**kwargs)

    def create_checkbox_axes(self, labels: List[str], **kwargs) -> CheckboxAxesData:
        """ Return a single CheckboxAxesData object - may later include the dynamic resizing of the axes based on labels """
        # Possibly compute bounding box from label count, etc.
        return CheckboxAxesData(**kwargs)

    def create_button_axes(self, num_buttons: int, left_bound: float, right_bound: float, **kwargs) -> List[ButtonAxesData]:
        """ Return a list of ButtonAxesData objects with computed positions for a horizontal row of `num_buttons` buttons """
        positions = compute_button_positions(num_buttons, left_bound, right_bound)
        button_list = []
        # leaving it like this for readability but it was previously just pos in positions
        for left, bottom, width, height in positions:
            btn_axes = ButtonAxesData(
                left=left,
                bottom=bottom,
                width=width,
                height=height,
                #color="lightgrey", alpha=0.5
                **kwargs
            )
            button_list.append(btn_axes)
        return button_list