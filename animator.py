import sys
import os
from pathlib import Path
from typing import Tuple, Union

from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal as Signal
import qimage2ndarray
import numpy as np
from cv2 import cv2

from gif import GifSequence
from keyframes import TextAnimationKeyframe
from templates import TextAnimationTemplate


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


# Subclass QMainWindow to customise your application's main window
class MainWindow(QMainWindow):

    def __init__(self, path_to_gif: Union[Path, str], *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle(f"Animator - {os.path.basename(path_to_gif)}")
        self.original_sequence = GifSequence.open(path=path_to_gif, method="mpy")
        self.sequence = self.original_sequence

        self.text_template = TextAnimationTemplate()

        self.current_frame_index = 0
        self.frames_slider = QSlider(Qt.Horizontal, self)
        self.frames_slider.setMinimum(0)
        self.frames_slider.setMaximum(len(self.sequence) - 1)
        self.frames_slider.setTickPosition(QSlider.TicksBelow)

        self.frames_slider.valueChanged[int].connect(self.on_change_frame)
        self.image_view = PictureLabel(self.sequence[self.frames_slider.value()].array)
        self.image_view.pictureClicked.connect(self.handle_image_press)

        self.render_sequence()
        self.refresh_frame()

        widget = QWidget()
        layout = QVBoxLayout()
        self.button = QPushButton('Save', self)
        self.button.clicked.connect(lambda: self.sequence.save("output.gif"))

        layout.addWidget(self.image_view)
        layout.addWidget(self.frames_slider)
        layout.addWidget(self.button)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def render_sequence(self):
        self.sequence = self.text_template.render(self.original_sequence, "Hello")

    def refresh_frame(self):
        self.image_view.setImage(self.sequence[self.frames_slider.value()].array)

    def on_change_frame(self, index: int):
        self.current_frame_index = index
        self.refresh_frame()

    def handle_image_press(self, position: Tuple[int, int]):
        x, y = position
        self.text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.current_frame_index, position=position)
        )
        self.render_sequence()
        self.refresh_frame()
        print(x, y)


if __name__ == '__main__':
    app = QApplication([])

    window = MainWindow("trump.gif")
    window.show()

    app.exec_()
