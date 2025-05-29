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
        # if self.file_list:
        #     self._load_image(0)
        first = self.data_manager.next()
        if first:
            self._render(first)
        self.view.main_loop()

    def on_undo_clicked(self, event):
        """ undo the last label sorting, popping the last label from all bins it was placed in """
        # NOTE: # "remove=True" triggers bin_manager.undo_sort() internally
        self.data_manager.undo_label()
        # step backwards unless at 0
        # TODO: remove negative indexing restriction globally after tracking down relevant logic
        # if self.current_idx > 0:
        #     self.current_idx -= 1
        # ###self._load_image(self.current_idx)
        # self.
        lr = self.data_manager._get_current()  # after undo we already stepped back
        self._render(lr)

    def on_exit_clicked(self, event): # formerly `on_stop_clicked`
        """ stops the review and closes the session """
        print("[CONTROLLER] Stopping review. Writing results to JSON...")
        #self.data_manager.write_results()
        # self.data_manager.flush() #& UPDATE: using new data manager where `flush` calls all task models to write their results and perform cleanup
        self._stop_requested = True
        # if hasattr(self.view, "request_stop"):
        #     self.view.request_stop()
        self.close_requested()  #& UPDATE: using new data manager where `close_requested` calls all task models to write their results and perform cleanup

    def get_on_label_clicked_cb(self, label):
        """ returns a callback function for single-label or multi-label buttons """
        def on_label_clicked(event=None):
            """ called when user clicks a single-label or multi-label button """
            # if not self.file_list:
            #     return
            # current_file = self.file_list[self.current_idx]
            # #self.data_manager.assign_labels(current_file, label)
            # self.data_manager.assign_label(current_file, [label])  #& UPDATE: now always passing a list of labels for the task models to handle
            # self._next_image()
            self.data_manager.assign_label(label)  #& UPDATE: using new data manager setup
            lr = self.data_manager.next()
            if lr is None:
                self.close_requested()
            else:
                self._render(lr)
        return on_label_clicked

    def on_next_clicked(self, event):
        """ for multi-label usage, user checks some boxes then clicks 'NEXT' """
        # if not self.file_list:
        #     return
        # If multi-label, gather the checkboxes from the view:
        if hasattr(self.view, "get_checked_labels"):
            chosen_labels = self.view.get_checked_labels(clear_after=True)
            if not chosen_labels:
                self.view.display_warning("Please select at least one checkbox before clicking 'NEXT'.")
                return
            self.data_manager.assign_label(chosen_labels)  #& UPDATE: using new data manager setup
        lr = self.data_manager.next()
        if lr is None:
            self.close_requested()
        else:
            self._render(lr)
        #     current_file = self.file_list[self.current_idx]
        #     #self.data_manager.assign_labels(current_file, chosen_labels)
        #     self.data_manager.assign_label(current_file, chosen_labels)  #& UPDATE: using new data manager setup
        # self._next_image()

    ############################### Navigation Methods ###############################

    # def _next_image(self):
    #     """ move to next image index, load from model, tell the view to display it """
    #     if self.current_idx < len(self.file_list) - 1:
    #         self.current_idx += 1
    #         self._load_image(self.current_idx)
    #     else:
    #         print("[CONTROLLER] Reached end of file list. Stopping automatically.")
    #         self.on_exit_clicked(None)
