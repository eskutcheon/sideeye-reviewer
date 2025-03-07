import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


###? NOTE: kept for reference on how initialization has changes, but the code below was removed ###
# def show_disputed_images(file_list, img_dirs):
#     from sideeye_reviewer.core.viewer import SortResultsViewer
#     header = "Disputed segmentation masks"
#     viewer = SortResultsViewer(file_list, img_dirs, header)
#     # The viewer constructor starts plt.show() and runs an animation loop

def show_disputed_v2(file_list, img_dirs, num_axes=2):
    from sideeye_reviewer.views.slides_viewer import SlideshowViewerView
    from sideeye_reviewer.controllers.slides_controller import SlideshowController  # formerly ViewerController
    from sideeye_reviewer.models.data_manager import DataManager
    img_folders = img_dirs[:num_axes]
    dm = DataManager(image_folders=img_folders, file_list=file_list, enable_sorting=False)
    viewer = SlideshowViewerView("My Slideshow")
    controller = SlideshowController(dm, viewer)
    controller.initialize()  # loads file list, sets up UI, enters loop


if __name__ == "__main__":
    root_data_dir = r"E:\Woodscape Soiling\soiling_dataset"
    image_train_folder = os.path.join(root_data_dir, 'train', 'rgbImages')
    label_train_folder = os.path.join(root_data_dir, 'train', 'rgbLabels')
    img_dirs = [image_train_folder, label_train_folder]
    file_list = os.listdir(label_train_folder)
    #show_disputed_images(file_list, img_dirs)
    show_disputed_v2(file_list, img_dirs, num_axes=1)