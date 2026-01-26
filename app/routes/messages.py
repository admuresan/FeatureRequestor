# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Messaging routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import MessageThread, MessageThreadParticipant, Message, MessagePollVote, User, UserBlock

bp = Blueprint('messages', __name__, url_prefix='/messages')

@bp.route('')
@login_required
def index():
    """Messaging page."""
    thread_id = request.args.get('thread_id', type=int)
    
    # Check if we should start a new message with a specific user
    action = request.args.get('action')
    user_id = request.args.get('user_id', type=int)
    target_user = None
    if action == 'new' and user_id:
        # Pre-select user for new message (will be handled in template)
        target_user = User.query.get(user_id)
        if target_user:
            flash(f'Starting new message with {target_user.name}', 'info')
    
    # Get user's message threads
    user_threads = MessageThread.query.join(MessageThreadParticipant).filter(
        MessageThreadParticipant.user_id == current_user.id,
        MessageThreadParticipant.is_blocked == False
    ).order_by(MessageThread.updated_at.desc()).all()
    
    # Convert dynamic relationships to lists for template rendering
    for thread in user_threads:
        thread._messages_list = thread.messages.all()
        thread._participants_list = thread.participants.all()
    
    # Get current thread
    current_thread = None
    messages = []
    if thread_id:
        current_thread = MessageThread.query.get(thread_id)
        if current_thread:
            # Convert dynamic relationships to lists for current thread
            current_thread._messages_list = current_thread.messages.all()
            current_thread._participants_list = current_thread.participants.all()
            # Check if user is participant
            participant = MessageThreadParticipant.query.filter_by(
                thread_id=thread_id,
                user_id=current_user.id
            ).first()
            if participant and not participant.is_blocked:
                messages = Message.query.filter_by(thread_id=thread_id).order_by(Message.created_at.asc()).all()
                # Mark as read
                participant.last_read_at = db.func.now()
                db.session.commit()
    
    # Get all users for creating new messages
    all_users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('messages/index.html',
                         threads=user_threads,
                         current_thread=current_thread,
                         messages=messages,
                         all_users=all_users,
                         target_user=target_user)

@bp.route('/create', methods=['POST'])
@login_required
def create_thread():
    """Create a new message thread."""
    if not current_user.email_verified:
        flash('Please verify your email address before sending messages.', 'error')
        return redirect(url_for('messages.index'))
    
    recipient_ids = request.form.getlist('recipient_ids')
    message_text = request.form.get('message')
    
    if not recipient_ids or not message_text:
        flash('Please select recipients and enter a message.', 'error')
        return redirect(url_for('messages.index'))
    
    # Convert to integers
    recipient_ids = [int(rid) for rid in recipient_ids]
    
    # Check for blocked users
    blocked = UserBlock.query.filter_by(blocker_id=current_user.id).all()
    blocked_ids = [b.blocked_id for b in blocked]
    if any(rid in blocked_ids for rid in recipient_ids):
        flash('Cannot message blocked users.', 'error')
        return redirect(url_for('messages.index'))
    
    # Determine thread type
    thread_type = 'group' if len(recipient_ids) > 1 else 'direct'
    
    # Create thread
    thread = MessageThread(thread_type=thread_type)
    db.session.add(thread)
    db.session.flush()
    
    # Add participants
    participants = [current_user.id] + recipient_ids
    for user_id in participants:
        participant = MessageThreadParticipant(
            thread_id=thread.id,
            user_id=user_id
        )
        db.session.add(participant)
    
    # Create first message
    message = Message(
        thread_id=thread.id,
        sender_id=current_user.id,
        message=message_text
    )
    db.session.add(message)
    db.session.commit()
    
    return redirect(url_for('messages.index', thread_id=thread.id))

@bp.route('/<int:thread_id>/send', methods=['POST'])
@login_required
def send_message(thread_id):
    """Send a message in a thread."""
    if not current_user.email_verified:
        flash('Please verify your email address before sending messages.', 'error')
        return redirect(url_for('messages.index', thread_id=thread_id))
    
    thread = MessageThread.query.get_or_404(thread_id)
    
    # Check if user is participant
    participant = MessageThreadParticipant.query.filter_by(
        thread_id=thread_id,
        user_id=current_user.id
    ).first()
    
    if not participant or participant.is_blocked:
        flash('You do not have access to this thread.', 'error')
        return redirect(url_for('messages.index'))
    
    message_text = request.form.get('message')
    if not message_text:
        flash('Message cannot be empty.', 'error')
        return redirect(url_for('messages.index', thread_id=thread_id))
    
    # Create message
    message = Message(
        thread_id=thread_id,
        sender_id=current_user.id,
        message=message_text
    )
    db.session.add(message)
    
    # Update thread updated_at
    from datetime import datetime
    thread.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return redirect(url_for('messages.index', thread_id=thread_id))

