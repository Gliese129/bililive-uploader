class InvalidParamException(Exception):
    pass


class ConfigNotCompleted(Exception):
    path: str

    def __init__(self, path: str):
        super().__init__(self)
        self.path = path

    def __str__(self):
        return f'{self.path} not found in config, please check if it\'s set.'

