# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Main application launcher.
See instructions/architecture for development guidelines.
"""

import os
import json
from pathlib import Path
from app import create_app

def get_port():
    """Get server port from deploy_config.json or environment variable."""
    # Try environment variable first
    port = os.environ.get('SERVER_PORT')
    if port:
        return int(port)
    
    # Try deploy_config.json
    config_path = Path(__file__).parent / 'ssh' / 'deploy_config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('server_port', 5000)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Default port
    return 5000

if __name__ == '__main__':
    app = create_app()
    
    # Determine if we're in dev mode
    # Default to debug mode unless explicitly set to production
    dev_mode = os.environ.get('FLASK_ENV') != 'production' and os.environ.get('PRODUCTION') != 'true'
    
    port = get_port()
    
    if dev_mode:
        # Development mode with auto-reload
        print(f"Running in DEBUG mode on http://127.0.0.1:{port}")
        print("Auto-reload enabled - changes will automatically update the app")
        app.run(host='127.0.0.1', port=port, debug=True)
    else:
        # Production mode - direct port access
        host = os.environ.get('HOST', '0.0.0.0')
        print(f"Running in PRODUCTION mode on http://{host}:{port}")
        print("Auto-reload disabled - restart server to see changes")
        app.run(host=host, port=port, debug=False)

