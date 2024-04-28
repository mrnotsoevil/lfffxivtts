import json
import subprocess
import tempfile
import platform
import sounddevice as sd
import soundfile as sf
import os
from os.path import join
from voice import select_voice
import queue
import threading
import time


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

        # Voicefixer
        if "voicefixer" in config:
            if config["tts"]["voiceFixerEnableSplitting"]:
                tts_voicefixer_splitting(config, piper_wav_file, temp_dir)
            else:
                tts_voicefixer_whole(config, piper_wav_file, temp_dir)
        else:
            # Playback of the original inference
            wav_data, sample_rate = sf.read(piper_wav_file)
            sd.play(wav_data * config["volume"], samplerate=sample_rate, blocking=True)


def tts_voicefixer_splitting(config, piper_wav_file, temp_dir):
    print("[i] Applying voicefixer (splitting) ...")

    from pydub import AudioSegment
    from pydub.silence import split_on_silence

    audio = AudioSegment.from_wav(piper_wav_file)
    audio.export("audio.wav", format="wav")
    segments = split_on_silence(audio,
                                min_silence_len=config["tts"]["voiceFixerSplittingSilenceDuration"],
                                silence_thresh=config["tts"]["voiceFixerSplittingSilenceThreshold"])
    print("[i] --> Found", len(segments), "segments")

    def process_sentences(segments, audio_queue):
        for i, segment in enumerate(segments):
            print("[i] voicefixer segment", i)
            input_wav = join(temp_dir, f"i_segment_{i}.wav")
            output_wav = join(temp_dir, f"o_segment_{i}.wav")
            silence_chunk = AudioSegment.silent(duration=100)
            padded = silence_chunk + segment + silence_chunk
            padded.export(input_wav, format="wav")

            padded.export(f"i_segment_{i}.wav", format="wav")

            config["voicefixer"].restore(input=input_wav, output=output_wav, cuda=False, mode=0)

            audio_queue.put(output_wav)
        audio_queue.put(None)

    def play_audio(audio_queue):
        while True:
            if not audio_queue.empty():
                wav_file = audio_queue.get()

                # Break condition
                if wav_file is None:
                    break

                wav_data, sample_rate = sf.read(wav_file)
                sd.play(wav_data * config["volume"], samplerate=sample_rate, blocking=True)
            else:
                time.sleep(0.1)  # Sleep briefly to avoid busy waiting

    audio_queue = queue.Queue()
    processing_thread = threading.Thread(target=process_sentences, args=(segments, audio_queue))
    processing_thread.start()

    audio_thread = threading.Thread(target=play_audio, args=(audio_queue,))
    audio_thread.start()

    # Wait for the processing thread to finish
    processing_thread.join()
    audio_thread.join()

def tts_voicefixer_whole(config, piper_wav_file, temp_dir):
    print("[i] Applying voicefixer (whole audio) ...")
    import time
    start = time.time()
    wav_file = join(temp_dir, "voicefixer.wav")
    config["voicefixer"].restore(input=piper_wav_file, output=wav_file, cuda=False, mode=0)
    end = time.time()
    print("[i] Applying voicefixer ...", "took", end - start)
    # Playback of the original inference
    wav_data, sample_rate = sf.read(piper_wav_file)
    sd.play(wav_data * config["volume"], samplerate=sample_rate, blocking=True)


def tts_init(config):
    if config["tts"]["enableVoiceFixer"]:
        import voicefixer
        print("[i] Initializing voicefixer ...")
        config["voicefixer"] = voicefixer.VoiceFixer()
        print("[i] Initializing voicefixer ... done")
