FROM python

MAINTAINER 3207960592@qq.com

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt

COPY ./*.py /
COPY ./utils /utils
COPY ./resources /resources

ENTRYPOINT [ "python3", "main.py" ]

CMD [ "-c", "/config" ]