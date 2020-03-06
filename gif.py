import copy
from pathlib import Path
from typing import Iterable, Union, Optional

import imageio
from PIL import Image, GifImagePlugin
from PIL import ImageSequence
import numpy as np
import cv2.cv2 as cv2
import itertools

from moviepy.video.io.VideoFileClip import VideoFileClip


class GifSequence:
    def __init__(self, images: Iterable[Image.Image], is_loop: bool = False):
        list_of_frames = []
        list_of_durations = []

        for image in images:
            list_of_frames.append(np.array(image.convert('RGB')))
            list_of_durations.append(image.info['duration'])

        self.is_loop: bool = is_loop
        self._frames_array: np.ndarray = np.array(list_of_frames)
        self._durations_array: np.ndarray = np.array(list_of_durations)

    def copy(self):
        return copy.deepcopy(self)

    @classmethod
    def open(cls, path: Union[str, Path], is_loop: bool = False, method: str = "pillow"):
        image_file = Image.open(path)
        assert type(image_file) is GifImagePlugin.GifImageFile

        if method == "pillow":
            return cls(ImageSequence.Iterator(image_file), is_loop=is_loop)
        elif method == "mpy":
            durations = [image.info['duration'] for image in ImageSequence.Iterator(image_file)]
            clip = VideoFileClip(path)
            frames = []
            for frame, duration in zip(clip.iter_frames(), durations):
                frames.append(GifFrame.from_array(array=frame, duration=duration))
            return GifSequence.from_frames(frames, is_loop=is_loop)
        else:
            raise ValueError("Method must be either pillow or mpy (moviepy)")

    @classmethod
    def from_frames(cls, frames: Iterable['GifFrame'], is_loop: bool = False):
        frames_array = np.stack([frame.array for frame in frames], axis=0)
        durations_array = np.array([frame.duration for frame in frames])

        sequence = cls.__new__(cls)
        sequence._frames_array = frames_array
        sequence._durations_array = durations_array
        sequence.is_loop = is_loop
        return sequence

    def show(self):
        frames_iterator = zip(self._frames_array, self._durations_array)
        if self.is_loop:
            frames_iterator = itertools.cycle(frames_iterator)

        for frame, duration in frames_iterator:
            cv2.imshow("Frame", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if cv2.waitKey(duration) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()

    def save(self, path: Union[Path, str]):
        images = list(self._frames_array)
        durations_in_seconds = list(self._durations_array / 1000)
        imageio.mimsave(path, images, duration=durations_in_seconds, loop=int(not self.is_loop))

        # MPY
        # clip = ImageSequenceClip(list(self._frames_array), durations=list(self._durations_array / 1000))
        # clip.write_gif(path, fps=12)

        # PIL
        # images[0].save(path, save_all=True, append_images=images[1:], optimize=False,
        #                duration=list(self._durations_array), loop=int(not self.is_loop))

    def __add__(self, other: Union['GifSequence', 'GifFrame']) -> 'GifSequence':
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
        if isinstance(item, slice):
            indices = range(*item.indices(len(self)))
            return GifSequence.from_frames([self.__getitem__(index) for index in indices],
                                           is_loop=self.is_loop)
        elif isinstance(item, int):
            return GifFrame.from_array(array=self._frames_array[item],
                                       duration=self._durations_array[item])
        else:
            raise TypeError(f"Expected int or slice, but got {type(item)}")

    def __setitem__(self, key: int, frame: 'GifFrame'):
        assert isinstance(key, int)
        self._frames_array[key] = frame.array
        self._durations_array[key] = frame.duration

    def __len__(self) -> int:
        return len(self._frames_array)


class GifFrame:
    def __init__(self, image: Image.Image):
        self._image: np.ndarray = np.array(image.convert('RGB'))
        self.duration: int = image.info['duration']

    @classmethod
    def from_array(cls, array: np.ndarray, duration: int) -> 'GifFrame':
        frame = cls.__new__(cls)
        frame._image = array
        frame.duration = duration
        return frame

    @property
    def array(self) -> np.ndarray:
        return self._image

    @property
    def shape(self):
        return self._image.shape

    def __add__(self, other: Union['GifFrame', GifSequence]) -> GifSequence:
        if isinstance(other, GifFrame):
            return GifSequence.from_frames([self, other])
        elif isinstance(other, GifSequence):
            return GifSequence.from_frames([self]) + other
        else:
            raise TypeError(f"Expected GifFrame or GifSequence, got {type(other)}")

    def __mul__(self, other: int) -> GifSequence:
        assert isinstance(other, int)
        return GifSequence.from_frames([self for _ in range(other)])

    def __rmul__(self, other: int) -> GifSequence:
        assert isinstance(other, int)
        return GifSequence.from_frames([self for _ in range(other)])

    def to_image(self) -> Image.Image:
        image = Image.fromarray(self._image)
        image.info['duration'] = self.duration
        return image

    def show(self, duration: Optional[int] = None):
        if duration is None:
            duration = self.duration
        cv2.imshow("Frame", cv2.cvtColor(self._image, cv2.COLOR_BGR2RGB))
        cv2.waitKey(duration)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    seq = GifSequence.open('tenor.gif', is_loop=True)
    seq.show()
    seq.save('tenor_output.gif')
    seq_short = 10 * seq[0] + seq[-1] * 20 + seq[2] * 10
    seq_short.is_loop = True
    print(len(seq_short))
    seq_short.show()
    seq_short.save('modified_output.gif')
# seq.show()
# frame = seq[5].show(duration=5000)
