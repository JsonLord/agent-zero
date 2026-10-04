#!/bin/bash
set -e

# install playwright - moved to install A0
# bash /ins/install_playwright.sh "$@"

# searxng - moved to base image
# bash /ins/install_searxng.sh "$@"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get unavailable; skipping LibreOffice install"
  exit 0
fi

KALI_SUITE="kali-last-snapshot"
LIBREOFFICE_VERSION="4:26.2.4.2-1"
XPRA_VERSION="6.5.2-r0-1"
arch="$(dpkg --print-architecture)"

XPRA_HTML5_VERSION="19-r1-1"
if [ "$arch" = "arm64" ]; then
  XPRA_HTML5_VERSION="21-r1-1"
fi

LIBREOFFICE_PACKAGES=(
  "libreoffice-core"
  "libreoffice-writer"
  "libreoffice-calc"
  "libreoffice-impress"
  "libreoffice-gtk3"
  "python3-uno"
)
XPRA_PACKAGES=(
  "xpra"
)

apt-get update
ATK_VERSION="$(dpkg-query -W -f='${Version}' libatk1.0-0t64)"
ATK_GIR_PACKAGE="/tmp/gir1.2-atk-1.0_${ATK_VERSION}_${arch}.deb"
(cd /tmp && apt-get download "gir1.2-atk-1.0=$ATK_VERSION")

XPRA_PACKAGES=()

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  "$ATK_GIR_PACKAGE" \
  gir1.2-gtk-3.0 \
  "${LIBREOFFICE_PACKAGES[@]}" \
  "${XPRA_PACKAGES[@]}" \
  xfce4-session \
  xfwm4 \
  xfce4-panel \
  xfdesktop4 \
  xfce4-settings \
  thunar \
  gvfs \
  libglib2.0-bin \
  xfce4-terminal \
  x11-xserver-utils \
  x11-utils \
  x11-apps \
  xdotool \
  xclip \
  xauth \
  xvfb \
  dbus-x11 \
  fonts-dejavu \
  fonts-liberation \
  fonts-crosextra-caladea \
  fonts-crosextra-carlito \
  fonts-noto-core \
  fonts-noto-cjk \
  fonts-noto-color-emoji

rm -f "$ATK_GIR_PACKAGE"
rm -rf /var/lib/apt/lists/*
