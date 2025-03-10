import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from typing import Callable, List, Optional


class ReviewerButton:
    """ wrapper class for matplotlib.widgets.Button to track relevant info: label, position, callback, the button widget"""
    def __init__(self, label: str, ax_pos: List[float], callback: Callable, hovercolor: Optional[str] = "0.975"):
        """
            :param label: text shown on the button
            :param ax_pos: [left, bottom, width, height] for the button
            :param callback: a function(event) -> None
            :param hovercolor: button color on hover
        """
        self.label = label
        self.ax_pos = ax_pos
        self.callback = callback
        self.hovercolor = hovercolor
        self.button_widget = None  # Will hold the Button object once created

    def create_button(self, fig: plt.Figure):
        """ Actually create the Axes and the Button, then attach the callback """
        ax = fig.add_axes(self.ax_pos)
        self.button_widget = Button(ax, self.label, hovercolor=self.hovercolor)
        self.button_widget.label.set_fontsize(24)
        self.button_widget.on_clicked(self.callback)

    @staticmethod
    def factory(fig: plt.Figure, label: str, ax_pos: List[float], callback: Callable, hovercolor: str = "0.975") -> "ReviewerButton":
        """ Alternate: create and return a ReviewerButton in one shot """
        rb = ReviewerButton(label, ax_pos, callback, hovercolor)
        rb.create_button(fig)
        return rb


