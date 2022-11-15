## 使用文档

### 运行程序
#### python 启动
~~~ commandline
python run.py -w ${work dir}
~~~

#### docker 启动
~~~ commandline
docker run -d -p ${port-outside}:8866 -v ${work-dir}:/process -v ${bililive-recorder-path}:/record --name record-uploader gliese129/record-uploader:latest
~~~

~~~ yaml
# 请确保 bot-config.yml 中:
recorder:
   is-docker: true
   
# 此时下面的配置项将被忽略
recorder:
   recorder-dir: /record
server:
   port: 8866
~~~

**请确保该目录下存在 config/bot-config.yml 和 config/room-config.yml**

**请在B站录播姬webhook v2 中加上[http://${your host}/process]()**

### [配置文件](./config-example/readme.md)

### 上传视频

处理完的录播将会放入上传队列等待上传，如果没有设置自动上传，可以通过[http://${your host}/upload]()手动上传

上传失败的视频会重新放入队列中， 等待下次上传

**注意:重启程序会导致上传队列清空**
