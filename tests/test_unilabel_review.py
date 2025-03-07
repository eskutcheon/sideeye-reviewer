import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# project files

# wrote like global constants since this is pretty much all the driver file is meant for.
SORTER_LABELS = ['agree', 'disagree', 'uncertain']
LEGEND_LABELS = {'clean': 'black', 'transparent': 'green', 'semi-transparent': 'blue', 'opaque': 'red'}


###? NOTE: kept for reference on how initialization has changes, but the code below was removed ###
# def test_review_v1(image_folders, output_dir, num_axes=2):
#     from sideeye_reviewer.core.sorter import ImageSorter
#     from sideeye_reviewer.core.unilabel_reviewer import SingleLabelReviewer
#     image_folders = image_folders[:num_axes]
#     json_name = f"test_{num_axes}label_sort_v1.json"
#     disputed_sorter = ImageSorter(image_folders, output_dir, SORTER_LABELS, json_name=json_name)
#     reviewer = SingleLabelReviewer(disputed_sorter, legend_dict=LEGEND_LABELS)
#     # optional argument checkooint (bool) - whether to resume from previous session or not - default True
#     reviewer.begin_review()


def test_review_v2(image_folders, output_dir, num_axes=2):
    from sideeye_reviewer.controllers.review_controller import ReviewerController
    from sideeye_reviewer.models.data_manager import DataManager
    from sideeye_reviewer.views.unilabel_reviewer import SingleLabelReviewerView
    image_folders = image_folders[:num_axes]
    json_name = f"test_unilabel_sort_{num_axes}img_v2.json"
    data_manager = DataManager(image_folders, output_dir, SORTER_LABELS, json_name=json_name, enable_sorting=True)
    reviewer = SingleLabelReviewerView(legend_dict=LEGEND_LABELS)
    controller = ReviewerController(data_manager, reviewer)
    controller.initialize()


if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'results', 'disputed_labels')
    # folders passed to the ImageSorter constructor must be in a list, even if singleton
    #test_review_v1([image_train_folder, label_train_folder], output_dir) # training set review
    test_review_v2([image_train_folder, label_train_folder], output_dir, num_axes=2) # training set review