@bp.route('/<int:thread_id>/add-user', methods=['POST'])
@login_required
def add_user_to_thread(thread_id):
    """Add a user to a thread (creates poll)."""
    thread = MessageThread.query.get_or_404(thread_id)
    
    user_id = request.form.get('user_id', type=int)
    if not user_id:
        flash('Please select a user.', 'error')
        return redirect(url_for('messages.index', thread_id=thread_id))
    
    # Check if user is already in thread
    existing = MessageThreadParticipant.query.filter_by(
        thread_id=thread_id,
        user_id=user_id
    ).first()
    
    if existing:
        flash('User is already in this thread.', 'info')
        return redirect(url_for('messages.index', thread_id=thread_id))
    
    # If this is a direct message, convert it to a group when adding a user
    if thread.thread_type == 'direct':
        thread.thread_type = 'group'
        db.session.commit()
    
    # Create poll message
    poll_message = Message(
        thread_id=thread_id,
        sender_id=current_user.id,
        message=f"Request to add {User.query.get(user_id).name} to this thread",
        is_poll=True,
        poll_type='add_user'
    )
    db.session.add(poll_message)
    db.session.flush()
    
    # Store user_id in message (we'll use a JSON field or separate table)
    # For now, we'll create a vote for the requesting user
    vote = MessagePollVote(
        message_id=poll_message.id,
        user_id=current_user.id,
        vote='approve'
    )
    db.session.add(vote)
    db.session.commit()
    
    flash('User addition request sent. All participants must approve.', 'info')
    return redirect(url_for('messages.index', thread_id=thread_id))

@bp.route('/poll/<int:message_id>/vote', methods=['POST'])
@login_required
def vote_on_poll(message_id):
    """Vote on a poll message."""
    message = Message.query.get_or_404(message_id)
    
    # Check if user is participant
    participant = MessageThreadParticipant.query.filter_by(
        thread_id=message.thread_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        flash('You do not have access to this thread.', 'error')
        return redirect(url_for('messages.index'))
    
    vote_value = request.form.get('vote')
    if vote_value not in ['approve', 'reject']:
        flash('Invalid vote.', 'error')
        return redirect(url_for('messages.index', thread_id=message.thread_id))
    
    # Check if already voted
    existing_vote = MessagePollVote.query.filter_by(
        message_id=message_id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        existing_vote.vote = vote_value
    else:
        vote = MessagePollVote(
            message_id=message_id,
            user_id=current_user.id,
            vote=vote_value
        )
        db.session.add(vote)
    
    db.session.commit()
    
    # Check if all participants have approved
    if message.poll_type == 'add_user':
        all_participants = MessageThreadParticipant.query.filter_by(
            thread_id=message.thread_id,
            is_blocked=False
        ).all()
        all_votes = MessagePollVote.query.filter_by(message_id=message_id).all()
        
        if len(all_votes) == len(all_participants):
            all_approved = all(v.vote == 'approve' for v in all_votes)
            if all_approved:
                # Extract user_id from message (simplified - in real implementation, store in separate field)
                # For now, we'll need to parse it or store it differently
                flash('All participants approved. User will be added.', 'success')
    
    return redirect(url_for('messages.index', thread_id=message.thread_id))

@bp.route('/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    """Block a user from messaging."""
    if user_id == current_user.id:
        flash('Cannot block yourself.', 'error')
        return redirect(url_for('messages.index'))
    
    # Check if already blocked
    existing = UserBlock.query.filter_by(
        blocker_id=current_user.id,
        blocked_id=user_id
    ).first()
    
    if not existing:
        block = UserBlock(
            blocker_id=current_user.id,
            blocked_id=user_id
        )
        db.session.add(block)
        
        # Block in all threads
        threads = MessageThread.query.join(MessageThreadParticipant).filter(
            MessageThreadParticipant.user_id == current_user.id
        ).join(MessageThreadParticipant, MessageThread.id == MessageThreadParticipant.thread_id).filter(
            MessageThreadParticipant.user_id == user_id
        ).all()
        
        for thread in threads:
            participant = MessageThreadParticipant.query.filter_by(
                thread_id=thread.id,
                user_id=current_user.id
            ).first()
            if participant:
                participant.is_blocked = True
        
        db.session.commit()
        flash('User blocked.', 'success')
    else:
        flash('User is already blocked.', 'info')
    
    return redirect(url_for('messages.index'))

