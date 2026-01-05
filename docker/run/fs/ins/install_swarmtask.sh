#!/bin/bash
# Install Go
apt-get update && apt-get install -y golang
# Download and build swarmtask
git clone https://github.com/rdhillbb/swarmtask.git /tmp/swarmtask
cd /tmp/swarmtask
go build -o /usr/local/bin/swarmtask .
cd /
rm -rf /tmp/swarmtask
