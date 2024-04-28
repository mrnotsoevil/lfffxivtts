import io
import json
import math
import os
import queue
import tempfile
import threading
import time
from os.path import join
import numpy as np

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
    with open(config_file, "r", encoding='utf-8') as f:
        model_config = json.load(f)

    from piper import PiperVoice

    voice = PiperVoice.load(model_file, config_path=config_file, use_cuda=False)

    phonemes = voice.phonemize(payload)
    # with wave.open(wav_file, "wb") as wav_file:

    # wav_file.setframerate(model_config["audio"]["sample_rate"])
    # wav_file.setsampwidth(2)  # 16-bit
    # wav_file.setnchannels(1)  # mono

    for index, sentence_ in enumerate(phonemes):
        min_phoneme_count = voice_config["minPhonemeCount"] if "minPhonemeCount" in voice_config else 0
        noise_scale = None

        if len(sentence_) <= 0:
            continue
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

        yield wav_file


def tts(config, payload, npc_id, full_name):
    voice = select_voice(config, npc_id, full_name)

    if voice is None:
        print("[!] No voice found. Cancelling!")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        def generate_audio(audio_queue):
            piper_generator = run_piper(config, payload, voice["model"], voice["language"],
                                        voice["speaker"], temp_dir, "piper")
            for index, piper_wav_file in enumerate(piper_generator):
                print("[i] Received sentence", index, "-->", piper_wav_file)
                output_wav = piper_wav_file

                if config["tts"]["enableNoiseReduce"]:
                    try:
                        import noisereduce as nr
                        audio = AudioSegment.from_file(output_wav)
                        samples = np.array(audio.get_array_of_samples())

                        reduced_noise = nr.reduce_noise(y=samples, sr=audio.frame_rate,
                                                        prop_decrease=config["tts"]["noiseReduceFactor"])
                        segment = AudioSegment(reduced_noise.tobytes(), frame_rate=audio.frame_rate,
                                               sample_width=audio.sample_width,
                                               channels=audio.channels)

                        output_wav = join(temp_dir, f"noisereduce_output_{index}.wav")
                        segment.export(output_wav, format="wav")
                    except Exception as e:
                        print("[!] Error during noise reduction", e)

                if config["tts"]["enableVoiceFixer"] and "voicefixer" in config:
                    try:
                        input_wav = output_wav
                        voicefixer_input_wav = join(temp_dir, f"voicefixer_input_{index}.wav")
                        voicefixer_output_wav = join(temp_dir, f"voicefixer_output_{index}.wav")
                        silence_chunk = AudioSegment.silent(duration=100)
                        segment = AudioSegment.from_wav(input_wav)
                        (silence_chunk + segment + silence_chunk).export(voicefixer_input_wav, format="wav")
                        config["voicefixer"].restore(input=voicefixer_input_wav, output=voicefixer_output_wav, cuda=False,
                                                     mode=0)

                        output_wav = voicefixer_output_wav
                    except Exception as e:
                        print("[!] Error during voicefixer", e)

                if config["tts"]["enableLoudnessNormalization"]:
                    try:
                        import pyloudnorm as pyln
                        input_wav = output_wav
                        output_wav = join(temp_dir, f"normalized_output_{index}.wav")
                        data, rate = sf.read(input_wav)
                        meter = pyln.Meter(rate)  # create BS.1770 meter
                        loudness = meter.integrated_loudness(data)
                        loudness_normalized_audio = pyln.normalize.loudness(data, loudness,
                                                                            config["tts"]["loudnessNormalizationTarget"])
                        sf.write(output_wav, loudness_normalized_audio, samplerate=rate)

                    except Exception as e:
                        print("[!] Error during loudness normalization", e)

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
        generate_thread = threading.Thread(target=generate_audio, args=(audio_queue,))
        generate_thread.start()

        audio_thread = threading.Thread(target=play_audio, args=(audio_queue,))
        audio_thread.start()

        # Wait for the processing thread to finish
        generate_thread.join()
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
