# Reference voices

## Directory "references"

Should contain short audio recordings of real voices (organized by language en/de/fr/jp) in WAV format.

All audio files need to be named as following:

```
<character name>_<male/female>.wav
```

The character name will be fuzzy-matched later on.

## Directory "tts"

Should contain a prediction of the TTS-generated voices, one per voice (organized by language en/de/fr/jp) in WAV format.

All audio files need to be named as following:

```
<model>_<language>_<speaker>_<male/female>.wav
```

## NPC database