import inspect
import logging
import os
import logging.handlers


class DefaultArgsFilter(logging.Filter):
    default_args = {
        'room_id': '',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in self.default_args.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return True


def init_logger(work_dir: str):
    folder = os.path.join(work_dir, 'logs')
    if not os.path.exists(folder):
        os.mkdir(folder)
    logger = logging.getLogger('bililive-uploader')
    logger.setLevel(logging.DEBUG)
    # logger for console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)-15s | %(levelname)-8s | %(room_id)-8s %(message)s'))
    console_handler.setLevel(logging.DEBUG)  # todo: change to INFO
    # logger for file
    file = os.path.join(work_dir, 'logs', 'bot.csv')
    csv_handler = logging.handlers.TimedRotatingFileHandler(file, when='midnight', encoding='utf-8')
    csv_handler.setFormatter(logging.Formatter('"%(asctime)s",%(levelname)s,%(filename)s,%(funcName)s,%(threadName)s,'
                                               '%(room_id)s,"%(message)s"'))
    csv_handler.setLevel(logging.DEBUG)
    # add handlers
    logger.addHandler(console_handler)
    logger.addHandler(csv_handler)
    # add filters
    logger.addFilter(DefaultArgsFilter())

    return logger
