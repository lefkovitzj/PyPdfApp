"""
    Author: lefkovitj (https://lefkovitzj.com)
    File Last Modified: 8/28/2025
    Project Name: PyPdfApp
    File Name: tamper_check.py
"""

import json
import requests
import hashlib
import os

def hash_md5(string_to_hash):
    """Create a MD5 hash of the string argument"""
    hashed = hashlib.md5(string_to_hash.encode("utf-8")).hexdigest()
    return hashed

def generate_all_py_file_hashes(hash_dir="/"):
    """Generate a MD5 hash for each .py file in the directory"""
    hashes = {}
    for dirfile in os.listdir(hash_dir):
        if dirfile.endswith(".py"):
            with open(hash_dir + dirfile,"r") as pyfile:
                hashes[dirfile] = hash_md5(pyfile.read())
    return hashes

def main():
    """Run the tamper checker for PyPdfApp"""
    with open("../settings.json", "r") as json_settings:
        settings = json.load(json_settings)
    settings_url = "https://raw.githubusercontent.com/lefkovitzj/PyPdfApp/main/settings.json" # Load from settings.json's data.
    github_url = "https://github.com/lefkovitzj/PyPdfApp/"

    tampered_files = []

    try:
        url_data = requests.get(settings_url).json() # Get the data at "newest_version_settings_url" as JSON data.
        source_hashes = url_data["source_file_hashes"]
    except: # Request failed due to lack of internet connection or missing online file.
        print(f"Please connect to wifi, if this issue persists, please submit a bug report at {github_url}.")
        return

    if settings["version"] != url_data["version"]:
        print(f"Update needed. Cannot check for file tampering. Download the most recent version of PyPdfApp from {github_url} and try again.")
        return


    instance_hashes = generate_all_py_file_hashes("../")
    if source_hashes != instance_hashes: # At least one file has been tampered with.
        source_keys = list(source_hashes.keys())
        instance_keys = list(instance_hashes.keys())
        source_keys.sort()
        instance_keys.sort()
        if source_keys != instance_keys: # At least one file has been added or removed.
            for key in source_keys: # Check for missing files.
                if key not in instance_keys:
                    tampered_files.append(f"File \"{key}\" is missing.")
                elif source_hashes[key] != instance_hashes[key]: # Check for tampering with files that should exist.
                    tampered_files.append(f"File \"{key}\" has been modified.")
            for key in instance_keys: # Check for extra files.
                if key not in source_keys:
                    tampered_files.append(f"File \"{key}\" is authorized.")

            print(f"TAMPERING DETECTION WARNING!!!\nThe following files have been tampered with:\n{'\n'.join(tampered_files)}\n\nIt is very strongly recommended that you re-install the file(s) above from the original source code found at {github_url} before running PyPdfApp!")
            return
        else: # No additional or missing files were detected.
            for key in source_keys:
                if source_hashes[key] != instance_hashes[key]: # Check for tampering with files that should exist.
                    tampered_files.append(f"File \"{key}\" has been modified.")
            print(f"TAMPERING DETECTION WARNING!!!\nThe following files have been tampered with:\n{'\n'.join(tampered_files)}\n\nIt is very strongly recommended that you re-install the file(s) above from the original source code found at {github_url} before running PyPdfApp!")
            return
    print("TAMPERING DETECTION CHECK COMPLETE\nNo files have been tampered with, added, or removed.\nYour installation of PyPdfApp is up-to-date and matches the official source code files.")

if __name__ == "__main__":
    main()