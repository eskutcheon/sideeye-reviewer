import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Callable, Union, Tuple, Iterable, Any
from numpy import ndarray as NDarray
# local imports
from .axes_wrappers import AxesData, ButtonAxesData, CheckboxAxesData, SummaryAxesData, LegendAxesData, ImageAxesData, PanelData
from .figure_defaults import ConstFigureDefaults


# may add this to the utils later
def get_axes_list(axes: Union[plt.Axes, List[plt.Axes], NDarray]) -> List[plt.Axes]:
    """ helper function to ensure that the axes are returned as a list of Axes objects """
    if not isinstance(axes, (list, NDarray)) and isinstance(axes, plt.Axes):
        axes = [axes]
    elif isinstance(axes, NDarray) and axes.ndim > 1:
        axes = axes.flatten()  # ensure axes is a 1D list of Axes objects
    # may still want to generalize this function further and assign axes to the panel's axes_items list
    return list(axes)

class AxesCreationManager:
    """ Standalone class that creates AxesData objects for common usage scenarios:
        - Image axes (a grid for multiple images)
        - Button axes (a row of buttons)
        - Single axes
        - Subplot axes (multiple subplots)
        It's meant to be a class member of FigureLayoutManager which calls to it to create and adjust axes
    """
    def __init__(self, used_axes_dict: Dict[str, bool]):
        # if I don't use this somewhere, there's no need to add a constructor
        self.used_axes_dict = used_axes_dict


    def create_image_axes_data(self,
                               panel_data: PanelData,
                               num_images: int,
                               nrows: int,
                               ncols: int,
                               **kwargs) -> List[ImageAxesData]:
        kwargs.setdefault("aspect", "auto")     # set the aspect ratio to auto for image axes
        kwargs.setdefault("adjustable", "box")  # set the adjustable to box for image axes
        kwargs.setdefault("snap", True)         # set the snap to True for image axes
        #kwargs.setdefault("layout", "tight")    # set the layout to tight for image axes
        #kwargs.setdefault("antialiased", True) # may or may not need this for the images - decide later
        img_axes_data: List[ImageAxesData] = []
        subfig = self._get_initialized_subfig(panel_data)
        img_axes: List[plt.Axes] = self._get_axes_subplots(subfig, nrows, ncols, **kwargs)
        for ax in img_axes[:num_images]:
            ax.set_aspect("auto", adjustable="box")
            img_axes_data.append(ImageAxesData(ax))
        # hide any unused image axes
        for ax in img_axes[num_images:]:
            ax.set_visible(False)
        return img_axes_data

    # TODO: add the actual axes creation later via self.set_axes_object() called from the layout manager
    def create_button_axes_data(self,
                                num_buttons: int,
                                left_bound: float,
                                right_bound: float,
                                **kwargs) -> List[ButtonAxesData]:
        """ Return a list of ButtonAxesData objects with computed positions for a horizontal row of `num_buttons` buttons """
        positions = self.compute_button_positions(num_buttons, left_bound, right_bound)
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


    def create_legend_axes_data(self, **kwargs) -> LegendAxesData:
        """Return a legend AxesData object."""
        #& currently unused in the layout manager
        return LegendAxesData(**kwargs)

    def create_summary_axes_data(self, **kwargs) -> SummaryAxesData:
        """Return a summary AxesData object."""
        kwargs.setdefault("use_border", True)
        return SummaryAxesData(**kwargs)

    def create_checkbox_axes_data(self, **kwargs) -> CheckboxAxesData:
        """ Return a single CheckboxAxesData object - may later include the dynamic resizing of the axes based on labels """
        # TODO: need to ensure that kwargs are properly passed from the layout manager - needs validation
        # Possibly compute bounding box from label count, etc.
        checkbox_axes =  CheckboxAxesData(**kwargs)
        # TODO: move this logic later - just removing it from _set_multiple_axes_objects for now
        # ensure the height is roughly half of what it would be with the entire right panel height
        #checkbox_axes.height *= 0.5
        return checkbox_axes



    ##########################################################################################################
    # GENERAL HELPER FUNCTIONS
    ##########################################################################################################

    def _get_initialized_subfig(self, panel_data: PanelData) -> plt.Figure:
        subfig = panel_data.subfigure
        if subfig is None:
            raise ValueError(f"Subfigure for panel '{panel_data.name}' is not yet initialized.")
        return subfig


    #& previously part of the implementation of FigureLayoutManager._place_figure_elements()
    def set_multiple_axes_objects(self, panel_data: PanelData, axes_data: List[AxesData], **axes_init_kwargs):
        for ax_data in axes_data:
            if ax_data.axes is None:
                self.set_axes_object(panel_data, ax_data, **axes_init_kwargs)


    #? NOTE: essentially the exact same logic as PaneledFigureWrapper.create_single_axes - could call this instead
    def set_axes_object(self, panel_data: PanelData, axes_data: AxesData, **axes_init_kwargs):
        """ creates axes in the given panel of the figure using the provided AxesData """
        subfig = self._get_initialized_subfig(panel_data)
        # create the axes in the subfigure using the provided AxesData, rescaled to the panel's bounding box
        panel_data.rescale_axes(axes_data)
        rect = [axes_data.left, axes_data.bottom, axes_data.width, axes_data.height]
        ax = subfig.add_axes(rect, **axes_init_kwargs)
        # initialize the axes with the data from the AxesData object
        axes_data.initialize_axes(ax)

    def _get_axes_subplots(self,
                          subfig: plt.Figure,
                          #axes_data: List[AxesData],
                          nrows: int = 1,
                          ncols: int = 1,
                          **axes_init_kwargs) -> List[plt.Axes]:
        """ creates subplots in the given panel subfigure to return a list of Axes objects """
        # create the subplots in the subfigure using the provided AxesData
        ax: Union[plt.Axes, List[plt.Axes]] = subfig.subplots(nrows=nrows, ncols=ncols, subplot_kw=axes_init_kwargs)
        # ensure list format before looping
        return get_axes_list(ax)


    @staticmethod
    def compute_button_positions(num_buttons: int, left_bound = None, right_bound = None) -> List[List[float]]:
        """ Re-implement get_button_axes using figure-relative coordinates - bottom right aligned """
        def get_total_width(w: float, s: float) -> float:
            return (w + s) * num_buttons - s
        # set default bounds if not provided
        default_bounds = ConstFigureDefaults()
        left_bound = left_bound or default_bounds.BOTTOM_PANEL_LEFT
        right_bound = right_bound or default_bounds.BOTTOM_PANEL_LEFT + default_bounds.BOTTOM_PANEL_WIDTH
        width, height = default_bounds.BUTTON_WIDTH, default_bounds.BUTTON_HEIGHT
        bottom_bound = default_bounds.BOTTOM_PANEL_BOTTOM + default_bounds.AXES_PADDING
        spacing = default_bounds.BUTTON_SPACING
        total_width = get_total_width(width, spacing)
        # rescale if total width exceeds available space
            # eventually, might want to allocate enough vertical space (more than the default 0.15) to have extra button rows
        if total_width > right_bound - left_bound:
            scale = (right_bound - left_bound)/total_width
            width *= scale
            spacing *= scale
            total_width = get_total_width(width, spacing)
        padding = (right_bound - left_bound - total_width)/2
        left_bound += padding
        positions = []
        for i in range(num_buttons):
            # create buttons starting from the right boundary - meaning positions are ordered from right to left
            left = right_bound - (i+1) * (width + spacing)
            # keep the bottom at 0.025 and the height at 0.075 so that the top of the buttons are all at 0.1
            positions.append([left, bottom_bound, width, height])
        return positions



