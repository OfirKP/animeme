import json
import os
from functools import partial
from pathlib import Path
from typing import Tuple, Union, List, Optional

import numpy as np
import qimage2ndarray
from PIL import ImageFont
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal as Signal, QPoint, QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QPaintEvent, QFontMetrics, QMouseEvent
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider, QVBoxLayout, QWidget, QPushButton, QGridLayout, \
    QGroupBox, QFormLayout, QLineEdit, QHBoxLayout, QFileDialog, QAction, QComboBox, QSizePolicy, QStyle, QRubberBand

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

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent: MainWindow = parent

        layout = QGridLayout()
        self.setLayout(layout)

        groupbox = QGroupBox("Text Template")
        layout.addWidget(groupbox)

        vbox = QVBoxLayout()
        groupbox.setLayout(vbox)

        self.combo = QComboBox(self)
        self.refresh_selector()
        self.combo.activated[str].connect(self.on_combo_change)
        vbox.addWidget(self.combo)

    def on_combo_change(self, template_id: str):
        self.parent.changeSelectedTextTemplate(template_id)

    def refresh_selector(self):
        self.combo.clear()
        self.combo.addItems([template.id for template in self.parent.meme_template.templates_list])
        self.combo.setCurrentIndex(self.parent.meme_template.templates_list.index(self.parent.selected_text_template))


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
                    self.parent_widget.frames_viewer.update()
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
        self.parent_widget.frames_viewer.update()

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


class KeyframesIndicator(QWidget):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.MinimumExpanding
        )

    def sizeHint(self):
        return QtCore.QSize(20, 40)

    def paintEvent(self, e):
        painter = QPainter(self)

        brush = QtGui.QBrush()
        brush.setColor(QColor('black'))
        brush.setStyle(Qt.SolidPattern)
        painter.setBrush(brush)
        rect = QtCore.QRect(0, 0, painter.device().width(), painter.device().height())
        painter.fillRect(rect, brush)

        keyframes_indices = self.parent.selected_text_template.keyframes.keyframes_frames_indices
        slider = self.parent.frames_slider

        pen = QPen()
        pen.setWidth(5)
        pen.setColor(QColor('red'))
        painter.setPen(pen)

        brush = QtGui.QBrush()
        brush.setColor(QColor('red'))
        brush.setStyle(Qt.SolidPattern)
        painter.setBrush(brush)

        for frame_ind in keyframes_indices:
            position = QStyle.sliderPositionFromValue(slider.minimum(), slider.maximum(), frame_ind, slider.width())
            painter.drawEllipse(position, 10, 2, 2)

        painter.end()

    def refresh(self):
        self.update()


class FramesViewer(QLabel):
    def __init__(self, sequence: GifSequence, parent: 'MainWindow', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.sequence = sequence
        self.pixmaps = [QPixmap.fromImage(qimage2ndarray.array2qimage(frame.array)) for frame in sequence]
        self.selected_frame_ind = 0
        self.text_template_to_rect = {}
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.rubberBand.show()
        self.setPixmap(self.pixmaps[self.selected_frame_ind])

    def mousePressEvent(self, e: QMouseEvent):
        for text_template in self.parent.meme_template.templates_list:
            if text_template.id in self.text_template_to_rect \
                    and text_template.id != self.parent.selected_text_template.id \
                    and self.text_template_to_rect[text_template.id].contains(e.pos()):
                self.parent.changeSelectedTextTemplate(text_template.id)
                self.update()
                return

        self.parent.selected_text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.selected_frame_ind, position=(e.x(), e.y()))
        )
        self.parent.frame_properties_panel.on_selected_frame_change()
        self.update()

    def mouseMoveEvent(self, e: QMouseEvent):
        self.parent.selected_text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.selected_frame_ind, position=(e.x(), e.y()))
        )
        self.parent.frame_properties_panel.on_selected_frame_change()
        self.update()

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        painter = QtGui.QPainter(self)

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor('white'))
        painter.setPen(pen)

        font = QtGui.QFont()
        font.setFamily('Montserrat')
        self.text_template_to_rect = {}
        for template_id, text in self.parent.render_options.items():
            text_template = self.parent.meme_template[template_id]
            keyframe = text_template.keyframes.interpolate(self.selected_frame_ind)
            font.setPixelSize(keyframe.text_size)
            painter.setFont(font)

            x, y, width, height = text_template.get_text_bounding_box(center_position=keyframe.position,
                                                                      font_size=keyframe.text_size,
                                                                      text=text)
            text_rect = QRect(x, y, width, height)
            self.text_template_to_rect[template_id] = text_rect
            if template_id == self.parent.selected_text_template.id:
                self.rubberBand.setGeometry(text_rect)
            painter.drawText(QRect(x, y, width, height), Qt.AlignHCenter | Qt.AlignVCenter, text)

        painter.end()

    def handle_frame_update(self, frame_ind: int):
        self.selected_frame_ind = frame_ind
        self.setPixmap(self.pixmaps[self.selected_frame_ind])


