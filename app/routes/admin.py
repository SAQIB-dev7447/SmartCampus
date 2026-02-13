from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from datetime import datetime
from app.db import get_db
from app.utils import admin_required, login_required

bp = Blueprint('admin', __name__)

@bp.route('/admin/dashboard')
@admin_required
def dashboard():
    db = get_db()
    
    # Filters
    status = request.args.get('status')
    category = request.args.get('category')
    
    query = '''
        SELECT i.*, u.fullname as reporter_name 
        FROM issues i JOIN users u ON i.reporter_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if status:
        query += " AND i.status = ?"
        params.append(status)
    if category:
        query += " AND i.category = ?"
        params.append(category)
        
    query += " ORDER BY i.created_at DESC"
    
    issues = db.execute(query, params).fetchall()
    
    # Validation Code to ensure we don't crash if DB is empty
    all_issues = db.execute("SELECT status FROM issues").fetchall()
    total = len(all_issues)
    submitted = sum(1 for i in all_issues if i['status'] == 'Submitted')
    in_progress = sum(1 for i in all_issues if i['status'] == 'In Progress')
    resolved = sum(1 for i in all_issues if i['status'] == 'Resolved')
    
    # Staff Workload
    staff_workload = db.execute('''
        SELECT assigned_to, COUNT(*) as active_count
        FROM issues WHERE assigned_to IS NOT NULL AND status != 'Resolved'
        GROUP BY assigned_to
    ''').fetchall()
    
    # Fetch all staff for assignment dropdown, grouped by department if possible
    # We'll just pass all staff for now, template can filter if needed or we just listed them all
    # Improved: Fetch staff and their department
    staff_list = db.execute("SELECT fullname, department FROM users WHERE role = 'staff'").fetchall()

    return render_template('admin_dashboard.html', 
                         issues=issues, total=total, 
                         submitted=submitted, in_progress=in_progress, 
                         resolved_count=resolved, staff_workload=staff_workload,
                         staff_list=staff_list,
                         status_filter=status, category_filter=category)

@bp.route('/admin/update_issue/<int:issue_id>', methods=['POST'])
@login_required # Allow staff to update too eventually? For now admin_required mostly
def update_issue(issue_id):
    # Check if admin OR staff assigned to it (improving permission slightly)
    if session['role'] not in ['admin', 'staff']:
         flash('Permission denied', 'error')
         return redirect(url_for('student.dashboard'))

    status = request.form.get('status')
    assigned_to = request.form.get('assigned_to')
    
    db = get_db()
    issue = db.execute('SELECT * FROM issues WHERE id = ?', (issue_id,)).fetchone()
    
    if not issue:
        flash('Issue not found', 'error')
        return redirect(url_for('admin.dashboard'))
        
    updates = []
    params = []
    
    if status and status != issue['status']:
        updates.append("status = ?")
        params.append(status)
        # Notify Reporter
        db.execute(
            'INSERT INTO notifications (user_id, issue_id, message) VALUES (?, ?, ?)',
            (issue['reporter_id'], issue_id, f"Issue #{issue_id} status updated to {status}")
        )
        
        if status == 'Resolved':
             updates.append("resolved_at = ?")
             params.append(datetime.utcnow())

    if assigned_to and assigned_to != issue['assigned_to']:
        updates.append("assigned_to = ?")
        params.append(assigned_to)
        # Notify Reporter
        db.execute(
            'INSERT INTO notifications (user_id, issue_id, message) VALUES (?, ?, ?)',
            (issue['reporter_id'], issue_id, f"Issue #{issue_id} assigned to {assigned_to}")
        )
        
    if updates:
        query = f"UPDATE issues SET {', '.join(updates)} WHERE id = ?"
        params.append(issue_id)
        db.execute(query, params)
        db.commit()
        flash('Issue updated successfully.', 'success')
        
    return redirect(request.referrer or url_for('admin.dashboard'))

@bp.route('/admin/issue/<int:issue_id>/comment', methods=['POST'])
@login_required
def add_comment(issue_id):
    content = request.form.get('content')
    if content:
        db = get_db()
        db.execute(
            'INSERT INTO comments (issue_id, user_id, content) VALUES (?, ?, ?)',
            (issue_id, session['user_id'], content)
        )
        
        # Notify relevant party
        issue = db.execute('SELECT reporter_id FROM issues WHERE id = ?', (issue_id,)).fetchone()
        
        # If Admin commented, notify Student. If Student commented, notify Admin (in future)
        if session['role'] in ['admin', 'staff'] and issue:
             db.execute(
                'INSERT INTO notifications (user_id, issue_id, message) VALUES (?, ?, ?)',
                (issue['reporter_id'], issue_id, f"New comment on Issue #{issue_id}")
            )
            
        db.commit()
        flash('Comment added.', 'success')
        
    return redirect(url_for('student.issue_detail', issue_id=issue_id))

@bp.route('/analytics')
@admin_required
def analytics():
    db = get_db()
    
    # 1. Categories Data - FIXED LOGIC
    # Get all categories and their counts
    categories_query = db.execute('''
        SELECT category, COUNT(*) as cnt 
        FROM issues 
        GROUP BY category
    ''').fetchall()
    
    # Convert Row objects to dicts for template
    categories = [{'category': row['category'], 'cnt': row['cnt']} for row in categories_query]
    
    # Prepare data for Chart.js
    categories_labels = [c['category'] for c in categories]
    categories_data = [c['cnt'] for c in categories]
    
    # Calculate max count for bar heights (legacy support if needed, but Chart.js handles scaling)
    max_cat_count = max([c['cnt'] for c in categories]) if categories else 0
    
    # 2. Status Data
    statuses_query = db.execute('''
        SELECT status, COUNT(*) as cnt 
        FROM issues 
        GROUP BY status
    ''').fetchall()
    statuses = [{'status': row['status'], 'cnt': row['cnt']} for row in statuses_query]
    
    # 3. Top Locations
    top_location = db.execute('''
        SELECT location, COUNT(*) as cnt 
        FROM issues 
        WHERE location IS NOT NULL AND location != '' 
        GROUP BY location 
        ORDER BY cnt DESC LIMIT 1
    ''').fetchone()
    
    top_areas = db.execute('''
        SELECT location, COUNT(*) as cnt 
        FROM issues 
        WHERE location IS NOT NULL AND location != '' 
        GROUP BY location 
        ORDER BY cnt DESC LIMIT 3
    ''').fetchall()

    # 4. KPI Metrics
    total = db.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    
    # Correct resolution rate and today's stats using IST if needed, but here simple date is fine if resolved_at is UTC
    # Actually, to get 'today' in IST:
    from app.utils import IST_OFFSET
    now_ist = datetime.utcnow() + IST_OFFSET
    today_ist_str = now_ist.strftime('%Y-%m-%d')
    
    resolved_today = db.execute(
        "SELECT COUNT(*) FROM issues WHERE status = 'Resolved' AND date(resolved_at, '+5 hours', '+30 minutes') = ?",
        (today_ist_str,)
    ).fetchone()[0]
    
    active_critical = db.execute(
        "SELECT COUNT(*) FROM issues WHERE priority = 'High' AND status != 'Resolved'"
    ).fetchone()[0]

    resolution_rate = 0
    avg_resolution_hours = 0
    
    resolved_issues = db.execute(
        "SELECT created_at, resolved_at FROM issues WHERE status = 'Resolved' AND resolved_at IS NOT NULL"
    ).fetchall()
    
    if total > 0:
        resolution_rate = (len(resolved_issues) / total) * 100
        
    if resolved_issues:
        total_seconds = 0
        for issue in resolved_issues:
            # SQLite TIMESTAMP are strings usually, but parse_decltypes might help. 
            # If they are strings:
            try:
                c_at = issue['created_at'] if isinstance(issue['created_at'], datetime) else datetime.strptime(issue['created_at'], '%Y-%m-%d %H:%M:%S')
                r_at = issue['resolved_at'] if isinstance(issue['resolved_at'], datetime) else datetime.strptime(issue['resolved_at'], '%Y-%m-%d %H:%M:%S')
                total_seconds += (r_at - c_at).total_seconds()
            except (ValueError, TypeError):
                continue
        
        avg_resolution_hours = (total_seconds / len(resolved_issues)) / 3600

    return render_template('analytics.html',
                         categories=categories, max_cat_count=max_cat_count,
                         categories_labels=categories_labels, categories_data=categories_data,
                         statuses=statuses, total=total,
                         top_location=top_location, top_areas=top_areas,
                         resolved_today=resolved_today, active_critical=active_critical,
                         resolution_rate=resolution_rate, avg_resolution_hours=avg_resolution_hours)
