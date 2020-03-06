from abc import ABC, abstractmethod
from itertools import cycle, islice
from typing import Tuple, Optional, List, Dict, Callable
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
    def __init__(self,
                 template_id: str,
                 initial_position: Optional[Tuple[int, int]] = None,
                 initial_text_size: Optional[int] = None):
        self.id = template_id
        self.keyframes: TextAnimationKeyframeCollection = TextAnimationKeyframeCollection()
        if initial_position is not None or initial_text_size is not None:
            self.keyframes.insert_keyframe(TextAnimationKeyframe(frame_ind=0,
                                                                 position=initial_position,
                                                                 text_size=initial_text_size))
        self.font = ImageFont.truetype('Montserrat-Regular.ttf', size=TextAnimationKeyframeCollection.DEFAULT_TEXT_SIZE)

    def render(self, sequence: GifSequence, content: str):
        rendered_frames = []
        for frame_ind, frame in enumerate(sequence):
            rendered_frames.append(self.render_frame(frame=frame, frame_ind=frame_ind, content=content))
        return GifSequence.from_frames(rendered_frames, is_loop=sequence.is_loop)

    def render_frame(self, sequence: GifSequence, frame_ind: int, content: str, inplace: bool = False) -> GifFrame:
        current_state: TextAnimationKeyframe = self.keyframes.interpolate(frame_ind=frame_ind)
        image = sequence[frame_ind].to_image()
        self._draw_outlined_text(image, position=current_state.position, content=content, font=self.font, width=1)
        new_frame = GifFrame(image)
        if inplace:
            sequence[frame_ind] = new_frame
        return new_frame

    def serialize(self) -> dict:
        return dict(id=self.id, keyframes=self.keyframes.serialize())

    @classmethod
    def deserialize(cls, serialized_dict: dict):
        template = TextAnimationTemplate(template_id=serialized_dict['id'])
        template.keyframes = template.keyframes.deserialize(serialized_dict['keyframes'])

    @staticmethod
    def _draw_outlined_text(image: Image,
                            position: Tuple[int, int],
                            content: str,
                            font: ImageFont.ImageFont,
                            background_fill=None,
                            width=1):

        black_alpha = 255
        white_alpha = 240

        overlay = Image.new('RGBA', image.size)

        draw = ImageDraw.ImageDraw(overlay, 'RGBA')
        if background_fill is not None:
            text_width, text_height = font.getsize(content)
            margin = 10
            x, y = position
            draw.rectangle([(x - margin, y - margin),
                            (x + text_width + margin - 1, y + text_height + margin - 1)],
                           fill=background_fill)

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


class MemeAnimationTemplate:
    __slots__ = 'text_templates', 'templates_dict'

    def __init__(self, text_templates: List[TextAnimationTemplate]):
        self.templates_dict: Dict[str, TextAnimationTemplate] = \
            {text_template.id: text_template for text_template in text_templates}

    @property
    def templates_list(self) -> List[TextAnimationTemplate]:
        return list(self.templates_dict.values())

    def render(self, sequence: GifSequence, render_options: Dict[str, str]) -> GifSequence:
        for template_id, content in render_options.items():
            sequence = self.templates_dict[template_id].render(sequence=sequence, content=content)
        return sequence

    @staticmethod
    def spiral(start_ind: int, length: int):
        def roundrobin(*iterables):
            "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
            # Recipe credited to George Sakkis
            num_active = len(iterables)
            nexts = cycle(iter(it).__next__ for it in iterables)
            while num_active:
                try:
                    for next in nexts:
                        yield next()
                except StopIteration:
                    num_active -= 1
                    nexts = cycle(islice(nexts, num_active))

        forward = range(start_ind, length)
        backward = range(start_ind - 1, -1, -1)
        return roundrobin(forward, backward)

    def render_spiral(self, sequence: GifSequence, render_options: Dict[str, str],
                      current_ind: int, refresh_callback: Callable):
        for frame_ind in self.spiral(start_ind=current_ind, length=len(sequence)):
            for template_id, content in render_options.items():
                self.templates_dict[template_id].render_frame(sequence=sequence,
                                                              frame_ind=frame_ind,
                                                              content=content,
                                                              inplace=True)
            if frame_ind == current_ind:
                refresh_callback()

    def serialize(self) -> List[dict]:
        return [template.serialize() for template in self.templates_list]

    def __getitem__(self, template_id: str) -> TextAnimationTemplate:
        return self.templates_dict[template_id]


if __name__ == '__main__':
    template = TextAnimationTemplate("Text", initial_position=(50, 50), initial_text_size=30)

    # keyframe1 = TextAnimationKeyframe(frame_ind=3, position=(80, 100))
    # keyframe2 = TextAnimationKeyframe(frame_ind=7, position=(150, 50))
    # keyframe3 = TextAnimationKeyframe(frame_ind=10, position=(50, 50))
    # template.keyframes.insert_keyframe(keyframe1)
    # template.keyframes.insert_keyframe(keyframe2)
    # template.keyframes.insert_keyframe(keyframe3)

    gif = GifSequence.open('tenor.gif', is_loop=True)
    print(len(gif))
    rendered = template.render(gif, "Hello World!")
    rendered.show()
    rendered.save("hello_world2.gif")
