import asyncio
import json
import multiprocessing

import websockets

from tts import tts_init, tts
import traceback

CURRENT_PROCESS = None


def tts_cancel():
    global CURRENT_PROCESS
    if CURRENT_PROCESS is not None:
        CURRENT_PROCESS.terminate()
        CURRENT_PROCESS = None


def tts_say(config, message):
    if "Speaker" not in message or not message["Speaker"]:
        print("[!] Rejected: ", json.dumps({"type": "run", "data": message}))
        return

    payload = message["Payload"]
    speaker = message["Speaker"] or ""
    npc_id = message["NpcId"] or 0

    global CURRENT_PROCESS
    CURRENT_PROCESS = multiprocessing.Process(target=tts, args=(config, payload, npc_id, speaker), daemon=True)
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
    tts_init(config)
    print("[i] TTS init complete")

    asyncio.run(start_client_(config))
