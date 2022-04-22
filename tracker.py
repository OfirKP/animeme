import cv2
from PyQt5 import QtCore


class Tracker:
    def __init__(self):
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self._tracker = None

    @property
    def rect(self):
        return QtCore.QRect(self.begin, self.end)

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
        self.begin = QtCore.QPoint(new_bbox[0], new_bbox[1])
        self.end = QtCore.QPoint(new_bbox[0] + new_bbox[2], new_bbox[1] + new_bbox[3])

        new_center = self.center()
        delta = new_center - old_center
        return delta

    def initialize(self, frame):
        bbox = self.to_xywh()
        ok = self._tracker.init(frame, bbox)
        print(ok)
