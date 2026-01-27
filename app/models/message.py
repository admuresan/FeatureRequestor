# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Message models for private messaging system.
See instructions/architecture for development guidelines.
"""

from app import db
from datetime import datetime

class MessageThread(db.Model):
    """Message thread (conversation) model."""
    __tablename__ = 'message_threads'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_type = db.Column(db.Text, nullable=False)  # 'direct' or 'group'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('MessageThreadParticipant', backref='thread', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='thread', lazy='dynamic', cascade='all, delete-orphan', order_by='Message.created_at')
    
    def __repr__(self):
        return f'<MessageThread {self.id}>'

class MessageThreadParticipant(db.Model):
    """Many-to-many relationship between threads and users."""
    __tablename__ = 'message_thread_participants'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('message_threads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    last_read_at = db.Column(db.DateTime, nullable=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='thread_participations')
    
    def __repr__(self):
        return f'<MessageThreadParticipant {self.thread_id}-{self.user_id}>'

class Message(db.Model):
    """Individual message model."""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('message_threads.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_poll = db.Column(db.Boolean, nullable=False, default=False)
    poll_type = db.Column(db.Text, nullable=True)  # 'add_user' or NULL
    poll_target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User to add for add_user polls
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref='sent_messages', foreign_keys=[sender_id])
    poll_target_user = db.relationship('User', backref='poll_target_messages', foreign_keys=[poll_target_user_id])
    poll_votes = db.relationship('MessagePollVote', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Message {self.id}>'

class MessagePollVote(db.Model):
    """Votes on poll messages."""
    __tablename__ = 'message_poll_votes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vote = db.Column(db.Text, nullable=False)  # 'approve' or 'reject'
    voted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='poll_votes')
    
    def __repr__(self):
        return f'<MessagePollVote {self.message_id}-{self.user_id}>'

