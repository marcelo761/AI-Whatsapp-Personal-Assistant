import json
import os

import yaml

with open("config.yml", "r", encoding="utf-8") as config_file:
    config = yaml.safe_load(config_file)

valid_language_codes: list[str] = []
lang_directory = "lang"
current_language_code = config["LANGUAGE"]

for filename in os.listdir(lang_directory):
    if (
        filename.startswith("lang.")
        and filename.endswith(".json")
        and os.path.isfile(os.path.join(lang_directory, filename))
    ):
        language_code = filename.split(".")[1]
        valid_language_codes.append(language_code)


def load_current_language() -> dict:
    lang_file_path = os.path.join(lang_directory, f"lang.{current_language_code}.json")
    with open(lang_file_path, encoding="utf-8") as lang_file:
        return json.load(lang_file)


def load_instructions() -> dict[str, str]:
    instructions: dict[str, str] = {}
    for file_name in os.listdir("instructions"):
        if file_name.endswith(".txt"):
            file_path = os.path.join("instructions", file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                variable_name = file_name.split(".")[0]
                instructions[variable_name] = file.read()
    return instructions


def load_contacts() -> dict[str, str]:
    if os.path.exists("contacts.json"):
        with open("contacts.json", "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


instructions = load_instructions()
