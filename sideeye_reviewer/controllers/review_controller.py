from typing import Optional, List, Union
# local imports
from ..types import ViewerLike, DataManagerType
from .base_controller import BaseReviewController



class ReviewerController(BaseReviewController):
    """ Track the Model and the View states - handles user actions (button clicks, etc.), updates the Model, and tells the View to re-draw """
    def __init__(self, data_manager: DataManagerType, view: ViewerLike):
        """ exact same constructor as the base class but added for clarity """
        super().__init__(data_manager, view)

    def initialize(self, checkpoint = True):
        super().initialize(checkpoint)
        labels = self.get_category_labels()
        #& UPDATE: passing use_summary to the view constructor to handle summary box logic - self.use_summary set by the base class constructor after retrieving it from the data manager
        self.view.setup_gui(self, labels, num_axes = self.data_manager.images_per_batch, use_summary=self.use_summary)
        if self.file_list:
            self._load_image(0)
        self.view.main_loop()

    def on_undo_clicked(self, event):
        """ undo the last label sorting, popping the last label from all bins it was placed in """
        # NOTE: # "remove=True" triggers bin_manager.undo_sort() internally
        self.data_manager.undo_label()
        # step backwards unless at 0
        # TODO: remove negative indexing restriction globally after tracking it all down
        if self.current_idx > 0:
            self.current_idx -= 1
        self._load_image(self.current_idx)

    #def on_stop_clicked(self, event):
    def on_exit_clicked(self, event):
        """ stops the review and closes the session """
        print("[CONTROLLER] Stopping review. Writing results to JSON...")
        self.data_manager.write_results()
        self._stop_requested = True
        if hasattr(self.view, "request_stop"):
            self.view.request_stop()

    def get_on_label_clicked_cb(self, label):
        def on_label_clicked(event):
            """ called when user clicks a single-label or multi-label button """
            if not self.file_list:
                return
            current_file = self.file_list[self.current_idx]
            self.data_manager.assign_labels(current_file, label)
            self._next_image()
        return on_label_clicked

    def on_next_clicked(self, event):
        """ for multi-label usage, user checks some boxes then clicks 'NEXT' """
        if not self.file_list:
            return
        # If multi-label, gather the checkboxes from the view:
        if hasattr(self.view, "get_checked_labels"):
            chosen_labels = self.view.get_checked_labels(clear_after=True)
            if not chosen_labels:
                self.view.display_warning("Please select at least one checkbox before clicking 'NEXT'.")
                return
            current_file = self.file_list[self.current_idx]
            self.data_manager.assign_labels(current_file, chosen_labels)
        self._next_image()

    ############################### Navigation Methods ###############################

    def _next_image(self):
        """ move to next image index, load from model, tell the view to display it """
        if self.current_idx < len(self.file_list) - 1:
            self.current_idx += 1
            self._load_image(self.current_idx)
        else:
            print("[CONTROLLER] Reached end of file list. Stopping automatically.")
            #self.on_stop_clicked(None)
            self.on_exit_clicked(None)
