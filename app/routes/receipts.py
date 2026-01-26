# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Receipt and paystub generation routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import PaymentTransaction
from app.utils.pdf_generation import generate_receipt_html, generate_paystub_html, generate_pdf_from_html
from datetime import datetime
from io import BytesIO

bp = Blueprint('receipts', __name__, url_prefix='/receipts')

@bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate_receipt():
    """Generate receipt page."""
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if not start_date_str or not end_date_str:
            flash('Please select both start and end dates.', 'error')
            return render_template('receipts/generate.html')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Get transactions
        transactions = PaymentTransaction.query.filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.direction.in_(['charged', 'tip']),
            PaymentTransaction.transaction_date >= start_date,
            PaymentTransaction.transaction_date <= end_date
        ).all()
        
        if not transactions:
            flash('No transactions found for the selected date range.', 'info')
            return render_template('receipts/generate.html')
        
        # Generate PDF
        html = generate_receipt_html(current_user, transactions, start_date, end_date)
        pdf_bytes = generate_pdf_from_html(html)
        
        # Return PDF
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'receipt_{start_date_str}_to_{end_date_str}.pdf'
        )
    
    return render_template('receipts/generate.html')

@bp.route('/paystub/generate', methods=['GET', 'POST'])
@login_required
def generate_paystub():
    """Generate paystub page (for developers)."""
    if current_user.role != 'dev':
        flash('Paystubs are only available for developers.', 'error')
        return redirect(url_for('home.dashboard'))
    
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if not start_date_str or not end_date_str:
            flash('Please select both start and end dates.', 'error')
            return render_template('receipts/generate_paystub.html')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Get transactions
        transactions = PaymentTransaction.query.filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.direction == 'paid',
            PaymentTransaction.transaction_date >= start_date,
            PaymentTransaction.transaction_date <= end_date
        ).all()
        
        if not transactions:
            flash('No payments found for the selected date range.', 'info')
            return render_template('receipts/generate_paystub.html')
        
        # Generate PDF
        html = generate_paystub_html(current_user, transactions, start_date, end_date)
        pdf_bytes = generate_pdf_from_html(html)
        
        # Return PDF
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'paystub_{start_date_str}_to_{end_date_str}.pdf'
        )
    
    return render_template('receipts/generate_paystub.html')

