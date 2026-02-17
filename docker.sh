#!/bin/bash

set -e

echo "🚀 Updating system..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "🧼 Removing older Docker versions (if any)..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

echo "🔐 Installing Docker dependencies..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "🔑 Adding Docker GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "📦 Adding Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "🔄 Updating package list..."
sudo apt-get update -y

echo "🐳 Installing Docker Engine and Compose plugin..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "👤 Adding current user to docker group..."
sudo usermod -aG docker $USER

echo "✅ Docker installed successfully!"
echo "🔁 Please log out and back in or reboot the VPS for group changes to take effect."