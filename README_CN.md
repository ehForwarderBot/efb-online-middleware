
### 主要功能

- 检查微信是否掉线

### 使用  

`~/.ehforwarderbot/profiles/default/online.OnlineMiddleware`目录下创建配置文件`config.yaml`  

```yaml
echo_mp: 'XXXXXX'       # 公众号名称
ping: 'PING'            # 关键词
pong: 'PONG'            # 关键词回复内容
interval: 1800          # 时间间隔(s)
```

> 公众号有关键词自动回复功能，发送`PING`，自动回复`PONG`

### 安装

`online.py`拷贝到`~/.ehforwarderbot/modules/`目录  

`~/.ehforwarderbot/profiles/default/config.yaml`文件添加配置启用中间件

```yaml
master_channel: blueset.telegram
slave_channels:
- blueset.wechat
middlewares:
- online.OnlineMiddleware
```
