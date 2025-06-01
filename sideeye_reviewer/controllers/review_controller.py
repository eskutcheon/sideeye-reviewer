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
        # super().initialize(checkpoint) #& UPDATE: new data manager setup doesn't use the superclass method anymore
        labels = self.get_category_labels() if self.data_manager.tasks else []
        self.view.setup_gui(self, labels, num_axes = self.images_per_fig, use_summary=self.use_summary)
        # intialize the view with the first image
        first = self.data_manager.next()
        print(f"first type: {type(first)}")
        print(f"[CONTROLLER] Initializing reviewer with first item: {first}")
        if first:
            self._render(first)
        self.view.main_loop()

    def on_undo_clicked(self, event):
        """ undo the last label sorting, popping the last label from all bins it was placed in """
        #? NOTE: "remove=True" triggers bin_manager.undo_sort() internally
        self.data_manager.undo_label()
        lr = self.data_manager.get_current()  # after undo we already stepped back
        self._render(lr)

    def on_exit_clicked(self, event): # formerly `on_stop_clicked`
        """ stops the review and closes the session """
        print("[CONTROLLER] Stopping review. Writing results to JSON...")
        self._stop_requested = True
        self.close_requested()  #& UPDATE: using new data manager where `close_requested` calls all task models to write their results and perform cleanup

    def get_on_label_clicked_cb(self, label):
        """ returns a callback function for single-label or multi-label buttons """
        def on_label_clicked(event=None):
            """ called when user clicks a single-label or multi-label button """
            self.data_manager.assign_label(label)  #& UPDATE: using new data manager setup
            lr = self.data_manager.next()
            if lr is None:
                self.close_requested()
            else:
                self._render(lr)
        return on_label_clicked

    def on_next_clicked(self, event):
        """ for multi-label usage, user checks some boxes then clicks 'NEXT' """
        # if multi-label, gather the checkboxes from the view:
        if hasattr(self.view, "get_checked_labels"):
            chosen_labels = self.view.get_checked_labels(clear_after=True)
            if not chosen_labels:
                self.view.display_warning("Please select at least one checkbox before clicking 'NEXT'.")
                return
            self.data_manager.assign_label(chosen_labels)  #& UPDATE: using new data manager setup
        # !!!! FIXME: empty assets bug traced back here - fix later
        lr = self.data_manager.next()
        if lr is None:
            self.close_requested()
        else:
            self._render(lr)