# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Authentication utilities for password hashing and verification.
See instructions/architecture for development guidelines.
"""

import bcrypt
import re

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password string
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def generate_username(name: str, email: str = None) -> str:
    """
    Generate a unique username from a name and optionally email.
    
    Args:
        name: User's full name
        email: User's email address (optional, used as fallback)
    
    Returns:
        A unique username string
    """
    # Import here to avoid circular imports
    from app.models import User, UserSignupRequest
    
    # Start with name-based username
    # Remove special characters, convert to lowercase, replace spaces with underscores
    username_base = re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(' ', '_'))
    
    # If name is too short or empty, use email prefix
    if len(username_base) < 3:
        if email:
            username_base = email.split('@')[0].lower()
            username_base = re.sub(r'[^a-zA-Z0-9_]', '', username_base)
        else:
            username_base = 'user'
    
    # Ensure minimum length
    if len(username_base) < 3:
        username_base = 'user'
    
    # Check if username exists and append number if needed
    username = username_base
    counter = 1
    while User.query.filter_by(username=username).first() or UserSignupRequest.query.filter_by(username=username).first():
        username = f"{username_base}{counter}"
        counter += 1
    
    return username

