# contention_review_driver.py

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

SORTER_LABELS = ["inaccurate_edges","inaccurate_labels","inaccurate_regions",
                 "missed_border","laziness","other","no_contest"]
CLASS_LABELS  = {'clean':'black','transparent':'green','semi-transparent':'blue','opaque':'red'}


###? NOTE: kept for reference on how initialization has changes, but the code below was removed ###
# def begin_review_v1(image_folders, output_dir, file_list, json_name):
#     from sideeye_reviewer.core.sorter import ImageSorter
#     from sideeye_reviewer.core.multilabel_reviewer import MultiLabelReviewer
#     sorter = ImageSorter(
#         image_folders=image_folders,
#         out_dir=output_dir,
#         labels=SORTER_LABELS,
#         file_list=file_list,
#         json_name=json_name,
#     )
#     reviewer = MultiLabelReviewer(sorter, legend_dict=CLASS_LABELS)
#     reviewer.begin_review()


def begin_review_v2(image_folders, output_dir, file_list, num_axes=2):
    from sideeye_reviewer.models.data_manager import DataManager
    from sideeye_reviewer.controllers.review_controller import ReviewerController
    from sideeye_reviewer.views.multilabel_reviewer import MultiLabelReviewerView
    image_folders = image_folders[:num_axes]
    json_name = f"multilabel_sort_{num_axes}img_v2.json"
    manager = DataManager(image_folders, output_dir, SORTER_LABELS, file_list, json_name=json_name, enable_sorting=True)
    reviewer = MultiLabelReviewerView(legend_dict=CLASS_LABELS)
    controller = ReviewerController(manager, reviewer)
    controller.initialize()



if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'results', 'disputed_labels')
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    #begin_review_v1([image_train_folder, label_train_folder], output_dir, None, "multilabel_output.json") # train review
    begin_review_v2([image_train_folder, label_train_folder], output_dir, file_list=None, num_axes=2)