import time

import numpy as np
import pytest
from PyQt5 import QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication
from pytestqt.qt_compat import qt_api
import qimage2ndarray

from animator import MainWindow
from gif import GifSequence, GifFrame
from templates import TextAnimationTemplate, MemeAnimationTemplate


@pytest.fixture
def mainwindow():
    _id = QtGui.QFontDatabase.addApplicationFont("Montserrat-Regular.ttf")
    default_sequence = GifSequence.from_frames([GifFrame.from_array(array=np.zeros((400, 400)), duration=50)])
    default_text_template = TextAnimationTemplate("Text 1")
    default_meme_template = MemeAnimationTemplate(text_templates=[default_text_template])
    window = MainWindow(sequence=default_sequence, meme_template=default_meme_template)
    window.show()

    return window


def test_add_remove_text_template(qtbot, mainwindow):
    qtbot.addWidget(mainwindow)
    templates = mainwindow.template_selection_panel.combo

    # click the remove button, should not do anything if only 1 text
    qtbot.mouseClick(mainwindow.delete_current_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1']

    # click the add new button and expect now 4 Texts
    qtbot.mouseClick(mainwindow.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(mainwindow.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(mainwindow.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1', 'Text 2', 'Text 3', 'Text 4']

    # Remove the last one
    qtbot.mouseClick(mainwindow.delete_current_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1', 'Text 2', 'Text 3']


def test_position_text_template(qtbot, mainwindow):
    qtbot.addWidget(mainwindow)
    # pix = QtGui.QPixmap(mainwindow.frames_viewer.size())
    # mainwindow.frames_viewer.render(pix)
    correct_default_frame_viewer = QtGui.QImage('test_assets/images/default_frame_viewer.png')
    test_default_frame_viewer = mainwindow.frames_viewer.grab().toImage()
    test_default_frame_viewer.save("/tmp/test_position_text_template.png", quality=100)
    # screen = QApplication.primaryScreen()
    # screenshot = screen.grabWindow(mainwindow.winId())
    # screenshot.save('test.png', 'png')

    assert QtGui.QImage('/tmp/test.png') == correct_default_frame_viewer


def test_click_to_select(qtbot, mainwindow):
    qtbot.addWidget(mainwindow)
    # Move the default text to somewhere else
    qtbot.mouseClick(mainwindow.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    qtbot.wait(10)
    # Create new text, should be selected automatically now
    qtbot.mouseClick(mainwindow.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.wait(10)
    # Click on the previous, moved, text and expect it to be selected now, instead of moving the new text
    qtbot.mouseClick(mainwindow.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    qtbot.wait(10)
    assert mainwindow.selected_text_template.id == 'Text 1'
