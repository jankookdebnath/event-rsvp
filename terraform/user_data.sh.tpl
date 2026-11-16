#!/bin/bash
# Runs once on first boot: install Docker, pull the app from GitHub, build and start it.
set -euxo pipefail
exec > >(tee /var/log/event-rsvp-setup.log) 2>&1

dnf install -y docker git
systemctl enable --now docker

rm -rf /opt/event-rsvp
git clone ${repo_url} /opt/event-rsvp
cd /opt/event-rsvp
git checkout ${git_commit}

docker build --build-arg APP_VERSION=$(git rev-parse --short HEAD) -t event-rsvp:latest app/
docker rm -f event-rsvp || true
docker run -d --name event-rsvp --restart unless-stopped \
  -p 80:8000 \
  -e SECRET_KEY=$(head -c 32 /dev/urandom | base64) \
  -v rsvp-data:/data \
  event-rsvp:latest
