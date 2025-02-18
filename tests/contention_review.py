# contention_review_driver.py

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sideeye_reviewer.core.sorter import ImageSorter
from sideeye_reviewer.core.multilabel_reviewer import MultiLabelReviewer

SORTER_LABELS = ["inaccurate_edges","inaccurate_labels","inaccurate_regions",
                 "missed_border","laziness","other","no_contest"]
CLASS_LABELS  = {'clean':'black','transparent':'green','semi-transparent':'blue','opaque':'red'}

def begin_review(image_folders, output_dir, file_list, json_name):
    sorter = ImageSorter(
        image_folders=image_folders,
        out_dir=output_dir,
        labels=SORTER_LABELS,
        file_list=file_list,
        json_name=json_name,
    )
    reviewer = MultiLabelReviewer(sorter, legend_dict=CLASS_LABELS)
    reviewer.begin_review()


if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'results', 'disputed_labels')
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    begin_review([image_train_folder, label_train_folder], output_dir, None, "multilabel_output.json") # train review