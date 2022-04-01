import copy
import itertools
from pathlib import Path
from typing import Iterable, Union, Optional

import cv2.cv2 as cv2
import imageio
import numpy as np
from PIL import Image, GifImagePlugin
from PIL import ImageSequence
from moviepy.video.io.VideoFileClip import VideoFileClip


class GifSequence:
    """
    Represents a GIF sequence of frames
    """

    __slots__ = '_frames_array', '_durations_array'

    def __init__(self, images: Iterable[Image.Image]):
        list_of_frames = []
        list_of_durations = []

        for image in images:
            list_of_frames.append(np.asarray(image.convert('RGB')))
            list_of_durations.append(image.info['duration'])

        self._frames_array: np.ndarray = np.array(list_of_frames)
        self._durations_array: np.ndarray = np.array(list_of_durations)

    def copy(self) -> 'GifSequence':
        """
        Returns a copy of the sequence
        :return: a deep-copied gif sequence
        """
        return copy.deepcopy(self)

    @classmethod
    def open(cls, path: Union[str, Path], method: str = "pillow") -> 'GifSequence':
        """
        Create a GifSequence from a GIF file using Pillow or MoviePy
        :param path: path to GIF file
        :param method: method to load GIF frames (pillow or mpy)
        :return: the opened GifSequence
        """
        image_file = Image.open(path)
        assert type(image_file) is GifImagePlugin.GifImageFile

        if method == "pillow":
            return cls(ImageSequence.Iterator(image_file))
        elif method == "mpy":
            durations = [image.info['duration'] for image in ImageSequence.Iterator(image_file)]
            clip = VideoFileClip(path)
            frames = []
            for frame, duration in zip(clip.iter_frames(), durations):
                frames.append(GifFrame.from_array(array=frame, duration=duration))
            return GifSequence.from_frames(frames)
        else:
            raise ValueError("Method must be either pillow or mpy (moviepy)")

    @classmethod
    def from_frames(cls, frames: Iterable['GifFrame']) -> 'GifSequence':
        """
        Create a GIF sequence out of GifFrames
        :param frames: sequence of GifFrames
        :return: new GifSequence
        """
        frames_array = np.stack([frame.array for frame in frames], axis=0)
        durations_array = np.array([frame.duration for frame in frames])

        sequence = cls.__new__(cls)
        sequence._frames_array = frames_array
        sequence._durations_array = durations_array
        return sequence

    def show(self, is_loop: bool = False):
        """
        Preview GifSequence using OpenCV
        :param is_loop: should the preview until quit
        """
        frames_iterator = zip(self._frames_array, self._durations_array)
        if is_loop:
            frames_iterator = itertools.cycle(frames_iterator)

        for frame, duration in frames_iterator:
            cv2.imshow("Frame", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            # Press 'q' to quit preview
            if cv2.waitKey(duration) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()

    def save(self, path: Union[Path, str], is_loop: bool = False):
        """
        Save GifSequence to given path
        :param path: output path
        :param is_loop: should the GIF file be configured to loop forever
        """
        images = list(self._frames_array)
        durations_in_seconds = list(self._durations_array / 1000)
        imageio.mimsave(path, images, duration=durations_in_seconds, loop=int(not is_loop))

    def __add__(self, other: Union['GifSequence', 'GifFrame']) -> 'GifSequence':
        """
        Concatenate GifSequences and GifFrames into a new GifSequence using the '+' operator
        :param other: another GifSequence or GifFrame
        :return: newly created GifSequence
        """
        if isinstance(other, GifSequence):
            # TODO: implement adding frames with different resolutions
            sequence = copy.copy(self)
            sequence._frames_array = np.concatenate((self._frames_array, other._frames_array))
            sequence._durations_array = np.concatenate((self._durations_array, other._durations_array))
            return sequence
        elif isinstance(other, GifFrame):
            return self + GifSequence.from_frames([other])
        else:
            raise TypeError(f"Expected GifSequence or GifFrame, but got {type(other)}")

    def __getitem__(self, item: Union[slice, int]) -> Union['GifSequence', 'GifFrame']:
        """
        Get GifFrame/GifSequence at given index/es
        :param item: index or slice
        :return: GifFrame/GifSequence at given index/es
        """
        if isinstance(item, slice):
            indices = range(*item.indices(len(self)))
            return GifSequence.from_frames([self.__getitem__(index) for index in indices])
        elif isinstance(item, int):
            return GifFrame.from_array(array=self._frames_array[item],
                                       duration=self._durations_array[item])
        else:
            raise TypeError(f"Expected int or slice, but got {type(item)}")

    def __setitem__(self, key: int, frame: 'GifFrame'):
        """
        Set frame at given index
        :param key: index of frame to set
        :param frame: frame to insert in given index
        """
        assert isinstance(key, int)
        self._frames_array[key] = frame.array
        self._durations_array[key] = frame.duration

    def __len__(self) -> int:
        """
        Returns number of frames in the given sequence
        :return: length of sequence
        """
        return len(self._frames_array)


class GifFrame:
    """
    Represents a frame of a GIF sequence
    """

    __slots__ = '_image', 'duration'

    def __init__(self, image: Image.Image):
        self._image: np.ndarray = np.array(image.convert('RGB'))
        self.duration: int = image.info['duration']

    @classmethod
    def from_array(cls, array: np.ndarray, duration: int) -> 'GifFrame':
        """
        Creates a GifFrame from a given array and duration
        :param array: a numpy array of frame in RGB format
        :param duration: duration of frame
        :return: created GifFrame
        """
        frame = cls.__new__(cls)
        frame._image = array
        frame.duration = duration
        return frame

    @property
    def array(self) -> np.ndarray:
        return self._image

    @property
    def shape(self):
        """
        :return: shape of frame array (rows, cols, num_channels)
        """
        return self._image.shape

    def __add__(self, other: Union['GifFrame', GifSequence]) -> GifSequence:
        """
        Concatenates GifFrames or GifFrame and GifSequence to create a new GifSequence
        :param other: another GifFrame or GifSequence
        :return: newly created GifSequence
        """
        if isinstance(other, GifFrame):
            return GifSequence.from_frames([self, other])
        elif isinstance(other, GifSequence):
            return GifSequence.from_frames([self]) + other
        else:
            raise TypeError(f"Expected GifFrame or GifSequence, got {type(other)}")

    def __mul__(self, other: int) -> GifSequence:
        """
        Creates a GifSequence of this frame repeated multiple times
        :param other: number of times to repeat frames
        :return: new GifSequence
        """
        assert isinstance(other, int)
        return GifSequence.from_frames([self for _ in range(other)])

    def __rmul__(self, other: int) -> GifSequence:
        """
        Creates a GifSequence of this frame repeated multiple times
        :param other: number of times to repeat frames
        :return: new GifSequence
        """
        assert isinstance(other, int)
        return GifSequence.from_frames([self for _ in range(other)])

    def to_image(self) -> Image.Image:
        """
        Convert frame into a Pillow image
        :return: converted Pillow image
        """
        image = Image.fromarray(self._image)
        image.info['duration'] = self.duration
        return image

    def show(self, duration: Optional[int] = None):
        """
        Preview GifFrame using OpenCV
        :param duration: length in milliseconds to display the frame (0 is indefinite)
        """
        if duration is None:
            duration = self.duration
        cv2.imshow("Frame", cv2.cvtColor(self._image, cv2.COLOR_BGR2RGB))
        cv2.waitKey(duration)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    seq = GifSequence.open('tenor.gif')
    seq.show()
    seq.save('tenor_output.gif')
    seq_short = 10 * seq[0] + seq[-1] * 20 + seq[2] * 10
    print(len(seq_short))
    seq_short.show()
    seq_short.save('modified_output.gif')
