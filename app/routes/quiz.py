# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Quiz routes for sign-up process.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import UserSignupRequest
from app.config import get_config_value

bp = Blueprint('quiz', __name__, url_prefix='/quiz')

# Quiz questions - in a real implementation, these would be stored in database or config
QUIZ_QUESTIONS = [
    {
        'id': 1,
        'question': 'When are payments collected from requesters?',
        'options': [
            'Immediately when they place a bid',
            'When the request is confirmed by the required percentage of requesters',
            'When the developer starts working on the request',
            'Never - it\'s free'
        ],
        'correct': 1,
        'explanation': 'Payments are collected when the request is confirmed by the required percentage (default 80%) of requesters who placed non-zero bids.'
    },
    {
        'id': 2,
        'question': 'How are Stripe fees distributed?',
        'options': [
            'Fees are deducted from developer payouts',
            'Fees are added to the total and distributed proportionally among all requesters who bid',
            'Fees are paid by the platform',
            'There are no fees'
        ],
        'correct': 1,
        'explanation': 'Stripe fees are calculated on the total bid amount and distributed proportionally among all requesters who placed non-zero bids. Each requester pays their original bid plus their share of fees.'
    },
    {
        'id': 3,
        'question': 'What percentage of requesters must confirm a request before payments are processed?',
        'options': [
            '50%',
            '80%',
            '100%',
            '75%'
        ],
        'correct': 1,
        'explanation': f'The default confirmation percentage is {get_config_value("confirmation_percentage", 80)}%. This can be configured by administrators.'
    }
]

@bp.route('/<int:signup_request_id>', methods=['GET', 'POST'])
def take_quiz(signup_request_id):
    """Take quiz after email verification."""
    signup_request = UserSignupRequest.query.get_or_404(signup_request_id)
    
    if not signup_request.email_verified:
        flash('Please verify your email before taking the quiz.', 'error')
        return redirect(url_for('auth.check_email'))
    
    if request.method == 'POST':
        # Check answers
        all_correct = True
        answers = {}
        
        for question in QUIZ_QUESTIONS:
            answer = request.form.get(f'question_{question["id"]}', type=int)
            answers[question['id']] = answer
            if answer != question['correct']:
                all_correct = False
        
        if all_correct:
            # Store quiz completion in signup request (would need a field for this)
            # For now, we'll just proceed to admin approval
            flash('Quiz passed! Your sign-up request has been submitted for admin approval.', 'success')
            return redirect(url_for('auth.check_email'))
        else:
            # Show results with explanations
            return render_template('quiz/results.html',
                                 questions=QUIZ_QUESTIONS,
                                 answers=answers,
                                 signup_request_id=signup_request_id,
                                 all_correct=False)
    
    return render_template('quiz/take.html', questions=QUIZ_QUESTIONS, signup_request_id=signup_request_id)

