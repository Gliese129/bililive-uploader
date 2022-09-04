import logging
import sys

logger = logging.getLogger('bililive-uploader')


class ConfigNotCompletedException(Exception):
    path: str

    def __init__(self, path: str):
        super().__init__(self)
        self.path = path
        logger.fatal(self)
        sys.exit(1)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.path} not found in config, please check if it\'s set.'



