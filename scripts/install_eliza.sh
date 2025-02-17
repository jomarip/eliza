#!/bin/bash

# Clean environment
echo "Cleaning previous installations..."
rm -rf node_modules eliza/node_modules .pnpm-store

# Set Node version
echo "Setting Node.js version..."
nvm install 23.3.0
nvm use 23.3.0

# Update corepack
echo "Updating package managers..."
corepack enable
corepack prepare pnpm@8.15.0 --activate

# Install dependencies with forced resolutions
echo "Installing dependencies..."
pnpm install --force \
  --frozen-lockfile=false \
  --strict-peer-dependencies=false \
  --config.auto-install-peers=true

# Rebuild native modules
echo "Rebuilding native modules..."
pnpm rebuild sharp canvas cpu-features keccak

# Fix permissions
echo "Fixing permissions..."
find node_modules -type d -exec chmod 755 {} +

echo "Installation complete!" 