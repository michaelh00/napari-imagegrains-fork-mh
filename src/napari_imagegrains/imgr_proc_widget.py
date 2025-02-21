import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


from typing import TYPE_CHECKING
from pathlib import Path

from qtpy.QtWidgets import QVBoxLayout, QTabWidget, QPushButton, QWidget, QFileDialog,  QLineEdit, QGroupBox, QHBoxLayout, QGridLayout, QLabel, QCheckBox, QProgressBar

#from qtpy.QtCore import QThread, Signal
#import time

from .folder_list_widget import FolderList
from .access_single_image_widget import predict_single_image

#from imagegrains import data_loader, segmentation_helper, plotting
from cellpose import models
#import matplotlib.pyplot as plt

import warnings
warnings.filterwarnings("ignore")

import requests


if TYPE_CHECKING:
    import napari


class ImageGrainProcWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        #self.setLayout(QVBoxLayout())

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # segmentation tab
        self.segmentation = QWidget()
        self._segmentation_layout = QVBoxLayout()
        self.segmentation.setLayout(self._segmentation_layout)
        self.tabs.addTab(self.segmentation, 'Segmentation')


        ### Elements "Model download" ###
        self.model_download_group = VHGroup('Model download', orientation='G')
        self._segmentation_layout.addWidget(self.model_download_group.gbox)

        ##### Elements "Download models" #####
        self.lbl_select_model_for_download = QLabel("Model URL")
        self.repo_model_path_display = QLineEdit("No URL")
        #self.btn_select_directory_for_download = QPushButton("Download directory")
        #self.btn_select_directory_for_download .setToolTip("Add local path for model download and click to select")
        self.lbl_select_directory_for_download = QLabel("Download directory")
        self.local_directory_model_path_display = QLineEdit("No local path")
        self.btn_download_model = QPushButton("Download model")
        self.btn_download_model.setToolTip("Add URL to model repo and click to download models")

        self.model_download_group.glayout.addWidget(self.lbl_select_model_for_download, 0, 0, 1, 1)
        self.model_download_group.glayout.addWidget(self.repo_model_path_display,  0, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.lbl_select_directory_for_download, 1, 0, 1, 1)
        self.model_download_group.glayout.addWidget(self.local_directory_model_path_display,  1, 1, 1, 1)
        self.model_download_group.glayout.addWidget(self.btn_download_model, 2, 0, 1, 2)


        ### Elements "Model selection" ###
        self.model_selection_group = VHGroup('Model selection', orientation='G')
        self._segmentation_layout.addWidget(self.model_selection_group.gbox)

        ##### Elements "Select model folder" #####
        self.btn_select_model_folder = QPushButton("Select model folder")
        self.model_selection_group.glayout.addWidget(self.btn_select_model_folder, 0, 0, 1, 2)

        ##### Elements "Model list" #####
        self.model_list = FolderList(viewer)
        self.model_selection_group.glayout.addWidget(self.model_list, 1, 0, 1, 2)


        ### Elements "Image selection"
        self.image_group = VHGroup('Image selection', orientation='G')
        self._segmentation_layout.addWidget(self.image_group.gbox)

        self.btn_select_image_folder = QPushButton("Select image folder")
        self.btn_select_image_folder.setToolTip("Select Image Folder")
        self.image_group.glayout.addWidget(self.btn_select_image_folder)

        ##### Elements "Image list" #####
        self.image_list = FolderList(viewer)
        self.image_group.glayout.addWidget(self.image_list)


        ### Elements "Segmentation options" ###
        self.segmentation_option_group = VHGroup('Segmentation options', orientation='G')
        self._segmentation_layout.addWidget(self.segmentation_option_group.gbox)

        self.check_use_gpu = QCheckBox('Use GPU')
        self.segmentation_option_group.glayout.addWidget(self.check_use_gpu, 0, 0, 1, 1)
        #self.check_return_results = QCheckBox('Return results')
        #self.segmentation_option_group.glayout.addWidget(self.check_return_results, 0, 1, 1, 1)
        self.check_save_mask = QCheckBox('Save mask(s)')
        self.segmentation_option_group.glayout.addWidget(self.check_save_mask, 0, 1, 1, 1)
        self.lbl_mask_directory = QLabel("Mask directory")
        self.segmentation_option_group.glayout.addWidget(self.lbl_mask_directory, 1, 0, 1, 1)
        self.local_directory_mask_path_display = QLineEdit("No local path")
        self.segmentation_option_group.glayout.addWidget(self.local_directory_mask_path_display, 1, 1, 1, 1)


        ### Elements "Run segmentation" ###
        self.run_segmentation_group = VHGroup('Run segmentation', orientation='G')
        self._segmentation_layout.addWidget(self.run_segmentation_group.gbox)

        self.btn_run_segmentation_on_single_image = QPushButton("Run on current image")
        self.btn_run_segmentation_on_single_image.setToolTip("Run segmentation on current image")
        self.run_segmentation_group.glayout.addWidget(self.btn_run_segmentation_on_single_image)

        self.btn_run_segmentation_on_folder = QPushButton("Run on folder")
        self.btn_run_segmentation_on_folder.setToolTip("Run segmentation on entire folder")
        self.run_segmentation_group.glayout.addWidget(self.btn_run_segmentation_on_folder)

        self.lbl_segmentation_progress = QLabel("Segmentation progress on image folder")
        self.run_segmentation_group.glayout.addWidget(self.lbl_segmentation_progress)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.run_segmentation_group.glayout.addWidget(self.progress_bar)


        # performance tab
        self.options_tab = QWidget()
        self._options_tab_layout = QVBoxLayout()
        self.options_tab.setLayout(self._options_tab_layout)
        self.tabs.addTab(self.options_tab, 'Performance')

        self.add_connections()


    def add_connections(self):

        self.btn_download_model.clicked.connect(self._on_click_download_model)

        self.image_list.currentItemChanged.connect(self._on_select_image)
        self.model_list.currentItemChanged.connect(self._on_select_model)
        self.btn_select_image_folder.clicked.connect(self._on_click_select_image_folder)
        self.btn_select_model_folder.clicked.connect(self._on_click_select_model_folder)
        self.btn_run_segmentation_on_single_image.clicked.connect(self._on_click_segment_single_image)
        self.btn_run_segmentation_on_folder.clicked.connect(self._on_click_segment_image_folder)

    
    def _on_click_download_model(self):
        """Downloads models from Github"""

        if self.repo_model_path_display.text() == "No URL":
            return False
        if self.local_directory_model_path_display.text() == "No local path":
             return False 
        
        self.model_url_user = self.repo_model_path_display.text()
        self.model_url_processed = self.model_url_user.replace("github.com", "raw.githubusercontent.com").replace("blob/", "")
        self.model_name = (self.model_url_processed.split("/")[-1])
        self.model_save_path = self.local_directory_model_path_display.text()

        content_in_bytes = requests.get(str(self.model_url_processed)).content
        assert type(content_in_bytes) is bytes
        with open(str(Path(self.model_save_path).joinpath(self.model_name)), 'wb') as f_out:
             f_out.write(content_in_bytes)


    def _on_click_select_image_folder(self):
        """Interactively select folder to analyze"""

        self.image_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.image_list.update_from_path(self.image_folder)
        self.reset_channels = True

        return self.image_folder
    

    def _on_click_select_model_folder(self):
        """Interactively select folder to analyze"""

        model_folder = Path(str(QFileDialog.getExistingDirectory(self, "Select Directory")))
        self.model_list.update_from_path(model_folder)
        self.reset_channels = True
    

    def _on_click_segment_single_image(self):
        """
        Segment image. In development...
        """
        model_path = self.model_path

        model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))

        # single image:
        image_path = self.image_path

        if self.local_directory_mask_path_display.text() == "No local path":
            SAVE_MASKS = False
            TAR_DIR = ""
            img_id = Path(self.image_name).stem
            MODEL_ID = Path(self.model_name).stem
        else:
            if not self.check_save_mask.isChecked():
                SAVE_MASKS = False
                TAR_DIR = ""
                img_id = Path(self.image_name).stem
                MODEL_ID = Path(self.model_name).stem
            else:
                SAVE_MASKS = True
                TAR_DIR = Path(self.local_directory_mask_path_display.text())
                img_id = Path(self.image_name).stem
                MODEL_ID = Path(self.model_name).stem

        self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = predict_single_image(image_path, model, mute=True, return_results=True, save_masks=SAVE_MASKS, tar_dir=TAR_DIR, model_id=MODEL_ID)

        self.viewer.add_labels(self.mask_l[0], name=f"{img_id}_{MODEL_ID}_pred")
    

    def _on_click_segment_image_folder(self):
        """
        Segment image. In development...
        """
        model_path = self.model_path

        model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))

        # single image:
        path_images_in_folder = self.image_folder

        if self.local_directory_mask_path_display.text() == "No local path":
            SAVE_MASKS = False
            TAR_DIR = ""
            MODEL_ID = Path(self.model_name).stem
        else:
            if not self.check_save_mask.isChecked():
                SAVE_MASKS = False
                TAR_DIR = ""
                MODEL_ID = Path(self.model_name).stem
            else:
                SAVE_MASKS = True
                TAR_DIR = Path(self.local_directory_mask_path_display.text())
                MODEL_ID = Path(self.model_name).stem

        img_list = [x for x in os.listdir(path_images_in_folder) if x.endswith(".jpg")]

        for idx, img in enumerate(img_list):
            self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = predict_single_image(path_images_in_folder.joinpath(img), model, mute=True, return_results=True, save_masks=SAVE_MASKS, tar_dir=TAR_DIR, model_id=MODEL_ID)
            self.viewer.open(path_images_in_folder.joinpath(img))
            self.viewer.add_labels(self.mask_l, name=f"{img}_{MODEL_ID}_pred")
            self.progress_bar.setValue(int((idx + 1) / len(img_list) * 100))

        self.progress_bar.setValue(100)  # Ensure it's fully completed


    # def _on_click_segment_image_folder_via_API(self):
    #     """
    #     Segment all images in selected folder. In development...
    #     """

    #     model_path = self.model_path

    #     model = models.CellposeModel(gpu=False, pretrained_model=str(model_path))

    #     # image folder
    #     image_path = self.image_folder

    #     if self.local_directory_mask_path_display.text() == "No local path":
    #         SAVE_MASKS = False
    #         TAR_DIR = ""
    #         MODEL_ID = Path(self.model_name).stem
    #     else:
    #         if not self.check_save_mask.isChecked():
    #             SAVE_MASKS = False
    #             TAR_DIR = ""
    #             MODEL_ID = Path(self.model_name).stem
    #         else:
    #             SAVE_MASKS = True
    #             TAR_DIR = Path(self.local_directory_mask_path_display.text())
    #             MODEL_ID = Path(self.model_name).stem

    #     self.mask_l, self.flow_l, self.styles_l, self.id_list, self.img_l = segmentation_helper.predict_folder(image_path, model, mute=True, return_results=True, save_masks=SAVE_MASKS, tar_dir=TAR_DIR, model_id=MODEL_ID)

    #     for idx, _ in enumerate(self.mask_l):
            
    #         self.viewer.open(self.img_l[idx])
    #         self.viewer.add_labels(self.mask_l[idx], name=f"{image_path}_{MODEL_ID}_pred")


    def _on_select_image(self, current_item, previous_item):
        
        success = self.open_image()
        if not success:
            return False
        else:
            return self.image_path
    

    def _on_select_model(self, current_item, previous_item):

        # if file list is empty stop here
        if self.model_list.currentItem() is None:
            return False
        
        # extract model path
        self.model_name = self.model_list.currentItem().text()
        self.model_path = self.model_list.folder_path.joinpath(self.model_name)
        print(self.model_path)
        
        return self.model_path
        

    def open_image(self):

        # clear existing layers.
        while len(self.viewer.layers) > 0:
             self.viewer.layers.clear()

        # if file list is empty stop here
        if self.image_list.currentItem() is None:
            return False
        
        # open image
        self.image_name = self.image_list.currentItem().text()
        self.image_path = self.image_list.folder_path.joinpath(self.image_name)

        self.viewer.open(self.image_path)


class VHGroup():
    """Group box with specific layout.

    Parameters
    ----------
    name: str
        Name of the group box
    orientation: str
        'V' for vertical, 'H' for horizontal, 'G' for grid
    """

    def __init__(self, name, orientation='V'):
        self.gbox = QGroupBox(name)
        if orientation=='V':
            self.glayout = QVBoxLayout()
        elif orientation=='H':
            self.glayout = QHBoxLayout()
        elif orientation=='G':
            self.glayout = QGridLayout()
        else:
            raise Exception(f"Unknown orientation {orientation}") 

        self.gbox.setLayout(self.glayout)



