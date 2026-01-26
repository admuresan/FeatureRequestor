# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Test data generation utilities for development and testing.
See instructions/architecture for development guidelines.
"""

from app import db
from app.models import (
    User, App, FeatureRequest, Comment, FeatureRequestDeveloper,
    FeatureRequestDeveloperHistory, PaymentRatio, PaymentRatioMessage,
    PaymentTransaction, MessageThread, MessageThreadParticipant, Message, MessagePollVote,
    Notification, NotificationPreference
)
from app.utils.auth import hash_password
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Test data constants
TEST_USER_PREFIX = 'test_'
TEST_APP_PREFIX = 'test-app-'

def generate_test_data():
    """
    Generate comprehensive test data for development and testing.
    Creates test users, apps, feature requests, comments, payments, messages, etc.
    Returns a dictionary with counts of created items.
    """
    counts = {
        'users': 0,
        'apps': 0,
        'feature_requests': 0,
        'comments': 0,
        'developers': 0,
        'payments': 0,
        'messages': 0,
        'notifications': 0
    }
    
    # Get existing admin user (or create a test admin)
    admin = User.query.filter_by(role='admin', is_test_data=False).first()
    if not admin:
        # Create a test admin if no admin exists
        admin = User(
            username='test_admin',
            name='Test Admin',
            email='test_admin@example.com',
            password_hash=hash_password('test123'),
            email_verified=True,
            role='admin',
            is_test_data=True
        )
        db.session.add(admin)
        db.session.flush()
        counts['users'] += 1
    
    # Generate test users
    test_users = _generate_test_users(admin)
    counts['users'] += len(test_users)
    
    # Generate test apps
    test_apps = _generate_test_apps(test_users, admin)
    counts['apps'] += len(test_apps)
    
    # Generate feature requests with various statuses
    test_requests = _generate_feature_requests(test_users, test_apps)
    counts['feature_requests'] += len(test_requests)
    
    # Assign developers to requests
    dev_assignments = _assign_developers_to_requests(test_users, test_requests)
    counts['developers'] += dev_assignments
    
    # Generate comments on requests
    comments_count = _generate_comments(test_users, test_requests)
    counts['comments'] += comments_count
    
    # Generate payment ratios and transactions
    payments_count = _generate_payments(test_users, test_requests)
    counts['payments'] += payments_count
    
    # Generate OEM messages
    messages_count = _generate_messages(test_users, test_requests)
    counts['messages'] += messages_count
    
    # Generate notifications
    notifications_count = _generate_notifications(test_users, test_requests)
    counts['notifications'] += notifications_count
    
    db.session.commit()
    return counts

def _generate_test_users(admin):
    """Generate test users with various roles."""
    test_users = []
    
    # Test requesters
    requester_names = [
        ('Alice', 'Smith'), ('Bob', 'Johnson'), ('Charlie', 'Williams'),
        ('Diana', 'Brown'), ('Eve', 'Jones'), ('Frank', 'Garcia'),
        ('Grace', 'Miller'), ('Henry', 'Davis')
    ]
    
    for first, last in requester_names:
        username = f"{TEST_USER_PREFIX}requester_{first.lower()}"
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                name=f"{first} {last}",
                email=f"{username}@test.example.com",
                password_hash=hash_password('test123'),
                email_verified=True,
                role='requester',
                preferred_currency=random.choice(['CAD', 'USD', 'EUR']),
                is_test_data=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            db.session.add(user)
            test_users.append(user)
    
    # Test developers
    dev_names = [
        ('Ivan', 'Rodriguez'), ('Julia', 'Martinez'), ('Kevin', 'Hernandez'),
        ('Luna', 'Lopez'), ('Mike', 'Gonzalez'), ('Nina', 'Wilson'),
        ('Oscar', 'Anderson'), ('Paula', 'Thomas')
    ]
    
    for first, last in dev_names:
        username = f"{TEST_USER_PREFIX}dev_{first.lower()}"
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                name=f"{first} {last}",
                email=f"{username}@test.example.com",
                password_hash=hash_password('test123'),
                email_verified=True,
                role='dev',
                preferred_currency=random.choice(['CAD', 'USD', 'EUR']),
                stripe_account_id=f"acct_test_{random.randint(100000, 999999)}" if random.random() > 0.3 else None,
                stripe_account_status=random.choice(['connected', 'pending', None]) if random.random() > 0.3 else None,
                is_test_data=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            db.session.add(user)
            test_users.append(user)
    
    db.session.flush()
    return test_users

def _generate_test_apps(test_users, admin):
    """Generate test apps."""
    test_apps = []
    app_owners = [u for u in test_users if u.role == 'requester'] + [admin]
    
    app_data = [
        ('task-manager', 'Task Manager Pro', 'A powerful task management application for teams.'),
        ('photo-editor', 'Photo Editor Studio', 'Professional photo editing software with AI features.'),
        ('music-player', 'Music Player Plus', 'Advanced music player with streaming capabilities.'),
        ('fitness-tracker', 'Fitness Tracker', 'Track your workouts and health metrics.'),
        ('recipe-book', 'Recipe Book', 'Discover and save your favorite recipes.'),
        ('expense-tracker', 'Expense Tracker', 'Manage your personal finances easily.')
    ]
    
    for app_name, display_name, description in app_data:
        full_name = f"{TEST_APP_PREFIX}{app_name}"
        if not App.query.filter_by(app_name=full_name).first():
            app = App(
                app_name=full_name,
                app_display_name=display_name,
                app_description=description,
                app_url=f"https://{app_name}.example.com",
                github_url=f"https://github.com/example/{app_name}",
                app_owner_id=random.choice(app_owners).id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 180))
            )
            db.session.add(app)
            test_apps.append(app)
    
    db.session.flush()
    return test_apps

def _generate_feature_requests(test_users, test_apps):
    """Generate feature requests with various statuses."""
    test_requests = []
    requesters = [u for u in test_users if u.role == 'requester']
    
    if not test_apps or not requesters:
        return test_requests  # Can't create requests without apps or requesters
    
    request_templates = [
        ('Dark mode support', 'UI/UX', 'enhancement', 'Add a dark mode theme option for better night-time usage.'),
        ('Export to PDF', 'backend', 'enhancement', 'Allow users to export their data to PDF format.'),
        ('Login page bug', 'UI/UX', 'bug', 'Login button is not responding on mobile devices.'),
        ('API rate limiting', 'backend', 'enhancement', 'Implement rate limiting for API endpoints.'),
        ('Drag and drop files', 'UI/UX', 'enhancement', 'Add drag and drop functionality for file uploads.'),
        ('Database optimization', 'backend', 'enhancement', 'Optimize database queries for better performance.'),
        ('Mobile responsive design', 'UI/UX', 'enhancement', 'Improve mobile responsiveness across all pages.'),
        ('Email notifications', 'backend', 'enhancement', 'Add email notification system for important events.'),
        ('Search functionality', 'backend', 'enhancement', 'Implement full-text search across all content.'),
        ('User profile pictures', 'UI/UX', 'enhancement', 'Allow users to upload and display profile pictures.'),
        ('Two-factor authentication', 'backend', 'enhancement', 'Add 2FA support for enhanced security.'),
        ('Loading spinner issue', 'UI/UX', 'bug', 'Loading spinner appears in wrong position.'),
        ('Bulk operations', 'backend', 'enhancement', 'Enable bulk operations for managing multiple items.'),
        ('Keyboard shortcuts', 'UI/UX', 'enhancement', 'Add keyboard shortcuts for common actions.'),
        ('Data backup feature', 'backend', 'enhancement', 'Automatic data backup functionality.'),
    ]
    
    statuses = ['requested', 'in_progress', 'completed', 'confirmed', 'cancelled']
    status_weights = [0.3, 0.25, 0.2, 0.15, 0.1]  # More requested/in_progress
    
    for title, req_type, category, description in request_templates:
        app = random.choice(test_apps)
        requester = random.choice(requesters)
        status = random.choices(statuses, weights=status_weights)[0]
        
        # Calculate dates based on status
        days_ago = random.randint(1, 120)
        date_requested = datetime.utcnow() - timedelta(days=days_ago)
        
        projected_date = None
        delivered_date = None
        
        if status in ['in_progress', 'completed', 'confirmed']:
            projected_date = date_requested + timedelta(days=random.randint(7, 30))
        
        if status in ['completed', 'confirmed']:
            delivered_date = projected_date + timedelta(days=random.randint(-5, 10)) if projected_date else date_requested + timedelta(days=random.randint(10, 40))
        
        request = FeatureRequest(
            title=title,
            app_id=app.id,
            creator_id=requester.id,
            request_type=req_type,
            request_category=category,
            status=status,
            date_requested=date_requested,
            total_bid_amount=Decimal('0.00'),
            projected_completion_date=projected_date,
            delivered_date=delivered_date,
            created_at=date_requested,
            updated_at=delivered_date if delivered_date else datetime.utcnow()
        )
        db.session.add(request)
        test_requests.append(request)
    
    db.session.flush()
    return test_requests

def _assign_developers_to_requests(test_users, test_requests):
    """Assign developers to feature requests."""
    developers = [u for u in test_users if u.role == 'dev']
    assignments = 0
    
    if not developers:
        return 0  # No developers to assign
    
    for request in test_requests:
        # Some requests have no developers (not picked up)
        if random.random() < 0.2:  # 20% have no developers
            continue
        
        # Assign 1-3 developers per request
        num_devs = random.randint(1, 3) if request.status != 'requested' else 0
        if request.status == 'requested':
            continue  # Requested status means no devs yet
        
        if not developers:
            continue
        
        num_devs = min(num_devs, len(developers))
        selected_devs = random.sample(developers, num_devs)
        
        for dev in selected_devs:
            added_at = request.date_requested + timedelta(days=random.randint(1, 10))
            
            dev_assignment = FeatureRequestDeveloper(
                feature_request_id=request.id,
                developer_id=dev.id,
                is_approved=True,
                approved_by_id=request.creator_id,
                added_at=added_at,
                removed_at=None
            )
            db.session.add(dev_assignment)
            assignments += 1
            
            # If request is completed/confirmed, some devs might have been removed
            if request.status in ['completed', 'confirmed'] and random.random() < 0.2:
                dev_assignment.removed_at = request.delivered_date
                # Add to history
                history = FeatureRequestDeveloperHistory(
                    feature_request_id=request.id,
                    developer_id=dev.id,
                    started_at=added_at,
                    removed_at=request.delivered_date,
                    removed_by='self'
                )
                db.session.add(history)
    
    db.session.flush()
    return assignments

def _generate_comments(test_users, test_requests):
    """Generate comments on feature requests."""
    comments_count = 0
    developers = [u for u in test_users if u.role == 'dev']
    requesters = [u for u in test_users if u.role == 'requester']
    
    if not developers and not requesters:
        return 0  # No users to create comments
    
    comment_templates = [
        "I can work on this! My estimated bid is ${amount}.",
        "This looks interesting. I'd like to take this on.",
        "I have experience with this type of feature. Bid: ${amount}",
        "Thanks for the update! Looking forward to seeing this implemented.",
        "Can we clarify the requirements for this feature?",
        "I've started working on this. Progress update coming soon.",
        "This is now complete! Please review and confirm.",
        "I need more information about the expected behavior.",
        "Great feature request! I'm interested in working on this.",
        "I've encountered an issue. Need to discuss approach."
    ]
    
    for request in test_requests:
        # Generate 2-8 comments per request
        num_comments = random.randint(2, 8)
        
        for i in range(num_comments):
            # Mix of requester and dev comments
            if i == 0:
                commenter = request.creator
                commenter_type = 'requester'
            elif developers and random.random() < 0.6:  # 60% dev comments
                commenter = random.choice(developers)
                commenter_type = 'dev'
            elif requesters:
                commenter = random.choice(requesters)
                commenter_type = 'requester'
            else:
                commenter = request.creator
                commenter_type = 'requester'
            
            # Calculate comment date (after request creation, before delivery if completed)
            max_date = request.delivered_date if request.delivered_date else datetime.utcnow()
            comment_date = request.date_requested + timedelta(
                days=random.randint(0, (max_date - request.date_requested).days)
            )
            
            # Generate comment text
            template = random.choice(comment_templates)
            if commenter_type == 'dev' and '${amount}' in template:
                amount = random.randint(100, 2000)
                currency = commenter.preferred_currency
                comment_text = template.replace('${amount}', str(amount))
            else:
                comment_text = template.replace('${amount}', '')
            
            # Add bid amount for dev comments
            bid_amount = Decimal('0.00')
            bid_currency = None
            if commenter_type == 'dev' and random.random() < 0.4:  # 40% of dev comments have bids
                bid_amount = Decimal(str(random.randint(100, 2000)))
                bid_currency = commenter.preferred_currency
                # Update request total
                request.total_bid_amount += bid_amount
            
            comment = Comment(
                feature_request_id=request.id,
                commenter_id=commenter.id,
                commenter_type=commenter_type,
                comment=comment_text,
                bid_amount=bid_amount,
                bid_currency=bid_currency,
                date=comment_date,
                created_at=comment_date
            )
            db.session.add(comment)
            comments_count += 1
    
    db.session.flush()
    return comments_count

def _generate_payments(test_users, test_requests):
    """Generate payment ratios and transactions."""
    payments_count = 0
    developers = [u for u in test_users if u.role == 'dev']
    requesters = [u for u in test_users if u.role == 'requester']
    
    # Create a lookup dict for developers
    dev_lookup = {d.id: d for d in developers}
    
    # Generate payment ratios for multi-dev requests
    for request in test_requests:
        if request.status not in ['completed', 'confirmed']:
            continue
        
        # Get developers on this request
        dev_assignments = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request.id,
            removed_at=None
        ).all()
        
        if not dev_assignments:
            continue
        
        # Create payment ratios
        total_percentage = Decimal('0.00')
        ratios = []
        
        for i, dev_assignment in enumerate(dev_assignments):
            if i == len(dev_assignments) - 1:
                # Last dev gets remaining percentage
                ratio = Decimal('100.00') - total_percentage
            else:
                # Distribute percentages
                ratio = Decimal(str(random.randint(20, 60)))
                total_percentage += ratio
            
            payment_ratio = PaymentRatio(
                feature_request_id=request.id,
                developer_id=dev_assignment.developer_id,
                ratio_percentage=ratio,
                is_accepted=True,
                accepted_at=request.delivered_date or datetime.utcnow()
            )
            db.session.add(payment_ratio)
            ratios.append((dev_assignment.developer_id, ratio))
        
        # Generate payment transactions
        if request.total_bid_amount > 0:
            # Charged to requester
            charge_transaction = PaymentTransaction(
                user_id=request.creator_id,
                transaction_type='feature_request_payment',
                amount=request.total_bid_amount,
                currency=request.creator.preferred_currency,
                app_id=request.app_id,
                feature_request_id=request.id,
                direction='charged',
                is_guest_transaction=False,
                transaction_date=request.delivered_date or datetime.utcnow()
            )
            db.session.add(charge_transaction)
            payments_count += 1
            
            # Paid to developers (distributed)
            for dev_id, ratio in ratios:
                dev = dev_lookup.get(dev_id)
                if dev:
                    dev_amount = (request.total_bid_amount * ratio / Decimal('100.00')).quantize(Decimal('0.01'))
                    pay_transaction = PaymentTransaction(
                        user_id=dev_id,
                        transaction_type='feature_request_payment',
                        amount=dev_amount,
                        currency=dev.preferred_currency,
                        app_id=request.app_id,
                        feature_request_id=request.id,
                        direction='paid',
                        is_guest_transaction=False,
                        transaction_date=request.delivered_date or datetime.utcnow()
                    )
                    db.session.add(pay_transaction)
                    payments_count += 1
        
        # Add some payment ratio messages
        if random.random() < 0.5:
            message = PaymentRatioMessage(
                feature_request_id=request.id,
                sender_id=random.choice([request.creator_id] + [d.developer_id for d in dev_assignments]),
                message=random.choice([
                    "Let's split this 50/50",
                    "I did most of the work, so I should get 70%",
                    "Fair split works for me",
                    "Agreed on the payment distribution"
                ]),
                created_at=request.delivered_date or datetime.utcnow()
            )
            db.session.add(message)
    
    # Generate some tip transactions
    apps = App.query.filter(App.app_name.like(f'{TEST_APP_PREFIX}%')).all()
    if not apps:
        db.session.flush()
        return payments_count
    
    for _ in range(random.randint(5, 15)):
        app = random.choice(apps)
        if random.random() < 0.5:
            # Authenticated tip
            user = random.choice(requesters)
            amount = Decimal(str(random.randint(5, 100)))
            tip = PaymentTransaction(
                user_id=user.id,
                transaction_type='tip',
                amount=amount,
                currency=user.preferred_currency,
                app_id=app.id,
                feature_request_id=None,
                direction='tip',
                is_guest_transaction=False,
                transaction_date=datetime.utcnow() - timedelta(days=random.randint(1, 60))
            )
        else:
            # Guest tip
            amount = Decimal(str(random.randint(5, 100)))
            tip = PaymentTransaction(
                user_id=None,
                guest_email=f"guest{random.randint(1, 100)}@example.com",
                transaction_type='tip',
                amount=amount,
                currency=random.choice(['CAD', 'USD', 'EUR']),
                app_id=app.id,
                feature_request_id=None,
                direction='tip',
                is_guest_transaction=True,
                transaction_date=datetime.utcnow() - timedelta(days=random.randint(1, 60))
            )
        db.session.add(tip)
        payments_count += 1
    
    db.session.flush()
    return payments_count

def _generate_messages(test_users, test_requests):
    """Generate OEM (Original Equipment Manufacturer) messages between users."""
    messages_count = 0
    all_users = test_users
    
    if len(all_users) < 2:
        return 0  # Need at least 2 users for messages
    
    # Create some direct message threads
    for _ in range(random.randint(10, 20)):
        participants = random.sample(all_users, 2)
        
        thread = MessageThread(
            thread_type='direct',
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))
        )
        db.session.add(thread)
        db.session.flush()
        
        # Add participants
        for user in participants:
            participant = MessageThreadParticipant(
                thread_id=thread.id,
                user_id=user.id,
                joined_at=thread.created_at
            )
            db.session.add(participant)
        
        # Generate messages in thread
        num_messages = random.randint(2, 10)
        for i in range(num_messages):
            sender = random.choice(participants)
            message_texts = [
                "Hey, are you available to work on a feature request?",
                "I saw your bid. Can we discuss the timeline?",
                "The feature is complete. Can you review it?",
                "Thanks for the update!",
                "I have a question about the implementation.",
                "Great work on the last feature!",
                "Can we schedule a call to discuss this?",
                "I've updated the requirements. Please check.",
                "The payment has been processed.",
                "Looking forward to working with you!"
            ]
            
            message = Message(
                thread_id=thread.id,
                sender_id=sender.id,
                message=random.choice(message_texts),
                created_at=thread.created_at + timedelta(hours=i * random.randint(1, 24))
            )
            db.session.add(message)
            messages_count += 1
        
        thread.updated_at = thread.created_at + timedelta(hours=num_messages * 12)
    
    # Create some group threads related to feature requests
    for request in test_requests[:5]:  # First 5 requests get group threads
        if request.status == 'requested':
            continue
        
        devs = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request.id,
            removed_at=None
        ).all()
        
        if not devs:
            continue
        
        participants = [request.creator] + [d.developer for d in devs]
        
        thread = MessageThread(
            thread_type='group',
            created_at=request.date_requested + timedelta(days=random.randint(1, 5))
        )
        db.session.add(thread)
        db.session.flush()
        
        # Add participants
        for user in participants:
            participant = MessageThreadParticipant(
                thread_id=thread.id,
                user_id=user.id,
                joined_at=thread.created_at
            )
            db.session.add(participant)
        
        # Generate messages
        num_messages = random.randint(3, 8)
        for i in range(num_messages):
            sender = random.choice(participants)
            message_texts = [
                f"Discussion about: {request.title}",
                "Let's coordinate on this feature.",
                "I'll handle the backend part.",
                "I can work on the UI components.",
                "When do you think we can complete this?",
                "I've pushed the initial implementation.",
                "Can someone review my changes?",
                "The feature is ready for testing."
            ]
            
            message = Message(
                thread_id=thread.id,
                sender_id=sender.id,
                message=random.choice(message_texts),
                created_at=thread.created_at + timedelta(hours=i * random.randint(2, 12))
            )
            db.session.add(message)
            messages_count += 1
        
        thread.updated_at = thread.created_at + timedelta(hours=num_messages * 8)
    
    db.session.flush()
    return messages_count

def _generate_notifications(test_users, test_requests):
    """Generate notifications for users."""
    notifications_count = 0
    all_users = test_users
    
    if not all_users:
        return 0
    
    notification_types = [
        'new_request', 'request_comment', 'request_comment_dev', 'developer_added', 'developer_removed',
        'request_completed', 'request_status_change', 'payment_received', 'message_received'
    ]
    
    for user in all_users:
        # Generate 2-10 notifications per user
        num_notifications = random.randint(2, 10)
        
        for _ in range(num_notifications):
            notif_type = random.choice(notification_types)
            notification_data = None
            
            if notif_type == 'new_request' and test_requests:
                request = random.choice(test_requests)
                notification_data = {
                    'feature_request_id': request.id
                }
            elif notif_type in ['request_comment', 'request_comment_dev'] and test_requests:
                request = random.choice(test_requests)
                # Generate a comment preview
                comment_preview = f"Test comment preview {random.randint(1, 100)}"
                notification_data = {
                    'feature_request_id': request.id,
                    'comment_preview': comment_preview
                }
            elif notif_type == 'request_status_change' and test_requests:
                request = random.choice(test_requests)
                statuses = ['requested', 'in_progress', 'completed', 'cancelled']
                old_status = random.choice(statuses)
                new_status = random.choice([s for s in statuses if s != old_status])
                # Sometimes include who changed it
                if random.random() < 0.5:
                    devs = [u for u in all_users if u.role == 'dev']
                    if devs:
                        dev = random.choice(devs)
                        notification_data = {
                            'feature_request_id': request.id,
                            'old_status': old_status,
                            'new_status': new_status,
                            'changed_by_name': dev.name
                        }
                    else:
                        notification_data = {
                            'feature_request_id': request.id,
                            'old_status': old_status,
                            'new_status': new_status
                        }
                else:
                    notification_data = {
                        'feature_request_id': request.id,
                        'old_status': old_status,
                        'new_status': new_status
                    }
            elif notif_type == 'developer_added' and test_requests:
                request = random.choice(test_requests)
                # Get a random developer for context
                devs = [u for u in all_users if u.role == 'dev']
                if devs:
                    dev = random.choice(devs)
                    notification_data = {
                        'feature_request_id': request.id,
                        'developer_id': dev.id,
                        'developer_name': dev.name
                    }
                else:
                    notification_data = {
                        'feature_request_id': request.id
                    }
            elif notif_type == 'developer_removed' and test_requests:
                request = random.choice(test_requests)
                notification_data = {
                    'feature_request_id': request.id,
                    'reason': random.choice([None, 'Test reason', 'No longer needed', None])
                }
            elif notif_type == 'request_completed' and test_requests:
                request = random.choice(test_requests)
                # Sometimes include completed_by_name for developers
                if random.random() < 0.5:
                    devs = [u for u in all_users if u.role == 'dev']
                    if devs:
                        dev = random.choice(devs)
                        notification_data = {
                            'feature_request_id': request.id,
                            'completed_by_name': dev.name
                        }
                    else:
                        notification_data = {
                            'feature_request_id': request.id
                        }
                else:
                    notification_data = {
                        'feature_request_id': request.id
                    }
            elif notif_type == 'payment_received':
                amount = random.randint(50, 500)
                notification_data = {
                    'amount': amount,
                    'currency': '$'
                }
            elif notif_type == 'message_received':
                # Get a random sender
                senders = [u for u in all_users if u.id != user.id]
                if senders:
                    sender = random.choice(senders)
                    notification_data = {
                        'sender_name': sender.name
                    }
                else:
                    notification_data = {
                        'sender_name': 'Test User'
                    }
            
            if notification_data:
                notification = Notification(
                    user_id=user.id,
                    notification_type=notif_type,
                    notification_message='',  # Empty string for backward compatibility with NOT NULL constraint
                    is_read=random.random() < 0.4,  # 40% are read
                    read_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)) if random.random() < 0.4 else None,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))
                )
                notification.set_data(notification_data)
                db.session.add(notification)
                notifications_count += 1
    
    db.session.flush()
    return notifications_count

def clear_test_data():
    """
    Clear all test data generated by generate_test_data().
    This deletes all data related to test users and test apps.
    Returns a dictionary with counts of deleted items.
    """
    counts = {
        'users': 0,
        'apps': 0,
        'feature_requests': 0,
        'comments': 0,
        'developers': 0,
        'payments': 0,
        'messages': 0,
        'notifications': 0
    }
    
    # Get all test users
    test_users = User.query.filter_by(is_test_data=True).all()
    test_user_ids = [u.id for u in test_users]
    
    if not test_user_ids:
        return counts
    
    # Delete notifications for test users
    notifications = Notification.query.filter(Notification.user_id.in_(test_user_ids)).all()
    counts['notifications'] = len(notifications)
    for notif in notifications:
        db.session.delete(notif)
    
    # Delete notification preferences for test users
    NotificationPreference.query.filter(NotificationPreference.user_id.in_(test_user_ids)).delete()
    
    # Delete messages and threads involving test users
    test_thread_ids = db.session.query(MessageThreadParticipant.thread_id).filter(
        MessageThreadParticipant.user_id.in_(test_user_ids)
    ).distinct().all()
    test_thread_ids = [t[0] for t in test_thread_ids]
    
    if test_thread_ids:
        # Delete poll votes
        MessagePollVote.query.filter(MessagePollVote.user_id.in_(test_user_ids)).delete()
        
        # Delete messages in test threads
        messages = Message.query.filter(Message.thread_id.in_(test_thread_ids)).all()
        counts['messages'] = len(messages)
        for msg in messages:
            db.session.delete(msg)
        
        # Delete participants
        MessageThreadParticipant.query.filter(MessageThreadParticipant.thread_id.in_(test_thread_ids)).delete()
        
        # Delete threads
        MessageThread.query.filter(MessageThread.id.in_(test_thread_ids)).delete()
    
    # Delete payment transactions for test users
    payments = PaymentTransaction.query.filter(
        (PaymentTransaction.user_id.in_(test_user_ids)) |
        (PaymentTransaction.guest_email.like('%@test.example.com'))
    ).all()
    counts['payments'] = len(payments)
    for payment in payments:
        db.session.delete(payment)
    
    # Delete payment ratio messages for test requests
    test_request_ids = db.session.query(FeatureRequest.id).filter(
        FeatureRequest.creator_id.in_(test_user_ids)
    ).all()
    test_request_ids = [r[0] for r in test_request_ids]
    
    if test_request_ids:
        PaymentRatioMessage.query.filter(
            PaymentRatioMessage.feature_request_id.in_(test_request_ids)
        ).delete()
        
        # Delete payment ratios
        PaymentRatio.query.filter(
            PaymentRatio.feature_request_id.in_(test_request_ids)
        ).delete()
    
    # Delete developer history
    FeatureRequestDeveloperHistory.query.filter(
        FeatureRequestDeveloperHistory.developer_id.in_(test_user_ids)
    ).delete()
    
    # Delete developer assignments
    dev_assignments = FeatureRequestDeveloper.query.filter(
        FeatureRequestDeveloper.developer_id.in_(test_user_ids)
    ).all()
    counts['developers'] = len(dev_assignments)
    for assignment in dev_assignments:
        db.session.delete(assignment)
    
    # Delete comments on test requests AND comments made by test users (even on non-test requests)
    comments_on_test_requests = []
    if test_request_ids:
        comments_on_test_requests = Comment.query.filter(Comment.feature_request_id.in_(test_request_ids)).all()
    
    comments_by_test_users = Comment.query.filter(Comment.commenter_id.in_(test_user_ids)).all()
    
    # Combine and deduplicate
    all_test_comments = list(set(comments_on_test_requests + comments_by_test_users))
    counts['comments'] = len(all_test_comments)
    for comment in all_test_comments:
        db.session.delete(comment)
    
    # Delete feature requests created by test users
    if test_request_ids:
        requests = FeatureRequest.query.filter(FeatureRequest.id.in_(test_request_ids)).all()
        counts['feature_requests'] = len(requests)
        for request in requests:
            db.session.delete(request)
    
    # Delete test apps
    test_apps = App.query.filter(App.app_name.like(f'{TEST_APP_PREFIX}%')).all()
    counts['apps'] = len(test_apps)
    for app in test_apps:
        db.session.delete(app)
    
    # Delete test users (this should be last)
    counts['users'] = len(test_users)
    for user in test_users:
        db.session.delete(user)
    
    db.session.commit()
    return counts

