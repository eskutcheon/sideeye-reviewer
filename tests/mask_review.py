import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
from sideeye_reviewer.core.sorter import ImageSorter
from sideeye_reviewer.core.unilabel_reviewer import SingleLabelReviewer

# wrote like global constants since this is pretty much all the driver file is meant for.
SORTER_LABELS = ['agree', 'disagree', 'uncertain']
LEGEND_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}

# just made a small function to make it easier to repeat for the test set
def begin_review(image_folders, output_dir):
    disputed_sorter = ImageSorter(image_folders, output_dir, SORTER_LABELS, json_name="train_output.json")
    reviewer = SingleLabelReviewer(disputed_sorter, legend_dict=LEGEND_LABELS)
    # optional argument checkooint (bool) - whether to resume from previous session or not - default True
    reviewer.begin_review()

if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'results', 'disputed_labels')
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    begin_review([image_train_folder, label_train_folder], output_dir) # train review
