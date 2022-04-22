import json
import os
from pathlib import Path
from typing import Tuple, List, Optional

import numpy as np
import qimage2ndarray
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal as Signal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QPaintEvent, QMouseEvent, QPainterPath
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider, QVBoxLayout, QWidget, QPushButton, \
    QGridLayout, QGroupBox, QFormLayout, QLineEdit, QHBoxLayout, QFileDialog, QAction, QComboBox, QSizePolicy, \
    QStyle, QRubberBand, QColorDialog, QPlainTextEdit, QMessageBox

from gif import GifSequence, GifFrame
from keyframes import TextAnimationKeyframe
from templates import TextAnimationTemplate, MemeAnimationTemplate


class TemplateSelectionPanel(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent

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
        self.parent.change_selected_text_template(template_id)

    def refresh_selector(self):
        self.combo.clear()
        self.combo.addItems([template.id for template in self.parent.meme_template.templates_list])
        self.combo.setCurrentIndex(self.parent.meme_template.templates_list.index(self.parent.selected_text_template))


class ColorButton(QPushButton):
    """
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).
    """

    colorChangedFromDialog = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("ColorButton")
        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.on_color_picker)

    def set_color(self, color: Optional[QColor]):
        if color != self._color:
            self._color = color

        if self._color:
            self.setStyleSheet("#ColorButton {background-color: %s}" % self._color.name())
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def on_color_picker(self):
        """
        Show color-picker dialog to select color.

        Qt will use the native dialog by default.

        """
        dlg = QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        if dlg.exec_():
            self.set_color(dlg.currentColor())
            # noinspection PyUnresolvedReferences
            self.colorChangedFromDialog.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.set_color(None)
            # noinspection PyUnresolvedReferences
            self.colorChangedFromDialog.emit()

        return super().mousePressEvent(e)


class TextTemplatePropertiesPanel(QWidget):
    text_template_properties_changed = Signal()

    def __init__(self, parent):
        super().__init__()

        self.is_enabled = False
        self.parent = parent
        self.keyframe: Optional[TextAnimationKeyframe] = None
        layout = QGridLayout()
        self.setLayout(layout)

        group_box = QGroupBox("Text Template Properties")
        layout.addWidget(group_box)

        self.textColorButton = ColorButton()

        self.textColorButton.set_color(QColor("white"))
        self.backgroundColorButton = ColorButton()
        self.strokeWidthEdit = QLineEdit()
        self.yEdit = QLineEdit()
        self.textValue = QPlainTextEdit()
        self.strokeColorButton = ColorButton()
        self.strokeColorButton.set_color(QColor("black"))

        self.strokeWidthEdit.setText("2")

        self.textValue.textChanged.connect(self.on_editing_finished)
        # noinspection PyUnresolvedReferences
        self.textColorButton.colorChangedFromDialog.connect(self.on_editing_finished)
        # noinspection PyUnresolvedReferences
        self.backgroundColorButton.colorChangedFromDialog.connect(self.on_editing_finished)
        self.strokeWidthEdit.editingFinished.connect(self.on_editing_finished)
        # noinspection PyUnresolvedReferences
        self.strokeColorButton.colorChangedFromDialog.connect(self.on_editing_finished)

        layout = QFormLayout()
        layout.addRow(QLabel("Text Value"), self.textValue)
        layout.addRow(QLabel("Text Color"), self.textColorButton)
        layout.addRow(QLabel("Background Color"), self.backgroundColorButton)
        layout.addRow(QLabel("Stroke"), self.strokeWidthEdit)
        layout.addRow(QLabel("Stroke Color"), self.strokeColorButton)
        group_box.setLayout(layout)

    def refresh(self):
        text_template = self.parent.selected_text_template
        self.textValue.setPlainText(str(text_template.text_value))
        self.textColorButton.set_color(QColor(text_template.text_color) if text_template.text_color else None)
        self.backgroundColorButton.set_color(QColor(text_template.background_color)
                                             if text_template.background_color else None)
        self.strokeColorButton.set_color(QColor(text_template.stroke_color) if text_template.stroke_color else None)
        self.strokeWidthEdit.setText(str(text_template.stroke_width))

    def on_editing_finished(self):
        text_value_str = self.textValue.toPlainText()
        stroke_width_str = self.strokeWidthEdit.text()
        text_color = self.textColorButton.color()
        background_color = self.backgroundColorButton.color()
        stroke_color = self.strokeColorButton.color()

        try:
            stroke_width = int(stroke_width_str) if stroke_width_str else 0
            text_color_name = text_color.name() if text_color is not None else None
            background_color_name = background_color.name() if background_color is not None else None
            stroke_color_name = stroke_color.name() if stroke_color is not None else None

            self.parent.selected_text_template.text_value = text_value_str
            self.parent.selected_text_template.stroke_width = stroke_width
            self.parent.selected_text_template.text_color = text_color_name
            self.parent.selected_text_template.background_color = background_color_name
            self.parent.selected_text_template.stroke_color = stroke_color_name

        except ValueError:
            self.parent.statusBar().showMessage("Invalid properties for template. Please try again.")

        # noinspection PyUnresolvedReferences
        self.text_template_properties_changed.emit()


