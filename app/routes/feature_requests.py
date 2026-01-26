# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Feature requests routes.
See instructions/architecture for development guidelines.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import FeatureRequest, App, Comment
from app.utils.currency import convert_currency, format_currency, get_user_preferred_currency
from datetime import datetime
from decimal import Decimal

bp = Blueprint('feature_requests', __name__, url_prefix='/feature-requests')

@bp.route('')
def list():
    """Feature requests list page (public)."""
    app_name = request.args.get('app')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get app filter
    app = None
    if app_name:
        app = App.query.filter_by(app_name=app_name).first()
    
    # Build query
    query = FeatureRequest.query
    
    if app:
        query = query.filter_by(app_id=app.id)
    
    if search_query:
        # Search in title and comments
        query = query.filter(
            db.or_(
                FeatureRequest.title.contains(search_query),
                FeatureRequest.id.in_(
                    db.session.query(Comment.feature_request_id).filter(
                        Comment.comment.contains(search_query)
                    )
                )
            )
        )
    
    # Get ordering parameters
    in_progress_order = request.args.get('in_progress_order', 'projected_completion_date_desc')
    requested_order = request.args.get('requested_order', 'total_bid_amount_desc')
    completed_order = request.args.get('completed_order', 'delivered_date_desc')
    
    # Helper function to get order_by clause
    def get_order_by(order_param, default_field):
        if order_param.endswith('_desc'):
            field = order_param[:-5]
            if field == 'projected_completion_date':
                return FeatureRequest.projected_completion_date.desc().nullslast()
            elif field == 'total_bid_amount':
                return FeatureRequest.total_bid_amount.desc()
            elif field == 'date_requested':
                return FeatureRequest.date_requested.desc()
            elif field == 'delivered_date':
                return FeatureRequest.delivered_date.desc().nullslast()
            elif field == 'title':
                return FeatureRequest.title.desc()
        elif order_param.endswith('_asc'):
            field = order_param[:-4]
            if field == 'projected_completion_date':
                return FeatureRequest.projected_completion_date.asc().nullslast()
            elif field == 'total_bid_amount':
                return FeatureRequest.total_bid_amount.asc()
            elif field == 'date_requested':
                return FeatureRequest.date_requested.asc()
            elif field == 'delivered_date':
                return FeatureRequest.delivered_date.asc().nullslast()
            elif field == 'title':
                return FeatureRequest.title.asc()
        # Default
        if default_field == 'projected_completion_date':
            return FeatureRequest.projected_completion_date.desc().nullslast()
        elif default_field == 'total_bid_amount':
            return FeatureRequest.total_bid_amount.desc()
        else:
            return FeatureRequest.delivered_date.desc().nullslast()
    
    # Get requests by status with ordering
    in_progress = query.filter_by(status='in_progress').order_by(
        get_order_by(in_progress_order, 'projected_completion_date')
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    requested = query.filter_by(status='requested').order_by(
        get_order_by(requested_order, 'total_bid_amount')
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    completed = query.filter(db.or_(
        FeatureRequest.status == 'completed',
        FeatureRequest.status == 'confirmed'
    )).order_by(
        get_order_by(completed_order, 'delivered_date')
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all apps for filter dropdown
    all_apps = App.query.all()
    
    error_message = None
    if request.args.get('error') == 'app_not_found':
        error_message = 'App name not found'
    
    # Calculate converted totals for viewing user
    viewing_currency = get_user_preferred_currency(current_user if current_user.is_authenticated else None)
    
    # Helper to calculate converted total for a request
    def get_converted_total(request):
        try:
            total = Decimal('0.00')
            # Use a separate query to avoid lazy loading issues
            comments = Comment.query.filter_by(
                feature_request_id=request.id,
                is_deleted=False
            ).all()
            for comment in comments:
                if comment.bid_amount and comment.bid_amount > 0:
                    bid_currency = comment.bid_currency or 'CAD'
                    total += convert_currency(comment.bid_amount, bid_currency, viewing_currency)
            return total
        except Exception as e:
            # Fallback to total_bid_amount if conversion fails
            return request.total_bid_amount or Decimal('0.00')
    
    return render_template('feature_requests/list.html',
                         in_progress=in_progress,
                         requested=requested,
                         completed=completed,
                         all_apps=all_apps,
                         current_app=app,
                         search_query=search_query,
                         error_message=error_message,
                         in_progress_order=in_progress_order,
                         requested_order=requested_order,
                         completed_order=completed_order,
                         viewing_currency=viewing_currency,
                         get_converted_total=get_converted_total)

@bp.route('/<int:request_id>')
def detail(request_id):
    """Feature request detail page (public)."""
    from app.models import FeatureRequestDeveloper
    
    feature_request = FeatureRequest.query.get_or_404(request_id)
    comments = Comment.query.filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).order_by(Comment.date.asc()).all()
    
    # Get developers
    developers = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        removed_at=None
    ).all()
    
    # Check if current user is a developer
    is_dev = False
    user_bid = None
    if current_user.is_authenticated:
        is_dev = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request_id,
            developer_id=current_user.id,
            removed_at=None
        ).first() is not None
        
        # Check if user has a non-zero bid
        user_bid = Comment.query.filter_by(
            feature_request_id=request_id,
            commenter_id=current_user.id,
            is_deleted=False
        ).filter(Comment.bid_amount > 0).first()
    
    # Get developer history (for expandable section)
    from app.models import FeatureRequestDeveloperHistory
    developer_history = FeatureRequestDeveloperHistory.query.filter_by(
        feature_request_id=request_id
    ).all() if current_user.is_authenticated else []
    
    # Calculate converted total bid amount for viewing user
    viewing_currency = get_user_preferred_currency(current_user if current_user.is_authenticated else None)
    converted_total = Decimal('0.00')
    for comment in comments:
        if comment.bid_amount > 0:
            bid_currency = comment.bid_currency or 'CAD'  # Default to CAD for old bids
            converted_total += convert_currency(comment.bid_amount, bid_currency, viewing_currency)
    
    return render_template('feature_requests/detail.html',
                         feature_request=feature_request,
                         comments=comments,
                         developers=developers,
                         is_dev=is_dev,
                         user_bid=user_bid,
                         developer_history=developer_history,
                         converted_total_bid=converted_total,
                         viewing_currency=viewing_currency)

