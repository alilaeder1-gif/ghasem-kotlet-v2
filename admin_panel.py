import os
import sys
import sqlite3
import hashlib
import json
import random
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import BOT_TOKEN, DATABASE_PATH, REDIS_URL, REDIS_ENABLED

app = Flask(__name__)
app.secret_key = 'ghasem-kotlet-secret-key-2024'
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

verify_codes = {}

redis_client = None
if REDIS_ENABLED:
    try:
        import redis
        kwargs = {"decode_responses": True, "socket_connect_timeout": 5, "socket_timeout": 5, "retry_on_timeout": True}
        if REDIS_URL.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = None
        redis_client = redis.from_url(REDIS_URL, **kwargs)
        redis_client.ping()
    except:
        redis_client = None


def get_db():
    db_path = DATABASE_PATH
    candidates = [db_path, '/app/bot_data.db', '/tmp/bot_data.db', '/app/data/bot_data.db', 'bot_data.db']
    found = False
    for path in candidates:
        try:
            d = os.path.dirname(path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            conn = sqlite3.connect(path)
            conn.execute('SELECT 1 FROM sqlite_master')
            db_path = path
            found = True
            break
        except:
            continue
    if not found:
        db_path = '/tmp/bot_data.db'
        conn = sqlite3.connect(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS panel_config (key TEXT PRIMARY KEY, value TEXT)')
    conn.commit()
    return conn


def send_telegram(user_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": user_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass


def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password):
    conn = get_db()
    row = conn.execute("SELECT value FROM panel_config WHERE key='password'").fetchone()
    conn.close()
    if row:
        return hash_pass(password) == row['value']
    return password == 'admin123'


def set_password(password):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO panel_config (key, value) VALUES ('password', ?)", (hash_pass(password),))
    conn.commit()
    conn.close()


def is_first_run():
    conn = get_db()
    row = conn.execute("SELECT value FROM panel_config WHERE key='password'").fetchone()
    conn.close()
    return row is None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_first_run():
        return redirect(url_for('setup'))

    if request.method == 'POST':
        action = request.form.get('action', '')
        user_id = request.form.get('user_id', '').strip()
        code = request.form.get('code', '').strip()
        password = request.form.get('password', '')

        if action == 'send_code':
            if not user_id or not user_id.isdigit():
                flash('لطفاً یک آیدی عددی معتبر وارد کن!', 'error')
                return render_template('login.html', step='code')
            uid = int(user_id)
            if ADMIN_IDS and uid not in ADMIN_IDS:
                flash('این آیدی مجاز به ورود نیست!', 'error')
                return render_template('login.html', step='code')
            vcode = str(random.randint(100000, 999999))
            verify_codes[uid] = vcode
            send_telegram(uid, f"🔐 کد ورود به پنل مدیریت:\n\n<code>{vcode}</code>\n\nاین کد تا ۵ دقیقه معتبر است.")
            flash(f'✅ کد تأیید به آیدی {uid} ارسال شد!', 'success')
            return render_template('login.html', step='verify', user_id=uid, password=password)

        if action == 'verify':
            if not user_id or not user_id.isdigit():
                flash('آیدی نامعتبر!', 'error')
                return render_template('login.html', step='code')
            uid = int(user_id)
            if uid in verify_codes and verify_codes[uid] == code and check_password(password):
                del verify_codes[uid]
                session['logged_in'] = True
                session['user_id'] = uid
                return redirect(url_for('dashboard'))
            flash('❌ کد یا رمز عبور اشتباه!', 'error')
            return render_template('login.html', step='verify', user_id=uid)

    return render_template('login.html', step='code')


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if not is_first_run():
        return redirect(url_for('login'))

    if request.method == 'POST':
        p1 = request.form.get('password', '')
        p2 = request.form.get('confirm', '')
        if len(p1) < 4:
            flash('رمز عبور باید حداقل ۴ کاراکتر باشه!', 'error')
        elif p1 != p2:
            flash('رمز عبور با تکرارش یکی نیست!', 'error')
        else:
            set_password(p1)
            session['logged_in'] = True
            flash('تنظیمات اولیه با موفقیت انجام شد!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('setup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    groups = conn.execute('SELECT COUNT(*) as cnt FROM bot_groups WHERE is_active=1').fetchone()['cnt']
    users = conn.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM group_users').fetchone()['cnt']
    total_msgs = conn.execute('SELECT COALESCE(SUM(message_count),0) as t FROM group_users').fetchone()['t']
    cmds = conn.execute('SELECT COUNT(*) as cnt FROM custom_commands').fetchone()['cnt']
    top_groups = conn.execute('SELECT * FROM bot_groups WHERE is_active=1 ORDER BY member_count DESC LIMIT 5').fetchall()
    recent_users = conn.execute('SELECT gu.*, bg.title FROM group_users gu JOIN bot_groups bg ON gu.chat_id=bg.chat_id ORDER BY gu.last_seen DESC LIMIT 10').fetchall()
    conn.close()
    return render_template('dashboard.html', groups=groups, users=users, total_messages=total_msgs, commands=cmds, top_groups=top_groups, recent_users=recent_users)


@app.route('/groups')
@login_required
def groups():
    conn = get_db()
    data = conn.execute('SELECT * FROM bot_groups WHERE is_active=1 ORDER BY member_count DESC').fetchall()
    conn.close()
    return render_template('groups.html', groups=data)


@app.route('/group/<int:chat_id>')
@login_required
def group_detail(chat_id):
    conn = get_db()
    group = conn.execute('SELECT * FROM bot_groups WHERE chat_id=?', (chat_id,)).fetchone()
    users = conn.execute('SELECT * FROM group_users WHERE chat_id=? ORDER BY message_count DESC LIMIT 50', (chat_id,)).fetchall()
    settings = conn.execute('SELECT * FROM group_settings WHERE chat_id=?', (chat_id,)).fetchone()
    persona = conn.execute('SELECT * FROM ai_persona WHERE chat_id=?', (chat_id,)).fetchone()
    commands = conn.execute('SELECT * FROM custom_commands WHERE chat_id=?', (chat_id,)).fetchall()
    replies = conn.execute('SELECT * FROM auto_replies WHERE chat_id=?', (chat_id,)).fetchall()
    conn.close()
    return render_template('group_detail.html', group=group, users=users, settings=settings, persona=persona, commands=commands, replies=replies)


@app.route('/users')
@login_required
def users():
    conn = get_db()
    data = conn.execute('''
        SELECT user_id, username, full_name,
               COUNT(DISTINCT chat_id) as group_count,
               COALESCE(SUM(message_count),0) as total_messages,
               MAX(last_seen) as last_seen
        FROM group_users GROUP BY user_id ORDER BY total_messages DESC
    ''').fetchall()
    conn.close()
    return render_template('users.html', users=data)


@app.route('/ai-settings', methods=['GET', 'POST'])
@login_required
def ai_settings():
    conn = get_db()
    if request.method == 'POST':
        chat_id = request.form.get('chat_id', '').strip()
        name = request.form.get('persona_name', '').strip()
        prompt = request.form.get('system_prompt', '').strip()
        enabled = 1 if request.form.get('is_enabled') else 0
        action = request.form.get('action', '')
        if action == 'delete':
            conn.execute('DELETE FROM ai_persona WHERE chat_id=?', (chat_id,))
            flash('شخصیت حذف شد!', 'success')
        elif chat_id and name and prompt:
            conn.execute('INSERT OR REPLACE INTO ai_persona (chat_id, persona_name, system_prompt, is_enabled) VALUES (?,?,?,?)', (chat_id, name, prompt, enabled))
            flash('تنظیمات AI ذخیره شد!', 'success')
        elif not chat_id:
            flash('گروه رو انتخاب کن!', 'error')
        else:
            flash('همه فیلدها رو پر کن!', 'error')
        conn.commit()
    personas = conn.execute('SELECT ap.*, bg.title FROM ai_persona ap LEFT JOIN bot_groups bg ON ap.chat_id=bg.chat_id').fetchall()
    groups = conn.execute('SELECT chat_id, title FROM bot_groups WHERE is_active=1').fetchall()
    conn.close()
    return render_template('ai_settings.html', personas=personas, groups=groups)


@app.route('/commands')
@login_required
def commands():
    conn = get_db()
    data = conn.execute('SELECT cc.*, bg.title FROM custom_commands cc LEFT JOIN bot_groups bg ON cc.chat_id=bg.chat_id ORDER BY cc.created_at DESC').fetchall()
    conn.close()
    return render_template('commands.html', commands=data)


@app.route('/auto-replies')
@login_required
def auto_replies():
    conn = get_db()
    data = conn.execute('SELECT ar.*, bg.title FROM auto_replies ar LEFT JOIN bot_groups bg ON ar.chat_id=bg.chat_id ORDER BY ar.created_at DESC').fetchall()
    conn.close()
    return render_template('auto_replies.html', replies=data)


@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    conn = get_db()
    if request.method == 'POST':
        msg = request.form.get('message', '').strip()
        if msg:
            import requests
            groups = conn.execute('SELECT chat_id, title FROM bot_groups WHERE is_active=1').fetchall()
            ok, fail = 0, 0
            for g in groups:
                try:
                    r = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', json={'chat_id': g['chat_id'], 'text': msg, 'parse_mode': 'HTML'}, timeout=10)
                    if r.status_code == 200: ok += 1
                    else: fail += 1
                except: fail += 1
            flash(f'✅ {ok} ارسال شد | ❌ {fail} ناموفق', 'success')
        else:
            flash('متن پیام خالیه!', 'error')
    data = conn.execute('SELECT chat_id, title FROM bot_groups WHERE is_active=1').fetchall()
    conn.close()
    return render_template('broadcast.html', groups=data)


@app.route('/database')
@login_required
def database_viewer():
    conn = get_db()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    result = {}
    for t in tables:
        name = t['name']
        count = conn.execute(f'SELECT COUNT(*) as c FROM "{name}"').fetchone()['c']
        cols = [d[0] for d in conn.execute(f'SELECT * FROM "{name}" LIMIT 0').description]
        rows = conn.execute(f'SELECT * FROM "{name}" LIMIT 50').fetchall()
        result[name] = {'columns': cols, 'rows': rows, 'count': count}
    conn.close()
    return render_template('database.html', tables=result)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'change_password':
            old = request.form.get('old_password', '')
            new = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')
            if not check_password(old):
                flash('رمز فعلی اشتباه!', 'error')
            elif len(new) < 4:
                flash('رمز جدید باید حداقل ۴ کاراکتر باشه!', 'error')
            elif new != confirm:
                flash('رمز جدید با تکرارش یکی نیست!', 'error')
            else:
                set_password(new)
                flash('رمز عبور با موفقیت تغییر کرد!', 'success')
    return render_template('settings.html')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
