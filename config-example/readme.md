# 配置文件

## bot-config.yml
~~~ yaml
bot:
  rec-dir:  # 录播姬工作目录
  is-docker:  # 是否使用docker，默认false
  workers:  # 处理视频线程数 *1

  process:
    damaku:  # 是否压制弹幕，默认为true

  upload:
    multipart:  # 视频是否多p(取决于web接口，可能会导致视频上传失败), 默认false
    delete-after-upload:  # 是否在上传完成后删除, 默认为true *2
    auto-upload:  # 是否自动上传，默认true
    min-time:  # 最短录播时间，单位为s，默认0s，支持表达式

  server:
    port: # 运行端口
    webhooks: # webhook, 在上传完成后触发

account:
  credential:   # 账户凭据, 详见 https://bili.moyu.moe/#/get-credential *3
    sessdata:
    bili_jct:
    buvid3:

~~~
1. 如果不设置 workers ，线程数为CPU核心数和32的最小值；否则为设置值和CPU核心数的最小值
2. 如果 delete-after-upload 设置为true，即便视频不需要处理也会删除
3. 账户凭据**不要**进行url decode，否则会上传失败

webhook内容:
~~~ json
POST [url]
Host: [your host]
Content-Type: application/json
User-Agent: Bililive Uploader

{
  "EventType": "ProcessFinished",
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
  "ProceedVideos": ["/session-id/result0.flv", "/session-id/result1.flv"],
  "WorkDirectory": "C://work-dir"
}
~~~

~~突然发现之前把directory打成dictionary了，得赶紧改掉~~

## room-config.yml
~~~ yaml
rooms:
  - id: # 需要上传的直播间 ID，长号短号均可
    tags:  # 上传所需的tag，英文逗号分割，注意不要加空格
    title: # 视频标题，可以使用模版*1
    description:  # 视频描述
    channel:  # 频道名称，父子分区用空格分割
    conditions:  # 额外的tag条件，注意判断逻辑为&
    - item: # 字段，例如title*2
      regexp: # 匹配的正则
      tags: # 该条件下额外的tag
      channel: # 该条件频道名称，父子分区用空格分割
      process: # 当匹配到对应条件时是否处理
~~~
1. title模板:
    1) ${anchor} => 主播
    2) ${title} => 直播间标题
    3) ${date} => 直播开始日期 YYYY-MM-DD
    4) ${time} => 直播开始时间 HH:mm:SS
    5) ${parent_area} => 直播主分区
    6) ${child_area} => 直播子分区
2. item: 
    1) room_id 长号
    2) short_id 短号
    3) title 直播间标题
    4) parent_area 主分区
    5) child_area 子分区
   
**condition的判定策略为&(and), 即只要有一个为false就不处理**

**channel覆盖逻辑: condition channel > live2video > default channel**
****