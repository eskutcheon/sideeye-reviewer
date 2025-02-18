import matplotlib.pyplot as plt
#from matplotlib.backend_bases import MouseEvent
from typing import Union, List, Optional, Callable
# local imports
from .sorter import ImageSorter
from .reviewer_button import ReviewerButton
from sideeye_reviewer.utils.utils import maximize_window




class BaseReviewer:
    """ Manages the main figure, the images, the 'Stop' and 'Undo' buttons, and a continuous event loop.
        Subclasses can add their own custom buttons and checkboxes. Pressing a button triggers a callback function immediately.
    """
    def __init__(self, sorter: ImageSorter, fig_title: str = "Image Reviewer"):
        """
            :param sorter: an ImageSorter instance
            :param fig_title: an optional title for the review window
        """
        self.sorter = sorter
        self.fig_title = fig_title
        self.fig = None
        self.axs = []
        self.canvas_images = []
        # track the file list and the current index in prepare_file_list().
        self.file_list: List[str] = []
        self.current_idx = 0
        # by default, set up Stop and Undo in the base class, but subclasses will add more in create_subclass_buttons().
        self.stop_button = None
        self.undo_button = None
        self._stop_requested = False
        #self.cidpress = self.fig.canvas.mpl_connect('button_press_event', self.on_button_press_callback)

    def prepare_file_list(self, checkpoint: Union[bool, int] = True):
        """ If checkpoint=True, resume from previous progress. If checkpoint is an int, skip that many files. If None/False for no skipping """
        ckpt_idx = self.sorter.check_if_resuming(checkpoint)
        all_files = self.sorter.get_file_list(ckpt_idx)
        self.file_list = all_files
        self.current_idx = 0

    def create_figure_and_axes(self):
        """ Creates a single figure with up to 2 Axes if sorter.img_dirs has length 2. """
        plt.ion()
        self.fig, ax_array = plt.subplots(1, len(self.sorter.img_dirs), figsize=(9, 5), gridspec_kw={'wspace': 0.1})
        if len(self.sorter.img_dirs) == 1:
            self.axs = [ax_array]
        else:
            self.axs = list(ax_array)
        self.fig.suptitle(self.fig_title, fontsize="x-large")
        maximize_window()
        self.fig.canvas.mpl_connect("close_event", self._on_close)


    def _on_close(self, event):
        # If the user forcibly closes the window, stop gracefully
        if not self._stop_requested:
            print("Window closed: stopping review.")
            self.stop_review()

    def create_base_buttons(self):
        """ Creates STOP and UNDO buttons in the bottom region of the figure. Subclasses add more buttons in separate functions """
        # Positions: [left, bottom, width, height]
        self.undo_button = ReviewerButton.factory(
            fig=self.fig,
            label="UNDO",
            ax_pos=[0.75, 0.025, 0.10, 0.075],
            callback=self.on_undo_clicked
        )
        self.stop_button = ReviewerButton.factory(
            fig=self.fig,
            # TODO: might want to change all instances of "STOP" buttons to "EXIT" for consistency with the viewer
            label="STOP",
            ax_pos=[0.86, 0.025, 0.10, 0.075],
            callback=self.on_stop_clicked
        )

    def on_undo_clicked(self, event):
        # Undo means remove the last file->labels association from the sorter
        self.sorter.update_bin(labels=None, remove=True)
        # We typically want to step back one index unless we are at zero
        if self.current_idx > 0:
            self.current_idx -= 1
        self.redraw_current_image()

    def on_stop_clicked(self, event):
        self.stop_review()

    def stop_review(self):
        """ writes final results and sets the internal stop flag to exit the main loop """
        print("Stopping review. Writing results to JSON...")
        self.sorter.bin_manager.write_to_outfiles()
        self._stop_requested = True

    def load_initial_image(self):
        """ called once after we have a figure. We show the first image in the list """
        if not self.file_list:
            return
        for i, ax in enumerate(self.axs):
            ax.axis("off")
            first_image = self.sorter.get_image_paths(self.file_list[self.current_idx])[i]
            img = plt.imread(first_image)
            im_obj = ax.imshow(img, aspect="auto")
            self.canvas_images.append(im_obj)
        self._update_title()

    def redraw_current_image(self):
        """ reload from disk the image(s) at self.current_idx, update canvas_images, draw """
        if not self.file_list:
            return
        paths = self.sorter.get_image_paths(self.file_list[self.current_idx])
        for i, p in enumerate(paths):
            self.canvas_images[i].set_data(plt.imread(p))
        self._update_title()
        self.fig.canvas.draw()

    def _update_title(self):
        fname = self.file_list[self.current_idx] if self.file_list else "No files"
        self.fig.suptitle(
            f"{self.fig_title}\n{fname}\n({self.current_idx+1}/{len(self.file_list)})",
            fontsize="xx-large"
        )

    def display_warning(self, message="Warning!", duration=3000):
        txt = self.fig.text(0.5, 0.3, message, ha='center', va='center', fontsize=18, color='red')
        self.fig.canvas.draw()
        def remove_text():
            try:
                txt.remove()
                self.fig.canvas.draw()
            except ValueError:
                pass
        # Create a timer that will remove the text after `duration` milliseconds
        timer = self.fig.canvas.new_timer(interval=duration)
        timer.add_callback(remove_text)
        timer.start()

    def next_image(self):
        """ Subclasses (or a button callback) can call this to move forward one image """
        if self.current_idx < len(self.file_list) - 1:
            self.current_idx += 1
            self.redraw_current_image()
        else:
            # If we're at the end, we can auto-stop or just ignore.
            print("Reached the end of file list. Stopping automatically.")
            self.stop_review()

    def main_loop(self):
        # Main loop: keep going until STOP is triggered
        while not self._stop_requested and plt.fignum_exists(self.fig.number):
            plt.pause(0.05)  # short pause to handle events
        # Once we break from the loop, close the figure if it still exists
        if plt.fignum_exists(self.fig.number):
            plt.close(self.fig)

    def begin_review(self, checkpoint: Union[bool, int] = True):
        """ Main entry point; Prepares the file list, sets up the figure, and other preliminaries,
            then enters a loop that keeps the figure alive until user hits STOP or closes it.
        """
        self.prepare_file_list(checkpoint)
        if not self.file_list:
            print("No files to review.")
            return
        self.create_figure_and_axes()
        self.create_base_buttons()
        self.load_initial_image()

