import os
import random
import string
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, abort, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash

# ─── CONFIG ─────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-change-me')

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///scripthub.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# ─── MODELS ─────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Script(db.Model):
    __tablename__ = 'scripts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    short_id = db.Column(db.String(24), unique=True, nullable=False)
    version = db.Column(db.String(20), default='1.0')
    real_content = db.Column(db.Text, default='')
    owner = db.Column(db.String(80), nullable=False)
    access_type = db.Column(db.String(20), default='public')
    allowed_ids = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def ids_list(self):
        if not self.allowed_ids:
            return []
        return [x.strip() for x in self.allowed_ids.split(',') if x.strip()]


class ExecutionLog(db.Model):
    __tablename__ = 'execution_logs'
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'))
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(80))
    allowed = db.Column(db.Boolean, default=True)
    kicked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Server(db.Model):
    __tablename__ = 'servers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner = db.Column(db.String(80), nullable=False)
    invite_code = db.Column(db.String(16), unique=True, nullable=False)
    icon = db.Column(db.String(8), default='🎮')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ServerMember(db.Model):
    __tablename__ = 'server_members'
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'))
    username = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), default='member')


class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'))
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), default='text')
    created_by = db.Column(db.String(80))


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'))
    username = db.Column(db.String(80))
    role = db.Column(db.String(20), default='user')
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── HELPERS ─────────────────────────────────────
def gen_short_id(n=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def gen_invite():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if session.get('role') != 'admin':
            abort(403)
        return f(*a, **kw)
    return wrapper


def current_user():
    return session.get('user')


def build_injected_code(script):
    """
    Auto-inject ID check at TOP of the script.
    Public → no check.
    Whitelist + IDs → has check + auto-kick.
    Whitelist + no IDs → no check.
    """
    if script.access_type != 'whitelist':
        return script.real_content or ''

    ids = script.ids_list()
    if not ids:
        return script.real_content or ''

    ids_lua = ', '.join(ids)
    injected = f"""-- ============================================
-- AUTO KICK + ID CHECK (ScriptHub)
-- ============================================
local ALLOWED_IDS = {{{ids_lua}}}
local _player = game.Players.LocalPlayer
local _authorized = false
for _, _id in ipairs(ALLOWED_IDS) do
    if _player.UserId == _id then _authorized = true break end
end
if not _authorized then
    _player:Kick("You are not authorized to use this script!")
    return
end
-- ============================================

"""
    return injected + (script.real_content or '')


# ─── AUTH ───────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '')
        admin_pw = request.form.get('admin_password', '')
        user = User.query.filter_by(username=u).first()

        if admin_pw and admin_pw == ADMIN_PASSWORD:
            session['user'] = u or 'admin'
            session['role'] = 'admin'
            return redirect(url_for('dashboard'))

        if user and check_password_hash(user.password, p):
            session['user'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '')
        if not u or not p:
            return render_template('register.html', error='Fill all fields')
        if User.query.filter_by(username=u).first():
            return render_template('register.html', error='Username taken')
        user = User(username=u, password=generate_password_hash(p), role='user')
        db.session.add(user)
        db.session.commit()
        session['user'] = u
        session['role'] = 'user'
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── DASHBOARD ──────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    user = current_user()
    if session.get('role') == 'admin':
        scripts = Script.query.order_by(Script.created_at.desc()).all()
    else:
        scripts = Script.query.filter_by(owner=user).order_by(Script.created_at.desc()).all()
    stats = {
        'total': len(scripts),
        'role': session.get('role', 'user'),
        'whitelist': sum(len(s.ids_list()) for s in scripts),
    }
    return render_template('dashboard.html', scripts=scripts, stats=stats)


# ─── SCRIPT CRUD ────────────────────────────────
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        version = request.form.get('version', '1.0').strip()
        access_type = request.form.get('access_type', 'public')
        real_content = request.form.get('real_content', '')
        allowed_ids = request.form.get('allowed_ids', '').strip()

        s = Script(
            name=name, short_id=gen_short_id(), version=version,
            real_content=real_content, owner=current_user(),
            access_type=access_type, allowed_ids=allowed_ids,
        )
        db.session.add(s)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create.html')


@app.route('/edit/<int:sid>', methods=['GET', 'POST'])
@login_required
def edit(sid):
    script = Script.query.get_or_404(sid)
    if session.get('role') != 'admin' and script.owner != current_user():
        abort(403)

    if request.method == 'POST':
        script.name = request.form.get('name', script.name)
        script.version = request.form.get('version', script.version)
        script.access_type = request.form.get('access_type', script.access_type)
        script.real_content = request.form.get('real_content', script.real_content)
        script.allowed_ids = request.form.get('allowed_ids', script.allowed_ids)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('edit.html', script=script)


# ─── ⭐ AUTO-INJECT ID (click → adds ID to script) ───
@app.route('/add_id/<int:sid>', methods=['POST'])
@login_required
def add_id(sid):
    script = Script.query.get_or_404(sid)
    if session.get('role') != 'admin' and script.owner != current_user():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    new_id = request.form.get('user_id', '').strip()
    if not new_id.isdigit():
        return jsonify({'ok': False, 'error': 'ID must be numeric'}), 400

    ids = script.ids_list()
    if new_id in ids:
        return jsonify({'ok': False, 'error': 'ID already exists'}), 400

    ids.append(new_id)
    script.allowed_ids = ','.join(ids)
    script.access_type = 'whitelist'
    db.session.commit()

    return jsonify({
        'ok': True,
        'ids': ids,
        'injected': build_injected_code(script)
    })


@app.route('/remove_id/<int:sid>', methods=['POST'])
@login_required
def remove_id(sid):
    script = Script.query.get_or_404(sid)
    if session.get('role') != 'admin' and script.owner != current_user():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403

    rem_id = request.form.get('user_id', '').strip()
    ids = [i for i in script.ids_list() if i != rem_id]
    script.allowed_ids = ','.join(ids)
    db.session.commit()
    return jsonify({'ok': True, 'ids': ids, 'injected': build_injected_code(script)})


@app.route('/delete/<int:sid>')
@login_required
def delete(sid):
    script = Script.query.get_or_404(sid)
    if session.get('role') != 'admin' and script.owner != current_user():
        abort(403)
    db.session.delete(script)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/logs/<int:sid>')
@login_required
def logs(sid):
    script = Script.query.get_or_404(sid)
    if session.get('role') != 'admin' and script.owner != current_user():
        abort(403)
    entries = ExecutionLog.query.filter_by(script_id=sid)\
        .order_by(ExecutionLog.created_at.desc()).limit(200).all()
    allowed = sum(1 for e in entries if e.allowed)
    kicked = sum(1 for e in entries if e.kicked)
    return render_template('logs.html', script=script, entries=entries,
                           allowed=allowed, kicked=kicked)


# ─── RAW API ────────────────────────────────────
@app.route('/api/raw')
def api_raw():
    short_id = request.args.get('id', '')
    script = Script.query.filter_by(short_id=short_id).first()
    if not script:
        return Response('-- Script not found', mimetype='text/plain')

    try:
        log = ExecutionLog(script_id=script.id, username=current_user() or 'anonymous',
                           allowed=True, kicked=False)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return Response(build_injected_code(script), mimetype='text/plain')


# ─── ADMIN ──────────────────────────────────────
@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    scripts = Script.query.order_by(Script.created_at.desc()).all()
    return render_template('admin.html', users=users, scripts=scripts)


@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
@login_required
@admin_required
def delete_user(uid):
    u = User.query.get_or_404(uid)
    if u.username == current_user():
        return redirect(url_for('admin'))
    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin'))


# ─── SERVERS ────────────────────────────────────
@app.route('/servers')
@login_required
def servers():
    user = current_user()
    rows = Server.query.join(ServerMember, Server.id == ServerMember.server_id)\
        .filter(ServerMember.username == user).all()
    seen, uniq = set(), []
    for s in rows:
        if s.id not in seen:
            seen.add(s.id)
            uniq.append(s)
    return render_template('servers.html', servers=uniq)


@app.route('/server/<int:sid>')
@login_required
def server_view(sid):
    server = Server.query.get_or_404(sid)
    user = current_user()
    member = ServerMember.query.filter_by(server_id=sid, username=user).first()
    if not member and server.owner != user:
        abort(403)
    channels = Channel.query.filter_by(server_id=sid).all()
    members = ServerMember.query.filter_by(server_id=sid).all()
    return render_template('server_view.html', server=server,
                           channels=channels, members=members)


@app.route('/api/servers/create', methods=['POST'])
@login_required
def api_create_server():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '🎮')
    if not name:
        return jsonify({'ok': False, 'error': 'Name required'}), 400
    s = Server(name=name, owner=current_user(), icon=icon, invite_code=gen_invite())
    db.session.add(s)
    db.session.flush()
    db.session.add(ServerMember(server_id=s.id, username=current_user(), role='owner'))
    db.session.add(Channel(server_id=s.id, name='general', type='text', created_by=current_user()))
    db.session.add(Channel(server_id=s.id, name='General Voice', type='voice', created_by=current_user()))
    db.session.commit()
    return jsonify({'ok': True, 'server_id': s.id})


