from tts import tts, tts_init
from config import read_config

def main():
    config = read_config()
    tts_init(config)
    while True:
        message = input("TTS> ")
        if message == "stop" or message == "exit":
            exit(0)
        elif message.startswith("lang "):
            lang = message.split(" ")[1].strip()
            if lang in ["de", "en", "fr", "jp"]:
                config["language"] = lang
                print("[i] --> set language to", lang)
            else:
                print("[!] invalid language. must be any of en, fr, jp, de")
        elif "//" in message:
            tts(config, message.split("//")[1], message.split("//")[0], message.split("//")[0])
        else:
            tts(config, message, 0, "")

if __name__ == "__main__":
    main()