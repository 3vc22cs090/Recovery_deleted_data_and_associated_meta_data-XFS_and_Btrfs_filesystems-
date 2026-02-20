# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
from io import BytesIO
import os
from datetime import datetime
from config import UPLOAD_FOLDER, SECRET_KEY, ADMIN_PASSWORD, ALLOWED_EXTENSIONS
from models import get_conn, init_db
import recovery_utils
from werkzeug.security import generate_password_hash, check_password_hash
init_db()
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    if ALLOWED_EXTENSIONS is None:
        return True
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        

        if not username or not password:
            flash("Username and password required","danger")
            return redirect(url_for('register'))

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
            conn.commit()
            flash("Registration successful. Please login.","success")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Username already taken or DB error.","warning")
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for('login'))

@app.route('/index')
def index():
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM files where uploaded_by=? ORDER BY uploaded_at DESC',(session['user_id'],))
    files = cur.fetchall()
    conn.close()
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    f = request.files['file']
    if f.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(save_path)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO files (filename, stored_path, uploaded_at,uploaded_by) VALUES (?, ?, ?,?)', 
                    (filename, save_path, datetime.utcnow().isoformat(),session['user_id']))
        conn.commit()
        conn.close()
        flash('Uploaded')
    return redirect(url_for('index'))

@app.route('/delete/<int:file_id>', methods=['POST'])
def delete(file_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM files WHERE id=?', (file_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash('File not found')
        return redirect(url_for('index'))
    filepath = row['stored_path']
    filename = row['filename']
    try:
        with open(filepath, 'rb') as fh:
            blob = fh.read()
    except Exception as e:
        blob = None
    cur.execute('INSERT INTO deleted_files (filename, original_path, deleted_at, filesystem, recovery_blob, recovered) VALUES (?, ?, ?, ?, ?, ?)',
                (filename, filepath, datetime.utcnow().isoformat(), None, blob, 0))
    try:
        os.remove(filepath)
    except Exception:
        pass
    cur.execute('DELETE FROM files WHERE id=?', (file_id,))
    conn.commit()
    conn.close()
    flash('File deleted and stored in deleted_files for admin recovery')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Bad password')
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM deleted_files ORDER BY deleted_at DESC')
    deleted = cur.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', deleted=deleted)

@app.route('/deleterecover')
def deleterecover():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM deleted_files ORDER BY deleted_at DESC')
    deleted = cur.fetchall()
    conn.close()
    import main as m
    m.main()
    return render_template('admin_dashboard.html', deleted=deleted)
@app.route('/admin/ufiles')
def admin_ufiles():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM files ')
    deleted = cur.fetchall()
    conn.close()
    return render_template('manage_files.html', deleted=deleted)

@app.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users ')
    deleted = cur.fetchall()
    conn.close()
    return render_template('manage_users.html', deleted=deleted)


@app.route('/admin/recover/<int:del_id>', methods=['POST'])
def admin_recover(del_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM deleted_files WHERE id=?', (del_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash('Deleted entry not found')
        return redirect(url_for('admin_dashboard'))
    blob = row['recovery_blob']
    filename = row['filename']
    if blob:
        cur.execute('UPDATE deleted_files SET recovered=1 WHERE id=?', (del_id,))
        conn.commit()
        conn.close()
        return send_file(BytesIO(blob), as_attachment=True, download_name=filename)
    conn.close()
    device = request.form.get('device') or '/dev/sdX'
    fs = request.form.get('filesystem') or 'xfs'
    pattern = filename
    if fs == 'btrfs':
        res = recovery_utils.attempt_btrfs_restore(device, None, pattern)
    else:
        res = recovery_utils.attempt_xfs_recover(device, pattern)
    return render_template('recovery_result.html', result=res, del_id=del_id)

if __name__ == '__main__':
    app.run(debug=True)
