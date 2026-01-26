# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Email sending utilities.
See instructions/architecture for development guidelines.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import load_email_config, load_email_templates
import re

def substitute_template_variables(template: str, variables: dict) -> str:
    """
    Substitute variables in email template.
    
    Args:
        template: Email template string with {variable} placeholders
        variables: Dictionary of variable names and values
    
    Returns:
        Template with variables substituted
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f'{{{key}}}', str(value))
    return result

def send_email(to_email: str, subject: str, body_html: str, body_text: str = None) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML email body
        body_text: Plain text email body (optional)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    config = load_email_config()
    
    # Check if email is configured
    if not config.get('smtp_host') or not config.get('smtp_username'):
        print("Warning: Email not configured. Skipping email send.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        # Use the email mask if configured, otherwise use SMTP username
        from_email = config.get('from_email_mask') or config.get('smtp_username')
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Add body
        if body_text:
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)
        
        # Connect to SMTP server
        smtp_port = config.get('smtp_port', 587)
        smtp_security = config.get('smtp_security', 'TLS')
        
        if smtp_security == 'SSL':
            server = smtplib.SMTP_SSL(config['smtp_host'], smtp_port)
        else:
            server = smtplib.SMTP(config['smtp_host'], smtp_port)
            if smtp_security == 'TLS':
                server.starttls()
        
        # Login and send
        server.login(config['smtp_username'], config['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_verification_email(email: str, token: str, verification_url: str, user_name: str = "User") -> bool:
    """
    Send email verification email.
    
    Args:
        email: Recipient email address
        token: Verification token
        verification_url: Full verification URL
        user_name: User's name for template substitution
    
    Returns:
        True if email sent successfully, False otherwise
    """
    templates = load_email_templates()
    template = templates.get('email_verification', {
        'subject': 'Verify your email address',
        'body': 'Please click the following link to verify your email: {verification_link}'
    })
    
    subject = substitute_template_variables(template.get('subject', 'Verify your email'), {
        'verification_link': verification_url,
        'user_name': user_name
    })
    
    body = substitute_template_variables(template.get('body', 'Please click the following link to verify your email: {verification_link}'), {
        'verification_link': verification_url,
        'user_name': user_name
    })
    
    return send_email(email, subject, body, body)

def send_password_reset_email(email: str, reset_url: str) -> bool:
    """
    Send password reset email.
    
    Args:
        email: Recipient email address
        reset_url: Password reset URL
    
    Returns:
        True if email sent successfully, False otherwise
    """
    templates = load_email_templates()
    template = templates.get('password_reset', {
        'subject': 'Reset your password',
        'body': 'Please click the following link to reset your password: {reset_link}'
    })
    
    subject = substitute_template_variables(template.get('subject', 'Reset your password'), {
        'reset_link': reset_url
    })
    
    body = substitute_template_variables(template.get('body', 'Please click the following link to reset your password: {reset_link}'), {
        'reset_link': reset_url
    })
    
    return send_email(email, subject, body, body)