class TrackerPropertiesPanel(QWidget):
    tracker_properties_changed = Signal()

    def __init__(self, parent: 'MainWindow'):
        super().__init__()

        self.parent = parent
        layout = QGridLayout()
        self.setLayout(layout)

        group_box = QGroupBox("Tracker Properties")
        layout.addWidget(group_box)

        self.toggle_tracker_button = QPushButton('Tracker Mode')
        self.toggle_tracker_button.setCheckable(True)
        self.toggle_tracker_button.setChecked(False)
        self.toggle_tracker_button.clicked.connect(self.on_tracker_mode)

        self.track_next_frame_button = QPushButton('Track Next Frame')
        self.track_next_frame_button.clicked.connect(self.on_next_frame)
        self.track_previous_frame_button = QPushButton('Track Previous Frame')
        self.track_previous_frame_button.clicked.connect(self.on_prev_frame)

        layout = QFormLayout()
        layout.addRow(self.toggle_tracker_button)
        layout.addRow(self.track_next_frame_button)
        layout.addRow(self.track_previous_frame_button)
        group_box.setLayout(layout)

    def on_tracker_mode(self):
        tracker_mode_enabled = self.parent.frames_viewer.tracker_mode
        self.parent.frames_viewer.tracker_mode = not tracker_mode_enabled
        self.parent.frames_slider.setEnabled(tracker_mode_enabled)
        self.parent.selected_text_template.tracker.reset()
        # noinspection PyUnresolvedReferences
        self.tracker_properties_changed.emit()

    def on_next_frame(self):
        self.track_frame(1)

    def on_prev_frame(self):
        self.track_frame(-1)

    def track_frame(self, frame_diff):
        if not self.parent.selected_text_template.tracker.active:
            return
        frame_num = self.parent.current_frame_index
        new_frame_num = frame_num + frame_diff
        if new_frame_num < 0 or new_frame_num > len(self.parent.sequence) - 1:
            return
        # Get current text keyframe, so we can access the position, create one from the current position
        # if it doesn't exist
        if frame_num not in self.parent.selected_text_template.keyframes.keyframes_frames_indices:
            keyframe = self.parent.selected_text_template.keyframes.interpolate(frame_num)
        else:
            keyframe = self.parent.selected_text_template.keyframes.get_keyframe(frame_num)
        # Get the new frame and run the tracker on it to get the new bounding box
        new_frame = qimage2ndarray.rgb_view(self.parent.frames_viewer.pixmaps[new_frame_num].toImage())
        delta = self.parent.selected_text_template.tracker.update(new_frame)
        # Calculate the new keyframe position as the old position plus the delta we get from the tracker
        new_position = (keyframe.x + delta.x(), keyframe.y + delta.y())
        new_keyframe = TextAnimationKeyframe(
            frame_ind=new_frame_num,
            position=new_position
        )
        self.parent.selected_text_template.keyframes.insert_keyframe(new_keyframe)

        # Update the viewer to the next frame
        self.parent.frames_slider.setValue(new_frame_num)


