import asyncio
import json
import multiprocessing
import tempfile
import time
import sounddevice as sd
import queue
import threading
import soundfile as sf

import websockets

from voice import select_voice
from tts import tts_init, run_piper, tts_post_process
import traceback
import uuid

CURRENT_PROCESS_UUID = None
CURRENT_PROCESS = None
CURRENT_PROCESS_TMP = None


def tts_cancel():
    print("[>] Cancellation requested")
    global CURRENT_PROCESS
    global CURRENT_PROCESS_TMP
    global CURRENT_PROCESS_UUID
    CURRENT_PROCESS_UUID = None
    try:
        if CURRENT_PROCESS is not None:
            CURRENT_PROCESS.terminate()
            CURRENT_PROCESS = None
    except:
        pass
    try:
        if CURRENT_PROCESS_TMP is not None:
            CURRENT_PROCESS_TMP.cleanup()
            CURRENT_PROCESS_TMP = None
    except:
        pass


def tts_post_process_say(config, temp_dir, wav_files):
    def generate_audio(audio_queue):
        for index, piper_wav_file in enumerate(wav_files):
            print("[i] Postprocess", index, "-->", piper_wav_file)
            output_wav = tts_post_process(config, piper_wav_file, temp_dir, index)
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


def tts_say(config, message):
    if not config["enable"]:
        print("[w] NO TTS WILL BE GENERATED (not enabled)")
        return

    if "Speaker" not in message or not message["Speaker"]:
        print("[!] Rejected: ", json.dumps({"type": "run", "data": message}))
        return

    payload = message["Payload"]
    speaker = message["Speaker"] or ""
    npc_id = message["NpcId"] or 0

    voice = select_voice(config, npc_id, speaker)

    if voice is None:
        print("[!] No voice found. Cancelling!")
        return

    global CURRENT_PROCESS_UUID
    current_job = uuid.uuid4().hex
    CURRENT_PROCESS_UUID = current_job
    print("[i] Preparing job", CURRENT_PROCESS_UUID)

    global CURRENT_PROCESS_TMP
    CURRENT_PROCESS_TMP = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_dir = CURRENT_PROCESS_TMP.name

    # Do piper inference here (multiprocessing drags the performance down due to DLL + model load)
    start = time.time()
    piper_wavs = list(run_piper(config, payload, voice["model"], voice["language"],
                                voice["speaker"], temp_dir, "piper"))
    end = time.time()
    print("[i] Full piper inference time was", end - start, "seconds")

    # Sync
    # await asyncio.sleep(0.2)

    # Check if we are still the job
    if current_job != CURRENT_PROCESS_UUID:
        return

    # Schedule audioplayer
    global CURRENT_PROCESS
    CURRENT_PROCESS = multiprocessing.Process(target=tts_post_process_say, args=(config, temp_dir, piper_wavs),
                                              daemon=True)
    CURRENT_PROCESS.start()


async def handle_message(config, message):
    print("[i] Received message:", message)
    try:
        data = json.loads(message)
        if data["Type"] == "Cancel":
            tts_cancel()
        elif data["Type"] == "Say":
            tts_cancel()
            tts_say(config, data)
    except Exception as e:
        traceback.print_exc()
        print("[!] Unable to parse message!", e)


async def start_ws(config):
    while True:
        try:
            websocket_uri = config["websocketURI"]
            print("[i] Attempting to connect to " + websocket_uri)
            async with websockets.connect(websocket_uri) as websocket:
                print("[i] Connected to WebSocket server. Awaiting messages ...")
                while True:
                    try:
                        message = await websocket.recv()
                        await handle_message(config, message)
                    except websockets.ConnectionClosed:
                        print("[!] Connection closed. Reconnecting...")
                        break
        except ConnectionRefusedError:
            print("[!] Connection refused. Retrying...")
        except Exception as e:
            print("[!] Error:", e)
        await asyncio.sleep(5)  # Retry after 5 seconds


# async def start_tts(config):
#     while True:
#         if len(MESSAGE_QUEUE) > 0:
#             message = MESSAGE_QUEUE.
#         print("[i] uuu", config["volume"])
#         await asyncio.sleep(1)


async def start_client_(config):
    websocket_task = asyncio.create_task(start_ws(config))
    # tts_task = asyncio.create_task(start_tts(config))

    print("[i] Starting websocket client & voice servers")
    await websocket_task


def start_client(config):
    # Initialize TTS
    time.sleep(1)
    tts_init(config)
    print("[i] TTS init complete")

    asyncio.run(start_client_(config))