@bp.route('/<int:request_id>/comment', methods=['POST'])
@login_required
def add_comment(request_id):
    """Add a comment to a feature request."""
    if not current_user.email_verified:
        flash('Please verify your email address before adding comments or placing bids.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    comment_text = request.form.get('comment')
    bid_amount = request.form.get('bid_amount', type=float) or 0.0
    
    if not comment_text:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    if bid_amount < 0:
        flash('Bid amount cannot be negative.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if user has Stripe account for bidding
    if bid_amount > 0 and not current_user.stripe_account_id:
        flash('You must connect a Stripe account to place bids.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Determine commenter type
    commenter_type = 'requester' if current_user.role == 'requester' else 'dev'
    
    # Create comment
    from datetime import datetime
    from decimal import Decimal
    comment = Comment(
        feature_request_id=request_id,
        commenter_id=current_user.id,
        commenter_type=commenter_type,
        comment=comment_text,
        bid_amount=Decimal(str(bid_amount)),
        bid_currency=current_user.preferred_currency if bid_amount > 0 else None,
        date=datetime.utcnow()
    )
    db.session.add(comment)
    
    # Update total bid amount
    feature_request.total_bid_amount = db.session.query(
        db.func.sum(Comment.bid_amount)
    ).filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).scalar() or Decimal('0.00')
    
    # Notify relevant users about the new comment
    from app.models import Notification, FeatureRequestDeveloper
    import json
    
    # Get users to notify (exclude the commenter)
    users_to_notify = set()
    
    # Get all requesters who placed bids
    requester_bids = Comment.query.filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).filter(Comment.bid_amount > 0).all()
    requester_ids = set([bid.commenter_id for bid in requester_bids])
    users_to_notify.update(requester_ids)
    
    # Get all developers working on the request
    dev_participants = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        removed_at=None
    ).all()
    dev_ids = set([p.developer_id for p in dev_participants])
    users_to_notify.update(dev_ids)
    
    # Remove the commenter from notification list
    users_to_notify.discard(current_user.id)
    
    # Create notifications - store data instead of message
    comment_preview = comment_text[:100] + ('...' if len(comment_text) > 100 else '')
    notification_type = 'request_comment' if commenter_type == 'requester' else 'request_comment_dev'
    
    for user_id in users_to_notify:
        notification_data = {
            'feature_request_id': request_id,
            'comment_preview': comment_preview
        }
        
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
        )
        notification.set_data(notification_data)
        db.session.add(notification)
    
    db.session.commit()
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new feature request page."""
    if request.method == 'POST':
        if not current_user.email_verified:
            flash('Please verify your email address before creating feature requests.', 'error')
            all_apps = App.query.all()
            return render_template('feature_requests/create.html', apps=all_apps)
        
        app_id = request.form.get('app_id', type=int)
        title = request.form.get('title')
        request_type = request.form.get('request_type')
        request_category = request.form.get('request_category')
        comment = request.form.get('comment')
        
        # Validate required fields
        if not all([app_id, title, request_type, request_category, comment]):
            flash('Please fill in all required fields.', 'error')
            all_apps = App.query.all()
            return render_template('feature_requests/create.html', apps=all_apps)
        
        # Validate request_type and request_category
        if request_type not in ['UI/UX', 'backend']:
            flash('Invalid request type.', 'error')
            all_apps = App.query.all()
            return render_template('feature_requests/create.html', apps=all_apps)
        
        if request_category not in ['bug', 'enhancement']:
            flash('Invalid request category.', 'error')
            all_apps = App.query.all()
            return render_template('feature_requests/create.html', apps=all_apps)
        
        # Check if app exists
        app = App.query.get(app_id)
        if not app:
            flash('Invalid app selected.', 'error')
            all_apps = App.query.all()
            return render_template('feature_requests/create.html', apps=all_apps)
        
        # Check for similar requests
        from app.utils.similar_requests import find_similar_requests
        similar_requests = find_similar_requests(title, comment, app_id)
        
        if similar_requests:
            # Show similar requests to user
            return render_template('feature_requests/create.html',
                                 apps=all_apps,
                                 similar_requests=similar_requests,
                                 form_data=request.form)
        
        # No similar requests found, proceed with creation
        
        # Create feature request
        from datetime import datetime
        feature_request = FeatureRequest(
            title=title,
            app_id=app_id,
            creator_id=current_user.id,
            request_type=request_type,
            request_category=request_category,
            status='requested',
            date_requested=datetime.utcnow(),
            total_bid_amount=0.00
        )
        db.session.add(feature_request)
        db.session.flush()  # Get the ID
        
        # Create first comment (request creation comment)
        first_comment = Comment(
            feature_request_id=feature_request.id,
            commenter_id=current_user.id,
            commenter_type='requester',
            comment=comment,
            bid_amount=0.00,
            bid_currency=None,
            date=datetime.utcnow()
        )
        db.session.add(first_comment)
        db.session.commit()
        
        flash('Feature request created successfully!', 'success')
        return redirect(url_for('feature_requests.detail', request_id=feature_request.id))
    
    # Get all apps for selection
    all_apps = App.query.all()
    return render_template('feature_requests/create.html', apps=all_apps)

@bp.route('/<int:request_id>/tag-onto', methods=['POST'])
@login_required
def tag_onto(request_id):
    """Tag a new request onto an existing one (adds as comment)."""
    if not current_user.email_verified:
        flash('Please verify your email address before tagging onto requests.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    existing_request = FeatureRequest.query.get_or_404(request_id)
    comment_text = request.form.get('comment')
    bid_amount = request.form.get('bid_amount', type=float) or 0.0
    
    if not comment_text:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Create comment on existing request
    from decimal import Decimal
    comment = Comment(
        feature_request_id=request_id,
        commenter_id=current_user.id,
        commenter_type='requester',
        comment=comment_text,
        bid_amount=Decimal(str(bid_amount)),
        bid_currency=current_user.preferred_currency if bid_amount > 0 else None,
        date=datetime.utcnow()
    )
    db.session.add(comment)
    
    # Update total bid amount
    existing_request.total_bid_amount = db.session.query(
        db.func.sum(Comment.bid_amount)
    ).filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).scalar() or Decimal('0.00')
    
    db.session.commit()
    
    flash('Your request has been added as a comment to the existing request.', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/confirm', methods=['POST'])
@login_required
def confirm_request(request_id):
    """Confirm a feature request as completed (requester action)."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    # Check if user has a non-zero bid
    user_bid = Comment.query.filter_by(
        feature_request_id=request_id,
        commenter_id=current_user.id,
        is_deleted=False
    ).filter(Comment.bid_amount > 0).first()
    
    if not user_bid:
        flash('You must have placed a bid to confirm this request.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    if feature_request.status != 'completed':
        flash('Request must be marked as completed by developers before you can confirm it.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check confirmation percentage
    from app.config import get_config_value
    from app.utils.payments import collect_payments, distribute_payments
    
    confirmation_percentage = get_config_value('confirmation_percentage', 80)
    
    # Get all non-zero bidders
    all_bids = Comment.query.filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).filter(Comment.bid_amount > 0).all()
    
    # Count confirmations (for now, we'll track this differently - TODO: add confirmation tracking)
    # For now, set status to confirmed and trigger payments
    feature_request.status = 'confirmed'
    feature_request.delivered_date = datetime.utcnow()
    
    # Collect payments and distribute to devs
    if collect_payments(request_id):
        distribute_payments(request_id)
        flash('Request confirmed! Payments have been processed.', 'success')
    else:
        flash('Request confirmed, but there was an error processing payments.', 'warning')
    
    db.session.commit()
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/set-status', methods=['POST'])
@login_required
def set_status(request_id):
    """Set feature request status (developer action)."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    new_status = request.form.get('status')
    
    # Check if user is a developer on this request
    from app.models import FeatureRequestDeveloper
    is_dev = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        developer_id=current_user.id,
        removed_at=None
    ).first()
    
    if not is_dev and current_user.role != 'admin':
        flash('You must be a developer on this request to change its status.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    if new_status not in ['requested', 'in_progress', 'completed', 'cancelled']:
        flash('Invalid status.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Store old status before changing
    old_status = feature_request.status
    
    from datetime import datetime
    feature_request.status = new_status
    
    # Handle projected completion date
    projected_date_str = request.form.get('projected_completion_date')
    if projected_date_str:
        try:
            feature_request.projected_completion_date = datetime.strptime(projected_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('feature_requests.detail', request_id=request_id))
    elif new_status == 'in_progress' and not feature_request.projected_completion_date:
        # Set projected completion date (default to 30 days from now)
        from datetime import timedelta
        feature_request.projected_completion_date = datetime.utcnow() + timedelta(days=30)
    elif new_status == 'completed':
        feature_request.delivered_date = datetime.utcnow()
        # Clear projected date when completed
        if feature_request.projected_completion_date:
            feature_request.projected_completion_date = None
    
    # Notify about status changes
    if new_status != old_status:
        from app.models import Notification
        import json
        
        # Get all requesters who placed bids
        requester_bids = Comment.query.filter_by(
            feature_request_id=request_id,
            is_deleted=False
        ).filter(Comment.bid_amount > 0).all()
        
        requester_ids = set([bid.commenter_id for bid in requester_bids])
        
        # Get all developers working on the request
        from app.models import FeatureRequestDeveloper
        dev_participants = FeatureRequestDeveloper.query.filter_by(
            feature_request_id=request_id,
            removed_at=None
        ).all()
        dev_ids = set([p.developer_id for p in dev_participants])
        
        # Special handling for completed status - send request_completed notification to requesters
        if new_status == 'completed':
            for requester_id in requester_ids:
                notification = Notification(
                    user_id=requester_id,
                    notification_type='request_completed',
                    notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
                )
                notification.set_data({'feature_request_id': request_id})
                db.session.add(notification)
            
            # Notify developers (except the one who made the change) about completion
            if current_user.id in dev_ids:
                dev_ids.remove(current_user.id)
            
            for dev_id in dev_ids:
                notification = Notification(
                    user_id=dev_id,
                    notification_type='request_completed',
                    notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
                )
                notification.set_data({
                    'feature_request_id': request_id,
                    'completed_by_name': current_user.name
                })
                db.session.add(notification)
        else:
            # For other status changes, notify requesters
            for requester_id in requester_ids:
                notification = Notification(
                    user_id=requester_id,
                    notification_type='request_status_change',
                    notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
                )
                notification.set_data({
                    'feature_request_id': request_id,
                    'old_status': old_status,
                    'new_status': new_status
                })
                db.session.add(notification)
            
            # Notify developers about status change (if not the one who made the change)
            if current_user.id in dev_ids:
                dev_ids.remove(current_user.id)
            
            for dev_id in dev_ids:
                notification = Notification(
                    user_id=dev_id,
                    notification_type='request_status_change',
                    notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
                )
                notification.set_data({
                    'feature_request_id': request_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by_name': current_user.name
                })
                db.session.add(notification)
    
    db.session.commit()
    flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/add-developer', methods=['POST'])
@login_required
def add_developer(request_id):
    """Add developer to feature request."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    if current_user.role != 'dev':
        flash('Only developers can be added to requests.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    from app.models import FeatureRequestDeveloper
    
    # Check if already a developer
    existing = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        developer_id=current_user.id,
        removed_at=None
    ).first()
    
    if existing:
        flash('You are already a developer on this request.', 'info')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if other developers need to approve
    other_devs = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        removed_at=None
    ).all()
    
    is_approved = len(other_devs) == 0  # Auto-approve if first dev
    
    dev = FeatureRequestDeveloper(
        feature_request_id=request_id,
        developer_id=current_user.id,
        is_approved=is_approved
    )
    db.session.add(dev)
    
    # Set status to in_progress if not already
    if feature_request.status == 'requested':
        feature_request.status = 'in_progress'
        from datetime import datetime, timedelta
        feature_request.projected_completion_date = datetime.utcnow() + timedelta(days=30)
    
    # Notify the developer that they've been added
    from app.models import Notification
    
    # Notify the developer themselves
    notification = Notification(
        user_id=current_user.id,
        notification_type='developer_added',
        notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
    )
    notification.set_data({'feature_request_id': request_id})
    db.session.add(notification)
    
    # Notify requesters who placed bids
    requester_bids = Comment.query.filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).filter(Comment.bid_amount > 0).all()
    requester_ids = set([bid.commenter_id for bid in requester_bids])
    
    for requester_id in requester_ids:
        notification = Notification(
            user_id=requester_id,
            notification_type='developer_added',
            notification_message=''  # Empty string for backward compatibility with NOT NULL constraint
        )
        notification.set_data({
            'feature_request_id': request_id,
            'developer_id': current_user.id,
            'developer_name': current_user.name
        })
        db.session.add(notification)
    
    db.session.commit()
    flash('You have been added as a developer on this request.', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(request_id, comment_id):
    """Edit a comment (requester only, only when status is 'requested')."""
    if not current_user.email_verified:
        flash('Please verify your email address before editing comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    feature_request = FeatureRequest.query.get_or_404(request_id)
    comment = Comment.query.get_or_404(comment_id)
    
    # Check ownership
    if comment.commenter_id != current_user.id:
        flash('You can only edit your own comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if requester
    if current_user.role != 'requester':
        flash('Only requesters can edit comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if status allows editing
    if feature_request.status != 'requested':
        flash('Comments can only be edited when the request status is "requested".', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    if request.method == 'POST':
        new_comment_text = request.form.get('comment')
        new_bid_amount = request.form.get('bid_amount', type=float) or 0.0
        
        if not new_comment_text:
            flash('Comment cannot be empty.', 'error')
            return redirect(url_for('feature_requests.edit_comment', request_id=request_id, comment_id=comment_id))
        
        if new_bid_amount < 0:
            flash('Bid amount cannot be negative.', 'error')
            return redirect(url_for('feature_requests.edit_comment', request_id=request_id, comment_id=comment_id))
        
        # Check if user has Stripe account for bidding
        if new_bid_amount > 0 and not current_user.stripe_account_id:
            flash('You must connect a Stripe account to place bids.', 'error')
            return redirect(url_for('feature_requests.edit_comment', request_id=request_id, comment_id=comment_id))
        
        # Store original if not already stored
        if not comment.is_edited:
            comment.original_comment = comment.comment
        
        # Update comment
        from decimal import Decimal
        comment.comment = new_comment_text
        comment.bid_amount = Decimal(str(new_bid_amount))
        comment.bid_currency = current_user.preferred_currency if new_bid_amount > 0 else None
        comment.is_edited = True
        comment.updated_at = datetime.utcnow()
        
        # Update total bid amount
        feature_request.total_bid_amount = db.session.query(
            db.func.sum(Comment.bid_amount)
        ).filter_by(
            feature_request_id=request_id,
            is_deleted=False
        ).scalar() or Decimal('0.00')
        
        db.session.commit()
        flash('Comment updated successfully!', 'success')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    return render_template('feature_requests/edit_comment.html',
                         feature_request=feature_request,
                         comment=comment)

@bp.route('/<int:request_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(request_id, comment_id):
    """Delete a comment (requester only, only when status is 'requested')."""
    if not current_user.email_verified:
        flash('Please verify your email address before deleting comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    feature_request = FeatureRequest.query.get_or_404(request_id)
    comment = Comment.query.get_or_404(comment_id)
    
    # Check ownership
    if comment.commenter_id != current_user.id:
        flash('You can only delete your own comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if requester
    if current_user.role != 'requester':
        flash('Only requesters can delete comments.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Check if status allows deletion
    if feature_request.status != 'requested':
        flash('Comments can only be deleted when the request status is "requested".', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Store original if not already stored
    if not comment.is_deleted:
        comment.original_comment = comment.comment
    
    # Mark as deleted
    comment.is_deleted = True
    comment.updated_at = datetime.utcnow()
    
    # Update total bid amount
    from decimal import Decimal
    feature_request.total_bid_amount = db.session.query(
        db.func.sum(Comment.bid_amount)
    ).filter_by(
        feature_request_id=request_id,
        is_deleted=False
    ).scalar() or Decimal('0.00')
    
    db.session.commit()
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    """Edit request type and category (developer only)."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    # Check if user is a developer on this request or admin
    from app.models import FeatureRequestDeveloper
    is_dev = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        developer_id=current_user.id,
        removed_at=None
    ).first()
    
    if not is_dev and current_user.role != 'admin':
        flash('Only developers on this request can edit it.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    if request.method == 'POST':
        request_type = request.form.get('request_type')
        request_category = request.form.get('request_category')
        projected_completion_date = request.form.get('projected_completion_date')
        
        if request_type not in ['UI/UX', 'backend']:
            flash('Invalid request type.', 'error')
            return redirect(url_for('feature_requests.edit_request', request_id=request_id))
        
        if request_category not in ['bug', 'enhancement']:
            flash('Invalid request category.', 'error')
            return redirect(url_for('feature_requests.edit_request', request_id=request_id))
        
        feature_request.request_type = request_type
        feature_request.request_category = request_category
        
        if projected_completion_date:
            from datetime import datetime
            try:
                feature_request.projected_completion_date = datetime.strptime(projected_completion_date, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('feature_requests.edit_request', request_id=request_id))
        
        db.session.commit()
        flash('Request updated successfully!', 'success')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    return render_template('feature_requests/edit_request.html',
                         feature_request=feature_request)

@bp.route('/<int:request_id>/remove-developer', methods=['POST'])
@login_required
def remove_developer(request_id):
    """Remove developer from request (self-removal)."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    from app.models import FeatureRequestDeveloper, FeatureRequestDeveloperHistory
    from datetime import datetime
    
    # Find developer relationship
    dev_rel = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        developer_id=current_user.id,
        removed_at=None
    ).first()
    
    if not dev_rel:
        flash('You are not a developer on this request.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Add to history
    history = FeatureRequestDeveloperHistory(
        feature_request_id=request_id,
        developer_id=current_user.id,
        started_at=dev_rel.added_at,
        removed_at=datetime.utcnow(),
        removed_by='self'
    )
    db.session.add(history)
    
    # Mark as removed
    dev_rel.removed_at = datetime.utcnow()
    
    # Check if any developers remain
    remaining_devs = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        removed_at=None
    ).count()
    
    if remaining_devs == 0:
        feature_request.status = 'requested'
        feature_request.projected_completion_date = None
    
    db.session.commit()
    flash('You have been removed from this request.', 'success')
    return redirect(url_for('feature_requests.detail', request_id=request_id))

@bp.route('/<int:request_id>/payment-ratios', methods=['GET', 'POST'])
@login_required
def payment_ratios(request_id):
    """Payment ratio management page (dev-only section)."""
    feature_request = FeatureRequest.query.get_or_404(request_id)
    
    from app.models import FeatureRequestDeveloper, PaymentRatio, PaymentRatioMessage
    
    # Check if user is a developer on this request or admin
    is_dev = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        developer_id=current_user.id,
        removed_at=None
    ).first()
    
    if not is_dev and current_user.role != 'admin':
        flash('Only developers on this request can manage payment ratios.', 'error')
        return redirect(url_for('feature_requests.detail', request_id=request_id))
    
    # Get all developers on this request
    developers = FeatureRequestDeveloper.query.filter_by(
        feature_request_id=request_id,
        removed_at=None
    ).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'set_ratios':
            # Set payment ratios
            total_percentage = 0
            ratios_to_update = []
            
            for dev_rel in developers:
                ratio_key = f'ratio_{dev_rel.developer_id}'
                ratio_value = request.form.get(ratio_key, type=float)
                
                if ratio_value is None or ratio_value < 0 or ratio_value > 100:
                    flash('Invalid ratio values. Each ratio must be between 0 and 100.', 'error')
                    return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
                
                total_percentage += ratio_value
                ratios_to_update.append((dev_rel.developer_id, ratio_value))
            
            if abs(total_percentage - 100.0) > 0.01:  # Allow small floating point differences
                flash(f'Ratios must sum to 100%. Current sum: {total_percentage}%', 'error')
                return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
            
            # Reset all acceptances when ratios change
            existing_ratios = PaymentRatio.query.filter_by(feature_request_id=request_id).all()
            for ratio in existing_ratios:
                ratio.is_accepted = False
                ratio.accepted_at = None
            
            # Update or create ratios
            from decimal import Decimal
            for dev_id, percentage in ratios_to_update:
                ratio = PaymentRatio.query.filter_by(
                    feature_request_id=request_id,
                    developer_id=dev_id
                ).first()
                
                if ratio:
                    ratio.ratio_percentage = Decimal(str(percentage))
                else:
                    ratio = PaymentRatio(
                        feature_request_id=request_id,
                        developer_id=dev_id,
                        ratio_percentage=Decimal(str(percentage))
                    )
                    db.session.add(ratio)
            
            db.session.commit()
            flash('Payment ratios updated. All developers must accept the new ratios.', 'success')
            return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
        
        elif action == 'accept_ratio':
            # Accept ratio for current user
            ratio = PaymentRatio.query.filter_by(
                feature_request_id=request_id,
                developer_id=current_user.id
            ).first()
            
            if not ratio:
                flash('No payment ratio found for you.', 'error')
                return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
            
            ratio.is_accepted = True
            ratio.accepted_at = datetime.utcnow()
            db.session.commit()
            flash('You have accepted the payment ratio.', 'success')
            return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
        
        elif action == 'add_message':
            # Add message to payment ratio section
            message_text = request.form.get('message')
            if not message_text:
                flash('Message cannot be empty.', 'error')
                return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
            
            message = PaymentRatioMessage(
                feature_request_id=request_id,
                sender_id=current_user.id,
                message=message_text
            )
            db.session.add(message)
            db.session.commit()
            flash('Message added.', 'success')
            return redirect(url_for('feature_requests.payment_ratios', request_id=request_id))
    
    # Get current payment ratios
    payment_ratios = PaymentRatio.query.filter_by(feature_request_id=request_id).all()
    ratio_dict = {r.developer_id: r for r in payment_ratios}
    
    # Initialize default ratios if none exist (even split)
    if not payment_ratios and len(developers) > 0:
        from decimal import Decimal
        default_percentage = Decimal('100.00') / len(developers)
        for dev_rel in developers:
            ratio = PaymentRatio(
                feature_request_id=request_id,
                developer_id=dev_rel.developer_id,
                ratio_percentage=default_percentage
            )
            db.session.add(ratio)
            ratio_dict[dev_rel.developer_id] = ratio
        db.session.commit()
    
    # Auto-accept if only one dev
    if len(developers) == 1 and payment_ratios:
        ratio = payment_ratios[0]
        if not ratio.is_accepted:
            ratio.is_accepted = True
            ratio.ratio_percentage = Decimal('100.00')
            ratio.accepted_at = datetime.utcnow()
            db.session.commit()
    
    # Get messages
    messages = PaymentRatioMessage.query.filter_by(
        feature_request_id=request_id
    ).order_by(PaymentRatioMessage.created_at.asc()).all()
    
    # Check if all ratios are accepted
    all_accepted = all(r.is_accepted for r in ratio_dict.values()) if ratio_dict else False
    
    return render_template('feature_requests/payment_ratios.html',
                         feature_request=feature_request,
                         developers=developers,
                         payment_ratios=ratio_dict,
                         messages=messages,
                         all_accepted=all_accepted)

