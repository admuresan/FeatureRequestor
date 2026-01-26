# IMPORTANT: Read instructions/architecture before making changes to this file
"""
PDF generation utilities for receipts and paystubs.
See instructions/architecture for development guidelines.
"""

from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from flask import current_app
import os
from app.models import PaymentTransaction, User

def generate_receipt_html(user: User, transactions: list, start_date: datetime, end_date: datetime) -> str:
    """
    Generate HTML for a receipt.
    
    Args:
        user: User object
        transactions: List of PaymentTransaction objects
        start_date: Start date for receipt
        end_date: End date for receipt
    
    Returns:
        HTML string
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; }}
            .info {{ margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .total {{ font-weight: bold; font-size: 1.2em; }}
            .summary {{ margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Receipt</h1>
            <p>Feature Requestor</p>
        </div>
        <div class="info">
            <p><strong>Name:</strong> {user.name}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Date Range:</strong> {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>App</th>
                    <th>Feature Request</th>
                    <th>Amount</th>
                    <th>Currency</th>
                </tr>
            </thead>
            <tbody>
    """
    
    totals_by_currency = {}
    
    for transaction in transactions:
        if transaction.direction == 'charged' or (transaction.direction == 'tip' and transaction.user_id == user.id):
            app_name = transaction.app.app_display_name if transaction.app else 'N/A'
            fr_title = transaction.feature_request.title if transaction.feature_request else 'Tip'
            
            html += f"""
                <tr>
                    <td>{transaction.transaction_date.strftime('%Y-%m-%d')}</td>
                    <td>{app_name}</td>
                    <td>{fr_title}</td>
                    <td>{transaction.amount}</td>
                    <td>{transaction.currency}</td>
                </tr>
            """
            
            if transaction.currency not in totals_by_currency:
                totals_by_currency[transaction.currency] = Decimal('0.00')
            totals_by_currency[transaction.currency] += transaction.amount
    
    html += """
            </tbody>
        </table>
        <div class="summary">
            <h2>Summary</h2>
    """
    
    for currency, total in totals_by_currency.items():
        html += f"<p><strong>Total in {currency}:</strong> {total}</p>"
    
    # Grand total in user's preferred currency
    grand_total = sum(totals_by_currency.values())  # Simplified - would need currency conversion
    html += f"<p class='total'><strong>Grand Total ({user.preferred_currency}):</strong> {grand_total}</p>"
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html

def generate_paystub_html(user: User, transactions: list, start_date: datetime, end_date: datetime) -> str:
    """
    Generate HTML for a paystub.
    
    Args:
        user: User object
        transactions: List of PaymentTransaction objects
        start_date: Start date for paystub
        end_date: End date for paystub
    
    Returns:
        HTML string
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; }}
            .info {{ margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .total {{ font-weight: bold; font-size: 1.2em; }}
            .summary {{ margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Paystub</h1>
            <p>Feature Requestor</p>
        </div>
        <div class="info">
            <p><strong>Name:</strong> {user.name}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Date Range:</strong> {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>App</th>
                    <th>Feature Request</th>
                    <th>Amount</th>
                    <th>Currency</th>
                </tr>
            </thead>
            <tbody>
    """
    
    totals_by_currency = {}
    
    for transaction in transactions:
        if transaction.direction == 'paid':
            app_name = transaction.app.app_display_name if transaction.app else 'N/A'
            fr_title = transaction.feature_request.title if transaction.feature_request else 'Tip'
            
            html += f"""
                <tr>
                    <td>{transaction.transaction_date.strftime('%Y-%m-%d')}</td>
                    <td>{app_name}</td>
                    <td>{fr_title}</td>
                    <td>{transaction.amount}</td>
                    <td>{transaction.currency}</td>
                </tr>
            """
            
            if transaction.currency not in totals_by_currency:
                totals_by_currency[transaction.currency] = Decimal('0.00')
            totals_by_currency[transaction.currency] += transaction.amount
    
    html += """
            </tbody>
        </table>
        <div class="summary">
            <h2>Summary</h2>
    """
    
    for currency, total in totals_by_currency.items():
        html += f"<p><strong>Total in {currency}:</strong> {total}</p>"
    
    grand_total = sum(totals_by_currency.values())
    html += f"<p class='total'><strong>Grand Total ({user.preferred_currency}):</strong> {grand_total}</p>"
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html

def generate_pdf_from_html(html: str) -> bytes:
    """
    Generate PDF from HTML string.
    
    Args:
        html: HTML string
    
    Returns:
        PDF bytes
    """
    # Validate HTML input
    if not html or not isinstance(html, str):
        raise ValueError("HTML must be a non-empty string")
    
    # Base URL for resolving relative paths (for images, etc.)
    base_url = None
    if current_app and hasattr(current_app, 'instance_path'):
        try:
            base_url = os.path.dirname(current_app.instance_path)
        except:
            pass
    
    # Render HTML to PDF using WeasyPrint
    try:
        if base_url:
            html_doc = HTML(string=html, base_url=base_url)
        else:
            html_doc = HTML(string=html)
        return html_doc.write_pdf()
    except Exception as e:
        # Fallback: try without base_url if it was set
        if base_url:
            try:
                html_doc = HTML(string=html)
                return html_doc.write_pdf()
            except Exception as e2:
                raise Exception(f"Failed to render PDF with WeasyPrint: {str(e2)}. Original error: {str(e)}")
        raise Exception(f"Failed to render PDF with WeasyPrint: {str(e)}")

