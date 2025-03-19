

# Plan
- refactor to begin managing primarily `AxesData` and `PanelData` objects in the lower level figure, panel, and axes creation within the current `panel_creator.py`
- replace circuitous accesses of figure and panel aspects from `layout_manager` to primarily use accessor methods in `PaneledFigureWrapper`
- further separate creation of axes through relative layout and explicit positioning via `subfigure.subplots` and `subfigure.add_axes`
- overhaul the view classes to either
    1. update figure axes through new methods in `AxesData` subclasses each time the figure is updated
    2. or modify only the `plt.Axes` objects through accessor methods in `FigureLayoutManager` that retrieve them from the `AxesData` objects

- (MAYBE) split `layout_manager.py` further into a new `AxesManager` class to handle the logic around adding and adjusting `AxesData` objects