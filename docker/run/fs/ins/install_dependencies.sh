#!/bin/bash
set -e

# Install curl and gnupg if they are not already installed.
apt-get update
apt-get install -y curl gnupg

# Add the NodeSource repository for Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

# Install Node.js
apt-get install -y nodejs

# Install @google/jules globally using npm
npm install -g @google/jules
