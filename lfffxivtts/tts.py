import io
import json
import math
import os
import queue
import tempfile
import threading
import time
from os.path import join

import sounddevice as sd
import soundfile as sf
from pydub import AudioSegment

from voice import select_voice


def run_piper(config, payload, model, language, speaker, temp_dir, file_name_template):
    model_file = os.path.abspath("piper/models/" + model + "_" + language + ".onnx")
    config_file = os.path.abspath("piper/models/" + model + "_" + language + ".json")
    voice_config = {}
    model_lang = model + "_" + language

    if model_lang in config["tts"]["modelConfig"]:
        voice_config = config["tts"]["modelConfig"][model_lang]
    with open(config_file, "r") as f:
        model_config = json.load(f)

    from piper import PiperVoice

    voice = PiperVoice.load(model_file, config_path=config_file, use_cuda=False)

    phonemes = voice.phonemize(payload)
    output_files = []
    # with wave.open(wav_file, "wb") as wav_file:

    # wav_file.setframerate(model_config["audio"]["sample_rate"])
    # wav_file.setsampwidth(2)  # 16-bit
    # wav_file.setnchannels(1)  # mono

    for index, sentence_ in enumerate(phonemes):
        min_phoneme_count = voice_config["minPhonemeCount"] if "minPhonemeCount" in voice_config else 0
        noise_scale = None

        if len(sentence_) >= min_phoneme_count:
            sentence = sentence_
            n_repetitions = 1
        else:
            n_repetitions = int(math.ceil(1.0 * min_phoneme_count / len(sentence_)))
            print("[i] Min phoneme count", min_phoneme_count, "not reached. Repeating", "".join(sentence_), "x",
                  n_repetitions)
            sentence = (sentence_ + [";", ",", " "]) * n_repetitions
            if "phonemeCountFixNoiseScale" in voice_config:
                noise_scale = voice_config["phonemeCountFixNoiseScale"]

        synthesize_args = {
            "phoneme_input": True,
            "speaker_id": int(speaker),
            "length_scale": None,
            "noise_scale": noise_scale,
            "noise_w": None,
            "sentence_silence": 0.2,
        }
        print("[i] TTS >", "".join(sentence))

        wav_bytes = b"".join(list(voice.synthesize_stream_raw("".join(sentence), **synthesize_args)))
        if n_repetitions > 1:
            width = int(len(wav_bytes) / n_repetitions)
            wav_bytes = wav_bytes[:width]

        bytes_io = io.BytesIO(wav_bytes)
        segment = AudioSegment.from_raw(bytes_io, frame_rate=model_config["audio"]["sample_rate"], sample_width=2,
                                        channels=1)

        wav_file = join(temp_dir, file_name_template + str(index) + ".wav")
        try:
            new_segment = segment.fade_out(100) + AudioSegment.silent(duration=150)
            new_segment.export(wav_file, format="wav")
        except:
            new_segment = segment + AudioSegment.silent(duration=150)
            new_segment.export(wav_file, format="wav")

        output_files.append(wav_file)

    return output_files


def get_wav_duration(file_path):
    with sf.SoundFile(file_path, 'r') as f:
        duration = len(f) / f.samplerate
    return duration


def tts(config, payload, npc_id, full_name):
    voice = select_voice(config, npc_id, full_name)

    if voice is None:
        print("[!] No voice found. Cancelling!")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        piper_wav_file = join(temp_dir, "piper.wav")

        piper_wav_files = run_piper(config, payload, voice["model"], voice["language"],
                                    voice["speaker"], temp_dir, "piper")

        # Voicefixer
        if "voicefixer" in config:
            if config["tts"]["voiceFixerEnableSplitting"]:
                tts_voicefixer_splitting(config, piper_wav_file, temp_dir)
            else:
                tts_voicefixer_whole(config, piper_wav_file, temp_dir)
        else:
            # Playback of the original inference
            for wav_file in piper_wav_files:
                wav_data, sample_rate = sf.read(wav_file)
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
