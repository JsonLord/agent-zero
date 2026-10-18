# Supervisor runtime control v5

This patch adds a non-root Supervisor control plane to OpenOperator.

## Files to upload at repository root

Replace:
- `Dockerfile`
- `init_training_master.sh`

Add:
- `supervisord.conf`
- `sctl`
- `supervisor-service-install`
- `supervisor-service-remove`

Keep the other already-working v4 files unchanged.

## Runtime architecture

The container starts one Supervisor as PID 1, under UID 1000.

Its immutable build-time config is:

`/etc/supervisor/conf.d/supervisord.conf`

It exposes a user-only Unix socket:

`/tmp/supervisor.sock`

Runtime service definitions live in the writable directory:

`/a0/usr/supervisor/*.conf`

Agent Zero can therefore add/remove persistent child processes without root.

## Basic control

```bash
sctl status
sctl reread
sctl update
sctl restart run_ui
```

Do not launch a second `supervisord`.

## Add a runtime service

Example config:

```ini
[program:training_api]
command=/opt/venv-training-master/bin/python /a0/usr/workdir/training_api.py
directory=/a0/usr/workdir
autostart=true
autorestart=true
startsecs=2
stopasgroup=true
killasgroup=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

Save it somewhere writable, then:

```bash
supervisor-service-install /a0/usr/workdir/training_api.conf
```

This copies the file into `/a0/usr/supervisor`, validates the full Supervisor
configuration, runs `reread`, and applies it with `update`.

## Remove

```bash
supervisor-service-remove training_api
```

## Security boundary

Supervisor itself runs as UID 1000. Dynamic services can persist/restart, but
they do not gain root privileges. This is service lifecycle control, not
privilege escalation.
