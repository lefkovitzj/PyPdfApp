from datetime import date
import hashlib
import os
import json
import pyperclip

def hash_md5(string_to_hash):
    hashed = hashlib.md5(string_to_hash.encode("utf-8")).hexdigest()
    return hashed

def generate_all_py_file_hashes(parse_dir="."):
    hashes = {}
    for dirfile in os.listdir(parse_dir):
        if dirfile.endswith(".py"):
            with open(parse_dir + dirfile,"r") as pyfile:
                hashes[dirfile] = hash_md5(pyfile.read())
    return hashes



template = {
    "version": "1.3",
    "author": "lefkovitzj",
    "release_date": "2024-09-07",
    "newest_version_settings_url": "https://raw.githubusercontent.com/lefkovitzj/PyPdfApp/main/settings.json",
    "newest_version_url": "https://github.com/lefkovitzj/PyPdfApp/",
    "source_file_hashes": {
        "app.py": "85131dcdcd2f31e61e71f8c2af93f87e",
        "extract.py": "3fcf135344a59b719e5e9736c45877c3",
        "gui.py": "e238312c1e35e4f96d8821e7257677d0",
        "load.py": "a6b9e07a16960c02d4848dba9ad3537c",
        "manipulate.py": "d7c36510f9e09fbe6356f3c6f3474c11",
        "merge.py": "045650cce3075d5417dec07950f5b44e",
        "pypdfgui.py": "ddd36f83bfe79f45cf059138f90172c6",
        "save.py": "7e091e2a31f704d694b2ef0c6f113d89"
    },
    "license_agreed_to": False,
    "app_max_zoom_scale": 2,
    "ask_save_before_exit": True,
    "allow_keyboard_events": True,
    "pubkey_storage_base": "/"
}

if __name__ == "__main__":
    print(f"Default data: \nAuthor: {template['author']}\nSettings URL: {template['newest_version_settings_url']}\nProject URL: {template['newest_version_url']}\nLicense Agreement Default: {template['license_agreed_to']}\nMax Zoom: {template['app_max_zoom_scale']}\nSave & Exit Popup: {template['ask_save_before_exit']}\nKeyboard Shortcuts: {template['allow_keyboard_events']}\nPublic Key Storage Location: {template['pubkey_storage_base']}")
    input("\nHit \"Enter\" to proceed... ")
    template['release_date'] = str(date.today())
    template['version'] = input("\nVersion number: ")
    template['source_file_hashes'] = generate_all_py_file_hashes(parse_dir="../")
    new_settings_json = json.dumps(template, indent=4)
    pyperclip.copy(new_settings_json)
    print(new_settings_json)
    print("Updated \"settings.json\" contents copied to clipboard.")