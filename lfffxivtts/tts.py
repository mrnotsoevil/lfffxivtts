import json
import subprocess
import tempfile
import platform
import sounddevice as sd
import soundfile as sf
import os
from os.path import join
from voice import select_voice


def get_wav_duration(file_path):
    with sf.SoundFile(file_path, 'r') as f:
        duration = len(f) / f.samplerate
    return duration


def run_piper(payload, model, language, speaker, wav_file):
    model_file = os.path.abspath("piper/models/" + model + "_" + language + ".onnx")
    config_file = os.path.abspath("piper/models/" + model + "_" + language + ".json")

    if platform.system() == 'Linux':
        executable = "piper/piper_linux_x86_64/piper"
    else:
        print("[!] Unknown operating system")
        return

    executable = os.path.abspath(executable)

    command = [executable, "--model", model_file, "--config", config_file, "--output_file", wav_file, "--speaker",
               speaker]
    print(payload, ">", " ".join(command))
    process = subprocess.Popen(command, stdin=subprocess.PIPE, cwd=os.path.dirname(executable))
    process.communicate(payload.encode("utf-8"))
    process.wait()


def tts(config, payload, npc_id, full_name):
    voice = select_voice(config, npc_id, full_name)

    if voice is None:
        print("[!] No voice found. Cancelling!")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        piper_wav_file = join(temp_dir, "piper.wav")

        run_piper(payload, voice["model"], voice["language"], voice["speaker"], piper_wav_file)

        wav_file = piper_wav_file

        # Voicefixer
        if "voicefixer" in config:
            print("[i] Applying voicefixer ...")
            import time
            start = time.time()
            wav_file = join(temp_dir, "voicefixer.wav")
            config["voicefixer"].restore(input=piper_wav_file, output=wav_file, cuda=False, mode=0)
            end = time.time()
            print("[i] Applying voicefixer ...", "took", end - start)

        # Playback
        wav_data, sample_rate = sf.read(wav_file)

        sd.play(wav_data, samplerate=sample_rate, blocking=True)


def tts_init(config):
    if config["tts"]["enableVoiceFixer"]:
        import voicefixer
        print("[i] Initializing voicefixer ...")
        config["voicefixer"] = voicefixer.VoiceFixer()
        print("[i] Initializing voicefixer ... done")

