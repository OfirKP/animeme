import json
import os
from functools import partial
from pathlib import Path
from typing import Tuple, Union, List, Optional

import numpy as np
import qimage2ndarray
from PIL import ImageFont
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal as Signal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider, QVBoxLayout, QWidget, QPushButton, QGridLayout, \
    QGroupBox, QFormLayout, QLineEdit, QHBoxLayout, QFileDialog, QAction, QComboBox

from gif import GifSequence
from keyframes import TextAnimationKeyframe
from templates import TextAnimationTemplate, MemeAnimationTemplate


class PictureLabel(QLabel):
    pictureClicked = Signal(tuple)  # can be other types (list, dict, object...)

    def __init__(self, image: np.ndarray, parent=None):
        super(PictureLabel, self).__init__(parent)
        self.setPixmap(
            QPixmap.fromImage(qimage2ndarray.array2qimage(image))
        )

    def setImage(self, image: np.ndarray):
        self.setPixmap(
            QPixmap.fromImage(qimage2ndarray.array2qimage(image))
        )

    def mousePressEvent(self, event):
        position = event.pos().x(), event.pos().y()
        self.pictureClicked.emit(position)


class TemplateSelectionPanel(QWidget):
    selected_template_changed = Signal(str)

    def __init__(self, meme_template: MemeAnimationTemplate):
        QWidget.__init__(self)

        layout = QGridLayout()
        self.setLayout(layout)

        groupbox = QGroupBox("Text Template")
        layout.addWidget(groupbox)

        vbox = QVBoxLayout()
        groupbox.setLayout(vbox)

        self.combo = QComboBox(self)
        self.refresh_selector(meme_template=meme_template)
        self.combo.activated[str].connect(self.on_combo_change)
        vbox.addWidget(self.combo)

    def on_combo_change(self, template_id: str):
        self.selected_template_changed.emit(template_id)

    def refresh_selector(self, meme_template: MemeAnimationTemplate):
        self.combo.clear()
        self.combo.addItems([template.id for template in meme_template.templates_list])


class FramePropertiesPanel(QWidget):
    def __init__(self, meme_template: MemeAnimationTemplate, parent=None):
        QWidget.__init__(self, parent=parent)

        self.is_enabled = False
        self.parent_widget: MainWindow = parent
        self.meme_template = meme_template
        self.keyframe: Optional[TextAnimationKeyframe] = None
        layout = QGridLayout()
        self.setLayout(layout)

        groupBox = QGroupBox("Frame Properties")
        layout.addWidget(groupBox)

        self.toggleKeyframeButton = QPushButton('Add Keyframe')
        self.toggleKeyframeButton.setCheckable(True)
        self.toggleKeyframeButton.clicked.connect(self.on_toggle_keyframe)

        self.frameEdit = QLineEdit()
        self.xEdit = QLineEdit()
        self.yEdit = QLineEdit()
        self.textSizeEdit = QLineEdit()

        self.frameEdit.editingFinished.connect(self.on_editing_finished)
        self.xEdit.editingFinished.connect(self.on_editing_finished)
        self.yEdit.editingFinished.connect(self.on_editing_finished)
        self.textSizeEdit.editingFinished.connect(self.on_editing_finished)

        layout = QFormLayout()
        layout.addRow(self.toggleKeyframeButton)
        layout.addRow(QLabel("Frame:"), self.frameEdit)
        layout.addRow(QLabel("x:"), self.xEdit)
        layout.addRow(QLabel("y:"), self.yEdit)
        layout.addRow(QLabel("Text Size:"), self.textSizeEdit)
        groupBox.setLayout(layout)

    def on_editing_finished(self):
        if self.is_enabled:
            frame_ind_str = self.frameEdit.text()
            x_str = self.xEdit.text()
            y_str = self.yEdit.text()
            text_size_str = self.textSizeEdit.text()

            try:
                new_position = (int(x_str), int(y_str)) if x_str and y_str else None
                new_keyframe = TextAnimationKeyframe(frame_ind=int(frame_ind_str) if frame_ind_str else None,
                                                     position=new_position,
                                                     text_size=int(text_size_str) if text_size_str else None)

                # TODO: handle frame index changing
                current_keyframe = self.parent_widget.selected_text_template.keyframes.get_keyframe(
                    self.parent_widget.current_frame_index
                )

                if current_keyframe != new_keyframe:
                    self.parent_widget.selected_text_template.keyframes.insert_keyframe(new_keyframe)
                    self.parent_widget.render_sequence()
            except ValueError:
                self.parent_widget.statusBar().showMessage("Invalid values for keyframe. Please try again.")

    @QtCore.pyqtSlot(bool)
    def on_toggle_keyframe(self, is_add: bool):
        keyframes_collection = self.parent_widget.selected_text_template.keyframes
        frame_ind = int(self.frameEdit.text())
        if is_add:
            keyframes_collection.insert_keyframe(keyframes_collection.interpolate(frame_ind))
        else:
            keyframes_collection.remove_keyframe(frame_ind)
        self.on_selected_frame_change()
        self.parent_widget.render_sequence()

    @QtCore.pyqtSlot(int)
    def on_selected_frame_change(self):
        frame_num = self.parent_widget.current_frame_index
        keyframes_collection = self.parent_widget.selected_text_template.keyframes
        if frame_num in keyframes_collection.keyframes_frames_indices:
            keyframe = keyframes_collection.get_keyframe(frame_num)
            self.updateForm(frame_ind=frame_num, x=keyframe.x, y=keyframe.y, text_size=keyframe.text_size)
            self.toggleKeyframeButton.setChecked(True)
            self.toggleKeyframeButton.setText("Remove Keyframe")
            self.enable()
        else:
            self.disable()
            keyframe = keyframes_collection.interpolate(frame_ind=frame_num)
            self.updateForm(frame_ind=frame_num, x=keyframe.x, y=keyframe.y, text_size=keyframe.text_size)
            self.toggleKeyframeButton.setChecked(False)
            self.toggleKeyframeButton.setText("Add Keyframe")

    def disable(self):
        self.is_enabled = False
        self.frameEdit.setDisabled(True)
        self.xEdit.setDisabled(True)
        self.yEdit.setDisabled(True)
        self.textSizeEdit.setDisabled(True)

    def enable(self):
        self.frameEdit.setEnabled(True)
        self.xEdit.setEnabled(True)
        self.yEdit.setEnabled(True)
        self.textSizeEdit.setEnabled(True)
        self.is_enabled = True

    def updateForm(self, frame_ind: int, x: int, y: int, text_size: int):
        self.frameEdit.setText(str(frame_ind) if frame_ind is not None else "")
        self.xEdit.setText(str(x) if x is not None else "")
        self.yEdit.setText(str(y) if y is not None else "")
        self.textSizeEdit.setText(str(text_size) if text_size is not None else "")


