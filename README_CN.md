
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


### 新版在线检测（独立入口，默认不启用）

原 `online.OnlineMiddleware` 不变。新版 `online.GuardedMiddleware` 使用**单一后台线程**，提供 PING/PONG 响应等待超时、连续失败判断、恢复在线通知、日志以及可供外部监控读取的 JSON 状态文件。

在 profile 的 `config.yaml` 中把 `online.GuardedMiddleware` 添加到 `middlewares` 列表，并在 `~/.ehforwarderbot/profiles/<profile>/online.GuardedMiddleware/config.yaml` 放置配置，参考 [配置模板](examples/config.guarded.yaml)。

**必须先准备一个公众号：发送 PING 后由公众号关键词自动回复 PONG。** 将 `echo_mp` 设置为该公众号准确名称，确认规则可用后再设置 `enabled: true`。

配置参数：`interval`（检查间隔秒数，默认 1800）、`reply_timeout`（等待 PONG 秒数，默认 45）、`failure_threshold`（连续失败次数，默认 3）、`notify_via_efb`（是否通过 EFB 自身发送通知，默认关闭）、`status_file`（自定义状态文件路径）。

状态有 `starting`、`online`、`degraded`、`offline`、`disabled`。外部监控需要检查状态文件是否过期，否则 EFB 进程挂起时会出现误报在线。注意：底层 wxpy HTTP 操作还有自己的超时，`reply_timeout` 只限制等待 PONG 的时长。本插件不会解决 SQLite 连接泄漏，也不会自动重启 EFB。
