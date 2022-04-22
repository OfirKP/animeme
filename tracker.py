import logging
import os

import cv2
from PyQt5 import QtCore

logging.basicConfig(format='%(asctime)s | [%(levelname)s] %(message)s', level=os.environ.get('LOGLEVEL', 'INFO'))


class Tracker:
    def __init__(self):
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self._tracker = None
        self.failed = False

    @property
    def rect(self):
        return QtCore.QRect(self.begin, self.end)

    @property
    def active(self):
        """
        Return whether there is a currently active tracking ROI available. This will not be the case either when
        The tracker has just been started or when it failed. In both cases the ROI rectangle will not be in the frame
        and we can't allow going to e.g. the next frame until a new (or first) ROI rectangle is provided which we can
        use to actually track with.
        """
        return self.begin != QtCore.QPoint() and self.end != QtCore.QPoint()

    def add(self):
        self._tracker = cv2.TrackerKCF_create()

    def to_xywh(self):
        bbox = (self.begin.x(), self.begin.y(), abs(self.end.x() - self.begin.x()), abs(self.end.y() - self.begin.y()))
        return bbox

    def center(self):
        center = QtCore.QPoint(int((self.end.x() + self.begin.x()) / 2), int((self.end.y() + self.begin.y()) / 2))
        return center

    def update(self, frame):
        # bbox will be in format (x, y, w, h)
        old_center = self.center()
        ok, new_bbox = self._tracker.update(frame)
        if not ok:
            self.failed = True
            self.begin = QtCore.QPoint()
            self.end = QtCore.QPoint()
            # Return an empty delta so the text doesn't move
            return QtCore.QPoint()
        self.begin = QtCore.QPoint(new_bbox[0], new_bbox[1])
        self.end = QtCore.QPoint(new_bbox[0] + new_bbox[2], new_bbox[1] + new_bbox[3])

        new_center = self.center()
        delta = new_center - old_center
        return delta

    def initialize(self, frame):
        bbox = self.to_xywh()
        # Can this ever be not ok?
        self.add()
        ok = self._tracker.init(frame, bbox)
        self._tracker.update(frame)
        self.failed = not ok
        logging.debug(f'Initialized tracker with failed state {self.failed}')
