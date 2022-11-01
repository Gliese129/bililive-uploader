import json
import os
from shutil import copy, rmtree
from typing import Tuple

import yaml


def readYml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        result = yaml.load(f.read(), Loader=yaml.Loader)
    return result


def readJson(path: str, default=None) -> dict:
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    return result


def creatFile(file: str, init='', ignore=True):
    """

    :param file:
    :param init: init string
    :param ignore: ignore when file exists
    :return:
    """
    if ignore and os.path.exists(file):
        return

    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)
    with open(file, 'w') as f:
        f.write(init)


def writeDict(file: str, obj: dict):
    creatFile(file)
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(obj, f)


def copyFiles(files: list[str], target: str, output_with_folder=True) -> list[str]:
    if not os.path.exists(target):
        os.mkdir(target)
    new_files = []
    for file in files:
        copy(src=file, dst=target)
        if output_with_folder:
            new_files.append(os.path.join(target, os.path.split(file)[1]))
        else:
            new_files.append(os.path.split(file)[1])
    return new_files


def deleteFolder(folder: str):
    if os.path.exists(folder):
        rmtree(folder)


def deleteFiles(files: list[str]):
    for file in files:
        if os.path.exists(file):
            os.remove(file)


def renameFile(file: str, new_name: str):
    if os.path.exists(file):
        os.rename(file, new_name)


def renameFiles(files: list[Tuple[str, str]]):
    for file, new_name in files:
        renameFile(file, new_name)
