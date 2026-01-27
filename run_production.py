"""
Production runner for Feature Requestor.
Configured to run on localhost for AppManager proxy compatibility.
"""

import os
import sys
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def get_port():
    """Get server port from environment variable or deploy_config.json."""
    # Try environment variable first
    port = os.environ.get('SERVER_PORT') or os.environ.get('PORT')
    if port:
        return int(port)
    
    # Try deploy_config.json
    config_path = Path(__file__).parent / 'ssh' / 'deploy_config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('server_port', 6003)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Default port
    return 6003

if __name__ == '__main__':
    app = create_app()
    
    # Production settings - port from environment variable or config
    port = get_port()
    
    # Use 127.0.0.1 when behind AppManager proxy (recommended for security)
    # Use 0.0.0.0 if the app needs to be accessible from outside the host
    host = os.environ.get('HOST', '127.0.0.1')
    
    print(f"Starting Feature Requestor on {host}:{port}...")
    app.run(host=host, port=port, debug=False)
