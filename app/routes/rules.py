# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Rules and documentation routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template
from app.config import get_config_value

bp = Blueprint('rules', __name__, url_prefix='/rules')

@bp.route('')
def index():
    """Rules and documentation page."""
    # Get config values for dynamic display
    confirmation_percentage = get_config_value('confirmation_percentage', 80)
    
    return render_template('rules/index.html', confirmation_percentage=confirmation_percentage)