@app.route('/api/servers/join', methods=['POST'])
@login_required
def api_join_server():
    code = request.form.get('invite_code', '').strip().upper()
    server = Server.query.filter_by(invite_code=code).first()
    if not server:
        return jsonify({'ok': False, 'error': 'Invalid code'}), 404
    if not ServerMember.query.filter_by(server_id=server.id, username=current_user()).first():
        db.session.add(ServerMember(server_id=server.id, username=current_user()))
        db.session.commit()
    return jsonify({'ok': True, 'server_id': server.id})


@app.route('/api/servers/<int:sid>/channels', methods=['POST'])
@login_required
def api_create_channel(sid):
    name = request.form.get('name', '').strip()
    ctype = request.form.get('type', 'text')
    if not name:
        return jsonify({'ok': False, 'error': 'Name required'}), 400
    c = Channel(server_id=sid, name=name, type=ctype, created_by=current_user())
    db.session.add(c)
    db.session.commit()
    return jsonify({'ok': True, 'channel_id': c.id})


@app.route('/api/channels/<int:cid>/delete', methods=['POST'])
@login_required
def api_delete_channel(cid):
    c = Channel.query.get_or_404(cid)
    server = Server.query.get(c.server_id)
    if session.get('role') != 'admin' and server.owner != current_user() \
            and c.created_by != current_user():
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    ChatMessage.query.filter_by(channel_id=cid).delete()
    db.session.delete(c)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/channels/<int:cid>/messages')
