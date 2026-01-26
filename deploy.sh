#!/bin/bash
# IMPORTANT: Read instructions/architecture before making changes to this file
# Deployment script for Feature Requestor
# See instructions/architecture for development guidelines.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Read deployment config
DEPLOY_CONFIG="ssh/deploy_config.json"
if [ ! -f "$DEPLOY_CONFIG" ]; then
    echo -e "${RED}Error: $DEPLOY_CONFIG not found${NC}"
    exit 1
fi

PROD_IP=$(python3 -c "import json; print(json.load(open('$DEPLOY_CONFIG'))['prod_server_ip'])")
SSH_KEY="ssh/ssh-key-2025-12-26.key"
APP_NAME="FeatureRequestor"
REMOTE_DIR="/home/ubuntu/$APP_NAME"

# Check for --full flag
FULL_DEPLOY=false
if [ "$1" == "--full" ]; then
    FULL_DEPLOY=true
    echo -e "${YELLOW}Warning: Full deploy mode - this will delete all instance data!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

echo -e "${GREEN}Starting deployment to $PROD_IP...${NC}"

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Set correct permissions for SSH key
chmod 600 "$SSH_KEY"

# Create remote directory if it doesn't exist
echo -e "${GREEN}Creating remote directory...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ubuntu@$PROD_IP "mkdir -p $REMOTE_DIR"

if [ "$FULL_DEPLOY" = true ]; then
    echo -e "${YELLOW}Removing existing files...${NC}"
    ssh -i "$SSH_KEY" ubuntu@$PROD_IP "rm -rf $REMOTE_DIR/*"
fi

# Copy files (exclude instance folder and other git-ignored files)
echo -e "${GREEN}Copying files...${NC}"
rsync -avz --exclude 'instance/' --exclude '.git/' --exclude '__pycache__/' --exclude '*.pyc' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./ ubuntu@$PROD_IP:$REMOTE_DIR/

# Create instance directory structure on remote
echo -e "${GREEN}Creating instance directory structure...${NC}"
ssh -i "$SSH_KEY" ubuntu@$PROD_IP "mkdir -p $REMOTE_DIR/instance/data $REMOTE_DIR/instance/uploads"

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
ssh -i "$SSH_KEY" ubuntu@$PROD_IP "cd $REMOTE_DIR && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Restart service (assuming systemd service)
echo -e "${GREEN}Restarting service...${NC}"
ssh -i "$SSH_KEY" ubuntu@$PROD_IP "sudo systemctl restart feature-requestor || echo 'Service restart skipped (service may not be configured yet)'"

echo -e "${GREEN}Deployment complete!${NC}"

