# IMPORTANT: Read instructions/architecture before making changes to this file
"""
External API routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, request, redirect, url_for, jsonify
from app.models import App

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/open-requests', methods=['POST', 'OPTIONS'])
def open_requests():
    """
    External endpoint for other applications to open feature requests page.
    Accepts JSON payload: {"app_name": "my-app"}
    Redirects to feature requests page filtered by app.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    # Set CORS headers
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Validate JSON payload
    if not request.is_json:
        return jsonify({'error': 'Invalid JSON'}), 400, response_headers
    
    data = request.get_json()
    app_name = data.get('app_name')
    
    if not app_name:
        return jsonify({'error': 'Missing app_name'}), 400, response_headers
    
    # Check if app exists
    app = App.query.filter_by(app_name=app_name).first()
    
    if app:
        # Redirect to feature requests page filtered by app
        redirect_url = url_for('feature_requests.list', app=app_name)
    else:
        # App not found - redirect with message
        redirect_url = url_for('feature_requests.list', app=app_name, error='app_not_found')
    
    # Return redirect response with CORS headers
    response = redirect(redirect_url)
    for key, value in response_headers.items():
        response.headers[key] = value
    return response

