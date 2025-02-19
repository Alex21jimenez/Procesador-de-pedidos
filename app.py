from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import sqlite3

app = Flask(__name__)
DATABASE = "pedidos.db"

# Función para inicializar la base de datos
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
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

@app.route("/")
def index():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, SUM(cantidad) 
            FROM pedidos 
            GROUP BY numero_parte, nombre_parte, almacen, fecha_vencimiento, ran
        """)
        pedidos = cursor.fetchall()

    data = {}
    semanas = set()

    for pedido in pedidos:
        numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, cantidad = pedido

        if numero_parte not in data:
            data[numero_parte] = {
                "Número de Parte": numero_parte,
                "Nombre de la Parte": nombre_parte,
                "Total CDR": 0,
                "Total APRC": 0,
                "Total Renault": 0
            }

        semana = fecha_vencimiento  # Asumimos que la fecha ya está en formato de semana
        semanas.add(semana)

        if semana not in data[numero_parte]:
            data[numero_parte][semana] = {"CDR": 0, "APRC": 0, "Renault": 0}

        data[numero_parte][semana][almacen] += cantidad
        data[numero_parte][f"Total {almacen}"] += cantidad

    return render_template("table.html", header="FASO - Procesador de Pedidos", data=data.values(), semanas=sorted(semanas))

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return redirect(request.url)

    files = request.files.getlist("files")
    almacen = request.form.get("almacen")

    if almacen not in ["CDR", "APRC", "Renault"]:
        return "Almacén no válido", 400

    for file in files:
        if file.filename == "":
            continue

        df = pd.read_excel(file, dtype={"LIN03": str})
        df.columns = df.columns.str.strip().str.upper()

        column_mapping = {
            "LIN03": "numero_parte",
            "REF02": "nombre_parte",
            "FST01": "cantidad",
            "FST04": "fecha_vencimiento",
            "FST09": "ran"
        }

        df.rename(columns=column_mapping, inplace=True)
        expected_columns = set(column_mapping.values())

        if not expected_columns.issubset(df.columns):
            return f"Error: Archivo inválido. Se esperaban las columnas {expected_columns}, pero se encontraron {df.columns.tolist()}", 400

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO pedidos (numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, cantidad) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (row["numero_parte"], row["nombre_parte"], almacen, row["fecha_vencimiento"], row["ran"], row["cantidad"]))
            conn.commit()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

