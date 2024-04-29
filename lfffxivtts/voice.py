import re
import random
import traceback


def select_voice(config, npc_id, full_name, lang):
    """
    Selects a voice based on available infos
    :param config: the global config
    :param npc_id: the npc id
    :param full_name: the full name
    :param lang: the language (auto will map to en)
    :return: tts voice (dict with model, language, speaker)
    """
    if lang not in ["en", "fr", "de", "jp"]:
        print("[w] Unknown language", lang, "--> Defaulting to en")
        lang = "en"
    npc_id = str(npc_id)
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

    # Use gender associated from NPC db
    if npc_id and npc_id in config["npcs"]:
        try:
            npc = config["npcs"][npc_id]
            gender = npc["gender"]
            if gender is not None:
                available_voices = [voice for voice in config["voices"][lang] if voice["gender"] == gender]
                id_num = int(npc_id)
                voice = available_voices[id_num % len(config["voices"][lang])]
                print("[w] Using NPC gender voice", voice["name"], "for", npc_id)
                return voice
        except Exception as e:
            print("[!] Error at select_voice / 3", e)
            traceback.print_exc()

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
                return voice

    # Use pattern (from race, based on name)
    if full_name:
        for race in ["hyur", "elezen", "lalafell", "miqo'te", "roegadyn", "au ra"]:
            gender = estimate_gender_by_name(full_name, race)
            if gender is not None:
                # Select by ID (filter by gender)
                available_voices = [voice for voice in config["voices"][lang] if voice["gender"] == gender]
                npc_id = hash(full_name)
                voice = available_voices[int(npc_id) % len(available_voices)]
                print("[i] Selecting voice via gender pattern", "-->", gender, "name", full_name)
                return voice


    # Fallback by gender (CLI)
    for voice in config["voices"][lang]:
        if voice["gender"] == full_name:
            print("[w] Using gender fallback voice", full_name, voice["name"])
            return voice

    # Select any (CLI)
    if npc_id == "any":
        voice = random.choice(config["voices"][lang])
        print("[i] Selecting random voice", voice["name"])
        return voice

    # Fallback voice by NPC ID
    if npc_id:
        try:
            id_num = int(npc_id)
            voice = config["voices"][lang][id_num % len(config["voices"][lang])]
            print("[w] Using fallback voice", voice["name"], "for NPC ID", npc_id)
            return voice
        except:
            pass

    # Fallback voice
    if config["voices"][lang]:
        voice = config["voices"][lang][0]
        print("[w] Using fallback voice", voice["name"])
        return voice
    return None


def estimate_gender_by_name(full_name, race):
    # Dictionary containing patterns for male and female names by race
    name_patterns = {
        "hyur": {"male": ["lfric", "ric", "fric"], "female": ["enlil", "lil"]},
        "elezen": {"male": ["ion", "nre", "dren"], "female": ["thel", "iane", "na"]},
        "lalafell": {"male": ["dodo", "odo"], "female": ["pepa", "epa"]},
        "miqo'te": {"male": ["x'rhun", "'rhun"], "female": ["miqo", "qo'te"]},
        "roegadyn": {"male": ["ff", "nn", "drud"], "female": ["a'to", "to"]},
        "au ra": {"male": ["iyo", "yo", "so"], "female": ["jorn", "orn", "va"]}
    }

    # Lowercase the full name for case-insensitive matching
    full_name_lower = full_name.lower()

    # Check each race for name patterns
    for race_name, patterns in name_patterns.items():
        if race_name.lower() in race.lower():
            for gender, gender_patterns in patterns.items():
                for pattern in gender_patterns:
                    if pattern in full_name_lower:
                        return gender
    # If no pattern matches, return None
    return None
