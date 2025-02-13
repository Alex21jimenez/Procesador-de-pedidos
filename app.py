import pandas as pd
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DATABASE = "pedidos.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_parte TEXT,
                nombre_parte TEXT,
                almacen TEXT,
                semana INTEGER,
                cantidad INTEGER
            )
        """)
        conn.commit()

@app.route("/")
def index():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT numero_parte, nombre_parte, almacen, semana, SUM(cantidad) 
            FROM pedidos 
            GROUP BY numero_parte, nombre_parte, almacen, semana
        """)
        pedidos = cursor.fetchall()

    data = {}
    semanas = set()

    for pedido in pedidos:
        numero_parte, nombre_parte, almacen, semana, cantidad = pedido
        semanas.add(semana)

        if numero_parte not in data:
            data[numero_parte] = {
                "Número de Parte": numero_parte,
                "Nombre de la Parte": nombre_parte,
                "Total CDR": 0,
                "Total APRC": 0,
                "Total Renault": 0
            }

        if semana not in data[numero_parte]:
            data[numero_parte][semana] = {"CDR": 0, "APRC": 0, "Renault": 0}

        data[numero_parte][semana][almacen] = cantidad
        data[numero_parte][f"Total {almacen}"] += cantidad

    return render_template("table.html", header="FASO - Procesador de Pedidos", data=data.values(), semanas=sorted(semanas))

@app.route("/upload", methods=["POST"])
def upload():
    if 'files' not in request.files:
        return redirect(request.url)

    files = request.files.getlist("files")
    almacen = request.form.get("almacen")

    if almacen not in ["CDR", "APRC", "Renault"]:
        return "Almacén no válido", 400

    for file in files:
        if file.filename == "":
            continue

        df = pd.read_excel(file, dtype={"Número de Parte": str})  # Convertir a string para evitar errores

        # Limpieza de columnas
        df.columns = df.columns.str.strip()

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        "INSERT INTO pedidos (numero_parte, nombre_parte, almacen, semana, cantidad) VALUES (?, ?, ?, ?, ?)",
                        (row["Número de Parte"], row["Nombre de la Parte"], almacen, row["Semana"], row["Cantidad"])
                    )
                except KeyError:
                    return f"Error: La columna esperada no se encontró en el archivo. Columnas detectadas: {df.columns.tolist()}", 400
            conn.commit()

    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

