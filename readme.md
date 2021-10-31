将B站录播姬录制的录播处理后上传到B站

## 使用文档
### 运行程序
#### python 启动
~~~ commandline
python main.py -c ${your config path}
~~~

#### docker 启动
~~~ commandline
docker run -d -p ${port-outside}:8866 -v ${config-path}:/config -v ${bililive-recorder-path}:/recorder -v ${video-process-path}:/process  --name record-uploader gliese/record-uploader:latest
~~~
~~~ yaml
# 请确保 global-config.yml 中:
recorder:
   is-docker: true
   
# 此时下面的字段将没有意义
recorder:
   recorder-dir: /recorder
   process-dir: /process
server:
   port: /8866
~~~

**注意:确保该目录下存在 global-config.yml 和 room-config.yml**

**请在B站录播姬webhook v2 中加上[http://${url}:${port}//video-process]()**
### 配置文件
#### global-config.yml
~~~ yaml
recorder:
  recorder-dir:  # 录播姬工作目录
  process-dir:  # 输出位置*1
  delete-after-upload:  # 是否在上传完成后删除*2
  is-docekr:  # 是否在docker中运行
server:
  port: # 运行端口
  webhooks: # webhook, 在视频处理完成后触发
account:
  username: your account # B站账号
  password: your password # 密码
~~~
1. 建议将此目录同时作为配置文件放置目录，~~因为这样省事~~
2. 如果设置为true，即便录播不需要处理也会删除

webhook内容:
~~~ json
POST /test
Host: 127.0.0.1
Content-Type: application/json
User-Agent: Record Uploader

{
  "EventType": "VideoProceed",
  "TimeStamp": "2021-05-14 17:52:44",
  "EventData": {
    "SessionId": "7c7f3672-70ce-405a-aa12-886702ced6e5",
    "RoomId": 23058,
    "ShortId": 3,
    "Name": "3号直播间",
    "Title": "哔哩哔哩音悦台",
    "AreaNameParent": "生活",
    "AreaNameChild": "影音馆"
  },
  "ProceedVideos": ["C:/proceed dir/out1.flv", "C:/proceed dir/out2.flv"],
  "WorkDictionary": "C:/proceed dir"
}
~~~
#### room-config.yml
~~~ yaml
rooms:
  - id: # 需要上传的直播间 ID，长号短号均可
    tags:  # 上传所需的tag，英文逗号分割，注意不要加空格
    title: # 视频标题，可以使用模版*1
    description:  # 视频描述
    conditions:  # 额外的tag条件，注意判断逻辑为&
    - item: # 字段，例如title*2
      regexp: # 匹配的正则
      tags: # 该条件下额外的tag
      process: # 当匹配到对应条件时是否处理
~~~
1. title模板:
    1) ${anchor} => 主播
    2) ${title} => 直播间标题
    3) ${date} => 直播开始日期 YYYY-MM-DD
    4) ${time} => 直播开始时间 HH:mm:SS
    5) ${parent_area} => 直播主分区
    6) ${child_area} => 直播子分区
2. item: ( 该部分本质上是调用self.\_\_getattribute\_\_实现的，如果乱填可能导致程序崩溃，请注意)
    1) room_id 长号
    2) short_id 短号
    3) title 直播间标题
    4) parent_area 主分区
    5) child_area 子分区
   
**condition的判定策略为&(and), 即只要有一个不符合就判定不需要处理**