import numpy as np
import pytest
from PyQt5 import QtGui
from PyQt5.QtCore import QPoint, Qt
from pytestqt.qt_compat import qt_api

from animator import MainWindow
from gif import GifSequence, GifFrame
from templates import TextAnimationTemplate, MemeAnimationTemplate


@pytest.fixture
def main_window():
    _id = QtGui.QFontDatabase.addApplicationFont("Montserrat-Regular.ttf")
    default_sequence = GifSequence.from_frames(10*[GifFrame.from_array(array=np.zeros((400, 400)), duration=50)])
    default_text_template = TextAnimationTemplate("Text 1")
    default_meme_template = MemeAnimationTemplate(text_templates=[default_text_template])
    window = MainWindow(sequence=default_sequence, meme_template=default_meme_template)
    window.show()

    return window


def test_add_remove_text_template(qtbot, main_window):
    qtbot.addWidget(main_window)
    templates = main_window.template_selection_panel.combo

    # click the remove button, should not do anything if only 1 text
    qtbot.mouseClick(main_window.delete_current_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1']

    # click the add new button and expect now 4 Texts
    qtbot.mouseClick(main_window.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(main_window.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(main_window.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1', 'Text 2', 'Text 3', 'Text 4']

    # Remove the last one
    qtbot.mouseClick(main_window.delete_current_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert [templates.itemText(i) for i in range(templates.count())] == ['Text 1', 'Text 2', 'Text 3']


def test_position_text_template(qtbot, main_window):
    qtbot.addWidget(main_window)

    correct_default_frame_viewer = QtGui.QImage('test_assets/images/default_frame_viewer.png')
    test_default_frame_viewer = main_window.frames_viewer.grab().toImage()
    test_default_frame_viewer.save("/tmp/test_position_text_template.png", quality=100)

    assert QtGui.QImage('/tmp/test_position_text_template.png') == correct_default_frame_viewer


def test_click_to_select(qtbot, main_window):
    qtbot.addWidget(main_window)
    # Move the default text to somewhere else
    qtbot.mouseClick(main_window.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    qtbot.wait(100)
    # Create new text, should be selected automatically now
    qtbot.mouseClick(main_window.add_text_template_button, qt_api.QtCore.Qt.MouseButton.LeftButton)
    qtbot.wait(100)
    # Click on the previous, moved, text and expect it to be selected now, instead of moving the new text
    qtbot.mouseClick(main_window.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    qtbot.wait(100)
    assert main_window.selected_text_template.id == 'Text 1'


def test_sticky_keyframes(qtbot, main_window):
    qtbot.addWidget(main_window)
    # Move the default text to somewhere to create an initial keyframe
    qtbot.mouseClick(main_window.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
    # Set the text_size lower
    qtbot.wait(10)
    main_window.frame_properties_panel.textSizeEdit.setText('20')
    qtbot.keyPress(main_window.frame_properties_panel.textSizeEdit, Qt.Key_Enter)
    qtbot.wait(10)
    qtbot.keyPress(main_window.frames_slider, Qt.Key_Right)
    qtbot.wait(10)
    # Click on the previous, moved, text and expect it to be selected now, instead of moving the new text
    qtbot.mouseClick(main_window.frames_viewer, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    qtbot.wait(10)
    assert main_window.selected_text_template.keyframes.get_keyframe(1).text_size == 20
