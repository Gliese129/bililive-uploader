FROM Python 3.9.7

MAINTAINER Gliese "3207960592@qq.com"

COPY ./requirements.txt /requirements.txt

WORKDIR /

RUN pip3 install -r requirements.txt

COPY . /

ENTRYPOINT [ "python3" ]

CMD [ "main.py" ]