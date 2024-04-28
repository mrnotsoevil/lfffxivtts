import re


def select_voice(config, npc_id, full_name):
    """
    Selects a voice based on available infos
    :param config: the global config
    :param npc_id: the npc id
    :param full_name: the full name
    :return: tts voice (dict with model, language, speaker)
    """
    lang = config["language"]
    print("[i] Select voice query", npc_id, "+", full_name)

    # Look for a known NPC
    if npc_id and npc_id in config["npcs"]:
        npc = config["npcs"][npc_id]

        # Known character?
        npc_name = re.sub(r"[^a-zA-Z ]", "", npc["name"]).lower()
        for char_name in config["chars"]:
            for segment in npc_name.split(" "):
                if segment.startswith(char_name):
                    print("[i] Selecting by NPC", npc_id, "name matched to character", char_name)
                    return config["chars"][char_name]["tts"][lang]

        # Select by ID (filter by gender)
        available_voices = [voice for voice in config["voices"][lang] if voice["gender"] == npc["gender"]]
        voice = available_voices[int(npc_id) % len(available_voices)]
        print("[i] Selecting NPC voice for", npc_id, "-->", voice["name"])
        return voice

    # Known character by name?
    if full_name.strip():
        npc_name = re.sub(r"[^a-zA-Z ]", "", full_name).lower()
        for char_name in config["chars"]:
            for segment in npc_name.split(" "):
                if segment.startswith(char_name):
                    print("[i] Selecting by NPC name", npc_id, "name matched to character", char_name)
                    return config["chars"][char_name]["tts"][lang]

    # Use the gender list
    if full_name.strip():
        first_name = re.sub(r"[^a-zA-Z ]", "", full_name.split(" ")[0]).lower()
        if first_name in config["genders"]:
            gender = config["genders"][first_name]

            if gender is not None:
                # Select by ID (filter by gender)
                available_voices = [voice for voice in config["voices"][lang] if voice["gender"] == gender]
                npc_id = hash(full_name)
                voice = available_voices[int(npc_id) % len(available_voices)]
                print("[i] Selecting NPC voice via gender list", "-->", gender)

    # Fallback by gender (CLI)
    for voice in config["voices"][lang]:
        if voice["gender"] == full_name:
            print("[w] Using gender fallback voice", full_name, voice["name"])
            return voice

    # Fallback voice
    if config["voices"][lang]:
        voice = config["voices"][lang][0]
        print("[w] Using fallback voice", voice["name"])
        return voice
    return None
