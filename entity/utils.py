from typing import Union, Tuple

from exceptions import ConfigNotCompletedException


def _getValue(path: str, default=None, data: dict = None):
    """ get value from a dict
    if not exists, return default value when default is not None,
    otherwise throw ConfigNotCompleted exception

    :param data:
    :param path: in format of xx/xx/xx
    :param default:
    :return:
    """
    assert data is not None
    for p in path.split('/'):
        if p in data:
            data = data[p]
        elif default is not None:
            return default
        else:
            raise ConfigNotCompletedException(path)
    return data


def _setChannel(self, data: Union[Tuple[str], str, list[str]]):
    if isinstance(data, tuple) and len(data) == 2:
        self._channel = data
    elif isinstance(data, list) and len(data) == 2:
        self._channel = tuple(data)
    elif isinstance(data, str) and len(data.split()) == 2:
        self._channel = tuple(data.split())
    else:
        self._channel = None
