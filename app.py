import os
import jwt
import hashlib
from os.path import join, dirname
from dotenv import load_dotenv

from flask import (
    Flask, 
    render_template, 
    jsonify, 
    request, 
    redirect, 
    url_for,)
from pymongo import MongoClient
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = "./static/profile_pics"

SECRET_KEY = "SPARTA"
TOKEN_KEY = 'mytoken'

@app.route('/', methods=['GET'])
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.petugas.find_one({'nik': payload.get('nik')})
        return render_template('homepetugas.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        msg = 'Your token has expired'
        return redirect(url_for('login', msg=msg))
    except jwt.exceptions.DecodeError:
        msg = 'There was a problem logging you in'
        return redirect(url_for('login', msg=msg))
    
@app.route('/homemhs', methods=['GET'])
def homemhs():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.mahasiswa.find_one({'nim': payload.get('nim')})
        return render_template('index.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        msg = 'Your token has expired'
        return redirect(url_for('loginmhs', msg=msg))
    except jwt.exceptions.DecodeError:
        msg = 'There was a problem logging you in'
        return redirect(url_for('loginmhs', msg=msg))
        
@app.route('/login', methods=['GET'])
def login():
    msg = request.args.get('msg')
    return render_template('login.html', msg=msg)

@app.route('/loginmhs', methods=['GET'])
def loginmhs():
    msg = request.args.get('msg')
    return render_template('loginmhs.html', msg=msg)

@app.route("/user/<nik>")
def user(nik):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        status = nik == payload["nik"]  

        user_info = db.petugas.find_one({"nik": nik}, {"_id": False})
        return render_template("profile.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route("/profile/<nim>")
def mahasiswa(nim):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        status = nim == payload["nim"]  

        user_info = db.mahasiswa.find_one({"nim": nim}, {"_id": False})
        return render_template("profilemhs.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("homemhs"))
    
@app.route("/update_profile", methods=["POST"])
def update_profile():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        nik = payload["nik"]
        name_receive = request.form["name_give"]
        new_doc = {"profile_name": name_receive}

        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{nik}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = file_path

        db.petugas.update_one({"nik": payload["nik"]}, {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profile updated!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route("/update_profilemhs", methods=["POST"])
def update_profilemhs():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        nim = payload["nim"]
        name_receive = request.form["name_give"]
        new_doc = {"profile_name": name_receive}

        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{nim}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path

        db.mahasiswa.update_one({"nim": payload["nim"]}, {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profile updated!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("homemhs"))


@app.route("/sign_in", methods=["POST"])
def sign_in():
    nik_receive = request.form["nik_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.petugas.find_one(
        {
            "nik": nik_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "nik": nik_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    nik_receive = request.form['nik_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "nik": nik_receive,                               
        "password": password_hash,                                  
        "profile_name": username_receive,                           
        "profile_pic": "profile_pics/profile_placeholder.jpeg",                                          
        "profile_pic_real": "profile_pics/profile_placeholder.jpeg", 
        "profile_info": "profile_pics/profile_placeholder.jpeg"                                          
    }
    db.petugas.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route("/sign_in/mhs", methods=["POST"])
def sign_in_mhs():
    nim_receive = request.form["nim_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.mahasiswa.find_one(
        {
            "nim": nim_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "nim": nim_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )


@app.route("/sign_up/save/mhs", methods=["POST"])
def sign_up_mhs():
    username_receive = request.form['username_give']
    nim_receive = request.form['nim_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "nim": nim_receive,                               
        "password": password_hash,                                  
        "profile_name": username_receive,                           
        "profile_pic": "profile_pics/profile_placeholder.jpeg",                                          
        "profile_pic_real": "profile_pics/profile_placeholder.jpeg", 
        "profile_info": "profile_pics/profile_placeholder.jpeg"                                          
    }
    db.mahasiswa.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/secret', methods=['GET'])
def secret():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.petugas.find_one({"username": payload("id")})
        return render_template('secret.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/beranda')
def beranda():
    return render_template("homepetugas.html")

@app.route('/loginpetugas')
def loginpetugas():
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.petugas.find_one({'nik': payload.get('nik')})
        riwayat_entries = list(db.riwayat.find({}, {'_id': False}))
        # Fetch the total number of students from the 'mahasiswa' collection
        total_siswa = db.mahasiswa.count_documents({})

        # Fetch the total number of books from the 'buku' collection
        total_buku = db.buku.count_documents({})

        # Fetch the total number of transactions from the 'peminjaman' collection
        total_transaksi = db.peminjaman.count_documents({})

        return render_template('dashboard.html', user_info=user_info, total_siswa=total_siswa, total_buku=total_buku, total_transaksi=total_transaksi, riwayat_entries=riwayat_entries)
    except (jwt.ExpiredSignatureError,jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/katalog')
def katalog():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.mahasiswa.find_one({'nim': payload.get('nim')})
        return render_template('katalog.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('homemhs'))

@app.route('/dashboardmhs')
def dashboardmhs():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.mahasiswa.find_one({'nim': payload.get('nim')})
        
        # Fetch permintaan data for the logged-in nim
        nim_permintaan = payload.get("nim")
        permintaan_list = list(db.permintaan.find({"nim": nim_permintaan}, {'_id': 0}))
        
        nim_peminjaman = payload.get("nim")
        peminjaman_list = list(db.peminjaman.find({"nim": nim_peminjaman}, {'_id': 0}))
        
        nim_riwayat = payload.get("nim")
        riwayat_list = list(db.riwayat.find({"nim": nim_riwayat}, {'_id': 0}))

        return render_template('dashboardmhs.html', user_info=user_info, permintaan_list=permintaan_list, peminjaman_list=peminjaman_list, riwayat_list=riwayat_list)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('homemhs'))
    

@app.route('/kelola')
def kelola():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.petugas.find_one({'nik': payload.get('nik')})
        buku_cursor = db.buku.find({}, {'_id': 0})
        # Buat daftar buku dari cursor
        buku_list = [buku for buku in buku_cursor]
        return render_template('kelola.html', user_info=user_info, buku_list=buku_list)
    except (jwt.ExpiredSignatureError,jwt.exceptions.DecodeError):
        return redirect(url_for('home'))

@app.route('/peminjaman')
def peminjaman():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        # Fetch the list of usernames from the 'mahasiswa' collection
        user_info = db.petugas.find_one({'nik': payload.get('nik')})
        mahasiswa_list = db.mahasiswa.find({}, {'nim': 1, '_id': 0})  # Ambil nim, bukan username
        permintaan_list = db.permintaan.find({}, {'nim': 1, 'judul': 1, 'tanggal_pinjam': 1, '_id': 0})
        # Fetch the list of books from the 'buku' collection
        buku_list = db.buku.find({}, {'judul': 1, '_id': 0})
        return render_template('peminjaman.html', user_info=user_info, mahasiswa_list=mahasiswa_list, buku_list=buku_list, permintaan_list=permintaan_list)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/terima_permintaan', methods=['POST'])
def terima_permintaan():
    try:
        # Ambil data dari permintaan
        nim_receive = request.form.get('nim')
        judul_receive = request.form.get('judul')
        tanggal_pinjam_receive = request.form.get('tanggal_pinjam')

        # Insert data ke peminjaman
        doc_peminjaman = {
            "nim": nim_receive,
            "buku": judul_receive,
            "tanggal": tanggal_pinjam_receive,
            "status": "pending"
        }
        db.peminjaman.insert_one(doc_peminjaman)

        # Hapus data dari permintaan
        db.permintaan.delete_one({"nim": nim_receive, "judul": judul_receive, "tanggal_pinjam": tanggal_pinjam_receive})

        return jsonify({'result': 'success', 'msg': 'Permintaan diterima'})
    except Exception as e:
        return jsonify({'result': 'fail', 'error': str(e)})


@app.route('/save_peminjaman', methods=['POST'])
def save_peminjaman():
    try:
        # Access form data
        mahasiswa = request.form["mahasiswa"]
        buku = request.form["buku"]
        date = request.form["date"]

        # Insert peminjaman data into the peminjaman collection
        doc_peminjaman = {
            "nim": mahasiswa,
            "buku": buku,
            "tanggal": date,
            "status": "Pending"  # You can set an initial status as needed
        }
        db.peminjaman.insert_one(doc_peminjaman)

        # Decrement the stock of the corresponding book in the buku collection
        db.buku.update_one(
            {"judul": buku},
            {"$inc": {"stock": -1}}
        )

        return '', 204  # No content (success)

    except Exception as e:
        print(str(e))
        return '', 500  # Internal Server Error
    

@app.route('/pengembalian')
def pengembalian():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        user_info = db.petugas.find_one({'nik': payload.get('nik')})
    # Fetch the list of peminjaman from the 'peminjaman' collection
        peminjaman_list = db.peminjaman.find({}, {'nim': 1, 'buku': 1, 'tanggal': 1, '_id': 0})

    # Pass the list to the template
        return render_template('pengembalian.html', user_info=user_info, peminjaman_list=peminjaman_list)
    except (jwt.ExpiredSignatureError,jwt.exceptions.DecodeError):
        return redirect(url_for('home'))
    
@app.route('/selesai_peminjaman', methods=['POST'])
def selesai_peminjaman():
    try:
        # Access form data
        nim_receive = request.form.get('nim')
        buku_receive = request.form.get('buku')
        tanggal_receive = request.form.get('tanggal')

        # Insert data into the "riwayat" collection
        doc_riwayat = {
            "nim": nim_receive,
            "buku": buku_receive,
            "tanggal": tanggal_receive,
            "status": "completed"
        }
        db.riwayat.insert_one(doc_riwayat)

        # Remove data from the "peminjaman" collection
        db.peminjaman.delete_one({"nim": nim_receive, "buku": buku_receive, "tanggal": tanggal_receive})

        return jsonify({'result': 'success', 'msg': 'Peminjaman selesai'})
    except Exception as e:
        return jsonify({'result': 'fail', 'error': str(e)})
    

@app.route('/tabel/buku', methods=['GET'])
def show_buku():
    articles = list(db.buku.find({},{'_id':False}))
    return jsonify({'articles': articles})

@app.route('/katalog/buku', methods=['GET'])
def katalog_buku():
    try:
        articles = list(db.buku.find({}, {'_id': False}))
        return jsonify({'articles': articles})
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/pinjam', methods=['POST'])
def pinjam_buku():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        nim = payload.get('nim')

        # Access form data
        judul = request.form.get('judul')
        tanggal = request.form.get('tanggal')

        # Insert borrowing data into the 'permintaan' collection
        doc_permintaan = {
            "nim": nim,
            "judul": judul,
            "tanggal_pinjam": tanggal,
            "status": "Pending"  # You can set an initial status as needed
        }
        db.permintaan.insert_one(doc_permintaan)
        
        db.buku.update_one(
            {"judul": judul},
            {"$inc": {"stock": -1}}
        )

        return jsonify({'result': 'success'})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({'result': 'fail', 'msg': 'Token expired or invalid'})


@app.route('/save_buku', methods=['POST'])
def save_buku():
    judul_receive = request.form["judul_give"]
    tautan_receive = request.form["tautan_give"]
    isbn_receive = request.form["isbn_give"]
    posisi_receive = request.form["posisi_give"]
    stock_receive = int(request.form["stock_give"])
    deskripsi_receive = request.form["deskripsi_give"]

    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    cover = request.files["cover_give"]
    extension = cover.filename.split('.')[-1]
    covername = f'static/img/buku-{mytime}.{extension}'
    cover.save(covername)
    
    time = today.strftime('%Y.%m.%d')

    doc = {
    'cover': covername,
    'judul' : judul_receive,
    'isbn': isbn_receive,
    'tautan': tautan_receive,
    'posisi': posisi_receive,
    'stock': stock_receive,
    'deskripsi': deskripsi_receive,
    'time' : time,
}
    db.buku.insert_one(doc)
    
    return jsonify({'msg':'Upload complete!'})

@app.route("/delete/buku", methods=["POST"])
def delete_buku():
    try:
        judul_receive = request.form["judul_give"]
        db.buku.delete_one({'judul': judul_receive})
        return jsonify({'msg': 'List Deleted!'})
    except Exception as e:
        return jsonify({'error': str(e)})
    
@app.route('/edit_buku', methods=['POST'])
def edit_buku():
    try:
        # Access form data
        judul = request.form.get('judul_give')
        isbn = request.form.get('isbn_give')
        posisi = request.form.get('posisi_give')
        stock = request.form.get('stock_give')
        deskripsi = request.form.get('deskripsi_give')

        # Handle cover file separately if needed

        # Perform update operation in MongoDB based on judul (book title)
        db.buku.update_one(
            {'judul': judul},
            {'$set': {'isbn': isbn, 'posisi': posisi, 'stock': stock, 'deskripsi': deskripsi}}
        )

        return jsonify({'msg': 'Book updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run("0.0.0.0", port=5000 , debug=True)