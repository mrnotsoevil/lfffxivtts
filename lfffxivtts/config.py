import json
import re


def read_genders(config):
    print("[i] Loading name-gender database ...")
    config["genders"] = {}

    def remove_non_alphanumeric(text):
        return re.sub(r'[^a-z]', '', text)

    with open("lfffxivtts/resources/genders/male.txt", "r") as f:
        for line_ in f:
            line = remove_non_alphanumeric(line_.strip().lower())
            if line:
                config["genders"][line] = "male"

    with open("lfffxivtts/resources/genders/female.txt", "r") as f:
        for line_ in f:
            line = remove_non_alphanumeric(line_.strip().lower())
            if line:
                config["genders"][line] = "female"

    print("[i] Loading name-gender database ... " + str(len(config["genders"])) + " items")


def read_voices(config):
    with open("lfffxivtts/resources/voices.json", "r") as f:
        config["voices"] = json.load(f)
    print("[i] --> Loaded voice presets")


def read_npcs(config):
    with open("lfffxivtts/resources/npcs.json", "r") as f:
        config["npcs"] = json.load(f)
    print("[i] --> Loaded", len(config["npcs"]), "NPCs")


def read_characters(config):
    with open("lfffxivtts/resources/characters.json", "r") as f:
        config["chars"] = json.load(f)
    print("[i] --> Loaded", len(config["chars"]), "special NPCs")


def read_config():
    with open("config.json", "r") as f:
        config = json.load(f)
    read_voices(config)
    read_npcs(config)
    read_characters(config)
    read_genders(config)
    print("[i] Configuration loaded")

    return config


def write_config(config):
    copy = {
        "language": config["language"],
        "volume": config["volume"],
        "enable": config["enable"],
        "outputDeviceIndex": config["outputDeviceIndex"],
        "websocketURI": config["websocketURI"],
        "tts": config["tts"]
    }
    with open("config.json", "w") as f:
        json.dump(copy, f, indent=4)
