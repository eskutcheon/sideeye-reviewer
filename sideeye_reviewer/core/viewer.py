import os
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation
from PIL import Image
from typing import List
# local imports
from .reviewer_button import ReviewerButton
from sideeye_reviewer.utils.utils import maximize_window


class SortResultsViewer:
    """ A read-only viewer for a set of images (and optionally their masks), stepping forward/back or auto-playing. Derived from the old show_sort_results.py """
    def __init__(self, file_list: List[str], img_dirs: List[str], figure_header: str):
        """
            :param file_list: the filenames to iterate over
            :param img_dirs: 1 or 2 directories to look in
            :param figure_header: text to display as a heading
        """
        self.file_list = file_list
        self.img_dirs = img_dirs
        self.num_dir = len(img_dirs)
        if not (1 <= self.num_dir <= 2):
            raise ValueError("Only support 1 or 2 image directories.")
        self.curr_idx = 0
        self.num_reviewed = len(file_list)
        self.figure_header = figure_header
        self.playing_animation = False
        self.initialize_figure()
        self.create_buttons()
        self.set_animator()
        plt.show()

    def initialize_figure(self):
        # Prepare the figure
        self.fig, self.axes = plt.subplots(1, self.num_dir, figsize=(10, 5))
        if self.num_dir == 1:
            self.axes = [self.axes]
        # Show the first image(s)
        self.img_display = []
        for i in range(self.num_dir):
            im = Image.open(os.path.join(self.img_dirs[i], self.file_list[self.curr_idx]))
            disp = self.axes[i].imshow(im)
            self.axes[i].axis("off")
            self.img_display.append(disp)
        self.fig.suptitle(
            f"{self.figure_header}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
            fontsize="xx-large",
            wrap=True
        )
        maximize_window()
        # Positions: [left, bottom, width, height]
        self.fig.tight_layout(rect=[0, 0.1, 1, 1])
        self.fig.canvas.mpl_connect("close_event", self._on_close)

    def create_buttons(self):
        self.buttons = {
            "prev": ReviewerButton.factory(self.fig, label="PREVIOUS", ax_pos=[0.41, 0.025, 0.1, 0.075], callback=self._on_prev_clicked),
            "next": ReviewerButton.factory(self.fig, label="NEXT", ax_pos=[0.52, 0.025, 0.1, 0.075], callback=self._on_next_clicked),
            "start": ReviewerButton.factory(self.fig, label="START", ax_pos=[0.63, 0.025, 0.1, 0.075], callback=self.start_animation),
            "stop": ReviewerButton.factory(self.fig, label="STOP", ax_pos=[0.74, 0.025, 0.1, 0.075], callback=self.stop_animation),
            "exit": ReviewerButton.factory(self.fig, label="EXIT", ax_pos=[0.85, 0.025, 0.1, 0.075], callback=self._on_close)
        }

    def set_animator(self):
        secs_per_frame = 2.5
        self.ani = FuncAnimation(self.fig, self.update_frame, interval=secs_per_frame * 1000, repeat=True, cache_frame_data=False)
        # manually start/stop it by toggling self.playing_animation

    def update_frame(self, frame):
        if self.playing_animation:
            self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
            self.update_display(self.curr_idx)

    def update_display(self, index):
        for i in range(self.num_dir):
            pth = os.path.join(self.img_dirs[i], self.file_list[index])
            im = Image.open(pth)
            self.img_display[i].set_data(im)
        self.fig.suptitle(
            f"{self.figure_header}\n{self.file_list[self.curr_idx]}\nProgress: {self.curr_idx + 1}/{self.num_reviewed}",
            fontsize="xx-large",
            wrap=True
        )
        self.fig.canvas.draw()

    def _on_prev_clicked(self, event):
        self.curr_idx = (self.curr_idx - 1) % self.num_reviewed
        self.update_display(self.curr_idx)

    def _on_next_clicked(self, event):
        self.curr_idx = (self.curr_idx + 1) % self.num_reviewed
        self.update_display(self.curr_idx)

    def start_animation(self, event):
        self.playing_animation = True

    def stop_animation(self, event):
        self.playing_animation = False

    def _on_close(self, event):
        plt.close("all")
