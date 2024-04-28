# Local Fast FFXIV Text-To-Speech

This is a *local* voice server for the [TextToTalk](https://github.com/karashiiro/TextToTalk) Dalamud plugin, meaning
that it will use your computer's resources for TTS generation.

Uses the [Piper](https://github.com/rhasspy/piper) project to rapidly generate TTS output based on existing models.
**This software does not do voice cloning of existing FFXIV characters.** Instead, voices were provided by the 
TTS software were matched as close as possible to some characters.

Supports [noisereduce](https://pypi.org/project/noisereduce/) and [voicefixer](https://github.com/haoheliu/voicefixer)
to improve the generated TTS output. (voicefixer is turned off by default due to the computational cost).

**Runs fully on CPU, meaning that you do not need a high-end GPU.** 

## Setup (Development)

This will require Python 3.10, various dependencies, and a special piper version with support for 
custom phonemes.

* Python 3.10
* `pip install sounddevice websockets aioconsole voicefixer pydub`
* `mkdir tmp && cd tmp && git clone https://github.com/mrnotsoevil/piper.git`
* `pip install tmp/piper/src/python_run/`

