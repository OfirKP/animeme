import argparse
import json
from pathlib import Path

from gif import GifSequence
from templates import MemeAnimationTemplate

parser = argparse.ArgumentParser()
parser.add_argument("template", help="path to GIF file")
parser.add_argument("-t", "--text", action="append", help="Strings to fill template with")
parser.add_argument("-o", "--output", help="path to output GIF")

args = parser.parse_args()

template_path = args.template
text = args.text
output_path = args.output

gif = GifSequence.open(template_path, method="mpy")
json_path = Path(template_path).with_suffix(".json")
serialized_template = json.loads(json_path.read_bytes())
template = MemeAnimationTemplate.deserialize(serialized_template)

template.render(gif, dict(zip(template.templates_dict.keys(), args.text))).save(output_path, is_loop=True)
