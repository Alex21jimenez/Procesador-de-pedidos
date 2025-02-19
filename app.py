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
        cursor.execute("SELECT numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, SUM(cantidad) FROM pedidos GROUP BY numero_parte, nombre_parte, almacen, fecha_vencimiento, ran")
        pedidos = cursor.fetchall()

    data = {}

    for pedido in pedidos:
        numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, cantidad = pedido

        if numero_parte not in data:
            data[numero_parte] = {
                "Número de Parte": numero_parte,
                "Nombre de la Parte": nombre_parte,
                "Total CDR": 0,
                "Total APRC": 0,
                "Total Renault": 0,
                "Pedidos": []
            }

        data[numero_parte]["Pedidos"].append({
            "almacen": almacen,
            "fecha_vencimiento": fecha_vencimiento,
            "ran": ran,
            "cantidad": cantidad
        })

        data[numero_parte][f"Total {almacen}"] += cantidad

    return render_template("table.html", header="FASO - Procesador de Pedidos", data=data.values())

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

        try:
            df = pd.read_excel(file, dtype=str)  # Cargar datos como texto para evitar problemas de conversión
        except Exception as e:
            return f"Error al leer el archivo: {str(e)}", 400

        print(f"Columnas detectadas en el archivo {file.filename}:", df.columns.tolist())

        # Convertir nombres de columnas a mayúsculas y eliminar espacios
        df.columns = df.columns.str.strip().str.upper()

        # Definir el mapeo esperado de columnas
        column_mapping = {
            "LIN03": "numero_parte",
            "REF02": "nombre_parte",
            "FST01": "cantidad",
            "FST04": "fecha_vencimiento",
            "FST09": "ran"
        }

        # Verificar si todas las columnas necesarias están en el archivo
        missing_columns = [col for col in column_mapping if col not in df.columns]
        if missing_columns:
            return f"Error: Archivo inválido. Faltan las columnas {missing_columns}. Se encontraron {df.columns.tolist()}", 400

        # Renombrar las columnas
        df.rename(columns=column_mapping, inplace=True)

        # Verificar que los datos no estén vacíos
        if df.empty:
            return "Error: El archivo no contiene datos válidos", 400

        # Imprimir algunos valores para depuración
        print(df.head())

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        "INSERT INTO pedidos (numero_parte, nombre_parte, almacen, fecha_vencimiento, ran, cantidad) VALUES (?, ?, ?, ?, ?, ?)", 
                        (row["numero_parte"], row["nombre_parte"], almacen, row["fecha_vencimiento"], row["ran"], row["cantidad"])
                    )
                except Exception as e:
                    print(f"Error insertando datos: {row.to_dict()} - {str(e)}")

            conn.commit()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

