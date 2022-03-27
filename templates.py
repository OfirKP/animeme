from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import cycle, islice
from typing import Tuple, Optional, List, Dict, Union

from PIL import Image, ImageDraw, ImageFont

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
        self.text_value = self.id
        self.font_path = 'Montserrat-Regular.ttf'
        self.text_color: str = "#FFF"
        self.background_color: Optional[Tuple] = None
        self.stroke_width: int = 2
        self.stroke_color: str = "#000"

    def render(self, sequence: GifSequence, content: str):
        rendered_frames = []
        for frame_ind, frame in enumerate(sequence):
            rendered_frames.append(self.render_frame(sequence=sequence, frame_ind=frame_ind, content=content))
        return GifSequence.from_frames(rendered_frames)

    def render_frame(self, sequence: GifSequence, frame_ind: int, content: str, inplace: bool = False) -> GifFrame:
        current_state: TextAnimationKeyframe = self.keyframes.interpolate(frame_ind=frame_ind)
        image = sequence[frame_ind].to_image()
        self._draw_outlined_text(image, position=current_state.position, content=content,
                                 font=ImageFont.truetype(self.font_path, size=current_state.text_size),
                                 background_color=self.background_color,
                                 stroke_width=self.stroke_width,
                                 stroke_color=self.stroke_color)
        new_frame = GifFrame(image)
        if inplace:
            sequence[frame_ind] = new_frame
        return new_frame

    def serialize(self) -> dict:
        return dict(id=self.id,
                    keyframes=self.keyframes.serialize(),
                    font_path=self.font_path,
                    text_color=self.text_color,
                    background_color=self.background_color,
                    stroke_width=self.stroke_width,
                    stroke_color=self.stroke_color)

    @classmethod
    def deserialize(cls, serialized_dict: dict):
        template = TextAnimationTemplate(template_id=serialized_dict['id'])
        template.keyframes = template.keyframes.deserialize(serialized_dict['keyframes'])
        template.font_path = serialized_dict['font_path']
        template.text_color = serialized_dict['text_color']
        template.background_color = serialized_dict['background_color']
        template.stroke_width = serialized_dict['stroke_width']
        template.stroke_color = serialized_dict['stroke_color']
        return template

    def __hash__(self):
        return hash(self.id)

    @lru_cache(maxsize=32)
    def get_text_box_shape(self, font_path: str, text_size: int, text: str):
        font = ImageFont.truetype(font_path, size=text_size)
        return font.getsize_multiline(text)

    def get_text_bounding_box(self, center_position: Tuple[int, int], font_size: int, text: str):
        text_width, text_height = self.get_text_box_shape(font_path=self.font_path, text_size=font_size, text=text)
        return center_position[0] - text_width // 2, center_position[1] - text_height // 2, text_width, text_height

    def _draw_outlined_text(self,
                            image: Image,
                            position: Tuple[int, int],
                            content: str,
                            font: ImageFont.ImageFont,
                            background_color: Optional[Union[Tuple, str]] = None,
                            stroke_width: int = 0,
                            stroke_color: Union[Tuple, str] = "#000"):

        overlay = Image.new('RGBA', image.size)
        x, y, text_width, text_height = self.get_text_bounding_box(center_position=position,
                                                                   font_size=font.size,
                                                                   text=content)

        draw = ImageDraw.ImageDraw(overlay, 'RGBA')
        if background_color is not None:
            margin = 10
            draw.rectangle([(x - margin, y - margin),
                            (x + text_width + 2 * margin, y + text_height + 2 * margin)],
                           fill=background_color)

        # Draw inner white text
        draw.multiline_text((x, y), content, self.text_color,
                            font=font, align='center', stroke_width=stroke_width, stroke_fill=stroke_color)

        image.paste(overlay, None, overlay)


class MemeAnimationTemplate:
    __slots__ = 'text_templates', 'templates_dict'

    def __init__(self, text_templates: List[TextAnimationTemplate]):
        self.templates_dict: Dict[str, TextAnimationTemplate] = \
            {text_template.id: text_template for text_template in text_templates}

    def add_template(self, template: TextAnimationTemplate):
        self.templates_dict[template.id] = template

    def remove_template(self, template: TextAnimationTemplate):
        del self.templates_dict[template.id]

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
                      current_ind: int):
        for frame_ind in self.spiral(start_ind=current_ind, length=len(sequence)):
            for template_id, content in render_options.items():
                self.templates_dict[template_id].render_frame(sequence=sequence,
                                                              frame_ind=frame_ind,
                                                              content=content,
                                                              inplace=True)

    def serialize(self) -> List[dict]:
        return [template.serialize() for template in self.templates_list]

    @classmethod
    def deserialize(cls, serialized_meme_template) -> 'MemeAnimationTemplate':
        return cls(text_templates=[TextAnimationTemplate.deserialize(serialized_text_template)
                                   for serialized_text_template in serialized_meme_template])

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

    gif = GifSequence.open('tenor.gif')
    print(len(gif))
    rendered = template.render(gif, "Hello World!")
    rendered.show()
    rendered.save("hello_world2.gif")
