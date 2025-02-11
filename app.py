import pandas as pd
import sqlite3
import os
from flask import Flask, render_template, request

app = Flask(__name__)

data_global = []
semanas_global = []

# Función para inicializar la base de datos y la tabla
def init_db():
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_parte TEXT,
            nombre_parte TEXT,
            semana TEXT,
            cantidad INTEGER,
            almacen TEXT
        )
    """)
    conn.commit()
    conn.close()

# Llamamos a la función para crear la base de datos si no existe
init_db()

def procesar_archivo(file, almacen):
    df = pd.read_excel(file, dtype=str)
    columnas_interes = ["LIN03", "REF02", "FST01", "FST04"]
    df_limpio = df[columnas_interes].copy()
    df_limpio["FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d", errors='coerce')
    df_limpio.dropna(subset=["FST04"], inplace=True)  # Elimina fechas inválidas
    df_limpio["Semana"] = df_limpio["FST04"].dt.strftime("%U")  # Número de la semana
    
    df_limpio["FST01"] = pd.to_numeric(df_limpio["FST01"], errors='coerce').fillna(0).astype(int)
    df_limpio["Almacén"] = almacen
    
    return df_limpio

@app.route('/')
def index():
    global data_global

    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT numero_parte, nombre_parte, semana, cantidad, almacen FROM pedidos")
    pedidos = cursor.fetchall()
    conn.close()

    data_dict = {}
    almacenes = set()
    
    for row in pedidos:
        numero_parte, nombre_parte, semana, cantidad, almacen = row
        almacenes.add(almacen)
        if numero_parte not in data_dict:
            data_dict[numero_parte] = {"Número de Parte": numero_parte, "Nombre de la Parte": nombre_parte, "Total CDR": 0, "Total APRC": 0, "Total Renault": 0}
        
        if semana not in data_dict[numero_parte]:
            data_dict[numero_parte][semana] = {}
        data_dict[numero_parte][semana][almacen] = cantidad
        
        # Sumar a la columna de total por almacén
        if almacen == "CDR":
            data_dict[numero_parte]["Total CDR"] += cantidad
        elif almacen == "APRC":
            data_dict[numero_parte]["Total APRC"] += cantidad
        elif almacen == "Renault":
            data_dict[numero_parte]["Total Renault"] += cantidad
    
    data_global = list(data_dict.values())
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg", almacenes=list(almacenes))

@app.route('/upload', methods=['POST'])
def upload():
    global data_global
    files = request.files.getlist('files')
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pedidos")  # Esto borra los registros anteriores
    
    for file in files:
        almacen = request.form.get("almacen", "Desconocido")  # Se espera que el formulario indique el almacén
        try:
            datos_procesados = procesar_archivo(file, almacen)
            for _, row in datos_procesados.iterrows():
                cantidad = min(row["FST01"], 2147483647)  # Límite de INTEGER en SQLite
                cursor.execute(
                    "INSERT INTO pedidos (numero_parte, nombre_parte, semana, cantidad, almacen) VALUES (?, ?, ?, ?, ?)",
                    (row["LIN03"], row["REF02"], row["Semana"], cantidad, row["Almacén"])
                )
        except Exception as e:
            print("Error procesando archivo:", e)
            conn.close()
            return str(e), 400  # Retornar error
    
    conn.commit()
    conn.close()
    
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)

