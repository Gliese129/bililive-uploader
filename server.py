import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from sanic import Sanic

app = Sanic('bililive-uploader')


@app.main_process_start
def init(*_):
    cpu_count = multiprocessing.cpu_count()
    app.ctx.process_pool = ThreadPoolExecutor