class FramePropertiesPanel(QWidget):
    def __init__(self, parent):
        super().__init__()

        self.is_enabled = False
        self.parent = parent
        self.keyframe: Optional[TextAnimationKeyframe] = None
        layout = QGridLayout()
        self.setLayout(layout)

        group_box = QGroupBox("Frame Properties")
        layout.addWidget(group_box)

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
        group_box.setLayout(layout)

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
                current_keyframe = self.parent.selected_text_template.keyframes.get_keyframe(
                    self.parent.current_frame_index
                )

                if current_keyframe != new_keyframe:
                    self.parent.selected_text_template.keyframes.insert_keyframe(new_keyframe)
                    self.parent.frames_viewer.update()
            except ValueError:
                self.parent.statusBar().showMessage("Invalid values for keyframe. Please try again.")

    @QtCore.pyqtSlot(bool)
    def on_toggle_keyframe(self, is_add: bool):
        keyframes_collection = self.parent.selected_text_template.keyframes
        frame_ind = int(self.frameEdit.text())
        if is_add:
            keyframes_collection.insert_keyframe(keyframes_collection.interpolate(frame_ind))
        else:
            keyframes_collection.remove_keyframe(frame_ind)
        self.on_selected_frame_change()
        self.parent.frames_viewer.update()

    @QtCore.pyqtSlot(int)
    def on_selected_frame_change(self):
        frame_num = self.parent.current_frame_index
        keyframes_collection = self.parent.selected_text_template.keyframes
        if frame_num in keyframes_collection.keyframes_frames_indices:
            keyframe = keyframes_collection.get_keyframe(frame_num)
            self.update_form(frame_ind=frame_num, x=keyframe.x, y=keyframe.y, text_size=keyframe.text_size)
            self.toggleKeyframeButton.setChecked(True)
            self.toggleKeyframeButton.setText("Remove Keyframe")
            self.enable()
        else:
            self.disable()
            keyframe = keyframes_collection.interpolate(frame_ind=frame_num)
            self.update_form(frame_ind=frame_num, x=keyframe.x, y=keyframe.y, text_size=keyframe.text_size)
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

    def update_form(self, frame_ind: int, x: int, y: int, text_size: int):
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
        self.pixmaps = []
        self.load_sequence(sequence)
        self.selected_frame_ind = 0
        self.text_template_to_rect = {}
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.rubberBand.show()
        self.current_pixmap = self.pixmaps[self.selected_frame_ind]
        self.setPixmap(self.current_pixmap)

        # Set tracker mode, if this mode is active clicking and dragging will create a tracking rectangle on the viewer
        # instead of moving the current text template.
        self.tracker_mode = False

    def load_sequence(self, sequence: GifSequence):
        self.pixmaps = [QPixmap.fromImage(qimage2ndarray.array2qimage(frame.array)) for frame in sequence]

    def mousePressEvent(self, e: QMouseEvent):
        if self.tracker_mode:
            self.parent.selected_text_template.tracker.begin = e.pos()
            self.parent.selected_text_template.tracker.end = e.pos()
        else:
            for text_template in self.parent.meme_template.templates_list:
                if text_template.id in self.text_template_to_rect \
                        and text_template.id != self.parent.selected_text_template.id \
                        and self.text_template_to_rect[text_template.id].contains(e.pos()):
                    self.parent.change_selected_text_template(text_template.id)
                    self.update()
                    return

            self.parent.selected_text_template.keyframes.insert_keyframe(
                TextAnimationKeyframe(frame_ind=self.selected_frame_ind, position=(e.x(), e.y()))
            )
            self.parent.frame_properties_panel.on_selected_frame_change()
        self.update()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self.tracker_mode:
            self.parent.selected_text_template.tracker.end = e.pos()
        else:
            self.parent.selected_text_template.keyframes.insert_keyframe(
                TextAnimationKeyframe(frame_ind=self.selected_frame_ind, position=(e.x(), e.y()))
            )
            self.parent.frame_properties_panel.on_selected_frame_change()
        self.update()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.tracker_mode:
            frame = qimage2ndarray.rgb_view(self.current_pixmap.toImage())
            self.parent.selected_text_template.tracker.initialize(frame)

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen()
        brush = QtGui.QBrush()
        brush.setStyle(Qt.SolidPattern)

        font = QtGui.QFont()
        font.setFamily('Montserrat')
        self.text_template_to_rect = {}

        for text_template in self.parent.meme_template.templates_list:
            pen.setColor(QtGui.QColor(text_template.text_color))
            painter.setPen(pen)

            keyframe = text_template.keyframes.interpolate(self.selected_frame_ind)
            font.setPixelSize(keyframe.text_size)
            painter.setFont(font)

            margin = 10
            x, y, width, height = text_template.get_text_bounding_box(center_position=keyframe.position,
                                                                      font_size=keyframe.text_size,
                                                                      text=text_template.text_value)
            text_rect = QRect(x, y, width, height)
            self.text_template_to_rect[text_template.id] = text_rect

            background_rect = None
            if text_template.background_color is not None:
                background_rect = text_rect.adjusted(-margin, -margin, margin, margin)
                painter.fillRect(background_rect, QColor(text_template.background_color))
            if text_template.id == self.parent.selected_text_template.id:
                rubber_rect = background_rect if background_rect is not None else text_rect
                self.rubberBand.setGeometry(rubber_rect)

            if text_template.stroke_width:
                painter.setRenderHint(QPainter.Antialiasing)
                brush.setColor(QColor(text_template.text_color))
                painter.setBrush(brush)

                pen.setColor(QColor(text_template.stroke_color))
                pen.setWidth(text_template.stroke_width * 2)
                painter.setPen(pen)

                path = QPainterPath()
                # Split multiline text
                lines = text_template.text_value.split('\n')
                # Reverse it so when multiline, the first line is on top
                lines.reverse()
                # Split up the height of the bounding box (which already correctly scales according to multiline)
                step = height / len(lines)
                # For each line, draw it
                for i, line in enumerate(lines):
                    # cfr. https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html#PySide2.QtGui.PySide2
                    # .QtGui.QPainterPath.addText Text is drawn from the base of the font, which is not in the middle
                    # of the bounding box By default Pillow adds a bounding box margin of 4 pixels, so we subtract
                    # that from the edge coordinate to get the correct height to draw the text. Then we subtract
                    # i*step which is basically "which line number should this text be on"
                    path.addText(text_rect.bottomLeft().x(), text_rect.bottomLeft().y() - 4 - i*step, font, line)
                painter.strokePath(path, pen)
                painter.fillPath(path, brush)

            else:
                painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignVCenter, text_template.text_value)

        # Paint the tracking rectangle if applicable
        if self.tracker_mode:
            tracker_rect_brush = QtGui.QColor(100, 10, 10, 40)
            painter.setBrush(tracker_rect_brush)
            painter.drawRect(self.parent.selected_text_template.tracker.rect)
        painter.end()

    def handle_frame_update(self, frame_ind: int):
        self.selected_frame_ind = frame_ind
        self.current_pixmap = self.pixmaps[self.selected_frame_ind]
        self.setPixmap(self.current_pixmap)


