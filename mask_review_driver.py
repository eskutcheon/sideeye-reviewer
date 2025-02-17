import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files
import core.image_reviewer as IR

# wrote like global constants since this is pretty much all the driver file is meant for.
SORTER_LABELS = ['agree', 'disagree', 'uncertain']
LEGEND_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}

# just made a small function to make it easier to repeat for the test set
def begin_review(image_folders, output_dir):
    ''' optional kwargs:
        file_list (List[str]) - to specify the names of files to review, if not just the whole directory
        json_name (str) - to specify the name of the json file to save the results to.'''
    disputed_sorter = IR.ImageSorter(image_folders, output_dir, SORTER_LABELS)
    # the second positional argument criteria_labels should be optional - but this adds a color legend (or image hint)
    Reviewer = IR.ImageReviewer(disputed_sorter, LEGEND_LABELS)
    # optional argument checkooint (bool) - whether to resume from previous session or not - default True
    Reviewer.begin_review()

if __name__ == "__main__":
    # change if doing this for the test directory too
    image_train_folder = os.path.join('data', 'soiling_dataset', 'train', 'rgbImages')
    label_train_folder = os.path.join('data', 'soiling_dataset', 'train', 'rgbLabels')
    image_test_folder = os.path.join('data', 'soiling_dataset', 'test', 'rgbImages')
    label_test_folder = os.path.join('data', 'soiling_dataset', 'test', 'rgbLabels')
    # /{this parent dir}/disputed_labels - maybe change to /data/sorting/disputed_labels later
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'disputed_labels')
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    begin_review([image_train_folder, label_train_folder], output_dir) # train review
    begin_review([image_test_folder, label_test_folder], output_dir)   # test review