# def measure_checkbox_labels(labels, main_fig_size=(12, 7), fontsize=16, line_spacing=1.2):
#     """ returns (total_width, total_height) in "text units" for stacked labels,
#         computed purely via text path metrics (no figure or event loop).
#     """
#     from matplotlib.textpath import TextPath
#     from matplotlib.font_manager import FontProperties
#     # create FontProperties instance for desired font & size
#     font = FontProperties(size=fontsize)
#     # track bounding box extremes for each label - subsequent labels placed at negative y offsets => "stacking" downward
#     min_x, min_y, max_x, max_y = np.inf, np.inf, -np.inf, -np.inf
#     baseline_y = 0.0
#     # iterate over labels while tracking extents
#     for lbl in labels:
#         # create TextPath at (x=0, y=baseline_y)
#         tp = TextPath(xy=(0, baseline_y), s=lbl, prop=font)
#         # textpath's bounding box => a matplotlib.path.Path in user coords
#         bbox = tp.get_extents()
#         # union bounding box
#         min_x = min(min_x, bbox.x0)
#         min_y = min(min_y, bbox.y0)
#         max_x = max(max_x, bbox.x1)
#         max_y = max(max_y, bbox.y1)
#         # typical line spacing = line_spacing * single-line offset
#         line_height = (bbox.y1 - bbox.y0) * line_spacing
#         # reduce baseline downward for next label
#         baseline_y -= line_height
#     #? NOTE: think this varies with screen resolution - need to look into it further
#     # convert from points to inches (1 point = 1/72 inch)
#     width_inch  = (max_x - min_x) / 72.0
#     height_inch = (max_y - min_y) / 72.0
#     # convert to fraction of your main figure size
#     fig_w_inch, fig_h_inch = main_fig_size
#     width_fraction  = width_inch  / fig_w_inch
#     height_fraction = height_inch / fig_h_inch
#     #width_fraction  *= 0.7
#     #height_fraction *= 0.8
#     return width_fraction, height_fraction