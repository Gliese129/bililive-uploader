import json
import os
from array import array
import yaml
import shutil


def YmlReader(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        result = yaml.load(f.read(), Loader=yaml.Loader)
    return result


def ReadJson(path: str) -> dict:
    if not os.path.exists(path):
        folder_path = os.path.dirname(path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{}')
    with open(path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    return result


def WriteDict(path: str, obj: dict):
    if not os.path.exists(path):
        folder_path = os.path.dirname(path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f)


def CopyFiles(files: array, target: str):
    print()
