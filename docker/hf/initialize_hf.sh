#!/bin/bash
set -e
mkdir -p /a0/usr /a0/logs /a0/tmp /a0/per
# Initialize environment
/opt/venv-a0/bin/python /a0/prepare.py --dockerized=true
# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
