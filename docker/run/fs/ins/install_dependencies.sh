#!/bin/bash
set -e

# Update the package manager and install Node.js and npm
apt-get update
apt-get install -y nodejs npm

# Install @google/jules globally using npm
npm install -g @google/jules
