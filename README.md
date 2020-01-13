[![PyPI release](https://img.shields.io/pypi/v/efb-online-middleware.svg)](https://pypi.org/project/efb-online-middleware/)
[![Downloads](https://pepy.tech/badge/efb-online-middleware/month)](https://pypi.org/project/efb-online-middleware/)

### Main Function

- Check if WeChat is still online

### Usage  

Create file `config.yaml` under document `~/.ehforwarderbot/profiles/default/online.OnlineMiddleware`  

```yaml
echo_mp: 'XXXXXX'       # mp name
ping: 'PING'            # keyword
pong: 'PONG'            # response with keyword
interval: 1800          # interval(s)
```

> MP needs to open auto response function, send `PING`, response with `PONG`

### Install

```bash
pip3 install efb-online-middleware
```  

`~/.ehforwarderbot/profiles/default/config.yaml` file add configuration to enable middleware

```yaml
master_channel: blueset.telegram
slave_channels:
- blueset.wechat
middlewares:
- online.OnlineMiddleware
```
