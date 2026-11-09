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


### Experimental guarded online checker (new, opt-in)

The original \`online.OnlineMiddleware\` entry point remains available unchanged. A new \`online.GuardedMiddleware\` adds a single daemon worker, a bounded PONG reply wait, configurable failure threshold, recovery notification, structured logging, and an atomic JSON status file for independent monitoring. No recursive scheduler threads are created.

\`\`\`yaml
master_channel: blueset.telegram
slave_channels:
  - blueset.wechat
middlewares:
  - online.GuardedMiddleware
\`\`\`

Create \`~/.ehforwarderbot/profiles/<profile>/online.GuardedMiddleware/config.yaml\` from [the safe example](examples/config.guarded.yaml). Set the exact \`echo_mp\` name of a WeChat Official Account that automatically responds with \`PONG\` when receiving \`PING\`. Set \`enabled: true\` **only after the auto-response is verified**.

- \`interval: 1800\`: seconds between probes.
- \`reply_timeout: 45\`: maximum wait for a matching PONG, not a global HTTP deadline.
- \`failure_threshold: 3\`: count before offline status.
- \`eat_echo_msg: true\`: suppress only the matching PONG during a pending probe.
- \`notify_via_efb: false\`: optional EFB-side notification; use an independent monitor for reliable alerts.
- \`status_file\`: optional absolute path, e.g. \`/run/efb-online-guard/sssuck.json\`. When omitted, a private status file is written next to the plugin config.

Status values: \`starting\`, \`online\`, \`degraded\`, \`offline\`, \`disabled\`. The external monitor must also check freshness; a stopped EFB process cannot update its own status. The synchronous underlying wxpy lookup/send operations retain their own HTTP timeouts, so \`reply_timeout\` bounds only the PONG wait. **This plugin does not repair SQLite connection leaks or restart EFB automatically.**

Run tests with \`python -m unittest discover -s tests -v\` in an EFB-compatible virtual environment.
