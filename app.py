# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Main application launcher (production runner).
Runs on port from SERVER_PORT/PORT env or deploy_config.json, default 6003.
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
    port = os.environ.get('SERVER_PORT') or os.environ.get('PORT')
    if port:
        return int(port)

    config_path = Path(__file__).parent / 'ssh' / 'deploy_config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('server_port', 6003)
        except (json.JSONDecodeError, IOError):
            pass

    return 6003

if __name__ == '__main__':
    app = create_app()

    # Production: port from env or config, bind 0.0.0.0 for AppManager
    port = get_port()
    host = os.environ.get('HOST', '0.0.0.0')

    print(f"Starting Feature Requestor on {host}:{port}...")
    app.run(host=host, port=port, debug=False)
