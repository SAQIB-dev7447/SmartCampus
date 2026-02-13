import os
import time
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from werkzeug.utils import secure_filename
from app.db import get_db
from app.utils import login_required, allowed_file

bp = Blueprint('student', __name__)

@bp.route('/student/dashboard')
@login_required
def dashboard():
    db = get_db()
    issues = db.execute(
        'SELECT * FROM issues WHERE reporter_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    
    total = len(issues)
    in_progress = sum(1 for i in issues if i['status'] == 'In Progress')
    resolved = sum(1 for i in issues if i['status'] == 'Resolved')
    
    return render_template('student_dashboard.html', 
                         issues=issues, total_issues=total, 
                         in_progress=in_progress, resolved=resolved)

@bp.route('/student/report', methods=('GET', 'POST'))
@login_required
def report_issue():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        description = request.form['description']
        location = request.form['location']
        priority = request.form['priority']
        image = request.files.get('image')
        
        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            timestamp = int(time.time())
            filename = f"{timestamp}_{filename}"
            # Ensure folder exists
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            # Store relative path for template usage
            image_path = f"uploads/{filename}"

        db = get_db()
        cur = db.execute(
            'INSERT INTO issues (title, category, description, location, priority, image_path, reporter_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (title, category, description, location, priority, image_path, session['user_id'])
        )
        issue_id = cur.lastrowid
        
        # NOTIFICATION LOGIC
        # 1. Notify Admins
        admins = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchall()
        for admin in admins:
            db.execute(
                'INSERT INTO notifications (user_id, issue_id, message) VALUES (?, ?, ?)',
                (admin['id'], issue_id, f"New {priority} priority issue reported: {title}")
            )
            
        # 2. Notify Staff of this Category
        staff_members = db.execute(
            "SELECT id FROM users WHERE role = 'staff' AND (department = ? OR department = 'Others')",
            (category,)
        ).fetchall()
        
        for staff in staff_members:
            db.execute(
                'INSERT INTO notifications (user_id, issue_id, message) VALUES (?, ?, ?)',
                (staff['id'], issue_id, f"New issue assigned to your department: {title}")
            )
            
        db.commit()
        flash('Issue reported successfully!', 'success')
        return redirect(url_for('student.dashboard'))
        
    return render_template('report_issues.html')

@bp.route('/issue/<int:issue_id>')
@login_required
def issue_detail(issue_id):
    db = get_db()
    issue = db.execute('''
        SELECT i.*, u.fullname as reporter_name, u.email as reporter_email, u.role as reporter_role
        FROM issues i JOIN users u ON i.reporter_id = u.id
        WHERE i.id = ?
    ''', (issue_id,)).fetchone()
    
    if issue is None:
        flash('Issue not found.', 'error')
        return redirect(url_for('student.dashboard'))
        
    comments = db.execute('''
        SELECT c.*, u.fullname, u.role
        FROM comments c JOIN users u ON c.user_id = u.id
        WHERE c.issue_id = ? ORDER BY c.created_at DESC
    ''', (issue_id,)).fetchall()
    
    # Mark notifications as read if visiting this issue
    db.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND issue_id = ?",
        (session['user_id'], issue_id)
    )
    db.commit()
    
    return render_template('issue_tracking.html', issue=issue, comments=comments)
