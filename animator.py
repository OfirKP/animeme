import json
import sys
import os
from functools import lru_cache
from pathlib import Path
from typing import Tuple, Union

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QSlider, QVBoxLayout, QWidget, QPushButton, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal as Signal
import qimage2ndarray
import numpy as np

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


# Subclass QMainWindow to customise your application's main window
class MainWindow(QMainWindow):

    def __init__(self, path_to_gif: Union[Path, str], meme_template: MemeAnimationTemplate, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setWindowTitle(f"Animator - {os.path.basename(path_to_gif)}")
        self.original_sequence = GifSequence.open(path=path_to_gif, method="mpy")
        self.sequence = self.original_sequence

        self.meme_template = meme_template
        self.selected_text_template = meme_template.templates_list[0]
        self.render_options = {key: value for key, value in
                               zip(self.meme_template.templates_dict.keys(), "Lorem Ipsum Dolor mit emet".split())}

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
        self.button.clicked.connect(self.on_click_save)

        layout.addWidget(self.image_view)
        layout.addWidget(self.frames_slider)
        layout.addWidget(self.button)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

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

    def on_change_frame(self, index: int):
        self.current_frame_index = index
        self.refresh_frame()

    @lru_cache(maxsize=8)
    def get_text_size(self, text):
        return self.selected_text_template.font.getsize(text)

    def handle_image_press(self, position: Tuple[int, int]):
        center_x, center_y = position
        text_width, text_height = self.get_text_size(self.render_options[self.selected_text_template.id])

        top_left_x = center_x - text_width // 2
        top_left_y = center_y - text_height // 2

        self.selected_text_template.keyframes.insert_keyframe(
            TextAnimationKeyframe(frame_ind=self.current_frame_index, position=(top_left_x, top_left_y))
        )
        self.render_sequence()

    def on_click_save(self):
        with open('output.json', mode='w') as f:
            json.dump(self.meme_template.serialize(), fp=f, indent=4)
        self.sequence.save("output.gif")
        self.statusBar().showMessage(f'Saved to output.gif')


if __name__ == '__main__':
    app = QApplication([])

    text_template = TextAnimationTemplate("Text 1")
    text_template2 = TextAnimationTemplate("Text 2")
    meme_template = MemeAnimationTemplate(text_templates=[text_template, text_template2])
    window = MainWindow("trump.gif", meme_template=meme_template)
    window.show()

    app.exec_()
