import json
import os
from shutil import copy, rmtree
import yaml


def readYml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        result = yaml.load(f.read(), Loader=yaml.Loader)
    return result


def readJson(path: str) -> dict:
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


def copyFiles(files: list[str], target: str) -> list[str]:
    if not os.path.exists(target):
        os.mkdir(target)
    new_files = []
    for file in files:
        copy(src=file, dst=target)
        new_files.append(os.path.join(target, os.path.split(file)[1]))
    return new_files


def deleteFolder(folder: str):
    if os.path.exists(folder):
        rmtree(folder)


def deleteFiles(files: list[str]):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
