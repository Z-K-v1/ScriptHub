import os
import json
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', secrets.token_hex(32))

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///scripthub.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==================== MODELS ====================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='USER')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Script(db.Model):
    __tablename__ = 'scripts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    short_id = db.Column(db.String(32), unique=True, nullable=False)
    version = db.Column(db.String(50), default='V1')
    real_content = db.Column(db.Text, nullable=False)
    owner = db.Column(db.String(50), nullable=False)
    access_type = db.Column(db.String(20), default='public')
    allowed_ids = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExecutionLog(db.Model):
    __tablename__ = 'execution_logs'
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(100), default='')
    allowed = db.Column(db.Boolean, default=False)
    kicked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== SERVER MODELS (para sa Part 2) ====================
class Server(db.Model):
    __tablename__ = 'servers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(50), nullable=False)
    invite_code = db.Column(db.String(16), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='🎮')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ServerMember(db.Model):
    __tablename__ = 'server_members'
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='MEMBER')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), default='text')
    created_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='USER')
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== INIT DB ====================
with app.app_context():
    db.create_all()
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')
    if not User.query.filter_by(username='Z-K').first():
        db.session.add(User(username='Z-K', password=admin_pass, role='ADMIN'))
        db.session.commit()
        print(f'✅ Admin: Z-K / {admin_pass}')
    print('✅ DB ready')

# ==================== HELPERS ====================
def require_login(f):
    @wraps(f)
    def d(*a, **k):
        if 'user_id' not in session: return redirect('/login')
        return f(*a, **k)
    return d

def require_admin(f):
    @wraps(f)
    def d(*a, **k):
        if 'user_id' not in session: return redirect('/login')
        u = User.query.get(session['user_id'])
        if not u or u.role != 'ADMIN': return 'Access Denied', 403
        return f(*a, **k)
    return d

def get_base_url():
    return os.environ.get('RENDER_EXTERNAL_URL', request.url_root.rstrip('/'))

def make_short_id():
    while True:
        sid = secrets.token_hex(5)
        if not Script.query.filter_by(short_id=sid).first(): return sid

def make_invite_code():
    while True:
        code = secrets.token_hex(4)
        if not Server.query.filter_by(invite_code=code).first(): return code

