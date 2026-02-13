from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from app.db import get_db
from app.utils import login_required

bp = Blueprint('common', __name__)

@bp.route('/notifications')
@login_required
def notifications():
    db = get_db()
    notifications = db.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Mark all as read when viewing the list? 
    # Or just let user click them. Let's keep them unread until clicked or marked.
    
    return render_template('notifications.html', notifications=notifications)

@bp.route('/notification/read/<int:notification_id>')
@login_required
def mark_read(notification_id):
    db = get_db()
    # verify ownership
    notif = db.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
    if not notif or notif['user_id'] != session['user_id']:
        flash("Notification not found", "error")
        return redirect(url_for('common.notifications'))
        
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    db.commit()
    
    if notif['issue_id']:
        # If admin, go to admin update? If student, go to issue detail.
        # This is tricky because route depends on role.
        # We can try to redirect to student.issue_detail since admins can view that too (it's the tracking page)?
        # Wait, admin uses issue_tracking.html? 
        # Admins usually use dashboard but can view details.
        # Let's check student.py: issue_detail is @login_required. So admins can see it.
        return redirect(url_for('student.issue_detail', issue_id=notif['issue_id']))
        
    return redirect(url_for('common.notifications'))

@bp.route('/notifications/clear')
@login_required
def clear_all():
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session['user_id'],))
    db.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for('common.notifications'))
