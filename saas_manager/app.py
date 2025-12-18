import docker
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text # (+) Import baru untuk baca DB Etherpad
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci_rahasia_proyek_akhir'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas.db'

# (+) Konfigurasi koneksi ke DB Etherpad (Postgres)
# Menggunakan nama service 'postgres-db' sesuai docker-compose
ETHERPAD_DB_URI = "postgresql://admin:password_rahasia@postgres-db:5432/etherpad_db"

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

docker_client = docker.from_env()

# --- Model User (SaaS Manager DB) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    container_port = db.Column(db.Integer, nullable=True)
    container_id = db.Column(db.String(100), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_free_port():
    used_ports = [user.container_port for user in User.query.filter(User.container_port != None).all()]
    for port in range(9001, 9100):
        if port not in used_ports:
            return port
    return None

# (+) Fungsi Baru: Mengambil Daftar Semua Pad dari DB Pusat
def get_all_global_pads():
    try:
        engine = create_engine(ETHERPAD_DB_URI)
        with engine.connect() as connection:
            # Query tabel 'store' milik Etherpad
            # Key format di Etherpad adalah "pad:nama_pad"
            query = text("SELECT key FROM store WHERE key LIKE 'pad:%' AND key NOT LIKE 'pad:%:%'") 
            result = connection.execute(query)
            
            pads = []
            for row in result:
                # row[0] misal "pad:proyek_rahasia", kita ambil "proyek_rahasia"
                pad_name = row[0].split(':')[1]
                pads.append(pad_name)
            return pads
    except Exception as e:
        print(f"Error reading pads: {e}")
        return []

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login gagal.')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # (+) Ambil daftar Pad Global
    global_pads = get_all_global_pads()
    
    # Ambil port user sendiri agar linknya benar
    my_port = current_user.container_port if current_user.container_port else 9001

    if current_user.role == 'admin':
        users = User.query.filter_by(role='user').all()
        return render_template('dashboard.html', user=current_user, tenants=users, pads=global_pads, port=my_port)
    else:
        return render_template('dashboard.html', user=current_user, pads=global_pads, port=my_port)

@app.route('/add_tenant', methods=['POST'])
@login_required
def add_tenant():
    if current_user.role != 'admin': return "Access Denied", 403
    username = request.form.get('username')
    password = request.form.get('password')

    if User.query.filter_by(username=username).first():
        flash("Username sudah dipakai!")
        return redirect(url_for('dashboard'))
    
    assigned_port = get_free_port()
    if not assigned_port:
        flash("Port penuh!")
        return redirect(url_for('dashboard'))

    try:
        container_name = f"etherpad_tenant_{username}"
        container = docker_client.containers.run(
            image="my-etherpad-saas",
            detach=True,
            ports={'9001/tcp': assigned_port},
            environment=[
                f"ETHERPAD_TITLE=Workspace {username}",
                "DB_TYPE=postgres",
                "DB_HOST=postgres-db",
                "DB_PORT=5432",
                "DB_NAME=etherpad_db",
                "DB_USER=admin",
                "DB_PASS=password_rahasia"
            ],
            # (+) VOLUME SHARING: Semua tenant berbagi folder upload yang sama
            volumes={
                'etherpad_uploads': {'bind': '/opt/etherpad-lite/var', 'mode': 'rw'}
            },
            name=container_name,
            network="saas-network"
        )
        
        new_user = User(username=username, password=password, role='user', container_port=assigned_port, container_id=container.id)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Tenant {username} sukses!')
        
    except Exception as e:
        flash(f'Gagal: {str(e)}')

    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='admin123', role='admin'))
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)