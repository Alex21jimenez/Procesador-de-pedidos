from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Cambia esto por una clave más segura

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

DATABASE = "pedidos.db"

# **1️⃣ Crear Base de Datos (Usuarios y Pedidos)**
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        """)
        # Tabla de pedidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_parte TEXT,
                nombre_parte TEXT,
                almacen TEXT,
                fecha_vencimiento TEXT,
                ran TEXT,
                cantidad INTEGER
            )
        """)
        conn.commit()

init_db()

# **2️⃣ Modelo de Usuario para Flask-Login**
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
    if user:
        return User(*user)
    return None

# **3️⃣ Ruta de Inicio de Sesión**
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user[2], password):
            login_user(User(user[0], user[1], user[3]))
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("index"))

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")

# **4️⃣ Ruta de Cierre de Sesión**
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "success")
    return redirect(url_for("login"))

# **5️⃣ Ruta Protegida: Página Principal**
@app.route("/")
@login_required
def index():
    return render_template("table.html", header="FASO - Procesador de Pedidos")

# **6️⃣ Ruta Protegida: Subir Pedidos (Solo Marta y Admin)**
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if current_user.role not in ["admin", "marta"]:
        flash("No tienes permisos para subir archivos", "danger")
        return redirect(url_for("index"))

    # Código para manejar archivos subidos
    flash("Archivo subido correctamente", "success")
    return redirect(url_for("index"))

# **7️⃣ Ruta Protegida: Gestión de Usuarios (Solo Admin)**
@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if current_user.role != "admin":
        flash("Acceso denegado", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        role = request.form["role"]

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
                conn.commit()
                flash("Usuario agregado con éxito", "success")
            except:
                flash("Error: Usuario ya existe", "danger")

    return render_template("admin.html")

if __name__ == "__main__":
    app.run(debug=True)

