# IMPORTANT: Read instructions/architecture before making changes to this file
"""
Notification scheduler for checking and sending bulk notification emails.
Uses APScheduler to periodically check for expired notification queues.
See instructions/architecture for development guidelines.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

_scheduler = None

def init_scheduler(app):
    """
    Initialize the notification scheduler.
    Checks for expired queues every minute.
    
    Args:
        app: Flask application instance
    """
    global _scheduler
    
    if _scheduler is not None:
        # Scheduler already initialized
        return
    
    # Create scheduler with Flask app context
    def check_with_context():
        from app.utils.notification_queue import check_and_send_expired_queues
        with app.app_context():
            check_and_send_expired_queues()
    
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    
    # Schedule job to check expired queues every minute
    _scheduler.add_job(
        func=check_with_context,
        trigger=IntervalTrigger(minutes=1),
        id='check_notification_queues',
        name='Check and send expired notification queues',
        replace_existing=True
    )
    
    # Shut down scheduler when app exits
    atexit.register(lambda: _scheduler.shutdown() if _scheduler else None)
