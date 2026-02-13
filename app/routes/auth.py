from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import get_db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

        if user is None:
            flash('Invalid email or password.', 'error')
        elif not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'error')
        elif user['role'] != role:
            flash(f'Please log in as {user["role"]}.', 'error')
        else:
            session.clear()
            session['user_id'] = user['id']
            session['fullname'] = user['fullname']
            session['role'] = user['role']
            session['department'] = user['department']

            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))

    return render_template('login.html')

@bp.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        
        db = get_db()
        error = None

        if not fullname or not email or not password:
            error = 'All fields are required.'
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            error = 'Email is already registered.'

        if error is None:
            db.execute(
                'INSERT INTO users (fullname, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (fullname, email, generate_password_hash(password), role)
            )
            db.commit()
            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))

        flash(error, 'error')

    return render_template('signup.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
