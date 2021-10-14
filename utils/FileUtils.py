# -*- coding: utf-8 -*-
import json
import logging
import os
import yaml
from shutil import copy


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


def CopyFiles(files: list[str], target: str, types: list[str]) -> list[str]:
    if not os.path.exists(target):
        os.makedirs(target)
    new_files = []
    for file in files:
        for file_type in types:
            copy(src=file + '.' + file_type, dst=target)
        new_files.append(os.path.join(target, os.path.split(file)[1]))
    return new_files


def DeleteFolder(folder: str):
    if os.path.exists(folder):
        os.removedirs(folder)


def DeleteFiles(files: list[str]):
    for file in files:
        file += '.flv'
        if os.path.exists(file):
            logging.debug('deleting file: %s' % file)
            os.remove(file)
