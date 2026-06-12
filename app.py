from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import io
from flask import send_file, send_from_directory

app = Flask(__name__)

# ==================== KONFIGURASI CORS ====================
CORS(app)

# ==================== KONFIGURASI DATABASE ====================
DATABASE_URL = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:@localhost/gdb_cash_db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# ==================== MODEL ====================

class User(db.Model):
    __tablename__ = 'users'
    id_user = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('Admin', 'Ketua', 'Bendahara', 'Anggota Umum'), nullable=False)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    no_hp = db.Column(db.String(20))
    foto = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

class PeriodeAktif(db.Model):
    __tablename__ = 'periode_aktif'
    id_periode = db.Column(db.Integer, primary_key=True)
    nama_periode = db.Column(db.String(20), nullable=False)
    tahun = db.Column(db.String(20), nullable=False)
    status_periode = db.Column(db.Enum('Aktif', 'Nonaktif'), default='Nonaktif')

class KategoriProgram(db.Model):
    __tablename__ = 'kategori_program'
    id_kategori = db.Column(db.Integer, primary_key=True)
    nama_kategori = db.Column(db.String(50), nullable=False)
    deskripsi_kategori = db.Column(db.Text)
    status = db.Column(db.Enum('Aktif', 'Nonaktif'), default='Aktif')