class MainWindow(QMainWindow):
    def __init__(self, path_to_gif: Union[Path, str], meme_template: MemeAnimationTemplate, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle(f"Animator - {os.path.basename(path_to_gif)}")
        self.original_sequence = GifSequence.open(path=path_to_gif, method="mpy")
        self.sequence = self.original_sequence

        self.meme_template = meme_template
        self.selected_text_template = meme_template.templates_list[0]
        self.render_options = {key: key for key in self.meme_template.templates_dict.keys()}
        self.current_frame_index = 0

        self.frame_properties_panel = FramePropertiesPanel(meme_template, parent=self)
        self.frame_properties_panel.on_selected_frame_change()

        self.frames_slider = QSlider(Qt.Horizontal, self)
        self.frames_slider.setMinimum(0)
        self.frames_slider.setMaximum(len(self.sequence) - 1)
        self.frames_slider.setTickPosition(QSlider.TicksBelow)
        self.frames_slider.valueChanged[int].connect(self.on_change_frame)
        self.frames_slider.valueChanged[int].connect(self.frame_properties_panel.on_selected_frame_change)

        self.image_view = PictureLabel(self.sequence[self.frames_slider.value()].array)
        self.image_view.pictureClicked.connect(self.handle_image_press)
        self.image_view.setCursor(QtGui.QCursor(Qt.CrossCursor))

        self.render_sequence()

        left_side_widget = QWidget()
        left_layout = QVBoxLayout()
        self.add_text_template_button = QPushButton('Add New Text Template', self)
        self.add_text_template_button.clicked.connect(self.on_click_add_text_template)

        self.delete_current_text_template = QPushButton('Delete Current Text Template', self)
        self.delete_current_text_template.clicked.connect(self.on_click_delete_current_text_template)

        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.on_click_reset)
        self.reset_button.clicked.connect(lambda _: self.frame_properties_panel.on_selected_frame_change())

        loadAction = QAction("&Load animation", self)
        loadAction.setShortcut("Ctrl+O")
        loadAction.setStatusTip('Load animation and existing template data if possible')
        loadAction.triggered.connect(self.on_click_load)

        saveAction = QAction("&Save template as", self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.setStatusTip('Save animation data to a JSON file')
        saveAction.triggered.connect(self.on_click_save)

        resetAllAction = QAction("&Reset all animation data", self)
        resetAllAction.setShortcut("Ctrl+R")
        resetAllAction.setStatusTip('Reset animation data in all text templates')
        resetAllAction.triggered.connect(self.on_click_reset_all)

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(saveAction)
        fileMenu.addAction(loadAction)
        fileMenu = mainMenu.addMenu('&Animation')
        fileMenu.addAction(resetAllAction)

        self.template_selection_panel = TemplateSelectionPanel(self.meme_template)
        self.template_selection_panel.selected_template_changed.connect(self.on_text_template_change)
        self.template_selection_panel.selected_template_changed.connect(
            lambda _: self.frame_properties_panel.on_selected_frame_change()
        )

        left_layout.addWidget(self.image_view)
        left_layout.addWidget(self.frames_slider)
        left_layout.addWidget(self.template_selection_panel)
        left_layout.addWidget(self.add_text_template_button)
        left_layout.addWidget(self.delete_current_text_template)
        left_layout.addWidget(self.reset_button)
        left_side_widget.setLayout(left_layout)

        right_side_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.frame_properties_panel)
        right_side_widget.setLayout(right_layout)

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_side_widget)
        main_layout.addWidget(right_side_widget)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def on_click_delete_current_text_template(self):
        if len(self.meme_template.templates_list) > 1:
            template_id = self.selected_text_template.id
            self.meme_template.remove_template(self.selected_text_template)
            self.template_selection_panel.refresh_selector(self.meme_template)
            self.on_text_template_change(self.meme_template.templates_list[0].id)
            del self.render_options[template_id]
            self.render_sequence()

    def on_click_add_text_template(self):
        initial_template_id = f"Text {1 + len(self.meme_template.templates_list)}"
        self.meme_template.add_template(TextAnimationTemplate(template_id=initial_template_id))
        self.template_selection_panel.refresh_selector(self.meme_template)
        self.render_options[initial_template_id] = initial_template_id
        self.template_selection_panel.combo.setCurrentIndex(len(self.meme_template.templates_list) - 1)
        self.on_text_template_change(self.template_selection_panel.combo.currentText())
        self.render_sequence()

    def on_text_template_change(self, template_id: str):
        self.selected_text_template = self.meme_template[template_id]

    def render_sequence(self):
        self.sequence = self.original_sequence.copy()
        self.meme_template.render_spiral(sequence=self.sequence,
                                         render_options=self.render_options,
                                         current_ind=self.current_frame_index,
                                         refresh_callback=self.refresh_frame)
        self.refresh_frame()

    def refresh_frame(self):
        self.image_view.setImage(self.sequence[self.frames_slider.value()].array)
        self.image_view.repaint()

    def load_new_sequence(self, sequence: GifSequence):
        self.original_sequence = sequence
        self.sequence = self.original_sequence
        self.render_sequence()
        self.frames_slider.setMaximum(len(self.sequence) - 1)

    def load_animation_data(self, serialized_meme_template: List):
        self.meme_template = MemeAnimationTemplate.deserialize(serialized_meme_template=serialized_meme_template)
        self.selected_text_template = self.meme_template.templates_list[0]
        self.render_sequence()
        self.frame_properties_panel.on_selected_frame_change()

    @QtCore.pyqtSlot(int)
    def on_change_frame(self, index: int):
        self.current_frame_index = index
        self.refresh_frame()

    @QtCore.pyqtSlot(tuple)
    def handle_image_press(self, position: Tuple[int, int]):
        self.selected_text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.current_frame_index, position=position)
        )
        self.frame_properties_panel.on_selected_frame_change()
        self.render_sequence()

    @QtCore.pyqtSlot()
    def on_click_save(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save Template as',
                                                        'c:\\', "JSON file (*.json)")
        if file_path:
            with open(file_path, mode='w') as f:
                json.dump(self.meme_template.serialize(), fp=f, indent=4)
            gif_path = Path(file_path).with_suffix(".gif")
            self.original_sequence.save(str(gif_path))
            self.statusBar().showMessage(f'Saved template to {file_path} and {gif_path}')
        else:
            self.statusBar().showMessage(f'File not saved')

    @QtCore.pyqtSlot()
    def on_click_load(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Load Animation',
                                                        'c:\\', "GIF file (*.gif)")
        if os.path.isfile(file_path):
            gif_path = Path(file_path)
            json_path = gif_path.with_suffix(".json")

            new_sequence = GifSequence.open(str(gif_path), method="mpy")
            self.load_new_sequence(new_sequence)
            self.statusBar().showMessage(f'Loaded {file_path}')

            if json_path.exists():
                serialized_meme_template = json.loads(json_path.read_bytes())
                self.load_animation_data(serialized_meme_template)
            self.setWindowTitle(f"Animator - {gif_path.name}")
        else:
            self.statusBar().showMessage(f'File does not exists')

    @QtCore.pyqtSlot()
    def on_click_reset(self):
        self.selected_text_template.keyframes.reset()
        self.render_sequence()

    @QtCore.pyqtSlot()
    def on_click_reset_all(self):
        for text_template in self.meme_template.templates_list:
            text_template.keyframes.reset()
        self.render_sequence()


if __name__ == '__main__':
    app = QApplication([])

    text_template = TextAnimationTemplate("Text 1")
    text_template2 = TextAnimationTemplate("Text 2")
    meme_template = MemeAnimationTemplate(text_templates=[text_template])
    window = MainWindow("trump.gif", meme_template=meme_template)
    window.show()

    app.exec_()
