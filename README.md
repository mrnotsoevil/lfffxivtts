# Local Fast FFXIV Text-To-Speech

![Screenshot](https://github.com/mrnotsoevil/lfffxivtts/blob/0fac4bfa9774aaf80e05a38b8c289868312ca3c1/dev/screenshot.png?raw=true)

This is a *local* voice server for the [TextToTalk](https://github.com/karashiiro/TextToTalk) Dalamud plugin, meaning
that it will use your computer's resources for TTS generation.

Uses the [Piper](https://github.com/rhasspy/piper) project to rapidly generate TTS output based on existing models.
**This software does not do voice cloning of existing FFXIV characters.** Instead, voices were provided by the 
TTS software were matched as close as possible to some characters.

Supports [noisereduce](https://pypi.org/project/noisereduce/) and [voicefixer](https://github.com/haoheliu/voicefixer)
to improve the generated TTS output. (voicefixer is turned off by default due to the computational cost and multiprocessing issues).

**Runs fully on CPU, meaning that you do not need a high-end GPU.** 

## Usage

Download the package and extract it. 

* Windows: Double-click the `start.bat` file
* Linux/macos: No package ready yet, sorry (use the dev environment and run the main.py)

In the TextToTalk plugin, choose the **Websocket** backend and 
set the port to 8081 (default for this tool).

The TTS tool should automatically connect to the Dalamud plugin within a few seconds.

Please give the TTS a few seconds to generate the audio. You can turn off noisereduce if you want 
a bit more performance (not much).

![TextToTalk settings](https://github.com/mrnotsoevil/lfffxivtts/blob/master/dev/screenshot_plugin.png?raw=true)

## Setup (Development)

This will require Python 3.10, various dependencies, and a special piper version with support for 
custom phonemes.

* Python 3.10
* `pip install sounddevice websockets aioconsole voicefixer pydub wxwidgets noisereduce pyloudnorm`
* `mkdir tmp && cd tmp && git clone https://github.com/mrnotsoevil/piper.git`
* `pip install tmp/piper/src/python_run/`

### Running 

* To run the GUI, start `lfffixvtts/main.py` from the **repo root directory** (where config.json is)
* To test out the TTS (debugging), you can `tts.py` to get a CLI. There you can type in `<npc name or id>//<text>` for an NPC voice or `any//<text>` for random voices. Change the language with `lang <de/en/jp/fr>`.