# ==================== STYLES ====================
STYLES = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#080404;--bg1:#0e0707;--bg2:#160b0b;--bg3:#1f0f0f;--glass:rgba(22,11,11,0.6);--border:rgba(255,255,255,0.06);--border1:rgba(255,255,255,0.1);--border2:rgba(255,59,59,0.3);--text:#fff;--text1:#e0e0e0;--text2:#9a9a9a;--text3:#5a5a5a;--red:#ff3b3b;--red2:#cc0000;--red-dim:rgba(255,59,59,0.12);--glow:rgba(255,59,59,0.6);--purple:#b855ff;--green:#22c55e;--yellow:#ffbb44;--blue:#4a9eff}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6;min-height:100vh;position:relative;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 1000px 800px at 10% -10%,rgba(255,59,59,0.18),transparent 55%),radial-gradient(ellipse 1000px 800px at 90% 110%,rgba(184,85,255,0.12),transparent 55%);pointer-events:none;z-index:0}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer;border:none;background:none;color:inherit}
input,textarea,select{font-family:inherit;width:100%;padding:13px 15px;background:rgba(0,0,0,0.4);border:1px solid var(--border);border-radius:11px;color:var(--text);font-size:15px;outline:none;min-height:48px;transition:all 0.2s;backdrop-filter:blur(10px)}
input:focus,textarea:focus,select:focus{border-color:var(--red);background:rgba(0,0,0,0.6);box-shadow:0 0 0 4px var(--red-dim)}
input::placeholder,textarea::placeholder{color:var(--text3)}
textarea{font-family:'JetBrains Mono',monospace;font-size:12.5px;min-height:320px;resize:vertical;line-height:1.6}
.layout{display:flex;min-height:100vh;position:relative;z-index:1}
.sidebar{width:280px;background:linear-gradient(180deg,rgba(16,8,8,0.95),rgba(10,5,5,0.98));backdrop-filter:blur(30px);border-right:1px solid var(--border);padding:24px 16px;display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:50}
.brand{display:flex;align-items:center;gap:12px;padding:8px 12px 22px;border-bottom:1px solid var(--border);margin-bottom:20px}
.brand-logo{width:44px;height:44px;border-radius:13px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-weight:900;font-size:17px;color:#fff;box-shadow:0 8px 24px rgba(255,59,59,0.4);animation:logoGlow 3s ease-in-out infinite alternate}
@keyframes logoGlow{0%{box-shadow:0 8px 24px rgba(255,59,59,0.4)}100%{box-shadow:0 8px 32px rgba(255,59,59,0.7)}}
.brand-name{font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:800}
.brand-sub{font-size:10px;color:var(--text3);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-top:3px}
.nav-label{font-size:10px;font-weight:800;color:var(--text3);text-transform:uppercase;letter-spacing:1.5px;padding:18px 14px 8px}
.nav-item{display:flex;align-items:center;gap:13px;padding:12px 14px;border-radius:12px;font-size:14px;font-weight:600;color:var(--text1);margin-bottom:3px;transition:all 0.25s;border:1px solid transparent;min-height:46px}
.nav-item:hover{background:rgba(255,255,255,0.03);color:var(--text);transform:translateX(3px)}
.nav-item.active{background:linear-gradient(90deg,var(--red-dim),rgba(255,59,59,0.02));color:var(--red);border-color:rgba(255,59,59,0.2);border-left:3px solid var(--red)}
.sidebar-footer{margin-top:auto;padding-top:16px;border-top:1px solid var(--border)}
.user-card{display:flex;align-items:center;gap:11px;padding:12px;border-radius:12px;background:linear-gradient(135deg,rgba(255,59,59,0.05),rgba(184,85,255,0.05));border:1px solid var(--border)}
.user-avatar{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:15px}
.user-avatar-admin{background:linear-gradient(135deg,#ffaa00,#ff6600)}
.user-name{font-size:14px;font-weight:700}
.user-role{font-size:10px;color:var(--text3);font-weight:800;text-transform:uppercase;letter-spacing:0.8px;margin-top:2px}
.main{flex:1;margin-left:280px;display:flex;flex-direction:column}
.topbar{height:72px;background:rgba(10,5,5,0.85);backdrop-filter:blur(30px);border-bottom:1px solid var(--border);padding:0 32px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:40}
.topbar-title{font-size:16px;font-weight:700;font-family:'Space Grotesk',sans-serif}
.content{padding:40px;flex:1;max-width:1500px;width:100%;margin:0 auto}
.page-title{font-family:'Space Grotesk',sans-serif;font-size:38px;font-weight:800;letter-spacing:-1.5px;background:linear-gradient(135deg,#fff 0%,#ff5555 50%,#b855ff 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.page-sub{font-size:14px;color:var(--text2);margin-bottom:32px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:9px;padding:12px 22px;border-radius:12px;font-weight:700;font-size:13.5px;cursor:pointer;border:1px solid transparent;min-height:46px;transition:all 0.25s;text-decoration:none}
.btn-primary{background:linear-gradient(135deg,var(--red),var(--red2));color:#fff;box-shadow:0 6px 24px rgba(255,59,59,0.35)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 12px 36px rgba(255,59,59,0.5)}
.btn-secondary{background:var(--glass);color:var(--text);border-color:var(--border1);backdrop-filter:blur(10px)}
.btn-secondary:hover{background:var(--bg3);border-color:var(--border2);transform:translateY(-2px)}
.btn-danger{background:rgba(255,59,59,0.1);color:#ff5555;border-color:rgba(255,59,59,0.25)}
.btn-danger:hover{background:rgba(255,59,59,0.2);transform:translateY(-2px)}
.btn-ghost{background:transparent;color:var(--text1);border-color:var(--border1)}
.btn-ghost:hover{background:var(--bg2);color:var(--text)}
.btn-sm{padding:10px 16px;font-size:12.5px;border-radius:10px;min-height:40px}
.btn-success{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;box-shadow:0 6px 24px rgba(34,197,94,0.35)}
.btn-success:hover{transform:translateY(-2px)}
.card{position:relative;background:linear-gradient(180deg,rgba(22,11,11,0.7),rgba(10,5,5,0.9));border:1px solid var(--border);border-radius:18px;padding:32px;backdrop-filter:blur(20px);transition:all 0.3s;margin-bottom:16px}
.card:hover{border-color:rgba(255,59,59,0.25);transform:translateY(-3px);box-shadow:0 20px 60px rgba(0,0,0,0.5)}
.form-group{margin-bottom:22px}
.form-label{display:block;font-size:11.5px;font-weight:800;color:var(--text1);margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid-scripts{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:20px}
.grid-servers{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:4px 11px;border-radius:8px;font-size:10.5px;font-weight:800;border:1px solid transparent}
.badge-purple{background:rgba(184,85,255,0.15);color:#d4a3ff;border-color:rgba(184,85,255,0.3)}
.badge-green{background:rgba(34,197,94,0.15);color:#4ade80;border-color:rgba(34,197,94,0.3)}
.badge-yellow{background:rgba(255,170,0,0.15);color:#ffcc66;border-color:rgba(255,170,0,0.3)}
.badge-red{background:rgba(255,59,59,0.15);color:#ff6666;border-color:rgba(255,59,59,0.3)}
.badge-admin{background:rgba(255,170,0,0.15);color:#ffcc66;border-color:rgba(255,170,0,0.3)}
.badge-blue{background:rgba(74,158,255,0.15);color:#7cc0ff;border-color:rgba(74,158,255,0.3)}
.id-row{display:flex;gap:12px;margin-bottom:12px}
.id-row input{flex:1;font-family:'JetBrains Mono',monospace}
.id-row button{width:52px;height:52px;border-radius:12px;background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.35);color:#ff5555;font-size:20px;flex-shrink:0}
.id-row button:hover{background:rgba(220,38,38,0.3)}
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;position:relative;z-index:1}
.login-card{background:linear-gradient(180deg,rgba(22,11,11,0.85),rgba(10,5,5,0.95));backdrop-filter:blur(40px);border:1px solid var(--border1);border-radius:26px;padding:52px 44px;width:460px;max-width:100%;box-shadow:0 40px 120px rgba(0,0,0,0.8)}
.login-logo{width:84px;height:84px;border-radius:24px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:32px;color:#fff;margin:0 auto 22px;box-shadow:0 12px 40px rgba(255,59,59,0.5)}
.login-title{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:800;text-align:center;margin-bottom:8px}
.login-sub{font-size:14px;color:var(--text2);text-align:center;margin-bottom:34px}
.login-card input{margin-bottom:14px}
.login-err{color:#ff5555;text-align:center;font-size:13px;font-weight:700;min-height:20px;margin-top:12px}
.login-link{display:block;text-align:center;margin-top:22px;font-size:14px;color:var(--red);font-weight:700}
.copy-box{display:inline-flex;align-items:center;gap:7px;background:rgba(0,0,0,0.5);border:1px solid var(--border);border-radius:9px;padding:6px 12px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#ff5555;cursor:pointer;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;width:100%;transition:all 0.25s}
.copy-box:hover{background:rgba(255,59,59,0.1);border-color:var(--red);color:#fff}
.empty{text-align:center;padding:80px 30px;border:1px dashed rgba(255,255,255,0.1);border-radius:20px}
.empty-icon{font-size:48px;margin-bottom:20px;opacity:0.5}
.log-item{display:flex;align-items:center;gap:14px;padding:16px 20px;border-radius:14px;margin-bottom:10px;border:1px solid}
.log-allowed{border-color:rgba(34,197,94,0.3);background:linear-gradient(90deg,rgba(34,197,94,0.05),transparent)}
.log-kicked{border-color:rgba(220,38,38,0.4);background:linear-gradient(90deg,rgba(220,38,38,0.08),transparent)}
.log-icon{width:40px;height:40px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:17px;flex-shrink:0}
.log-icon.allowed{background:linear-gradient(135deg,#22c55e,#16a34a)}
.log-icon.kicked{background:linear-gradient(135deg,#dc2626,#991b1b)}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-bottom:36px}
.stat{background:linear-gradient(180deg,rgba(22,11,11,0.7),rgba(10,5,5,0.9));border:1px solid var(--border);border-radius:18px;padding:26px}
.stat-label{font-size:12px;color:var(--text2);font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.stat-value{font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:800;letter-spacing:-1px}
.chat-layout{display:grid;grid-template-columns:260px 1fr;background:var(--bg1);border:1px solid var(--border);border-radius:16px;overflow:hidden;height:calc(100vh - 280px);min-height:500px}
.chat-sidebar{background:var(--bg);border-right:1px solid var(--border);display:flex;flex-direction:column}
.chat-sidebar-header{padding:18px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.channel-group-label{font-size:10px;font-weight:800;color:var(--text3);text-transform:uppercase;letter-spacing:1px;padding:14px 14px 8px;display:flex;justify-content:space-between;align-items:center}
.channel-group-label button{color:var(--text3);font-size:16px}
.channel-group-label button:hover{color:var(--red)}
.channel-item{display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:8px;cursor:pointer;color:var(--text2);font-size:13.5px;font-weight:600;margin:2px 8px;transition:all 0.2s;justify-content:space-between}
.channel-item:hover{background:var(--bg2);color:var(--text)}
.channel-item.active{background:var(--red-dim);color:var(--red)}
.channel-item-left{display:flex;align-items:center;gap:8px;flex:1;min-width:0}
.channel-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.channel-delete{width:22px;height:22px;border-radius:5px;color:var(--text3);font-size:12px;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 0.2s}
.channel-item:hover .channel-delete{opacity:1}
.channel-delete:hover{background:rgba(220,38,38,0.3);color:#ff5555}
.chat-main{display:flex;flex-direction:column;min-width:0}
.chat-header{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg)}
.chat-messages{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:14px}
.chat-message{display:flex;gap:12px;align-items:flex-start}
.msg-avatar{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;color:#fff;flex-shrink:0}
.msg-body{flex:1;min-width:0}
.msg-meta{display:flex;align-items:center;gap:8px;margin-bottom:5px;flex-wrap:wrap}
.msg-username{font-weight:700;font-size:13.5px}
.msg-time{font-size:11px;color:var(--text3);font-weight:600}
.msg-content{font-size:14px;line-height:1.55;word-wrap:break-word}
.chat-input-area{padding:16px 20px;border-top:1px solid var(--border);background:var(--bg)}
.chat-input-area form{display:flex;gap:10px;align-items:center}
.chat-input-area input{flex:1;margin:0;background:var(--bg2);border-color:transparent}
.members-list{padding:14px;overflow-y:auto;border-left:1px solid var(--border);background:var(--bg);width:200px}
.member-item{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:8px;font-size:13px;font-weight:600;color:var(--text1);margin-bottom:2px}
.member-item:hover{background:var(--bg2)}
.member-avatar{width:24px;height:24px;border-radius:7px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#fff;flex-shrink:0}
@media(max-width:900px){.sidebar{transform:translateX(-100%)}.main{margin-left:0}.content{padding:20px}.page-title{font-size:28px}.grid-2{grid-template-columns:1fr}.grid-scripts{grid-template-columns:1fr}.grid-servers{grid-template-columns:1fr}.chat-layout{grid-template-columns:1fr}.members-list{display:none}}
"""

# ==================== LAYOUT ====================
def render_page(title, page_title, content, user=None, active='dashboard', subtitle='', actions=''):
    is_admin = user and user['role'] == 'ADMIN'
    admin_link = '<div class="nav-label">Admin</div><a href="/admin" class="nav-item ' + ('active' if active=='admin' else '') + '">♛ Admin Panel</a>' if is_admin else ''
    user_html = ''
    if user:
        user_html = f'''<div class="sidebar-footer"><a href="/logout" class="user-card"><div class="user-avatar {'user-avatar-admin' if is_admin else ''}">{user['username'][0].upper()}</div><div><div class="user-name">{user['username']}</div><div class="user-role">{'♛ Admin' if is_admin else 'Member'}</div></div></a></div>'''
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · ScriptHub</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>{STYLES}</style></head><body>
<div class="layout">
<aside class="sidebar">
<div class="brand"><div class="brand-logo">ZK</div><div><div class="brand-name">ScriptHub</div><div class="brand-sub">By Zyrox-Kido</div></div></div>
<div class="nav-label">Workspace</div>
<a href="/" class="nav-item {'active' if active=='dashboard' else ''}">◈ Dashboard</a>
<a href="/create" class="nav-item {'active' if active=='create' else ''}">✦ Create Script</a>
<a href="/servers" class="nav-item {'active' if active=='servers' else ''}">🏠 Servers</a>
{admin_link}
{user_html}
</aside>
<div class="main">
<header class="topbar"><div class="topbar-title">{page_title}</div></header>
<div class="content">
<div class="page-title">{page_title}</div>
{f'<div class="page-sub">{subtitle}</div>' if subtitle else ''}
{actions}
{content}
</div></div></div>
<script>
function copyText(t){{navigator.clipboard.writeText(t).then(function(){{alert('✅ Copied!')}})}}
function confirmDelete(i,n){{if(confirm('Delete "'+n+'"?'))window.location.href='/delete/'+i}}
</script>
</body></html>'''

# ==================== AUTH ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter(db.func.lower(User.username) == request.form.get('username','').lower()).first()
        if not u or u.password != request.form.get('password',''):
            return redirect('/login?error=1')
        session['user_id'] = u.id
        return redirect('/')
    err = 'Invalid credentials' if request.args.get('error') else ''
    return f'''<!DOCTYPE html><html><head><title>Login · ScriptHub</title><style>{STYLES}</style></head><body>
<div class="login-wrap"><div class="login-card">
<div class="login-logo">ZK</div><div class="login-title">Welcome back</div><div class="login-sub">Sign in to continue</div>
<form method="POST"><input type="text" name="username" placeholder="Username" required autofocus>
<input type="password" name="password" placeholder="Password" required>
<button type="submit" class="btn btn-primary" style="width:100%">Sign In →</button></form>
<div class="login-err">{err}</div>
<a href="/register" class="login-link">Create account →</a>
</div></div></body></html>'''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        confirm = request.form.get('confirmPassword','')
        if password != confirm: return redirect('/register?error=1')
        if len(username) < 2 or len(password) < 4: return redirect('/register?error=2')
        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            return redirect('/register?error=3')
        role = 'ADMIN' if username == 'Z-K' else 'USER'
        db.session.add(User(username=username, password=password, role=role))
        db.session.commit()
        return redirect('/login')
    errs = {1:'Passwords do not match',2:'Min 2 chars user, 4 chars pass',3:'Username taken'}
    err = errs.get(int(request.args.get('error',0)),'')
    return f'''<!DOCTYPE html><html><head><title>Register · ScriptHub</title><style>{STYLES}</style></head><body>
<div class="login-wrap"><div class="login-card">
<div class="login-logo">ZK</div><div class="login-title">Create account</div><div class="login-sub">Join ScriptHub</div>
<form method="POST"><input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<input type="password" name="confirmPassword" placeholder="Confirm password" required>
<button type="submit" class="btn btn-primary" style="width:100%">Create Account →</button></form>
<div class="login-err">{err}</div>
<a href="/login" class="login-link">← Back to sign in</a>
</div></div></body></html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==================== DASHBOARD ====================
@app.route('/')
@require_login
def dashboard():
    u = User.query.get(session['user_id'])
    scripts = Script.query.filter_by(owner=u.username).order_by(Script.created_at.desc()).all()
    stats = f'''<div class="stat-grid">
    <div class="stat"><div class="stat-label">Total Scripts</div><div class="stat-value">{len(scripts)}</div></div>
    <div class="stat"><div class="stat-label">Role</div><div class="stat-value">{'Admin' if u.role=='ADMIN' else 'Member'}</div></div>
    <div class="stat"><div class="stat-label">Whitelist</div><div class="stat-value">{len([s for s in scripts if s.access_type=='whitelist'])}</div></div>
    </div>'''
    if not scripts:
        content = '<div class="empty"><div class="empty-icon">◈</div><div style="font-size:18px;font-weight:700;margin-bottom:8px;">No scripts yet</div><div style="color:var(--text2);margin-bottom:20px;">Create your first script</div><a href="/create" class="btn btn-primary">✦ Create Script</a></div>'
    else:
        base = get_base_url()
        cards = ''
        for s in scripts:
            try: count = len(json.loads(s.allowed_ids or '[]'))
            except: count = 0
            ls = f"loadstring(game:HttpGet('{base}/api/raw?id={s.short_id}'))()"
            badge = f'<span class="badge badge-yellow">🔒 Whitelist ({count})</span>' if s.access_type=='whitelist' else '<span class="badge badge-green">🌐 Public</span>'
            cards += f'''<div class="card">
<div style="display:flex;gap:14px;margin-bottom:16px;">
<div style="width:48px;height:48px;border-radius:13px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">◈</div>
<div><div style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:800;margin-bottom:8px;">{s.name}</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;">{badge}<span class="badge badge-purple">{s.version}</span></div></div></div>
<div class="copy-box" onclick="copyText(`{ls}`)">🔗 {ls} 📋</div>
<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;">
<button class="btn btn-primary btn-sm" onclick="copyText(`{ls}`)">📋 Loadstring</button>
<a href="/logs/{s.id}" class="btn btn-secondary btn-sm">📊 Logs</a>
<a href="/edit/{s.id}" class="btn btn-ghost btn-sm">✎ Edit</a>
<button class="btn btn-danger btn-sm" onclick="confirmDelete({s.id}, '{s.name}')">🗑</button>
</div></div>'''
        content = f'<div class="grid-scripts">{cards}</div>'
    actions = '<div style="margin-bottom:24px;"><a href="/create" class="btn btn-primary">✦ New Script</a></div>'
    return render_page('Dashboard', 'Dashboard', content, {'username': u.username, 'role': u.role}, 'dashboard', 'Manage your Lua scripts', actions)

# ==================== CREATE ====================
@app.route('/create', methods=['GET', 'POST'])
@require_login
def create_script():
    u = User.query.get(session['user_id'])
    if request.method == 'POST':
        allowed_ids = request.form.get('allowed_ids', '[]')
        try:
            p = json.loads(allowed_ids)
            allowed_ids = json.dumps([str(x).strip() for x in p if str(x).strip()])
        except: allowed_ids = '[]'
        s = Script(
            name=request.form.get('name','').strip(),
            short_id=make_short_id(),
            version=request.form.get('version','V1'),
            real_content=request.form.get('content',''),
            owner=u.username,
            access_type=request.form.get('access_type','public'),
            allowed_ids=allowed_ids
        )
        db.session.add(s)
        db.session.commit()
        return redirect('/')
    
    access_ui = '''
<div class="form-group"><label class="form-label">🔒 Access Type</label>
<select id="accessType" onchange="updateAccessUI()">
<option value="public">🌐 Public (Everyone)</option>
<option value="whitelist">🔒 Whitelist (Specific User IDs only)</option>
</select></div>
<div class="form-group" id="idListWrap" style="display:none;">
<label class="form-label">👤 Roblox User IDs</label>
<div id="idList">
<div class="id-row"><input type="text" class="id-input" placeholder="Roblox User ID" inputmode="numeric"><button type="button" onclick="removeIdRow(this)">×</button></div>
</div>
<button type="button" class="btn btn-success btn-sm" onclick="addIdRow()">+ Add User</button>
<div style="font-size:12px;color:var(--text3);margin-top:12px;line-height:1.6;">
💡 <b style="color:var(--red);">Ang User ID ay HINDI makikita ng player</b>.<br>
Kung hindi kasali sa listahan, <b>AUTO-KICK</b> ang player.
</div>
</div>
<input type="hidden" name="access_type" id="accessTypeHidden" value="public">
<input type="hidden" name="allowed_ids" id="allowedIdsHidden" value="[]">'''
    
    content = f'''<div class="card" style="max-width:920px;"><form method="POST" onsubmit="return prepareAccessSubmit()">
<div class="grid-2" style="margin-bottom:20px;">
<div class="form-group"><label class="form-label">📝 Script Name</label><input type="text" name="name" required autofocus placeholder="e.g., Fly UI"></div>
<div class="form-group"><label class="form-label">🏷 Version</label><select name="version">{''.join(f'<option value="V{i}">V{i}</option>' for i in range(1,51))}</select></div>
</div>
{access_ui}
<div class="form-group"><label class="form-label">📜 Lua Code</label><textarea name="content" required placeholder="-- Isulat ang Lua script dito..."></textarea></div>
<div style="display:flex;gap:12px;"><button type="submit" class="btn btn-primary">💾 Save Script</button><a href="/" class="btn btn-ghost">Cancel</a></div>
</form></div>
<script>
function updateAccessUI(){{document.getElementById('idListWrap').style.display=document.getElementById('accessType').value==='whitelist'?'block':'none';}}
function addIdRow(){{var l=document.getElementById('idList');var d=document.createElement('div');d.className='id-row';d.innerHTML='<input type="text" class="id-input" placeholder="Roblox User ID" inputmode="numeric"><button type="button" onclick="removeIdRow(this)">×</button>';l.appendChild(d);}}
function removeIdRow(b){{b.parentNode.remove();}}
function prepareAccessSubmit(){{
var s=document.getElementById('accessType');
document.getElementById('accessTypeHidden').value=s.value;
if(s.value==='whitelist'){{
var ids=[];document.querySelectorAll('.id-input').forEach(function(el){{var v=el.value.trim();if(v&&/^[0-9]+$/.test(v))ids.push(v)}});
if(ids.length===0){{alert('Add at least one User ID');return false;}}
document.getElementById('allowedIdsHidden').value=JSON.stringify(ids);
}} else document.getElementById('allowedIdsHidden').value='[]';
return true;
}}
</script>'''
    return render_page('Create', 'Create Script', content, {'username': u.username, 'role': u.role}, 'create', 'Add a new Lua script')

# ==================== EDIT ====================
@app.route('/edit/<int:sid>', methods=['GET', 'POST'])
@require_login
def edit_script(sid):
    u = User.query.get(session['user_id'])
    s = Script.query.get_or_404(sid)
    if s.owner != u.username and u.role != 'ADMIN': return 'Denied', 403
    if request.method == 'POST':
        s.name = request.form.get('name', s.name).strip()
        s.version = request.form.get('version', s.version)
        s.real_content = request.form.get('content', s.real_content)
        s.access_type = request.form.get('access_type', 'public')
        allowed_ids = request.form.get('allowed_ids', '[]')
        try:
            p = json.loads(allowed_ids)
            s.allowed_ids = json.dumps([str(x).strip() for x in p if str(x).strip()])
        except: s.allowed_ids = '[]'
        db.session.commit()
        return redirect('/')
    try: ids = json.loads(s.allowed_ids or '[]')
    except: ids = []
    at = s.access_type or 'public'
    base = get_base_url()
    ls = f"loadstring(game:HttpGet('{base}/api/raw?id={s.short_id}'))()"
    ids_html = ''.join(f'<div class="id-row"><input type="text" class="id-input" value="{i}" placeholder="Roblox User ID" inputmode="numeric"><button type="button" onclick="removeIdRow(this)">×</button></div>' for i in ids)
    if not ids_html: ids_html = '<div class="id-row"><input type="text" class="id-input" placeholder="Roblox User ID" inputmode="numeric"><button type="button" onclick="removeIdRow(this)">×</button></div>'
    escaped = s.real_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    content = f'''<div class="card" style="max-width:920px;">
<div class="copy-box" onclick="copyText(`{ls}`)" style="margin-bottom:20px;">🔗 {ls} 📋</div>
<form method="POST" onsubmit="return prepareAccessSubmit()">
<div class="form-group"><label class="form-label">📝 Script Name</label><input type="text" name="name" value="{s.name}" required></div>
<div class="form-group"><label class="form-label">🏷 Version</label><select name="version">{''.join(f'<option value="V{i}" {"selected" if f"V{i}"==s.version else ""}>V{i}</option>' for i in range(1,51))}</select></div>
<div class="form-group"><label class="form-label">🔒 Access Type</label>
<select id="accessType" onchange="updateAccessUI()">
<option value="public" {"selected" if at=="public" else ""}>🌐 Public</option>
<option value="whitelist" {"selected" if at=="whitelist" else ""}>🔒 Whitelist</option>
</select></div>
<div class="form-group" id="idListWrap" style="display:{"block" if at=="whitelist" else "none"};">
<label class="form-label">👤 Roblox User IDs</label>
<div id="idList">{ids_html}</div>
<button type="button" class="btn btn-success btn-sm" onclick="addIdRow()">+ Add User</button>
</div>
<input type="hidden" name="access_type" id="accessTypeHidden" value="{at}">
<input type="hidden" name="allowed_ids" id="allowedIdsHidden" value="[]">
<div class="form-group"><label class="form-label">📜 Lua Code</label><textarea name="content" required style="min-height:400px;">{escaped}</textarea></div>
<div style="display:flex;gap:12px;"><button type="submit" class="btn btn-primary">💾 Save Changes</button><a href="/" class="btn btn-ghost">Cancel</a></div>
</form></div>
<script>
function updateAccessUI(){{document.getElementById('idListWrap').style.display=document.getElementById('accessType').value==='whitelist'?'block':'none';}}
function addIdRow(){{var l=document.getElementById('idList');var d=document.createElement('div');d.className='id-row';d.innerHTML='<input type="text" class="id-input" placeholder="Roblox User ID" inputmode="numeric"><button type="button" onclick="removeIdRow(this)">×</button>';l.appendChild(d);}}
function removeIdRow(b){{b.parentNode.remove();}}
function prepareAccessSubmit(){{
var s=document.getElementById('accessType');
document.getElementById('accessTypeHidden').value=s.value;
if(s.value==='whitelist'){{
var ids=[];document.querySelectorAll('.id-input').forEach(function(el){{var v=el.value.trim();if(v&&/^[0-9]+$/.test(v))ids.push(v)}});
document.getElementById('allowedIdsHidden').value=JSON.stringify(ids);
}} else document.getElementById('allowedIdsHidden').value='[]';
return true;
}}
</script>'''
    return render_page('Edit', 'Edit Script', content, {'username': u.username, 'role': u.role}, 'dashboard', s.name)

# ==================== DELETE SCRIPT ====================
@app.route('/delete/<int:sid>')
@require_login
def delete_script(sid):
    u = User.query.get(session['user_id'])
    s = Script.query.get_or_404(sid)
    if s.owner != u.username and u.role != 'ADMIN': return 'Denied', 403
    ExecutionLog.query.filter_by(script_id=s.id).delete()
    db.session.delete(s)
    db.session.commit()
    return redirect('/')

# ==================== SERVER (AUTO-INJECT ID CHECK) ====================
@app.route('/api/raw')
def api_raw():
    short_id = request.args.get('id')
    if not short_id: return '-- [ScriptHub] Invalid request --', 400
    s = Script.query.filter_by(short_id=short_id).first()
    if not s: return '-- [ScriptHub] Script not found --', 404
    
    if s.access_type == 'whitelist':
        try: allowed_ids = json.loads(s.allowed_ids or '[]')
        except: allowed_ids = []
        if not allowed_ids: return '-- [ScriptHub] No IDs --', 403
        ids_lua = ', '.join(str(i) for i in allowed_ids)
        injected = f'''-- ============================================
-- AUTO KICK (Injected by ScriptHub Server)
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
-- ORIGINAL SCRIPT
-- ============================================

'''
        return injected + s.real_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    return s.real_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

# ==================== LOGS ====================
@app.route('/logs/<int:sid>')
@require_login
def view_logs(sid):
    u = User.query.get(session['user_id'])
    s = Script.query.get_or_404(sid)
    if s.owner != u.username and u.role != 'ADMIN': return 'Denied', 403
    logs = ExecutionLog.query.filter_by(script_id=s.id).order_by(ExecutionLog.created_at.desc()).limit(200).all()
    total = len(logs)
    allowed_count = len([l for l in logs if l.allowed])
    kicked_count = len([l for l in logs if l.kicked])
    stats = f'''<div class="stat-grid">
    <div class="stat"><div class="stat-label">Total</div><div class="stat-value">{total}</div></div>
    <div class="stat"><div class="stat-label">✓ Allowed</div><div class="stat-value" style="color:#4ade80">{allowed_count}</div></div>
    <div class="stat"><div class="stat-label">🚫 Kicked</div><div class="stat-value" style="color:#ff5555">{kicked_count}</div></div>
    </div>'''
    if not logs:
        content = stats + '<div class="empty"><div class="empty-icon">📊</div><div style="font-size:18px;font-weight:700;margin-bottom:8px;">No logs yet</div></div>'
    else:
        rows = ''
        for l in logs:
            cls = 'allowed' if l.allowed else 'kicked'
            icon = '✓' if l.allowed else '✗'
            badge = '<span class="badge badge-green">✓ Allowed</span>' if l.allowed else '<span class="badge badge-red">🚫 Kicked</span>'
            rows += f'''<div class="log-item log-{cls}">
<div class="log-icon {cls}">{icon}</div>
<div style="flex:1;"><div style="font-weight:700;font-size:14px;">{l.username or 'Unknown'} <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text3);">({l.user_id})</span></div>
<div style="font-size:11.5px;color:var(--text3);margin-top:3px;">{l.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div></div>
{badge}</div>'''
        content = stats + rows
    actions = f'<div style="margin-bottom:20px;display:flex;gap:10px;"><a href="/edit/{s.id}" class="btn btn-ghost btn-sm">← Back</a><button onclick="location.reload()" class="btn btn-secondary btn-sm">🔄 Refresh</button></div>'
    return render_page('Logs', 'Execution Logs', content, {'username': u.username, 'role': u.role}, 'dashboard', s.name, actions)

# ==================== ADMIN ====================
@app.route('/admin')
@require_admin
def admin_panel():
    u = User.query.get(session['user_id'])
    users = User.query.order_by(User.id.desc()).all()
    rows = ''
    for x in users:
        is_a = x.role == 'ADMIN'
        cnt = Script.query.filter_by(owner=x.username).count()
        rows += f'''<div class="card" style="display:flex;align-items:center;gap:16px;">
<div class="user-avatar {'user-avatar-admin' if is_a else ''}">{x.username[0].upper()}</div>
<div style="flex:1;"><div style="font-weight:700;font-size:15px;">{x.username} <span class="badge {'badge-admin' if is_a else 'badge-purple'}">{'♛ Admin' if is_a else 'Member'}</span></div>
<div style="font-size:12px;color:var(--text2);margin-top:4px;">{cnt} scripts</div></div></div>'''
    content = rows or '<div class="empty"><div class="empty-icon">◉</div><div>No users</div></div>'
    return render_page('Admin', 'Admin Panel', content, {'username': u.username, 'role': u.role}, 'admin', f'{len(users)} users')

# ==================== START ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
# ==================== PART 2A: SERVERS LIST + CREATE + JOIN ====================

@app.route('/servers')
@require_login
def servers_list():
    u = User.query.get(session['user_id'])
    my_servers = Server.query.filter(
        (Server.owner == u.username) | 
        (Server.id.in_(db.session.query(ServerMember.server_id).filter_by(username=u.username)))
    ).order_by(Server.created_at.desc()).all()
    
    if not my_servers:
        content = '<div class="empty"><div class="empty-icon">🏠</div><div style="font-size:18px;font-weight:700;margin-bottom:8px;">No servers yet</div><div style="color:var(--text2);margin-bottom:20px;">Create your first server or join with an invite code</div></div>'
    else:
        cards = ''
        for s in my_servers:
            member_count = ServerMember.query.filter_by(server_id=s.id).count()
            is_owner = s.owner == u.username
            owner_badge = '<span class="badge badge-yellow">👑 Owner</span>' if is_owner else '<span class="badge badge-purple">Member</span>'
            cards += f'''<div class="card" style="cursor:pointer;" onclick="window.location.href='/server/{s.id}'">
<div style="display:flex;gap:14px;margin-bottom:14px;">
<div style="width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,var(--red),var(--red2));display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">{s.icon}</div>
<div><div style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:800;margin-bottom:8px;">{s.name}</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;">{owner_badge}<span class="badge badge-purple">{member_count} members</span></div></div></div>
<div class="copy-box" onclick="event.stopPropagation();copyText('{s.invite_code}')">🔑 Invite: {s.invite_code} 📋</div>
<div style="display:flex;gap:8px;margin-top:14px;">
<a href="/server/{s.id}" class="btn btn-primary btn-sm" style="flex:1;" onclick="event.stopPropagation();">Open Server</a>
</div></div>'''
        content = f'<div class="grid-servers">{cards}</div>'
    
    actions = '''<div style="margin-bottom:24px;display:flex;gap:10px;flex-wrap:wrap;">
<button class="btn btn-primary" onclick="document.getElementById('createServerModal').style.display='flex'">➕ Create Server</button>
<button class="btn btn-secondary" onclick="document.getElementById('joinServerModal').style.display='flex'">🔗 Join Server</button>
</div>

<div id="createServerModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(8px);z-index:1000;align-items:center;justify-content:center;padding:20px;">
<div class="card" style="width:460px;max-width:100%;">
<div style="font-size:20px;font-weight:800;margin-bottom:20px;">Create Server</div>
<div class="form-group"><label class="form-label">Server Name</label><input type="text" id="newServerName" placeholder="My Server"></div>
<div class="form-group"><label class="form-label">Icon (Emoji)</label><input type="text" id="newServerIcon" value="🎮" maxlength="2"></div>
<div style="display:flex;gap:10px;justify-content:flex-end;">
<button class="btn btn-ghost" onclick="document.getElementById('createServerModal').style.display='none'">Cancel</button>
<button class="btn btn-primary" onclick="createServer()">Create</button>
</div></div></div>

<div id="joinServerModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(8px);z-index:1000;align-items:center;justify-content:center;padding:20px;">
<div class="card" style="width:460px;max-width:100%;">
<div style="font-size:20px;font-weight:800;margin-bottom:20px;">Join Server</div>
<div class="form-group"><label class="form-label">Invite Code</label><input type="text" id="joinInviteCode" placeholder="Paste invite code here"></div>
<div style="display:flex;gap:10px;justify-content:flex-end;">
<button class="btn btn-ghost" onclick="document.getElementById('joinServerModal').style.display='none'">Cancel</button>
<button class="btn btn-primary" onclick="joinServer()">Join</button>
</div></div></div>

<script>
async function createServer(){
    const name = document.getElementById('newServerName').value.trim();
    const icon = document.getElementById('newServerIcon').value.trim() || '🎮';
    if(!name) return alert('Name required');
    const r = await fetch('/api/servers/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,icon})});
    const d = await r.json();
    if(d.id) window.location.href = '/server/'+d.id;
    else alert(d.error || 'Error');
}
async function joinServer(){
    const code = document.getElementById('joinInviteCode').value.trim();
    if(!code) return alert('Code required');
    const r = await fetch('/api/servers/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invite_code:code})});
    const d = await r.json();
    if(d.id) window.location.href = '/server/'+d.id;
    else alert(d.error || 'Invalid code');
}
</script>'''
    
    return render_page('Servers', 'Servers', content, {'username': u.username, 'role': u.role}, 'servers', 'Your Discord-style servers', actions)

@app.route('/api/servers/create', methods=['POST'])
@require_login
def api_create_server():
    u = User.query.get(session['user_id'])
    data = request.get_json() or {}
    name = data.get('name', '').strip()[:100]
    icon = data.get('icon', '🎮')[:2] or '🎮'
    if len(name) < 2:
        return {'error': 'Name too short'}, 400
    invite = make_invite_code()
    s = Server(name=name, owner=u.username, invite_code=invite, icon=icon)
    db.session.add(s)
    db.session.flush()
    db.session.add(ServerMember(server_id=s.id, username=u.username, role='OWNER'))
    db.session.add(Channel(server_id=s.id, name='general', type='text', created_by=u.username))
    db.session.commit()
    return {'id': s.id, 'invite_code': invite}

@app.route('/api/servers/join', methods=['POST'])
@require_login
def api_join_server():
    u = User.query.get(session['user_id'])
    data = request.get_json() or {}
    code = data.get('invite_code', '').strip()
    s = Server.query.filter_by(invite_code=code).first()
    if not s:
        return {'error': 'Invalid code'}, 404
    existing = ServerMember.query.filter_by(server_id=s.id, username=u.username).first()
    if not existing:
        db.session.add(ServerMember(server_id=s.id, username=u.username))
        db.session.commit()
    return {'id': s.id}

# ==================== END PART 2A ====================

# ==================== PART 2B: SERVER VIEW + CHANNELS + DELETE + CHAT ====================

@app.route('/server/<int:sid>')
@require_login
def server_view(sid):
    u = User.query.get(session['user_id'])
    s = Server.query.get_or_404(sid)
    is_owner = s.owner == u.username
    is_admin = u.role == 'ADMIN'
    member = ServerMember.query.filter_by(server_id=s.id, username=u.username).first()
    if not member and not is_owner and not is_admin:
        return redirect('/servers')

    channels = Channel.query.filter_by(server_id=s.id).order_by(Channel.id.asc()).all()
    members = ServerMember.query.filter_by(server_id=s.id).all()
    can_manage = is_owner or is_admin

    channels_html = ''
    for c in channels:
        icon = '#' if c.type == 'text' else '🔊'
        delete_btn = ''
        if can_manage:
            delete_btn = f'<button class="channel-delete" onclick="event.stopPropagation();deleteChannel({c.id})" title="Delete Channel">🗑</button>'
        channels_html += f'''<div class="channel-item" data-channel-id="{c.id}" data-channel-name="{c.name}" data-channel-type="{c.type}" onclick="switchChannel({c.id}, '{c.name}', '{c.type}')">
<div class="channel-item-left"><span style="color:var(--text3);">{icon}</span><span class="channel-name">{c.name}</span></div>
{delete_btn}
</div>'''

    members_html = ''
    for m in members:
        mu = User.query.filter(db.func.lower(User.username) == m.username.lower()).first()
        role = mu.role if mu else 'USER'
        badge = '👑' if m.role == 'OWNER' else ('♛' if role == 'ADMIN' else '')
        members_html += f'''<div class="member-item"><div class="member-avatar">{m.username[0].upper()}</div><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{m.username}</span><span style="font-size:11px;">{badge}</span></div>'''

    content = f'''<div class="chat-layout">
<div class="chat-sidebar">
<div class="chat-sidebar-header"><div style="display:flex;align-items:center;gap:10px;min-width:0;"><span style="font-size:22px;">{s.icon}</span><span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{s.name}</span></div></div>
<div class="channel-group-label"><span>💬 CHANNELS</span>{'<button onclick="openCreateChannel()">+</button>' if can_manage else ''}</div>
<div id="channelsList">{channels_html}</div>
<div style="margin-top:auto;padding:14px;border-top:1px solid var(--border);">
<div class="copy-box" onclick="copyText('{s.invite_code}')">🔑 {s.invite_code} 📋</div>
<a href="/servers" style="display:block;text-align:center;color:var(--text2);font-size:12px;font-weight:700;padding:10px;margin-top:8px;">← All Servers</a>
</div>
</div>
<div class="chat-main">
<div class="chat-header"><div style="display:flex;align-items:center;gap:8px;"><span style="color:var(--text3);font-size:18px;" id="currentChannelIcon">#</span><span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:15px;" id="currentChannelName">Select a channel</span></div></div>
<div class="chat-messages" id="chatMessages"><div style="text-align:center;color:var(--text3);padding:40px;">Select a channel to start chatting</div></div>
<div class="chat-input-area"><form id="chatForm" onsubmit="event.preventDefault();sendMessage();"><input type="text" id="chatInput" placeholder="Message..." maxlength="500" autocomplete="off"><button type="submit" class="btn btn-primary">➤</button></form></div>
</div>
<div class="members-list">
<div style="font-size:11px;font-weight:800;color:var(--text3);text-transform:uppercase;letter-spacing:1px;padding:8px;">Members ({len(members)})</div>
{members_html}
</div>
</div>

<div id="createChannelModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(8px);z-index:1000;align-items:center;justify-content:center;padding:20px;">
<div class="card" style="width:420px;max-width:100%;">
<div style="font-size:20px;font-weight:800;margin-bottom:20px;">Create Channel</div>
<div class="form-group"><label class="form-label">Channel Name</label><input type="text" id="newChannelName" placeholder="e.g., general"></div>
<div class="form-group"><label class="form-label">Type</label><select id="newChannelType"><option value="text">💬 Text</option><option value="voice">🔊 Voice</option></select></div>
<div style="display:flex;gap:10px;justify-content:flex-end;">
<button class="btn btn-ghost" onclick="document.getElementById('createChannelModal').style.display='none'">Cancel</button>
<button class="btn btn-primary" onclick="createChannel()">Create</button>
</div></div></div>

<script>
const SERVER_ID = {sid};
const CURRENT_USER = {json.dumps(u.username)};
let currentChannelId = null;

function openCreateChannel(){{document.getElementById('createChannelModal').style.display = 'flex';}}

async function createChannel(){{
    const name = document.getElementById('newChannelName').value.trim();
    const type = document.getElementById('newChannelType').value;
    if(!name) return alert('Name required');
    const r = await fetch('/api/servers/'+SERVER_ID+'/channels', {{method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify({{name:name, type:type}})}});
    const d = await r.json();
    if(d.id){{
        addChannelToSidebar(d);
        document.getElementById('createChannelModal').style.display = 'none';
        document.getElementById('newChannelName').value = '';
    }} else alert(d.error || 'Error');
}}

function addChannelToSidebar(c){{
    const list = document.getElementById('channelsList');
    const icon = c.type === 'text' ? '#' : '🔊';
    const div = document.createElement('div');
    div.className = 'channel-item';
    div.dataset.channelId = c.id;
    div.dataset.channelName = c.name;
    div.dataset.channelType = c.type;
    div.onclick = function(){{ switchChannel(c.id, c.name, c.type); }};
    div.innerHTML = '<div class="channel-item-left"><span style="color:var(--text3);">'+icon+'</span><span class="channel-name">'+c.name+'</span></div><button class="channel-delete" onclick="event.stopPropagation();deleteChannel('+c.id+')" title="Delete Channel">🗑</button>';
    list.appendChild(div);
}}

async function deleteChannel(id){{
    if(!confirm('Delete this channel?')) return;
    const r = await fetch('/api/channels/'+id+'/delete', {{method:'POST'}});
    const d = await r.json();
    if(d.success){{
        const el = document.querySelector('.channel-item[data-channel-id="'+id+'"]');
        if(el) el.remove();
        if(currentChannelId === id){{
            currentChannelId = null;
            document.getElementById('chatMessages').innerHTML = '<div style="text-align:center;color:var(--text3);padding:40px;">Select a channel</div>';
            document.getElementById('currentChannelName').textContent = 'Select a channel';
        }}
    }} else alert(d.error || 'Error');
}}

async function switchChannel(id, name, type){{
    currentChannelId = id;
    document.querySelectorAll('.channel-item').forEach(function(el){{el.classList.remove('active');}});
    const el = document.querySelector('.channel-item[data-channel-id="'+id+'"]');
    if(el) el.classList.add('active');
    document.getElementById('currentChannelName').textContent = name;
    document.getElementById('currentChannelIcon').textContent = type === 'voice' ? '🔊' : '#';
    document.getElementById('chatMessages').innerHTML = '<div style="text-align:center;color:var(--text3);padding:20px;">Loading...</div>';
    const r = await fetch('/api/channels/'+id+'/messages');
    const msgs = await r.json();
    renderMessages(msgs);
}}

function renderMessages(msgs){{
    const box = document.getElementById('chatMessages');
    if(msgs.length === 0){{
        box.innerHTML = '<div style="text-align:center;color:var(--text3);padding:40px;">No messages yet. Say hi! 👋</div>';
        return;
    }}
    box.innerHTML = '';
    msgs.forEach(function(m){{
        const isAdmin = m.role === 'ADMIN';
        const av = isAdmin ? 'linear-gradient(135deg,#ffaa00,#ff6600)' : 'linear-gradient(135deg,var(--red),var(--red2))';
        const div = document.createElement('div');
        div.className = 'chat-message';
        div.innerHTML = '<div class="msg-avatar" style="background:'+av+';">'+m.username[0].toUpperCase()+'</div><div class="msg-body"><div class="msg-meta"><span class="msg-username">'+m.username+'</span>'+(isAdmin?'<span class="badge badge-admin">♛ Admin</span>':'')+'<span class="msg-time">'+m.created_at+'</span></div><div class="msg-content">'+m.message+'</div></div>';
        box.appendChild(div);
    }});
    box.scrollTop = box.scrollHeight;
}}

async function sendMessage(){{
    if(!currentChannelId) return;
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if(!msg) return;
    await fetch('/api/channels/'+currentChannelId+'/send', {{method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify({{message: msg}})}});
    input.value = '';
    switchChannel(currentChannelId, document.getElementById('currentChannelName').textContent, document.getElementById('currentChannelIcon').textContent === '🔊' ? 'voice' : 'text');
}}

setInterval(function(){{
    if(currentChannelId) switchChannel(currentChannelId, document.getElementById('currentChannelName').textContent, document.getElementById('currentChannelIcon').textContent === '🔊' ? 'voice' : 'text');
}}, 5000);
</script>'''

    return render_page(s.name, s.name, content, {'username': u.username, 'role': u.role}, 'servers', f'{len(members)} members')

@app.route('/api/servers/<int:sid>/channels', methods=['POST'])
@require_login
def api_create_channel(sid):
    u = User.query.get(session['user_id'])
    s = Server.query.get_or_404(sid)
    is_owner = s.owner == u.username
    is_admin = u.role == 'ADMIN'
    if not is_owner and not is_admin:
        return {'error': 'Only owner can create channels'}, 403
    data = request.get_json() or {}
    name = data.get('name', '').strip().lower().replace(' ', '-')[:30]
    ctype = data.get('type', 'text')
    if not name:
        return {'error': 'Name required'}, 400
    if Channel.query.filter_by(server_id=sid, name=name).first():
        return {'error': 'Channel exists'}, 400
    c = Channel(server_id=sid, name=name, type=ctype, created_by=u.username)
    db.session.add(c)
    db.session.commit()
    return {'id': c.id, 'name': c.name, 'type': c.type}

@app.route('/api/channels/<int:cid>/delete', methods=['POST'])
@require_login
def api_delete_channel(cid):
    u = User.query.get(session['user_id'])
    c = Channel.query.get_or_404(cid)
    s = Server.query.get_or_404(c.server_id)
    is_owner = s.owner == u.username
    is_admin = u.role == 'ADMIN'
    if not is_owner and not is_admin:
        return {'error': 'Only owner can delete channels'}, 403
    ChatMessage.query.filter_by(channel_id=c.id).delete()
    db.session.delete(c)
    db.session.commit()
    return {'success': True}

@app.route('/api/channels/<int:cid>/messages')
@require_login
def api_channel_messages(cid):
    c = Channel.query.get_or_404(cid)
    u = User.query.get(session['user_id'])
    s = Server.query.get_or_404(c.server_id)
    member = ServerMember.query.filter_by(server_id=s.id, username=u.username).first()
    if not member and s.owner != u.username and u.role != 'ADMIN':
        return {'error': 'Not a member'}, 403
    msgs = ChatMessage.query.filter_by(channel_id=cid).order_by(ChatMessage.created_at.desc()).limit(100).all()
    result = []
    for m in reversed(msgs):
        result.append({'username': m.username, 'role': m.role, 'message': m.message, 'created_at': m.created_at.strftime('%H:%M')})
    return result

@app.route('/api/channels/<int:cid>/send', methods=['POST'])
@require_login
def api_send_message(cid):
    u = User.query.get(session['user_id'])
    c = Channel.query.get_or_404(cid)
    s = Server.query.get_or_404(c.server_id)
    member = ServerMember.query.filter_by(server_id=s.id, username=u.username).first()
    if not member and s.owner != u.username and u.role != 'ADMIN':
        return {'error': 'Not a member'}, 403
    data = request.get_json() or {}
    msg = data.get('message', '').strip()[:500]
    if not msg:
        return {'error': 'Empty message'}, 400
    m = ChatMessage(channel_id=cid, username=u.username, role=u.role, message=msg)
    db.session.add(m)
    db.session.commit()
    return {'success': True}

# ==================== END PART 2B ====================
