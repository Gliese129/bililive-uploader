import logging
import os


def init_logger(work_dir: str):
    folder = os.path.join(work_dir, 'logs')
    if not os.path.exists(folder):
        os.mkdir(folder)
    file = os.path.join(work_dir, 'logs', 'log.csv')
    logger = logging.getLogger('bililive-uploader')
    logger.setLevel(logging.DEBUG)
    # logger for console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    console_handler.setLevel(logging.INFO)
    # logger for file
    with open(file, 'w') as f:
        f.write('time,level,file,function,thread,message\n')
    debug_handler = logging.FileHandler(file)
    debug_handler.setFormatter(logging.Formatter('"%(asctime)s",%(levelname)s,%(filename)s,%(funcName)s,%(threadName)s,'
                                                 '"%(message)s"'))
    debug_handler.setLevel(logging.DEBUG)
    # add handlers
    logger.addHandler(console_handler)
    logger.addHandler(debug_handler)
    return logger
