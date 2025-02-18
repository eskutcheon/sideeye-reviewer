import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# meeting_presentation.py or similar
from sideeye_reviewer.core.viewer import SortResultsViewer

def show_disputed_images(file_list, img_dirs):
    header = "Disputed segmentation masks"
    viewer = SortResultsViewer(file_list, img_dirs, header)
    # The viewer constructor starts plt.show() and runs an animation loop

if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    img_dirs = [image_train_folder, label_train_folder]
    file_list = os.listdir(label_train_folder)
    show_disputed_images(file_list, img_dirs)