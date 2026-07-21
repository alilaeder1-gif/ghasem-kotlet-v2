import os
import sys
import asyncio
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import BOT_TOKEN, DATABASE_PATH, ADMIN_IDS
from database import db

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Admin(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return Admin(user_id)


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if ADMIN_IDS and session.get('user_id') not in ADMIN_IDS:
            flash('دسترسی غیرمجاز!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.getenv('PANEL_PASSWORD', 'admin123'):
            user = Admin(1)
            login_user(user, remember=True)
            session['user_id'] = 1
            flash('ورود موفق!', 'success')
            return redirect(url_for('dashboard'))
        flash('رمز عبور اشتباه!', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@admin_required
def dashboard():
    conn = get_db()
    try:
        groups = conn.execute('SELECT COUNT(*) as cnt FROM bot_groups WHERE is_active=1').fetchone()['cnt']
        users = conn.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM group_users').fetchone()['cnt']
        total_messages = conn.execute('SELECT SUM(message_count) as total FROM group_users').fetchone()['total'] or 0
        commands = conn.execute('SELECT COUNT(*) as cnt FROM custom_commands').fetchone()['cnt']
        auto_replies = conn.execute('SELECT COUNT(*) as cnt FROM auto_replies').fetchone()['cnt']
        
        recent_users = conn.execute('''
            SELECT gu.*, bg.title as group_title 
            FROM group_users gu 
            JOIN bot_groups bg ON gu.chat_id = bg.chat_id 
            ORDER BY gu.last_seen DESC 
            LIMIT 10
        ''').fetchall()
        
        top_groups = conn.execute('''
            SELECT * FROM bot_groups 
            WHERE is_active=1 
            ORDER BY member_count DESC 
            LIMIT 5
        ''').fetchall()
        
        return render_template('dashboard.html',
            groups=groups,
            users=users,
            total_messages=total_messages,
            commands=commands,
            auto_replies=auto_replies,
            recent_users=recent_users,
            top_groups=top_groups
        )
    finally:
        conn.close()


@app.route('/groups')
@admin_required
def groups():
    conn = get_db()
    try:
        all_groups = conn.execute('SELECT * FROM bot_groups WHERE is_active=1 ORDER BY member_count DESC').fetchall()
        return render_template('groups.html', groups=all_groups)
    finally:
        conn.close()


@app.route('/groups/<int:chat_id>')
@admin_required
def group_detail(chat_id):
    conn = get_db()
    try:
        group = conn.execute('SELECT * FROM bot_groups WHERE chat_id=?', (chat_id,)).fetchone()
        if not group:
            flash('گروه پیدا نشد!', 'error')
            return redirect(url_for('groups'))
        
        users = conn.execute('''
            SELECT * FROM group_users 
            WHERE chat_id=? 
            ORDER BY message_count DESC
        ''', (chat_id,)).fetchall()
        
        settings = conn.execute('SELECT * FROM group_settings WHERE chat_id=?', (chat_id,)).fetchone()
        persona = conn.execute('SELECT * FROM ai_persona WHERE chat_id=?', (chat_id,)).fetchone()
        commands = conn.execute('SELECT * FROM custom_commands WHERE chat_id=?', (chat_id,)).fetchall()
        replies = conn.execute('SELECT * FROM auto_replies WHERE chat_id=?', (chat_id,)).fetchall()
        
        return render_template('group_detail.html',
            group=group,
            users=users,
            settings=settings,
            persona=persona,
            commands=commands,
            replies=replies
        )
    finally:
        conn.close()


@app.route('/users')
@admin_required
def users():
    conn = get_db()
    try:
        all_users = conn.execute('''
            SELECT user_id, username, full_name, 
                   COUNT(DISTINCT chat_id) as group_count,
                   SUM(message_count) as total_messages,
                   MAX(last_seen) as last_seen
            FROM group_users 
            GROUP BY user_id 
            ORDER BY total_messages DESC
        ''').fetchall()
        return render_template('users.html', users=all_users)
    finally:
        conn.close()


@app.route('/commands')
@admin_required
def commands():
    conn = get_db()
    try:
        all_commands = conn.execute('''
            SELECT cc.*, bg.title as group_title 
            FROM custom_commands cc 
            JOIN bot_groups bg ON cc.chat_id = bg.chat_id 
            ORDER BY cc.created_at DESC
        ''').fetchall()
        return render_template('commands.html', commands=all_commands)
    finally:
        conn.close()


@app.route('/auto-replies')
@admin_required
def auto_replies():
    conn = get_db()
    try:
        all_replies = conn.execute('''
            SELECT ar.*, bg.title as group_title 
            FROM auto_replies ar 
            JOIN bot_groups bg ON ar.chat_id = bg.chat_id 
            ORDER BY ar.created_at DESC
        ''').fetchall()
        return render_template('auto_replies.html', replies=all_replies)
    finally:
        conn.close()


@app.route('/ai-settings')
@admin_required
def ai_settings():
    conn = get_db()
    try:
        personas = conn.execute('''
            SELECT ap.*, bg.title as group_title 
            FROM ai_persona ap 
            JOIN bot_groups bg ON ap.chat_id = bg.chat_id
        ''').fetchall()
        return render_template('ai_settings.html', personas=personas)
    finally:
        conn.close()


@app.route('/broadcast', methods=['GET', 'POST'])
@admin_required
def broadcast():
    if request.method == 'POST':
        message = request.form.get('message')
        if not message:
            flash('پیام خالیه!', 'error')
            return redirect(url_for('broadcast'))
        
        conn = get_db()
        try:
            groups = conn.execute('SELECT chat_id FROM bot_groups WHERE is_active=1').fetchall()
            success = 0
            failed = 0
            
            for g in groups:
                try:
                    import requests
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    data = {'chat_id': g['chat_id'], 'text': message, 'parse_mode': 'HTML'}
                    r = requests.post(url, data=data, timeout=10)
                    if r.status_code == 200:
                        success += 1
                    else:
                        failed += 1
                except:
                    failed += 1
            
            flash(f'ارسال شد: {success} | ناموفق: {failed}', 'success' if success > 0 else 'error')
        finally:
            conn.close()
        
        return redirect(url_for('broadcast'))
    
    conn = get_db()
    try:
        groups = conn.execute('SELECT chat_id, title FROM bot_groups WHERE is_active=1').fetchall()
        return render_template('broadcast.html', groups=groups)
    finally:
        conn.close()


@app.route('/database')
@admin_required
def database_viewer():
    conn = get_db()
    try:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_data = {}
        for table in tables:
            name = table['name']
            rows = conn.execute(f'SELECT * FROM {name} LIMIT 100').fetchall()
            columns = [desc[0] for desc in conn.execute(f'SELECT * FROM {name} LIMIT 1').description] if rows else []
            table_data[name] = {'columns': columns, 'rows': rows, 'count': conn.execute(f'SELECT COUNT(*) as cnt FROM {name}').fetchone()['cnt']}
        return render_template('database.html', tables=table_data)
    finally:
        conn.close()


@app.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        panel_password = request.form.get('panel_password')
        if panel_password:
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            with open(env_path, 'r') as f:
                content = f.read()
            if 'PANEL_PASSWORD=' in content:
                content = content.replace('PANEL_PASSWORD=.*', f'PANEL_PASSWORD={panel_password}')
            else:
                content += f'\nPANEL_PASSWORD={panel_password}'
            with open(env_path, 'w') as f:
                f.write(content)
            flash('تنظیمات ذخیره شد!', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html')


@app.route('/api/stats')
@admin_required
def api_stats():
    conn = get_db()
    try:
        return jsonify({
            'groups': conn.execute('SELECT COUNT(*) as cnt FROM bot_groups WHERE is_active=1').fetchone()['cnt'],
            'users': conn.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM group_users').fetchone()['cnt'],
            'messages': conn.execute('SELECT SUM(message_count) as total FROM group_users').fetchone()['total'] or 0,
            'commands': conn.execute('SELECT COUNT(*) as cnt FROM custom_commands').fetchone()['cnt']
        })
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
