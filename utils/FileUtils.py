# -*- coding: utf-8 -*-
import json
import logging
import os
import yaml
from shutil import copy, rmtree


def YmlReader(path: str) -> dict:
    """ Read yaml file

    :param path: file path
    :return: dictionary
    """
    with open(path, 'r', encoding='utf-8') as f:
        result = yaml.load(f.read(), Loader=yaml.Loader)
    return result


def ReadJson(path: str) -> dict:
    """ Read json file

    :param path: file path
    :return: json dictionary
    """
    if not os.path.exists(path):
        folder_path = os.path.dirname(path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{}')
    with open(path, 'r', encoding='utf-8') as f:
        result = json.load(f)
    return result


def WriteDict(path: str, obj: dict) -> None:
    """  Write dict to json file

    :param path: file path
    :param obj: object need to write
    :return: None
    """
    if not os.path.exists(path):
        folder_path = os.path.dirname(path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f)


def CopyFiles(files: list[str], target: str, types: list[str]) -> list[str]:
    """ Copy files to target folder

    :param files: files need to copy(no extension)
    :param target: target folder
    :param types: file extensions
    :return: files copied
    """
    if not os.path.exists(target):
        os.makedirs(target)
    new_files = []
    for file in files:
        for file_type in types:
            copy(src=file + '.' + file_type, dst=target)
        new_files.append(os.path.join(target, os.path.split(file)[1]))
    return new_files


def DeleteFolder(folder: str) -> None:
    """ Delete an empty folder

    :param folder: folder path
    :return: None
    """
    if os.path.exists(folder):
        rmtree(folder)


def DeleteFiles(files: list[str], types: list[str]) -> None:
    """ Delete files

    :param files: files need to delete(no extension)
    :param types: file extensions
    :return: None
    """
    for file in files:
        for file_type in types:
            if os.path.exists(file + '.' + file_type):
                delete_file = f'{file}.{file_type}'
                logging.debug('deleting file: %s' % delete_file)
                os.remove(delete_file)