@login_required
def api_messages(cid):
    msgs = ChatMessage.query.filter_by(channel_id=cid)\
        .order_by(ChatMessage.created_at.asc()).limit(200).all()
    return jsonify([{
        'id': m.id, 'username': m.username, 'role': m.role,
        'message': m.message, 'time': m.created_at.strftime('%H:%M'),
    } for m in msgs])


@app.route('/api/channels/<int:cid>/send', methods=['POST'])
@login_required
def api_send(cid):
    text = request.form.get('message', '').strip()
    if not text:
        return jsonify({'ok': False}), 400
    m = ChatMessage(channel_id=cid, username=current_user(),
                    role=session.get('role', 'user'), message=text)
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True})


# ─── SOCKETIO (Voice + WebRTC) ──────────────────
voice_rooms = {}


@socketio.on('connect')
def on_connect():
    emit('connected', {'ok': True})


@socketio.on('join_voice')
def on_join_voice(data):
    room = f"voice_{data['channel_id']}"
    join_room(room)
    voice_rooms.setdefault(room, {})[request.sid] = {
        'username': session.get('user', 'anon'), 'muted': False, 'streaming': False}
    emit('voice_participants', voice_rooms[room], to=room)


@socketio.on('leave_voice')
def on_leave_voice(data):
    room = f"voice_{data['channel_id']}"
    voice_rooms.get(room, {}).pop(request.sid, None)
    leave_room(room)
    emit('voice_participants', voice_rooms.get(room, {}), to=room)


@socketio.on('toggle_mute')
def on_toggle_mute(data):
    room = f"voice_{data['channel_id']}"
    if request.sid in voice_rooms.get(room, {}):
        voice_rooms[room][request.sid]['muted'] = data.get('muted', False)
        emit('voice_participants', voice_rooms[room], to=room)


@socketio.on('toggle_stream')
def on_toggle_stream(data):
    room = f"voice_{data['channel_id']}"
    if request.sid in voice_rooms.get(room, {}):
        voice_rooms[room][request.sid]['streaming'] = data.get('streaming', False)
        emit('voice_participants', voice_rooms[room], to=room)


@socketio.on('webrtc_offer')
def on_offer(data):
    room = f"voice_{data['channel_id']}"
    emit('webrtc_offer', {'from': request.sid, 'sdp': data['sdp']}, to=room, include_self=False)


@socketio.on('webrtc_answer')
def on_answer(data):
    emit('webrtc_answer', {'from': request.sid, 'sdp': data['sdp']}, to=data['to'])


@socketio.on('webrtc_ice')
def on_ice(data):
    room = f"voice_{data['channel_id']}"
    emit('webrtc_ice', {'from': request.sid, 'candidate': data['candidate']},
         to=room, include_self=False)


@socketio.on('disconnect')
def on_disconnect():
    for room, members in list(voice_rooms.items()):
        if request.sid in members:
            members.pop(request.sid)
            emit('voice_participants', members, to=room)


# ─── INIT ───────────────────────────────────────
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        db.session.add(User(username='admin',
                            password=generate_password_hash(ADMIN_PASSWORD),
                            role='admin'))
        db.session.commit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
