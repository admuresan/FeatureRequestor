#!/bin/bash
# Deployment script for Feature Requestor
# Copies files to BlackGrid server. No sudo needed if /BlackGrid exists.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECTS_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
CENTRAL_SSH="$PROJECTS_ROOT/ssh"
SSH_KEY="$CENTRAL_SSH/ssh-key-2025-12-26.key"
cd "$SCRIPT_DIR"

SERVER_IP="192.168.2.86"
SERVER_USER="remoteterminal"
for cfg in "$CENTRAL_SSH/deploy_config" "$CENTRAL_SSH/deploy_config.json"; do
    [ -f "$cfg" ] || continue
    SERVER_IP=$(python3 -c "import json; d=json.load(open('$cfg')); print(d.get('internalIP','192.168.2.86'))" 2>/dev/null) || true
    SERVER_USER=$(python3 -c "import json; d=json.load(open('$cfg')); print(d.get('username','remoteterminal'))" 2>/dev/null) || true
    break
done
SERVER_IP="${SERVER_IP:-192.168.2.86}"
SERVER_USER="${SERVER_USER:-remoteterminal}"

APP_NAME="featurerequestor"
APP_DIR="/BlackGrid/$APP_NAME"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
SCP="scp -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "=========================================="
echo "Deploying Feature Requestor (files only)"
echo "=========================================="
echo "Server: $SERVER_USER@$SERVER_IP"
echo "App Directory: $APP_DIR"
echo "=========================================="

[ ! -f "$SSH_KEY" ] && { echo "❌ SSH key not found"; exit 1; }
chmod 600 "$SSH_KEY"

$SSH "$SERVER_USER@$SERVER_IP" "mkdir -p $APP_DIR" || { echo "❌ Failed to create $APP_DIR"; exit 1; }

echo "📦 Copying files..."
TEMP_DIR=$(mktemp -d 2>/dev/null || echo "/tmp/deploy_$$")
trap "rm -rf $TEMP_DIR" EXIT
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='venv' --exclude='feature_requestor_venv' --exclude='node_modules' \
    --exclude='.gitignore' --exclude='*.bat' --exclude='instance' \
    --exclude='ssh' --exclude='instructions' \
    -czf "$TEMP_DIR/app.tar.gz" .

$SCP "$TEMP_DIR/app.tar.gz" "$SERVER_USER@$SERVER_IP:/tmp/"
$SSH "$SERVER_USER@$SERVER_IP" "cd $APP_DIR && tar -xzf /tmp/app.tar.gz && rm /tmp/app.tar.gz"

echo "✅ Deployment complete!"
