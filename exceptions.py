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


class UnknownError(Exception):
    msg: str

    def __init__(self, msg):
        super().__init__(self)
        self.msg = msg
        logger.error(self)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.msg}\n' \
                f'This error shouldn\'t happen when bot is running normally. ' \
                f'You can ignore this error if bot is still able to run normally.' \
                f'It might happen when bot restarts when bililive recorder is recording.' \
                f'If you think this error is caused by a bug, please report it to the developer.'



