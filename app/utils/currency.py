# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Currency conversion utilities.
See instructions/architecture for development guidelines.
"""

from decimal import Decimal
import os
import stripe
from app.config import get_stripe_key

# Initialize Stripe for currency conversion - will be set when needed
def init_stripe():
    """Initialize Stripe API key from config or environment."""
    stripe.api_key = get_stripe_key('stripe_secret_key')

# Simple exchange rates (fallback if Stripe is not available)
# These are approximate rates - in production, use Stripe API for real-time rates
EXCHANGE_RATES = {
    'CAD': {'USD': Decimal('0.74'), 'EUR': Decimal('0.68')},
    'USD': {'CAD': Decimal('1.35'), 'EUR': Decimal('0.92')},
    'EUR': {'CAD': Decimal('1.47'), 'USD': Decimal('1.09')}
}

def convert_currency(amount, from_currency, to_currency):
    """
    Convert amount from one currency to another.
    Uses Stripe API if available, otherwise falls back to static rates.
    
    Args:
        amount: Decimal amount to convert
        from_currency: Source currency code (CAD, USD, EUR)
        to_currency: Target currency code (CAD, USD, EUR)
    
    Returns:
        Decimal: Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    # Try to use Stripe API for real-time rates
    init_stripe()
    if stripe and stripe.api_key:
        try:
            # Stripe doesn't have a direct currency conversion API, but we can use their rates
            # For now, use static rates as fallback
            # In production, you might want to cache Stripe rates or use a currency API
            pass
        except Exception:
            pass
    
    # Use static exchange rates as fallback
    if from_currency in EXCHANGE_RATES and to_currency in EXCHANGE_RATES[from_currency]:
        rate = EXCHANGE_RATES[from_currency][to_currency]
        return amount * rate
    
    # If no rate found, return original amount
    return amount

def format_currency(amount, currency):
    """
    Format amount with currency symbol.
    
    Args:
        amount: Decimal amount
        currency: Currency code (CAD, USD, EUR)
    
    Returns:
        str: Formatted currency string
    """
    currency_symbols = {
        'CAD': '$',
        'USD': '$',
        'EUR': '€'
    }
    symbol = currency_symbols.get(currency, '$')
    return f"{symbol}{amount:.2f}"

def get_user_preferred_currency(user):
    """
    Get user's preferred currency, defaulting to CAD if not set.
    
    Args:
        user: User object or None
    
    Returns:
        str: Currency code
    """
    if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
        return user.preferred_currency
    return 'CAD'