class MainWindow(QMainWindow):
    selected_text_template_changed = Signal(str)

    def __init__(self, path_to_gif: Union[Path, str], meme_template: MemeAnimationTemplate, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle(f"Animator - {os.path.basename(path_to_gif)}")
        self.original_sequence = GifSequence.open(path=path_to_gif, method="mpy")
        self.sequence = self.original_sequence

        self.meme_template = meme_template
        self.selected_text_template = meme_template.templates_list[0]
        self.render_options = {key: key for key in self.meme_template.templates_dict.keys()}
        self.current_frame_index = 0

        # self.keyframes_indicator = KeyframesIndicator(self)
        self.frame_properties_panel = FramePropertiesPanel(meme_template, parent=self)
        self.frame_properties_panel.on_selected_frame_change()
        # self.frame_properties_panel.toggleKeyframeButton.clicked.connect(self.keyframes_indicator.refresh)

        self.frames_slider = QSlider(Qt.Horizontal, self)
        self.frames_slider.setMinimum(0)
        self.frames_slider.setMaximum(len(self.sequence) - 1)
        self.frames_slider.setTickPosition(QSlider.TicksBelow)
        self.frames_slider.valueChanged[int].connect(self.on_change_frame)
        self.frames_slider.valueChanged[int].connect(self.frame_properties_panel.on_selected_frame_change)

        self.frames_viewer = FramesViewer(sequence=self.original_sequence, parent=self)
        self.frames_slider.valueChanged[int].connect(self.frames_viewer.handle_frame_update)
        self.frames_viewer.setCursor(QtGui.QCursor(Qt.CrossCursor))

        left_side_widget = QWidget()
        left_layout = QVBoxLayout()
        self.add_text_template_button = QPushButton('Add New Text Template', self)
        self.add_text_template_button.clicked.connect(self.on_click_add_text_template)

        self.delete_current_text_template_button = QPushButton('Delete Current Text Template', self)
        self.delete_current_text_template_button.clicked.connect(self.on_click_delete_current_text_template)

        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.on_click_reset)
        self.reset_button.clicked.connect(lambda _: self.frame_properties_panel.on_selected_frame_change())
        self.reset_button.clicked.connect(self.frames_viewer.update)

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

        self.template_selection_panel = TemplateSelectionPanel(self)
        self.selected_text_template_changed.connect(
            lambda _: self.frame_properties_panel.on_selected_frame_change()
        )
        self.selected_text_template_changed.connect(
            lambda _: self.template_selection_panel.refresh_selector()
        )
        self.selected_text_template_changed.connect(
            lambda _: self.frames_viewer.update()
        )

        left_layout.addWidget(self.frames_viewer)
        left_layout.addWidget(self.frames_slider)
        left_layout.addWidget(self.template_selection_panel)
        left_layout.addWidget(self.add_text_template_button)
        left_layout.addWidget(self.delete_current_text_template_button)
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
            self.changeSelectedTextTemplate(self.meme_template.templates_list[0].id)
            del self.render_options[template_id]

    def on_click_add_text_template(self):
        initial_template_id = f"Text {1 + len(self.meme_template.templates_list)}"
        self.meme_template.add_template(TextAnimationTemplate(template_id=initial_template_id))
        self.render_options[initial_template_id] = initial_template_id
        self.changeSelectedTextTemplate(initial_template_id)

    def changeSelectedTextTemplate(self, template_id: str):
        self.selected_text_template = self.meme_template[template_id]
        self.selected_text_template_changed.emit(template_id)

    def render_sequence(self):
        pass
        self.sequence = self.original_sequence.copy()
        self.meme_template.render_spiral(sequence=self.sequence,
                                         render_options=self.render_options,
                                         current_ind=self.current_frame_index)

    def load_new_sequence(self, sequence: GifSequence):
        self.original_sequence = sequence
        self.sequence = self.original_sequence
        self.frames_slider.setMaximum(len(self.sequence) - 1)

    def load_animation_data(self, serialized_meme_template: List):
        self.meme_template = MemeAnimationTemplate.deserialize(serialized_meme_template=serialized_meme_template)
        self.render_options = {key: key for key in self.meme_template.templates_dict.keys()}
        self.changeSelectedTextTemplate(self.meme_template.templates_list[0].id)
        self.frame_properties_panel.on_selected_frame_change()

    @QtCore.pyqtSlot(int)
    def on_change_frame(self, index: int):
        self.current_frame_index = index

    @QtCore.pyqtSlot(tuple)
    def handle_image_press(self, position: Tuple[int, int]):
        self.selected_text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.current_frame_index, position=position)
        )
        self.frame_properties_panel.on_selected_frame_change()

    @QtCore.pyqtSlot()
    def on_click_save(self):
        self.render_sequence()
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save Template as',
                                                   'c:\\', "JSON file (*.json)")
        if file_path:
            with open(file_path, mode='w') as f:
                json.dump(self.meme_template.serialize(), fp=f, indent=4)
            gif_path = Path(file_path).with_suffix(".gif")
            self.original_sequence.save(str(gif_path), is_loop=True)
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

    @QtCore.pyqtSlot()
    def on_click_reset_all(self):
        for text_template in self.meme_template.templates_list:
            text_template.keyframes.reset()
        self.frames_viewer.update()


if __name__ == '__main__':
    app = QApplication([])
    _id = QtGui.QFontDatabase.addApplicationFont("Montserrat-Regular.ttf")
    print(QtGui.QFontDatabase.applicationFontFamilies(_id))

    text_template = TextAnimationTemplate("Text 1")
    text_template2 = TextAnimationTemplate("Text 2")
    meme_template = MemeAnimationTemplate(text_templates=[text_template])
    window = MainWindow("trump.gif", meme_template=meme_template)
    window.show()

    app.exec_()
