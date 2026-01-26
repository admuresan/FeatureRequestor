# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Email verification token utilities.
See instructions/architecture for development guidelines.
"""

import secrets
from datetime import datetime, timedelta
from app import db
from app.models import EmailVerificationToken, User, UserSignupRequest
from app.utils.email import send_verification_email
from flask import url_for

def generate_verification_token() -> str:
    """
    Generate a cryptographically secure random token.
    
    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)

def create_verification_token(email: str, verification_type: str = 'signup', 
                             user_id: int = None, signup_request_id: int = None,
                             old_email: str = None) -> EmailVerificationToken:
    """
    Create a new email verification token.
    
    Args:
        email: Email address to verify
        verification_type: 'signup' or 'email_change'
        user_id: User ID (for email changes)
        signup_request_id: Signup request ID (for signups)
        old_email: Previous email address (for email changes)
    
    Returns:
        EmailVerificationToken object
    """
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    verification_token = EmailVerificationToken(
        email=email,
        token=token,
        verification_type=verification_type,
        expires_at=expires_at,
        user_id=user_id,
        signup_request_id=signup_request_id,
        old_email=old_email
    )
    
    db.session.add(verification_token)
    db.session.commit()
    
    return verification_token

def send_verification_email_for_token(token_obj: EmailVerificationToken, base_url: str = 'http://localhost:5000') -> bool:
    """
    Send verification email for a token.
    
    Args:
        token_obj: EmailVerificationToken object
        base_url: Base URL for generating verification link
    
    Returns:
        True if email sent successfully, False otherwise
    """
    verification_url = f"{base_url}/auth/verify-email?token={token_obj.token}"
    
    # Get user name for template substitution
    user_name = "User"  # Default fallback
    if token_obj.user_id:
        user = User.query.get(token_obj.user_id)
        if user:
            user_name = user.name
    elif token_obj.signup_request_id:
        signup_request = UserSignupRequest.query.get(token_obj.signup_request_id)
        if signup_request:
            user_name = signup_request.name
    
    return send_verification_email(token_obj.email, token_obj.token, verification_url, user_name=user_name)

def verify_token(token_string: str):
    """
    Verify a token and mark it as verified.
    
    Args:
        token_string: Token string to verify
    
    Returns:
        Tuple of (success, token_object, error_message)
    """
    token = EmailVerificationToken.query.filter_by(token=token_string).first()
    
    if not token:
        return False, None, "Invalid verification token."
    
    if token.is_expired():
        return False, token, "Verification token has expired."
    
    if token.verified_at:
        return False, token, "Token has already been verified."
    
    # Mark as verified
    token.verified_at = datetime.utcnow()
    db.session.commit()
    
    return True, token, ""

