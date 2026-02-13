import sqlite3
import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # Create Users Table with department column
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Issues Table
    db.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            location TEXT,
            priority TEXT DEFAULT 'Low',
            status TEXT DEFAULT 'Submitted',
            image_path TEXT,
            reporter_id INTEGER NOT NULL,
            assigned_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES users (id)
        )
    ''')

    # Create Notifications Table
    db.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            issue_id INTEGER,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (issue_id) REFERENCES issues (id)
        )
    ''')
    
    # Create Comments Table
    db.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (issue_id) REFERENCES issues (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Check/Add department column if missing (for migration)
    try:
        db.execute("SELECT department FROM users LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE users ADD COLUMN department TEXT")

    # Seed Admin
    cur = db.execute("SELECT id FROM users WHERE email = ?", ('admin@campus.edu',))
    if cur.fetchone() is None:
        db.execute(
            "INSERT INTO users (fullname, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
            ('Admin User', 'admin@campus.edu', generate_password_hash('admin123'), 'admin', 'Administration')
        )

    # Seed Staff for Categories
    staff_accounts = [
        ('IT Support Staff', 'it_staff@campus.edu', 'IT Support'),
        ('Infrastructure Staff', 'infra_staff@campus.edu', 'Infrastructure'),
        ('Cleanliness Staff', 'clean_staff@campus.edu', 'Cleanliness'),
        ('Safety Officer', 'safety_staff@campus.edu', 'Safety'),
        ('General Staff', 'other_staff@campus.edu', 'Others')
    ]

    for name, email, dept in staff_accounts:
        cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone() is None:
            db.execute(
                "INSERT INTO users (fullname, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
                (name, email, generate_password_hash('staff123'), 'staff', dept)
            )

    db.commit()

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