class ProgramKerja(db.Model):
    __tablename__ = 'program_kerja'
    id_program = db.Column(db.Integer, primary_key=True)
    nama_program = db.Column(db.String(100), nullable=False)
    deskripsi_program = db.Column(db.Text)
    periode = db.Column(db.String(20))
    kategori = db.Column(db.String(100))
    status_program = db.Column(db.Enum('Rencana', 'Berjalan', 'Selesai', 'Batal'), default='Rencana')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RabDinamis(db.Model):
    __tablename__ = 'rab_dinamis'
    id_rab = db.Column(db.Integer, primary_key=True)
    id_program = db.Column(db.Integer, db.ForeignKey('program_kerja.id_program'), nullable=False)
    nama_biaya = db.Column(db.String(100), nullable=False)
    biaya_minimal = db.Column(db.Numeric(15,2), default=0)
    biaya_maksimal = db.Column(db.Numeric(15,2), default=0)
    realisasi = db.Column(db.Numeric(15,2), default=0)
    sisa = db.Column(db.Numeric(15,2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RAB(db.Model):
    __tablename__ = 'rab'
    id_rab = db.Column(db.Integer, primary_key=True)
    id_program = db.Column(db.Integer, db.ForeignKey('program_kerja.id_program'), nullable=False)
    nama_item = db.Column(db.String(150), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False, default=1)
    harga_satuan = db.Column(db.Numeric(15,2), nullable=False, default=0)
    keterangan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    program = db.relationship('ProgramKerja', backref='rab_items')

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id_transaksi = db.Column(db.Integer, primary_key=True)
    id_program = db.Column(db.Integer, db.ForeignKey('program_kerja.id_program'), nullable=False)
    id_pengguna = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    id_kategori = db.Column(db.Integer, db.ForeignKey('kategori_program.id_kategori'))
    jenis = db.Column(db.Enum('Masuk', 'Keluar'), nullable=False)
    nominal = db.Column(db.Numeric(15,2), nullable=False)
    tanggal = db.Column(db.Date, nullable=False)
    keterangan = db.Column(db.Text)
    bukti_file = db.Column(db.String(255))
    status_validasi = db.Column(db.Enum('Valid', 'Pending', 'Tidak Valid'), default='Valid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PengajuanTransaksi(db.Model):
    __tablename__ = 'pengajuan_transaksi'
    id_pengajuan = db.Column(db.Integer, primary_key=True)
    id_transaksi = db.Column(db.Integer, db.ForeignKey('transaksi.id_transaksi'))
    id_pengguna = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    alasan = db.Column(db.Text)
    status = db.Column(db.Enum('Menunggu', 'Disetujui', 'Ditolak'), default='Menunggu')
    catatan_penolakan = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)

class KatalogBiaya(db.Model):
    __tablename__ = 'katalog_biaya'
    id_biaya = db.Column(db.Integer, primary_key=True)
    nama_biaya = db.Column(db.String(100), nullable=False)
    biaya_minimal = db.Column(db.Numeric(15,2), default=0)
    biaya_maksimal = db.Column(db.Numeric(15,2), default=0)
    deskripsi_biaya = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LogAktivitas(db.Model):
    __tablename__ = 'log_aktivitas'
    id_log = db.Column(db.Integer, primary_key=True)
    id_pengguna = db.Column(db.Integer, db.ForeignKey('users.id_user'))
    aktivitas = db.Column(db.String(50))
    deskripsi = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    waktu = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== HELPER: CATAT LOG ====================

def catat_log(id_pengguna, aktivitas, deskripsi):
    """Helper untuk mencatat log aktivitas"""
    try:
        log_entry = LogAktivitas(
            id_pengguna=id_pengguna,
            aktivitas=aktivitas,
            deskripsi=deskripsi,
            ip_address=request.remote_addr
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Gagal mencatat log: {e}")

# ==================== ENDPOINT HEALTH ====================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'success', 'message': 'Backend running!'})

# ==================== ENDPOINT AKSES FILE UPLOAD ====================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== ENDPOINT LOGIN ====================

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, deleted_at=None).first()
    
    if not user:
        return jsonify({'status': 'error', 'message': 'Username tidak ditemukan'}), 401
    
    if user.password != password:
        return jsonify({'status': 'error', 'message': 'Password salah'}), 401
    
    catat_log(user.id_user, 'Login', f'User {user.username} berhasil login')
    
    return jsonify({
        'status': 'success',
        'message': 'Login berhasil',
        'user': {
            'id_user': user.id_user,
            'username': user.username,
            'nama_lengkap': user.nama_lengkap,
            'role': user.role,
            'email': user.email,
            'no_hp': user.no_hp
        }
    })

# ==================== ENDPOINT LOGOUT ====================

@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.get_json() or {}
    id_pengguna = data.get('id_pengguna')
    
    if id_pengguna:
        user = User.query.get(id_pengguna)
        if user:
            catat_log(id_pengguna, 'Logout', f'User {user.username} logout')
    
    return jsonify({'status': 'success', 'message': 'Logout berhasil'})

# ==================== ENDPOINT LOGS (PAGINATION) ====================

@app.route('/api/logs', methods=['GET'])
def get_logs():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    query = LogAktivitas.query.order_by(LogAktivitas.waktu.desc())
    total = query.count()
    total_pages = max(1, (total + limit - 1) // limit)
    
    logs = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for log in logs:
        user = User.query.get(log.id_pengguna) if log.id_pengguna else None
        result.append({
            'id_log': log.id_log,
            'waktu': log.waktu.strftime('%Y-%m-%d %H:%M:%S') if log.waktu else None,
            'pengguna': user.nama_lengkap if user else 'System',
            'aktivitas': log.aktivitas,
            'deskripsi': log.deskripsi,
            'ip_address': log.ip_address
        })
    
    return jsonify({
        'status': 'success',
        'data': result,
        'total': total,
        'total_pages': total_pages,
        'current_page': page
    })

# ==================== ENDPOINT PROGRAM KERJA ====================

@app.route('/api/program-kerja', methods=['GET'])
def get_all_program_kerja():
    periode_filter = request.args.get('periode')
    
    if periode_filter:
        programs = ProgramKerja.query.filter_by(periode=periode_filter).all()
    else:
        programs = ProgramKerja.query.all()
    
    result = []
    for p in programs:
        result.append({
            'id_program': p.id_program,
            'nama_program': p.nama_program,
            'deskripsi_program': p.deskripsi_program,
            'periode': p.periode,
            'kategori': p.kategori,
            'status_program': p.status_program
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/program-kerja', methods=['POST'])
def create_program_kerja():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    new_program = ProgramKerja(
        nama_program=data['nama_program'],
        deskripsi_program=data.get('deskripsi_program', ''),
        periode=data.get('periode', ''),
        kategori=data.get('kategori', ''),
        status_program=data.get('status', 'Rencana'),
        created_by=id_pengguna
    )
    db.session.add(new_program)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah program kerja: {data["nama_program"]}')
    
    return jsonify({'status': 'success', 'message': 'Program kerja berhasil ditambahkan'})

@app.route('/api/program-kerja/<int:id_program>', methods=['PUT'])
def update_program_kerja(id_program):
    program = ProgramKerja.query.get(id_program)
    if not program:
        return jsonify({'status': 'error', 'message': 'Program tidak ditemukan'}), 404
    
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    nama_lama = program.nama_program
    status_lama = program.status_program
    
    program.nama_program = data.get('nama_program', program.nama_program)
    program.deskripsi_program = data.get('deskripsi_program', program.deskripsi_program)
    program.periode = data.get('periode', program.periode)
    program.kategori = data.get('kategori', program.kategori)
    program.status_program = data.get('status', program.status_program)
    db.session.commit()
    
    if data.get('status') and data['status'] != status_lama:
        catat_log(id_pengguna, 'Ubah', f'Mengubah status program "{nama_lama}" dari {status_lama} menjadi {data["status"]}')
    else:
        catat_log(id_pengguna, 'Ubah', f'Mengedit program kerja: {nama_lama}')
    
    return jsonify({'status': 'success', 'message': 'Program kerja berhasil diupdate'})

# ==================== ENDPOINT RAB DINAMIS ====================

@app.route('/api/rab-dinamis', methods=['GET'])
def get_all_rab_dinamis():
    rab = RabDinamis.query.all()
    result = []
    for r in rab:
        program = ProgramKerja.query.get(r.id_program)
        result.append({
            'id_rab': r.id_rab,
            'id_program': r.id_program,
            'nama_program': program.nama_program if program else '-',
            'nama_biaya': r.nama_biaya,
            'biaya_minimal': float(r.biaya_minimal),
            'biaya_maksimal': float(r.biaya_maksimal),
            'realisasi': float(r.realisasi),
            'sisa': float(r.sisa)
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/rab-dinamis', methods=['POST'])
def create_rab_dinamis():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    new_rab = RabDinamis(
        id_program=data['id_program'],
        nama_biaya=data['nama_biaya'],
        biaya_minimal=data.get('biaya_minimal', 0),
        biaya_maksimal=data.get('biaya_maksimal', 0),
        realisasi=data.get('realisasi', 0),
        sisa=data.get('sisa', 0)
    )
    db.session.add(new_rab)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah RAB dinamis: {data["nama_biaya"]}')
    
    return jsonify({'status': 'success', 'message': 'Item RAB berhasil ditambahkan'})

@app.route('/api/rab-dinamis/<int:id_rab>', methods=['PUT'])
def update_rab_dinamis(id_rab):
    rab = RabDinamis.query.get(id_rab)
    if not rab:
        return jsonify({'status': 'error', 'message': 'Item RAB tidak ditemukan'}), 404
    data = request.get_json() or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    rab.nama_biaya = data.get('nama_biaya', rab.nama_biaya)
    rab.biaya_minimal = data.get('biaya_minimal', rab.biaya_minimal)
    rab.biaya_maksimal = data.get('biaya_maksimal', rab.biaya_maksimal)
    rab.realisasi = data.get('realisasi', rab.realisasi)
    rab.sisa = data.get('sisa', rab.sisa)
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengedit RAB dinamis: {rab.nama_biaya}')
    
    return jsonify({'status': 'success', 'message': 'Item RAB berhasil diupdate'})

@app.route('/api/rab-dinamis/<int:id_rab>', methods=['DELETE'])
def delete_rab_dinamis(id_rab):
    data = request.get_json(silent=True) or {}
    rab = RabDinamis.query.get(id_rab)
    if not rab:
        return jsonify({'status': 'error', 'message': 'Item RAB tidak ditemukan'}), 404
    
    id_pengguna = data.get('id_pengguna', 1)
    nama_biaya = rab.nama_biaya
    
    db.session.delete(rab)
    db.session.commit()
    
    catat_log(id_pengguna, 'Hapus', f'Menghapus RAB dinamis: {nama_biaya}')
    
    return jsonify({'status': 'success', 'message': 'Item RAB berhasil dihapus'})

# ==================== ENDPOINT USERS ====================

@app.route('/api/users', methods=['GET'])
def get_all_users():
    users = User.query.filter(User.deleted_at.is_(None)).all()
    result = []
    for u in users:
        result.append({
            'id_user': u.id_user,
            'username': u.username,
            'nama_lengkap': u.nama_lengkap,
            'email': u.email,
            'role': u.role,
            'no_hp': u.no_hp
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    existing = User.query.filter_by(username=data['username']).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Username sudah digunakan'}), 400
    
    new_user = User(
        username=data['username'],
        password=data['password'],
        nama_lengkap=data['nama_lengkap'],
        email=data['email'],
        role=data['role']
    )
    db.session.add(new_user)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah user: {data["nama_lengkap"]} ({data["role"]})')
    
    return jsonify({'status': 'success', 'message': 'User berhasil ditambahkan'})

@app.route('/api/users/<int:id_user>', methods=['PUT'])
def update_user(id_user):
    user = User.query.get(id_user)
    if not user:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404
    
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    user.nama_lengkap = data.get('nama_lengkap', user.nama_lengkap)
    user.email = data.get('email', user.email)
    user.role = data.get('role', user.role)
    if data.get('password'):
        user.password = data['password']
    
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengedit user: {user.nama_lengkap}')
    
    return jsonify({'status': 'success', 'message': 'User berhasil diupdate'})

@app.route('/api/users/<int:id_user>/reset-password', methods=['POST'])
def reset_password_user(id_user):
    user = User.query.get(id_user)
    if not user:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404
    
    data = request.get_json() or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    user.password = 'password123'
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mereset password user: {user.nama_lengkap}')
    
    return jsonify({'status': 'success', 'message': 'Password direset menjadi password123'})

@app.route('/api/users/<int:id_user>', methods=['DELETE'])
def delete_user(id_user):
    user = User.query.get(id_user)
    if not user:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404
    if user.username == 'admin':
        return jsonify({'status': 'error', 'message': 'Tidak dapat menghapus admin'}), 400
    
    data = request.get_json(silent=True) or {}
    id_pengguna = data.get('id_pengguna', 1)
    nama_user = user.nama_lengkap
    
    user.deleted_at = datetime.utcnow()
    db.session.commit()
    
    catat_log(id_pengguna, 'Hapus', f'Menonaktifkan user: {nama_user}')
    
    return jsonify({'status': 'success', 'message': 'User berhasil dinonaktifkan'})

@app.route('/api/users/<int:id_user>/restore', methods=['POST'])
def restore_user(id_user):
    user = User.query.get(id_user)
    if not user:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan'}), 404
    
    data = request.get_json() or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    user.deleted_at = None
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengaktifkan kembali user: {user.nama_lengkap}')
    
    return jsonify({'status': 'success', 'message': 'User diaktifkan kembali'})

@app.route('/api/users/<int:id_user>/upload-photo', methods=['POST'])
def upload_user_photo(id_user):
    if 'photo' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada file'}), 400
    file = request.files['photo']
    if file and allowed_file(file.filename):
        filename = secure_filename(f"user_{id_user}_{datetime.now().timestamp()}.{file.filename.rsplit('.',1)[1].lower()}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        user = User.query.get(id_user)
        if user:
            user.foto = filename
            db.session.commit()
            
            id_pengguna = request.form.get('id_pengguna', id_user)
            catat_log(int(id_pengguna), 'Ubah', f'Mengupload foto profil user: {user.nama_lengkap}')
            
        return jsonify({'status': 'success', 'filename': filename})
    return jsonify({'status': 'error', 'message': 'File tidak diizinkan'}), 400

# ==================== ENDPOINT DASHBOARD STATS ====================

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    periode_aktif = PeriodeAktif.query.filter_by(status_periode='Aktif').all()
    tahun_aktif = [str(p.tahun) for p in periode_aktif]
    
    total_pemasukan = db.session.query(db.func.sum(Transaksi.nominal)).filter(
        Transaksi.jenis == 'Masuk',
        Transaksi.status_validasi.in_(['Valid', 'Pending'])
    ).scalar() or 0
    
    total_pengeluaran = db.session.query(db.func.sum(Transaksi.nominal)).filter(
        Transaksi.jenis == 'Keluar',
        Transaksi.status_validasi.in_(['Valid', 'Pending'])
    ).scalar() or 0
    
    sisa_saldo = float(total_pemasukan) - float(total_pengeluaran)
    
    if tahun_aktif:
        program_aktif = ProgramKerja.query.filter(
            ProgramKerja.status_program == 'Berjalan',
            ProgramKerja.periode.in_(tahun_aktif)
        ).count()
    else:
        program_aktif = ProgramKerja.query.filter_by(status_program='Berjalan').count()
    
    total_program = ProgramKerja.query.count()
    
    return jsonify({
        'status': 'success',
        'data': {
            'total_pemasukan': float(total_pemasukan),
            'total_pengeluaran': float(total_pengeluaran),
            'sisa_saldo': sisa_saldo,
            'program_aktif': program_aktif,
            'total_program': total_program,
            'periode_aktif': tahun_aktif
        }
    })

# ==================== ENDPOINT KATEGORI ====================

@app.route('/api/kategori', methods=['GET'])
def get_kategori():
    kategori = KategoriProgram.query.all()
    result = []
    for k in kategori:
        result.append({
            'id_kategori': k.id_kategori,
            'nama_kategori': k.nama_kategori,
            'deskripsi_kategori': k.deskripsi_kategori,
            'status': k.status
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/kategori', methods=['POST'])
def create_kategori():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    new_kategori = KategoriProgram(
        nama_kategori=data['nama_kategori'],
        deskripsi_kategori=data.get('deskripsi_kategori', ''),
        status=data.get('status', 'Aktif')
    )
    db.session.add(new_kategori)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah kategori: {data["nama_kategori"]}')
    
    return jsonify({'status': 'success', 'message': 'Kategori berhasil ditambahkan'})

@app.route('/api/kategori/<int:id_kategori>', methods=['PUT'])
def update_kategori(id_kategori):
    kategori = KategoriProgram.query.get(id_kategori)
    if not kategori:
        return jsonify({'status': 'error', 'message': 'Kategori tidak ditemukan'}), 404
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    kategori.nama_kategori = data.get('nama_kategori', kategori.nama_kategori)
    kategori.deskripsi_kategori = data.get('deskripsi_kategori', kategori.deskripsi_kategori)
    kategori.status = data.get('status', kategori.status)
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengedit kategori: {kategori.nama_kategori}')
    
    return jsonify({'status': 'success', 'message': 'Kategori berhasil diupdate'})

@app.route('/api/kategori/<int:id_kategori>', methods=['DELETE'])
def delete_kategori(id_kategori):
    data = request.get_json(silent=True) or {}
    kategori = KategoriProgram.query.get(id_kategori)
    if not kategori:
        return jsonify({'status': 'error', 'message': 'Kategori tidak ditemukan'}), 404
    
    id_pengguna = data.get('id_pengguna', 1)
    nama_kategori = kategori.nama_kategori
    
    db.session.delete(kategori)
    db.session.commit()
    
    catat_log(id_pengguna, 'Hapus', f'Menghapus kategori: {nama_kategori}')
    
    return jsonify({'status': 'success', 'message': 'Kategori berhasil dihapus'})

# ==================== ENDPOINT KATALOG BIAYA ====================

@app.route('/api/katalog-biaya', methods=['GET'])
def get_all_katalog_biaya():
    katalog = KatalogBiaya.query.order_by(KatalogBiaya.nama_biaya.asc()).all()
    result = []
    for k in katalog:
        result.append({
            'id_biaya': k.id_biaya,
            'nama_biaya': k.nama_biaya,
            'biaya_minimal': float(k.biaya_minimal),
            'biaya_maksimal': float(k.biaya_maksimal),
            'deskripsi_biaya': k.deskripsi_biaya
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/katalog-biaya', methods=['POST'])
def create_katalog_biaya():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    new_biaya = KatalogBiaya(
        nama_biaya=data['nama_biaya'],
        biaya_minimal=data.get('biaya_minimal', 0),
        biaya_maksimal=data.get('biaya_maksimal', 0),
        deskripsi_biaya=data.get('deskripsi_biaya', '')
    )
    db.session.add(new_biaya)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah katalog biaya: {data["nama_biaya"]}')
    
    return jsonify({'status': 'success', 'message': 'Biaya berhasil ditambahkan'})

@app.route('/api/katalog-biaya/<int:id_biaya>', methods=['PUT'])
def update_katalog_biaya(id_biaya):
    biaya = KatalogBiaya.query.get(id_biaya)
    if not biaya:
        return jsonify({'status': 'error', 'message': 'Biaya tidak ditemukan'}), 404
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    biaya.nama_biaya = data.get('nama_biaya', biaya.nama_biaya)
    biaya.biaya_minimal = data.get('biaya_minimal', biaya.biaya_minimal)
    biaya.biaya_maksimal = data.get('biaya_maksimal', biaya.biaya_maksimal)
    biaya.deskripsi_biaya = data.get('deskripsi_biaya', biaya.deskripsi_biaya)
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengedit katalog biaya: {biaya.nama_biaya}')
    
    return jsonify({'status': 'success', 'message': 'Biaya berhasil diupdate'})

@app.route('/api/katalog-biaya/<int:id_biaya>', methods=['DELETE'])
def delete_katalog_biaya(id_biaya):
    data = request.get_json(silent=True) or {}
    biaya = KatalogBiaya.query.get(id_biaya)
    if not biaya:
        return jsonify({'status': 'error', 'message': 'Biaya tidak ditemukan'}), 404
    
    id_pengguna = data.get('id_pengguna', 1)
    nama_biaya = biaya.nama_biaya
    
    db.session.delete(biaya)
    db.session.commit()
    
    catat_log(id_pengguna, 'Hapus', f'Menghapus katalog biaya: {nama_biaya}')
    
    return jsonify({'status': 'success', 'message': 'Biaya berhasil dihapus'})

# ==================== ENDPOINT TRANSAKSI ====================

@app.route('/api/transaksi', methods=['GET'])
def get_all_transaksi():
    role = request.args.get('role', None)
    hide_selesai = request.args.get('hide_selesai', 'false').lower() == 'true'
    
    if hide_selesai:
        program_selesai_ids = [p.id_program for p in ProgramKerja.query.filter_by(status_program='Selesai').all()]
        transaksi = Transaksi.query.filter(~Transaksi.id_program.in_(program_selesai_ids)).order_by(Transaksi.tanggal.desc()).all()
    else:
        transaksi = Transaksi.query.order_by(Transaksi.tanggal.desc()).all()
    
    result = []
    for t in transaksi:
        program = ProgramKerja.query.get(t.id_program)
        user = User.query.get(t.id_pengguna)
        kategori = KategoriProgram.query.get(t.id_kategori)
        result.append({
            'id_transaksi': t.id_transaksi,
            'id_program': t.id_program,
            'nama_program': program.nama_program if program else '-',
            'nama_pengguna': user.nama_lengkap if user else '-',
            'kategori': kategori.nama_kategori if kategori else '-',
            'jenis': t.jenis,
            'nominal': float(t.nominal),
            'tanggal': t.tanggal.strftime('%Y-%m-%d'),
            'keterangan': t.keterangan,
            'bukti_file': t.bukti_file,
            'status': t.status_validasi,
            'status_validasi': t.status_validasi,
            'status_program': program.status_program if program else None
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/transaksi', methods=['POST'])
def create_transaksi():
    id_program = request.form.get('id_program')
    id_pengguna = request.form.get('id_pengguna')
    jenis = request.form.get('jenis')
    nominal = request.form.get('nominal')
    tanggal = request.form.get('tanggal')
    keterangan = request.form.get('keterangan', '')
    status = request.form.get('status', 'Selesai')
    
    bukti_file = None
    if 'bukti_file' in request.files:
        file = request.files['bukti_file']
        if file and file.filename:
            filename = secure_filename(f"bukti_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            bukti_file = filename
    
    new_transaksi = Transaksi(
        id_program=id_program,
        id_pengguna=id_pengguna,
        jenis=jenis,
        nominal=nominal,
        tanggal=datetime.strptime(tanggal, '%Y-%m-%d').date(),
        keterangan=keterangan,
        bukti_file=bukti_file,
        status_validasi='Valid' if status == 'Selesai' else 'Pending'
    )
    db.session.add(new_transaksi)
    db.session.flush()
    
    if status != 'Selesai':
        pengajuan = PengajuanTransaksi(
            id_transaksi=new_transaksi.id_transaksi,
            id_pengguna=int(id_pengguna) if id_pengguna else 1,
            status='Menunggu',
            alasan=keterangan if keterangan else 'Transaksi tanpa bukti - Menunggu konfirmasi Ketua'
        )
        db.session.add(pengajuan)
    
    db.session.commit()
    
    user = User.query.get(int(id_pengguna)) if id_pengguna else None
    program = ProgramKerja.query.get(int(id_program)) if id_program else None
    nama_user = user.nama_lengkap if user else 'Unknown'
    nama_program = program.nama_program if program else '-'
    catat_log(int(id_pengguna) if id_pengguna else 1, 'Transaksi', 
              f'{nama_user} menambah transaksi {jenis} Rp {float(nominal):,.0f} untuk program {nama_program}')
    
    return jsonify({'status': 'success', 'message': 'Transaksi berhasil', 'id': new_transaksi.id_transaksi})

@app.route('/api/transaksi/<int:id_transaksi>', methods=['PUT'])
def update_transaksi(id_transaksi):
    transaksi = Transaksi.query.get(id_transaksi)
    if not transaksi:
        return jsonify({'status': 'error', 'message': 'Transaksi tidak ditemukan'}), 404
    data = request.form.to_dict() if request.form else request.get_json() or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    transaksi.id_program = data.get('id_program', transaksi.id_program)
    transaksi.jenis = data.get('jenis', transaksi.jenis)
    transaksi.nominal = data.get('nominal', transaksi.nominal)
    if data.get('tanggal'):
        transaksi.tanggal = datetime.strptime(data['tanggal'], '%Y-%m-%d').date()
    transaksi.keterangan = data.get('keterangan', transaksi.keterangan)
    transaksi.status_validasi = data.get('status_validasi', transaksi.status_validasi)
    
    if 'bukti_file' in request.files:
        file = request.files['bukti_file']
        if file and file.filename:
            filename = secure_filename(f"bukti_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            transaksi.bukti_file = filename
    
    db.session.commit()
    
    catat_log(int(id_pengguna), 'Ubah', f'Mengedit transaksi #{id_transaksi}')
    
    return jsonify({'status': 'success', 'message': 'Transaksi diupdate'})

@app.route('/api/transaksi/<int:id_transaksi>', methods=['DELETE'])
def delete_transaksi(id_transaksi):
    data = request.get_json(silent=True) or {}
    transaksi = Transaksi.query.get(id_transaksi)
    if not transaksi:
        return jsonify({'status': 'error', 'message': 'Transaksi tidak ditemukan'}), 404
    
    id_pengguna = data.get('id_pengguna', 1)
    
    pengajuan = PengajuanTransaksi.query.filter_by(id_transaksi=id_transaksi).first()
    if pengajuan:
        db.session.delete(pengajuan)
    
    db.session.delete(transaksi)
    db.session.commit()
    
    catat_log(int(id_pengguna), 'Hapus', f'Menghapus transaksi #{id_transaksi}')
    
    return jsonify({'status': 'success', 'message': 'Transaksi dihapus'})

# ==================== ENDPOINT PROGRAM SELESAI ====================

@app.route('/api/program-kerja/selesai', methods=['GET'])
def get_program_kerja_selesai():
    program_selesai = ProgramKerja.query.filter_by(status_program='Selesai').order_by(ProgramKerja.created_at.desc()).all()
    result = []
    for p in program_selesai:
        result.append({
            'id_program': p.id_program,
            'nama_program': p.nama_program,
            'deskripsi_program': p.deskripsi_program,
            'periode': p.periode,
            'kategori': p.kategori,
            'status_program': p.status_program,
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else None
        })
    return jsonify({'status': 'success', 'count': len(result), 'data': result})

# ==================== ENDPOINT PENGAJUAN ====================

@app.route('/api/pengajuan/menunggu', methods=['GET'])
def get_pengajuan_menunggu_list():
    pengajuan = PengajuanTransaksi.query.filter_by(status='Menunggu').all()
    result = []
    for p in pengajuan:
        transaksi = Transaksi.query.get(p.id_transaksi)
        if transaksi:
            program = ProgramKerja.query.get(transaksi.id_program)
            pengaju = User.query.get(p.id_pengguna)
            kategori = KategoriProgram.query.get(transaksi.id_kategori)
            result.append({
                'id_pengajuan': p.id_pengajuan,
                'id_transaksi': p.id_transaksi,
                'nama_program': program.nama_program if program else 'Tidak Diketahui',
                'nama_pengaju': pengaju.nama_lengkap if pengaju else 'Tidak Diketahui',
                'kategori': kategori.nama_kategori if kategori else 'Pengeluaran',
                'jenis': transaksi.jenis,
                'nominal': float(transaksi.nominal),
                'tanggal': transaksi.tanggal.strftime('%Y-%m-%d'),
                'keterangan': transaksi.keterangan,
                'bukti_file': transaksi.bukti_file,
                'alasan': p.alasan,
                'status': p.status
            })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/pengajuan/<int:id_pengajuan>/konfirmasi', methods=['POST'])
def proses_konfirmasi_pengajuan(id_pengajuan):
    data = request.get_json()
    status = data.get('status')
    catatan = data.get('catatan', '')
    id_pengguna = data.get('id_pengguna', 1)
    
    pengajuan = PengajuanTransaksi.query.get(id_pengajuan)
    if not pengajuan:
        return jsonify({'status': 'error', 'message': 'Pengajuan tidak ditemukan'}), 404
    
    pengajuan.status = status
    pengajuan.catatan_penolakan = catatan if status == 'Ditolak' else None
    pengajuan.approved_at = datetime.utcnow()
    pengajuan.approved_by = id_pengguna
    
    if status == 'Disetujui':
        transaksi = Transaksi.query.get(pengajuan.id_transaksi)
        if transaksi:
            transaksi.status_validasi = 'Valid'
    
    db.session.commit()
    
    if status == 'Disetujui':
        catat_log(int(id_pengguna), 'Konfirmasi', f'Menyetujui pengajuan transaksi #{pengajuan.id_transaksi}')
    else:
        catat_log(int(id_pengguna), 'Tolak', f'Menolak pengajuan transaksi #{pengajuan.id_transaksi}: {catatan}')
    
    return jsonify({'status': 'success', 'message': f'Pengajuan {status}'})

# ==================== ENDPOINT LAPORAN KEUANGAN ====================

@app.route('/api/laporan-keuangan/<int:id_program>', methods=['GET'])
def get_laporan_keuangan(id_program):
    program = ProgramKerja.query.get(id_program)
    if not program:
        return jsonify({'status': 'error', 'message': 'Program tidak ditemukan'}), 404

    transaksi_list = Transaksi.query.filter_by(id_program=id_program).order_by(Transaksi.tanggal).all()
    total_masuk = sum(t.nominal for t in transaksi_list if t.jenis == 'Masuk')
    total_keluar = sum(t.nominal for t in transaksi_list if t.jenis == 'Keluar')
    sisa = float(total_masuk) - float(total_keluar)

    rab_list = RabDinamis.query.filter_by(id_program=id_program).all()
    total_anggaran = sum(r.biaya_maksimal for r in rab_list)
    total_realisasi = sum(r.realisasi for r in rab_list)
    persentase = (float(total_realisasi) / float(total_anggaran) * 100) if float(total_anggaran) > 0 else 0

    transaksi_data = []
    for t in transaksi_list:
        transaksi_data.append({
            'id_transaksi': t.id_transaksi,
            'tanggal': t.tanggal.strftime('%Y-%m-%d'),
            'jenis': t.jenis,
            'nominal': float(t.nominal),
            'keterangan': t.keterangan,
            'bukti_file': t.bukti_file
        })

    return jsonify({
        'status': 'success',
        'data': {
            'program': {
                'id_program': program.id_program,
                'nama_program': program.nama_program,
                'periode': program.periode,
                'status': program.status_program
            },
            'ringkasan': {
                'total_pemasukan': float(total_masuk),
                'total_pengeluaran': float(total_keluar),
                'sisa_saldo': sisa,
                'total_anggaran': float(total_anggaran),
                'realisasi_anggaran': float(total_realisasi),
                'persentase': persentase
            },
            'transaksi': transaksi_data
        }
    })

# ==================== ENDPOINT PERIODE ====================

@app.route('/api/periode-aktif', methods=['GET'])
def get_periode_aktif_status():
    tahun_sekarang = False
    tahun_depan = False
    periode = PeriodeAktif.query.all()
    for p in periode:
        if p.nama_periode == 'Tahun Sekarang' and p.status_periode == 'Aktif':
            tahun_sekarang = True
        elif p.nama_periode == 'Tahun Depan' and p.status_periode == 'Aktif':
            tahun_depan = True
    return jsonify({'status': 'success', 'data': {'tahun_sekarang': tahun_sekarang, 'tahun_depan': tahun_depan}})

@app.route('/api/periode-aktif', methods=['POST'])
def save_periode_aktif_status():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    current_year = datetime.now().year
    next_year = current_year + 1
    
    periode = PeriodeAktif.query.filter_by(nama_periode='Tahun Sekarang').first()
    if periode:
        periode.status_periode = 'Aktif' if data.get('tahun_sekarang') else 'Nonaktif'
        periode.tahun = str(current_year)
    else:
        db.session.add(PeriodeAktif(nama_periode='Tahun Sekarang', tahun=str(current_year), status_periode='Aktif' if data.get('tahun_sekarang') else 'Nonaktif'))
    
    periode2 = PeriodeAktif.query.filter_by(nama_periode='Tahun Depan').first()
    if periode2:
        periode2.status_periode = 'Aktif' if data.get('tahun_depan') else 'Nonaktif'
        periode2.tahun = str(next_year)
    else:
        db.session.add(PeriodeAktif(nama_periode='Tahun Depan', tahun=str(next_year), status_periode='Aktif' if data.get('tahun_depan') else 'Nonaktif'))
    
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', 'Mengubah pengaturan periode aktif')
    
    return jsonify({'status': 'success', 'message': 'Periode aktif disimpan'})

@app.route('/api/periode/tahun-list', methods=['GET'])
def get_tahun_list():
    periode_list = PeriodeAktif.query.all()
    tahun_set = set()
    for p in periode_list:
        tahun_set.add(str(p.tahun))
    program_tahun = db.session.query(ProgramKerja.periode).distinct().all()
    for pt in program_tahun:
        if pt[0]:
            tahun_set.add(str(pt[0]))
    result = sorted(list(tahun_set), reverse=True)
    if not result:
        cy = datetime.now().year
        result = [f"{cy}/{cy+1}", str(cy+1), str(cy)]
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/periode/tahun', methods=['POST'])
def tambah_tahun():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    tahun = data.get('tahun', '').strip()
    if not tahun:
        return jsonify({'status': 'error', 'message': 'Tahun tidak boleh kosong'}), 400
    existing = PeriodeAktif.query.filter_by(tahun=tahun).first()
    if not existing:
        db.session.add(PeriodeAktif(nama_periode=f'Periode {tahun}', tahun=tahun, status_periode='Nonaktif'))
        db.session.commit()
        
        catat_log(id_pengguna, 'Tambah', f'Menambah tahun periode: {tahun}')
        
    return jsonify({'status': 'success', 'message': 'Tahun ditambahkan'})

@app.route('/api/periode/tahun/<path:tahun>', methods=['DELETE'])
def hapus_tahun(tahun):
    data = request.get_json(silent=True) or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    periode = PeriodeAktif.query.filter_by(tahun=tahun).first()
    if periode:
        db.session.delete(periode)
        db.session.commit()
        
        catat_log(id_pengguna, 'Hapus', f'Menghapus tahun periode: {tahun}')
        
    return jsonify({'status': 'success', 'message': 'Tahun dihapus'})

@app.route('/api/periode/aktif', methods=['GET'])
def get_periode_aktif_list():
    periode_aktif = PeriodeAktif.query.filter_by(status_periode='Aktif').all()
    result = [str(p.tahun) for p in periode_aktif]
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/periode/aktif', methods=['POST'])
def set_periode_aktif():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    tahun_list = data.get('tahun_list', [])
    if len(tahun_list) > 2:
        return jsonify({'status': 'error', 'message': 'Maksimal 2 periode aktif'}), 400
    PeriodeAktif.query.update({'status_periode': 'Nonaktif'})
    for tahun in tahun_list:
        periode = PeriodeAktif.query.filter_by(tahun=tahun).first()
        if periode:
            periode.status_periode = 'Aktif'
        else:
            db.session.add(PeriodeAktif(nama_periode=f'Periode {tahun}', tahun=tahun, status_periode='Aktif'))
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengatur periode aktif: {", ".join(tahun_list) if tahun_list else "tidak ada"}')
    
    return jsonify({'status': 'success', 'message': 'Periode aktif disimpan', 'data': tahun_list})

# ==================== ENDPOINT RAB ====================

@app.route('/api/rab', methods=['GET'])
def get_all_rab():
    rab_list = RAB.query.all()
    result = []
    for r in rab_list:
        program = ProgramKerja.query.get(r.id_program)
        result.append({
            'id_rab': r.id_rab,
            'id_program': r.id_program,
            'nama_item': r.nama_item,
            'jumlah': int(r.jumlah),
            'harga_satuan': float(r.harga_satuan),
            'keterangan': r.keterangan,
            'status_program': program.status_program if program else None
        })
    return jsonify({'status': 'success', 'data': result})

@app.route('/api/rab/<int:id_rab>', methods=['GET'])
def get_rab_by_id(id_rab):
    r = RAB.query.get(id_rab)
    if not r:
        return jsonify({'status': 'error', 'message': 'RAB tidak ditemukan'}), 404
    return jsonify({'status': 'success', 'data': {
        'id_rab': r.id_rab, 'id_program': r.id_program,
        'nama_item': r.nama_item, 'jumlah': int(r.jumlah),
        'harga_satuan': float(r.harga_satuan), 'keterangan': r.keterangan
    }})

@app.route('/api/rab', methods=['POST'])
def create_rab():
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    if not data.get('id_program') or not data.get('nama_item'):
        return jsonify({'status': 'error', 'message': 'Data tidak lengkap'}), 400
    new_rab = RAB(
        id_program=data['id_program'], nama_item=data['nama_item'],
        jumlah=data.get('jumlah', 1), harga_satuan=data.get('harga_satuan', 0),
        keterangan=data.get('keterangan', '')
    )
    db.session.add(new_rab)
    db.session.commit()
    
    catat_log(id_pengguna, 'Tambah', f'Menambah item RAB: {data["nama_item"]}')
    
    return jsonify({'status': 'success', 'message': 'RAB ditambahkan'}), 201

@app.route('/api/rab/<int:id_rab>', methods=['PUT'])
def update_rab(id_rab):
    rab = RAB.query.get(id_rab)
    if not rab:
        return jsonify({'status': 'error', 'message': 'RAB tidak ditemukan'}), 404
    data = request.get_json()
    id_pengguna = data.get('id_pengguna', 1)
    
    rab.nama_item = data.get('nama_item', rab.nama_item)
    rab.jumlah = data.get('jumlah', rab.jumlah)
    rab.harga_satuan = data.get('harga_satuan', rab.harga_satuan)
    rab.keterangan = data.get('keterangan', rab.keterangan)
    rab.updated_at = datetime.utcnow()
    db.session.commit()
    
    catat_log(id_pengguna, 'Ubah', f'Mengedit item RAB: {rab.nama_item}')
    
    return jsonify({'status': 'success', 'message': 'RAB diupdate'})

@app.route('/api/rab/<int:id_rab>', methods=['DELETE'])
def delete_rab(id_rab):
    data = request.get_json(silent=True) or {}
    rab = RAB.query.get(id_rab)
    if not rab:
        return jsonify({'status': 'error', 'message': 'RAB tidak ditemukan'}), 404
    
    id_pengguna = data.get('id_pengguna', 1)
    nama_item = rab.nama_item
    
    db.session.delete(rab)
    db.session.commit()
    
    try:
        catat_log(id_pengguna, 'Hapus', f'Menghapus item RAB: {nama_item}')
    except:
        pass
    
    return jsonify({'status': 'success', 'message': 'RAB dihapus'})

@app.route('/api/rab/program/<int:id_program>', methods=['GET'])
def get_rab_by_program(id_program):
    rab_list = RAB.query.filter_by(id_program=id_program).all()
    total_rab = 0
    result = []
    for r in rab_list:
        item_total = float(r.jumlah) * float(r.harga_satuan)
        total_rab += item_total
        result.append({
            'id_rab': r.id_rab, 'id_program': r.id_program,
            'nama_item': r.nama_item, 'jumlah': int(r.jumlah),
            'harga_satuan': float(r.harga_satuan), 'total': item_total,
            'keterangan': r.keterangan
        })
    return jsonify({'status': 'success', 'data': result, 'total_rab': total_rab})

# ==================== ENDPOINT RIWAYAT ====================

@app.route('/api/riwayat', methods=['GET'])
def get_riwayat_pagination():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    tahun = request.args.get('tahun', None)
    
    query = ProgramKerja.query.filter_by(status_program='Selesai')
    if tahun:
        query = query.filter_by(periode=tahun)
    query = query.order_by(ProgramKerja.periode.desc(), ProgramKerja.created_at.desc())
    
    total = query.count()
    total_pages = max(1, (total + limit - 1) // limit)
    programs = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for p in programs:
        result.append({
            'id_program': p.id_program, 'nama_program': p.nama_program,
            'deskripsi_program': p.deskripsi_program, 'periode': p.periode,
            'kategori': p.kategori, 'status_program': p.status_program,
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else None
        })
    
    return jsonify({'status': 'success', 'data': result, 'total': total, 'total_pages': total_pages, 'current_page': page})

# ==================== ENDPOINT SETUJUI/TOLAK PENGAJUAN ====================

@app.route('/api/pengajuan/<int:id_pengajuan>/setujui', methods=['POST'])
def setujui_pengajuan(id_pengajuan):
    data = request.get_json() or {}
    id_pengguna = data.get('id_pengguna', 1)
    
    pengajuan = PengajuanTransaksi.query.get(id_pengajuan)
    if not pengajuan:
        return jsonify({'status': 'error', 'message': 'Pengajuan tidak ditemukan'}), 404
    
    pengajuan.status = 'Disetujui'
    pengajuan.approved_at = datetime.utcnow()
    pengajuan.approved_by = id_pengguna
    
    transaksi = Transaksi.query.get(pengajuan.id_transaksi)
    if transaksi:
        transaksi.status_validasi = 'Valid'
    
    db.session.commit()
    
    catat_log(int(id_pengguna), 'Konfirmasi', f'Menyetujui transaksi #{pengajuan.id_transaksi}')
    
    return jsonify({'status': 'success', 'message': 'Pengajuan disetujui', 'id_transaksi': pengajuan.id_transaksi})


@app.route('/api/pengajuan/<int:id_pengajuan>/tolak', methods=['POST'])
def tolak_pengajuan(id_pengajuan):
    data = request.get_json() or {}
    catatan = data.get('catatan', '')
    id_pengguna = data.get('id_pengguna', 1)
    
    pengajuan = PengajuanTransaksi.query.get(id_pengajuan)
    if not pengajuan:
        return jsonify({'status': 'error', 'message': 'Pengajuan tidak ditemukan'}), 404
    
    pengajuan.status = 'Ditolak'
    pengajuan.catatan_penolakan = catatan
    pengajuan.approved_at = datetime.utcnow()
    pengajuan.approved_by = id_pengguna
    
    transaksi = Transaksi.query.get(pengajuan.id_transaksi)
    if transaksi:
        transaksi.status_validasi = 'Tidak Valid'
    
    db.session.commit()
    
    catat_log(int(id_pengguna), 'Tolak', f'Menolak transaksi #{pengajuan.id_transaksi}: {catatan}' if catatan else f'Menolak transaksi #{pengajuan.id_transaksi}')
    
    return jsonify({'status': 'success', 'message': 'Pengajuan ditolak'})

# ==================== ENDPOINT INIT DATABASE ====================

@app.route('/api/init-db', methods=['GET'])
def init_database():
    try:
        db.create_all()
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            users = [
                User(username='admin', password='admin123', role='Admin', nama_lengkap='Administrator', email='admin@gdb.com'),
                User(username='ketua', password='ketua123', role='Ketua', nama_lengkap='Ketua GDB', email='ketua@gdb.com'),
                User(username='bendahara', password='bendahara123', role='Bendahara', nama_lengkap='Bendahara GDB', email='bendahara@gdb.com'),
                User(username='anggota', password='anggota123', role='Anggota Umum', nama_lengkap='Anggota GDB', email='anggota@gdb.com'),
            ]
            for u in users:
                db.session.add(u)
            db.session.commit()
        
        katalog = KatalogBiaya.query.first()
        if not katalog:
            biaya_list = [
                KatalogBiaya(nama_biaya='Konsumsi', biaya_minimal=100000, biaya_maksimal=10000000, deskripsi_biaya='Biaya untuk konsumsi, snack, makan siang'),
                KatalogBiaya(nama_biaya='Transportasi', biaya_minimal=50000, biaya_maksimal=5000000, deskripsi_biaya='Biaya transportasi, bensin, parkir, tol'),
                KatalogBiaya(nama_biaya='Perlengkapan', biaya_minimal=100000, biaya_maksimal=20000000, deskripsi_biaya='Biaya perlengkapan acara'),
                KatalogBiaya(nama_biaya='Dokumentasi', biaya_minimal=50000, biaya_maksimal=5000000, deskripsi_biaya='Biaya dokumentasi foto dan video'),
                KatalogBiaya(nama_biaya='Honorarium', biaya_minimal=100000, biaya_maksimal=10000000, deskripsi_biaya='Biaya honorarium pembicara, panitia'),
                KatalogBiaya(nama_biaya='Publikasi', biaya_minimal=50000, biaya_maksimal=5000000, deskripsi_biaya='Biaya publikasi, cetak spanduk, desain'),
            ]
            for b in biaya_list:
                db.session.add(b)
            db.session.commit()
        
        user_count = User.query.count()
        return jsonify({
            'status': 'success',
            'message': 'Database berhasil diinisialisasi',
            'user_count': user_count,
            'users': ['admin', 'ketua', 'bendahara', 'anggota']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RUN SERVER ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
