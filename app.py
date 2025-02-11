import pandas as pd
import sqlite3
from flask import Flask, render_template, request

app = Flask(__name__)

# Variables globales para la interfaz
data_global = []
semanas_global = []

# 📌 Función para inicializar la base de datos SQLite
def init_db():
    with sqlite3.connect("pedidos.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_parte TEXT,
                nombre_parte TEXT,
                semana TEXT,
                cantidad INTEGER
            )
        """)
        conn.commit()

# Inicializamos la base de datos
init_db()

# 📌 Función para procesar archivo Excel y extraer información relevante
def procesar_archivo(file):
    try:
        df = pd.read_excel(file, dtype=str)
        columnas_interes = ["LIN03", "REF02", "FST01", "FST04"]
        
        if not set(columnas_interes).issubset(df.columns):
            raise ValueError("El archivo no tiene las columnas requeridas")

        df_limpio = df[columnas_interes].copy()
        df_limpio["FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d")
        df_limpio["Semana"] = df_limpio["FST04"].dt.strftime("%U")  # Extraer número de semana

        # Crear tabla pivote con semanas como columnas
        df_pivot = df_limpio.pivot_table(index=["LIN03", "REF02"],
                                         columns="Semana",
                                         values="FST01",
                                         aggfunc="sum",
                                         fill_value=0)

        df_pivot.reset_index(inplace=True)
        semanas_numeros = list(df_pivot.columns[2:])  # Lista de semanas únicas
        df_pivot.columns = ["Número de Parte", "Nombre de la Parte"] + semanas_numeros

        # Guardamos las semanas en variable global
        semanas_global.clear()
        semanas_global.extend(semanas_numeros)

        return df_pivot.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error procesando archivo: {e}")
        return []

# 📌 Ruta principal - Cargar datos de la base de datos y mostrar tabla
@app.route('/')
def index():
    global data_global

    with sqlite3.connect("pedidos.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT numero_parte, nombre_parte, semana, cantidad FROM pedidos")
        pedidos = cursor.fetchall()

    # Convertir datos en formato adecuado para la tabla
    data_global = []
    for row in pedidos:
        pedido_dict = next((p for p in data_global if p["Número de Parte"] == row[0]), None)
        if not pedido_dict:
            pedido_dict = {"Número de Parte": row[0], "Nombre de la Parte": row[1]}
            data_global.append(pedido_dict)
        pedido_dict[row[2]] = row[3]

    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

# 📌 Ruta para cargar pedidos desde un archivo
@app.route('/upload', methods=['POST'])
def upload():
    global data_global
    files = request.files.getlist('files')

    with sqlite3.connect("pedidos.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pedidos")  # Limpiar tabla antes de cargar nuevos datos

        for file in files:
            datos_procesados = procesar_archivo(file)

            for pedido in datos_procesados:
                for semana, cantidad in pedido.items():
                    if semana not in ["Número de Parte", "Nombre de la Parte"]:
                        try:
                            cantidad = int(cantidad) if cantidad.isdigit() else 0
                            cursor.execute("""
                                INSERT INTO pedidos (numero_parte, nombre_parte, semana, cantidad) 
                                VALUES (?, ?, ?, ?)
                            """, (pedido["Número de Parte"], pedido["Nombre de la Parte"], semana, cantidad))
                        except Exception as e:
                            print(f"Error insertando en la BD: {e}")

        conn.commit()

    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

# 📌 Iniciar la aplicación en modo debug
if __name__ == '__main__':
    app.run(debug=True)

