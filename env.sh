#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " Raspberry Pi environment setup for QRe-paper"
echo "============================================================"

echo
echo "[1/8] OS information"
echo "------------------------------------------------------------"
if [[ -f /etc/os-release ]]; then
  cat /etc/os-release
else
  uname -a
fi

echo
echo "[2/8] Update apt package index"
echo "------------------------------------------------------------"
sudo apt update

echo
echo "[3/8] Install base tools"
echo "------------------------------------------------------------"
sudo apt install -y \
  git \
  curl \
  wget \
  jq \
  unzip \
  zip \
  ca-certificates \
  vim \
  nano \
  tree \
  htop

echo
echo "[4/8] Install Python and build dependencies"
echo "------------------------------------------------------------"
sudo apt install -y \
  python3 \
  python3-full \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  pkg-config \
  swig \
  liblgpio-dev

echo
echo "[5/8] Install image / QR related native libraries"
echo "------------------------------------------------------------"
sudo apt install -y \
  libjpeg-dev \
  zlib1g-dev \
  libtiff-dev \
  libfreetype6-dev \
  libopenjp2-7 \
  libopenjp2-7-dev \
  libatlas-base-dev

echo
echo "[6/8] Install GPIO / SPI / I2C utilities"
echo "------------------------------------------------------------"
sudo apt install -y \
  gpiod \
  i2c-tools \
  python3-gpiozero \
  python3-lgpio

echo
echo "[7/8] Enable SPI"
echo "------------------------------------------------------------"

if command -v raspi-config >/dev/null 2>&1; then
  echo "Enabling SPI using raspi-config nonint..."
  sudo raspi-config nonint do_spi 0 || true
else
  echo "raspi-config not found. Trying to enable SPI via boot config..."

  if [[ -f /boot/firmware/config.txt ]]; then
    CONFIG_FILE="/boot/firmware/config.txt"
  elif [[ -f /boot/config.txt ]]; then
    CONFIG_FILE="/boot/config.txt"
  else
    CONFIG_FILE=""
  fi

  if [[ -n "${CONFIG_FILE}" ]]; then
    if grep -qE '^\s*dtparam=spi=on' "${CONFIG_FILE}"; then
      echo "SPI already enabled in ${CONFIG_FILE}"
    else
      echo "Adding dtparam=spi=on to ${CONFIG_FILE}"
      echo 'dtparam=spi=on' | sudo tee -a "${CONFIG_FILE}" >/dev/null
    fi
  else
    echo "WARNING: Could not find Raspberry Pi boot config file."
    echo "Please enable SPI manually using raspi-config."
  fi
fi

echo
echo "[8/8] Final checks"
echo "------------------------------------------------------------"

echo
echo "Python:"
python3 --version || true

echo
echo "Git:"
git --version || true

echo
echo "GPIO tool:"
if command -v gpioinfo >/dev/null 2>&1; then
  gpioinfo | head || true
else
  echo "gpioinfo not found"
fi

echo
echo "SPI devices:"
if ls /dev/spidev* >/dev/null 2>&1; then
  ls -l /dev/spidev*
else
  echo "No /dev/spidev* found yet."
  echo "SPI may require reboot."
fi

echo
echo "============================================================"
echo " Setup completed."
echo "============================================================"
echo
echo "Recommended next step:"
echo
echo "  sudo reboot"
echo
echo "After reboot, check:"
echo
echo "  ls /dev/spidev*"
echo "  git --version"
echo "  python3 --version"
echo "  gpioinfo | head"
echo
echo "Then clone your repository:"
echo
echo "  cd ~/Desktop"
echo "  git clone <YOUR_REPOSITORY_URL>"
echo
