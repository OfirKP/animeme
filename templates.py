from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

import numpy as np

from gif import GifSequence, GifFrame
from keyframes import TextAnimationKeyframeCollection, TextAnimationKeyframe


class AnimationTemplate(ABC):
    __slots__ = 'keyframes',

    @abstractmethod
    def render(self, sequence: GifSequence, content):
        raise NotImplementedError


class TextAnimationTemplate(AnimationTemplate):

    def __init__(self, initial_position: Tuple[int, int], initial_text_size):
        self.keyframes: TextAnimationKeyframeCollection = TextAnimationKeyframeCollection()
        self.keyframes.insert_keyframe(TextAnimationKeyframe(frame_ind=0,
                                                             position=initial_position,
                                                             text_size=initial_text_size))
        self.font = ImageFont.truetype('Montserrat-Regular.ttf', size=initial_text_size)

    def render(self, sequence: GifSequence, content: str):
        rendered_frames = []
        for frame_ind, frame in enumerate(sequence):
            rendered_frames.append(self._render_frame(frame=frame, frame_ind=frame_ind, content=content))
        return GifSequence.from_frames(rendered_frames, is_loop=sequence.is_loop)

    def _render_frame(self, frame: GifFrame, frame_ind: int, content: str) -> GifFrame:
        current_state: TextAnimationKeyframe = self.keyframes.interpolate(frame_ind=frame_ind)
        image = frame.to_image()
        self._draw_outlined_text(image, position=current_state.position, content=content, font=self.font, width=1)
        return GifFrame(image)

    @staticmethod
    def _draw_outlined_text(image, position: Tuple[int, int], content: str, font: ImageFont.ImageFont, width=1):

        black_alpha = 255
        white_alpha = 240

        overlay = Image.new('RGBA', image.size)
        draw = ImageDraw.ImageDraw(overlay, 'RGBA')

        # Draw black text outlines
        for x in range(-width, 1 + width):
            for y in range(-width, 1 + width):
                pos = (position[0] + x, position[1] + y)
                draw.multiline_text(pos, content, (0, 0, 0, black_alpha),
                                    font=font, align='center')

        # Draw inner white text
        draw.text(position, content, (255, 255, 255, white_alpha),
                  font=font, align='center')

        image.paste(overlay, None, overlay)


if __name__ == '__main__':
    template = TextAnimationTemplate(initial_position=(50, 50), initial_text_size=30)

    keyframe1 = TextAnimationKeyframe(frame_ind=3, position=(80, 100))
    keyframe2 = TextAnimationKeyframe(frame_ind=7, position=(150, 50))
    keyframe3 = TextAnimationKeyframe(frame_ind=10, position=(50, 50))
    template.keyframes.insert_keyframe(keyframe1)
    template.keyframes.insert_keyframe(keyframe2)
    template.keyframes.insert_keyframe(keyframe3)

    gif = GifSequence.open('tenor.gif', is_loop=True)
    print(len(gif))
    rendered = template.render(gif, "Hello World!")
    rendered.show()
    rendered.save("hello_world2.gif")
