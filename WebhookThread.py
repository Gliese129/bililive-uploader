import datetime
import json
import logging
import threading
import requests


class WebhookThread(threading.Thread):
    urls: list[str]
    event_data: dict
    videos: list[str]
    work_dic: str

    def __init__(self, webhooks: list[str], event_data: dict, proceed_videos: list[str], work_dic: str,
                 name: str = 'webhook'):
        threading.Thread.__init__(self, name=name)
        self.urls = webhooks
        self.event_data = event_data
        self.videos = proceed_videos
        self.work_dic = work_dic

    def run(self) -> None:
        logging.info('sending webhooks...')
        data = {
            'EventType': 'VideoProceed',
            'TimeStamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'EventData': self.event_data,
            'ProceedVideos': self.videos,
            'WorkDictionary': self.work_dic
        }
        headers = {
            'User-Agent': 'Record Uploader',
            'content-type': 'application/json'
        }
        for url in self.urls:
            logging.info('sending webhook to url: %s' % url)
            flag = False
            for i in range(0, 3):
                try:
                    r = requests.post(url=url, headers=headers, data=json.dumps(data), timeout=10)
                    code = r.status_code
                    if 200 <= code <= 300:
                        logging.info('status: success, code: %d' % code)
                        flag = True
                        break
                    else:
                        logging.error('failed, error code: %d, try time: %d' % (code, i + 1))
                except Exception as e:
                    logging.error(e)
                finally:
                    continue
            if not flag:
                logging.error('sending webhook failed!')
