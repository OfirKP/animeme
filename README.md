# Animeme - Create Animated Meme Templates


<p align="center">
  <img src="https://user-images.githubusercontent.com/11351634/76687768-bdadc700-662f-11ea-9afc-b2ae6cae2257.gif">
</p>

## Installation
Clone this project:
```bash
$ git clone https://github.com/OfirKP/pymeme
```
Then, install the required packages:
```bash
$ pip install -r requirements.txt
```

## Animator
A studio made with a PyQt5 GUI to create and edit animated meme templates.
<p align="center">
  <img src="https://user-images.githubusercontent.com/11351634/76688005-96f09000-6631-11ea-94d4-19b93b5d4698.png" width=560 alt="animator">
</p>

### Run 
> **TO BE FIXED**: Make sure you have [Montserrat-Regular.ttf](https://github.com/google/fonts/commits/master/ofl/montserrat/Montserrat-Regular.ttf) in the cloned folder.

To open the animator, run `$ python animator.py` using the python environment with the installed packages.

### Loading the animation
Click `File -> Load animation` or `Ctrl + O` and load the GIF file you wish to create a template of.
If a `json` template file with the same name as the GIF is present in the same folder, both the animation and the animation data will be loaded into the Animator.

### Keyframes
The animation is linearly interpolated from the given keyframes, **currently supporting only animated text position & font size keyframes**.

Adding keyframes can be done in 2 ways:
1. Clicking 'Add Keyframe' which will create a keyframe in the current frame with interpolated values.
2. Dragging a text template across the screen will automatically create a text position keyframe.

### Editing Template
- Adding/removing a text template can be done using the _Add New Text Template_/_Delete Current Text Template_.
- Pressing the _Reset_ button will reset the current text template's animation.
- Clicking `Animation -> Reset all animation data` or `Ctrl + R` will remove all keyframes of all text templates.
- The _Frame Properties_ panel is used to edit keyframe data. An empty value will cause interpolation of field in the frame.
- The _Text Template Properties_ panel is used to edit the selected text template's properties (which will apply to all frames).

### Saving the template
Click `File -> Save template as` or `Ctrl + S` and save the meme template to your preferred location.
This will create both `<template name>.json` and `<template name>.gif` that are used for generating memes and loading to the animator.

## Generate Memes from Template
Make sure you have a template (both GIF and json files in the same directory), then run the python script `generate_meme.py` with the following format:
```
$ python generate_meme.py <GIF file> [-t TEXT1] [-t TEXT2] [-t TEXT3] ... [-o OUTPUT] 
```

> **NOTE:** Add -t "some string" for each corresponding text in the template.

Arguments:
- `-o`, `--output`: output GIF path to save the generated meme 
 of identical contacts in other files
- `-h`, `--help`: help message to get more info about the usage of the script

## Prerequisites
:snake: _python 3.7+_ (may work on older versions)

## TODO
- [ ] Support using a text-box with a specified width (and maybe height).
- [ ] Add a font selector that will support multiple platforms.
- [ ] Create a web client (and server) for generating memes out of templates/animator.