class MainWindow(QMainWindow):
    selected_text_template_changed = Signal(str)

    def __init__(self, sequence: GifSequence, meme_template: MemeAnimationTemplate, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle(f"Animator")
        self.sequence = sequence
        self.meme_template = meme_template
        self.selected_text_template: TextAnimationTemplate = meme_template.templates_list[0]
        self.current_frame_index = 0

        # self.keyframes_indicator = KeyframesIndicator(self)
        self.frame_properties_panel = FramePropertiesPanel(parent=self)
        self.frame_properties_panel.on_selected_frame_change()

        self.tracker_properties_panel = TrackerPropertiesPanel(parent=self)

        self.text_template_properties_panel = TextTemplatePropertiesPanel(parent=self)
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.connect(lambda: self.text_template_properties_panel.refresh())
        # self.frame_properties_panel.toggleKeyframeButton.clicked.connect(self.keyframes_indicator.refresh)

        self.frames_slider = QSlider(Qt.Horizontal, self)
        self.frames_slider.setMinimum(0)
        self.frames_slider.setMaximum(len(self.sequence) - 1)
        self.frames_slider.setTickPosition(QSlider.TicksBelow)
        self.frames_slider.valueChanged[int].connect(self.on_change_frame)
        self.frames_slider.valueChanged[int].connect(self.frame_properties_panel.on_selected_frame_change)

        self.frames_viewer = FramesViewer(sequence=self.sequence, parent=self)
        self.frames_slider.valueChanged[int].connect(self.frames_viewer.handle_frame_update)
        self.frames_viewer.setCursor(QtGui.QCursor(Qt.CrossCursor))

        # noinspection PyUnresolvedReferences
        self.text_template_properties_panel.text_template_properties_changed.connect(self.frames_viewer.update)
        # noinspection PyUnresolvedReferences
        self.tracker_properties_panel.tracker_properties_changed.connect(self.frames_viewer.update)

        left_side_widget = QWidget()
        left_layout = QVBoxLayout()
        self.add_text_template_button = QPushButton('Add New Text Template', self)
        self.add_text_template_button.clicked.connect(self.on_click_add_text_template)

        self.delete_current_text_template_button = QPushButton('Delete Current Text Template', self)
        self.delete_current_text_template_button.clicked.connect(self.on_click_delete_current_text_template)

        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.on_click_reset)
        self.reset_button.clicked.connect(lambda: self.frame_properties_panel.on_selected_frame_change())
        self.reset_button.clicked.connect(self.frames_viewer.update)

        load_action = QAction("&Load animation", self)
        load_action.setShortcut("Ctrl+O")
        load_action.setStatusTip('Load animation and existing template data if possible')
        load_action.triggered.connect(self.on_click_load)

        save_action = QAction("&Save template as", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip('Save animation data to a JSON file')
        save_action.triggered.connect(self.on_click_save)

        export_action = QAction("&Export as gif", self)
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip('Export project as gif')
        export_action.triggered.connect(self.on_click_export)

        reset_all_action = QAction("&Reset all animation data", self)
        reset_all_action.setShortcut("Ctrl+R")
        reset_all_action.setStatusTip('Reset animation data in all text templates')
        reset_all_action.triggered.connect(self.on_click_reset_all)

        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('&File')
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)
        file_menu.addAction(export_action)
        file_menu = main_menu.addMenu('&Animation')
        file_menu.addAction(reset_all_action)

        self.template_selection_panel = TemplateSelectionPanel(self)
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.connect(
            lambda: self.frame_properties_panel.on_selected_frame_change()
        )
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.connect(
            lambda: self.template_selection_panel.refresh_selector()
        )
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.connect(
            lambda: self.frames_viewer.update()
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
        right_layout.addWidget(self.text_template_properties_panel)
        right_layout.addWidget(self.tracker_properties_panel)
        right_side_widget.setLayout(right_layout)

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_side_widget)
        main_layout.addWidget(right_side_widget)
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

        # Trigger the initial refresh
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.emit(self.meme_template.templates_list[0].id)

    def on_click_delete_current_text_template(self):
        if len(self.meme_template.templates_list) > 1:
            self.meme_template.remove_template(self.selected_text_template)
            self.change_selected_text_template(self.meme_template.templates_list[0].id)

    def on_click_add_text_template(self):
        initial_template_id = f"Text {1 + len(self.meme_template.templates_list)}"
        self.meme_template.add_template(TextAnimationTemplate(template_id=initial_template_id))
        self.change_selected_text_template(initial_template_id)

    def change_selected_text_template(self, template_id: str):
        self.selected_text_template = self.meme_template[template_id]
        # noinspection PyUnresolvedReferences
        self.selected_text_template_changed.emit(template_id)

    def load_new_sequence(self, sequence: GifSequence):
        self.sequence = sequence
        self.frames_slider.setMaximum(len(self.sequence) - 1)
        self.frames_viewer.load_sequence(sequence)
        self.frames_viewer.handle_frame_update(frame_ind=self.current_frame_index)

    def load_animation_data(self, serialized_meme_template: List):
        self.meme_template = MemeAnimationTemplate.deserialize(serialized_meme_template=serialized_meme_template)
        self.change_selected_text_template(self.meme_template.templates_list[0].id)
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
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save Template as',
                                                   str(Path.home()), "JSON file (*.json)")
        if file_path:
            with open(file_path, mode='w') as f:
                json.dump(self.meme_template.serialize(), fp=f, indent=4)
            gif_path = Path(file_path).with_suffix(".gif")
            try:
                self.sequence.save(str(gif_path), is_loop=True)
            except PermissionError:
                self.statusBar().showMessage(f"PermissionError: Couldn't save file to this location")

            self.statusBar().showMessage(f'Saved template to {file_path} and {gif_path}')
        else:
            self.statusBar().showMessage(f'File not saved')

    @QtCore.pyqtSlot()
    def on_click_load(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Load Animation',
                                                   str(Path.home()), "GIF file (*.gif)")
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
    def on_click_export(self):
        if self.sequence:
            gif = self.sequence
            file_path, _ = QFileDialog.getSaveFileName(
                self, 'Save animation as', str(Path.home()), "GIF file (*.gif)"
            )
            self.meme_template.render(gif, list(self.meme_template.templates_dict.keys())).save(file_path, is_loop=True)
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Done!")
            dlg.setText(f"The gif was successfully rendered to {file_path}")
            dlg.exec()
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error!")
            dlg.setText(f"Not a valid gif.")
            dlg.exec()

    @QtCore.pyqtSlot()
    def on_click_reset(self):
        self.selected_text_template.keyframes.reset()

    @QtCore.pyqtSlot()
    def on_click_reset_all(self):
        for text_template in self.meme_template.templates_list:
            text_template.keyframes.reset()
        self.frames_viewer.update()

    def keyPressEvent(self, e):
        """
        Add hotkeys
        """
        if not self.selected_text_template.tracker.active:
            if e.key() == Qt.Key_L:
                self.frames_slider.setValue(self.current_frame_index + 1)
            elif e.key() == Qt.Key_J:
                self.frames_slider.setValue(self.current_frame_index - 1)
        else:
            if e.key() == Qt.Key_L:
                self.tracker_properties_panel.on_next_frame()
            elif e.key() == Qt.Key_J:
                self.tracker_properties_panel.on_prev_frame()


if __name__ == '__main__':
    app = QApplication([])
    _id = QtGui.QFontDatabase.addApplicationFont("Montserrat-Regular.ttf")
    obama_sequence = GifSequence.open('/home/victor/Pictures/cars-race.gif')
    default_sequence = GifSequence.from_frames(10*[GifFrame.from_array(array=np.zeros((400, 400)), duration=50)])
    default_text_template = TextAnimationTemplate("Text 1")
    default_meme_template = MemeAnimationTemplate(text_templates=[default_text_template])
    window = MainWindow(sequence=obama_sequence, meme_template=default_meme_template)
    window.show()

    app.exec_()
