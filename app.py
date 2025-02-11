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
            cantidad INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Llamamos a la función para crear la base de datos si no existe
init_db()

def procesar_archivo(file):
    df = pd.read_excel(file, dtype=str)
    columnas_interes = ["LIN03", "REF02", "FST01", "FST04"]
    df_limpio = df[columnas_interes].copy()
    df_limpio["FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d", errors='coerce')
    df_limpio.dropna(subset=["FST04"], inplace=True)  # Elimina fechas inválidas
    df_limpio["Semana"] = df_limpio["FST04"].dt.strftime("%U")  # Número de la semana
    
    df_limpio["FST01"] = pd.to_numeric(df_limpio["FST01"], errors='coerce').fillna(0).astype(int)
    
    df_pivot = df_limpio.pivot_table(index=["LIN03", "REF02"],
                                     columns="Semana",
                                     values="FST01",
                                     aggfunc="sum",
                                     fill_value=0)
    df_pivot.reset_index(inplace=True)
    semanas_numeros = list(df_pivot.columns[2:])
    
    df_pivot.columns = ["Número de Parte", "Nombre de la Parte"] + semanas_numeros
    
    semanas_global.clear()
    semanas_global.extend(semanas_numeros)
    
    return df_pivot.to_dict(orient='records')

@app.route('/')
def index():
    global data_global

    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT numero_parte, nombre_parte, semana, cantidad FROM pedidos")
    pedidos = cursor.fetchall()
    conn.close()

    data_global = []
    for row in pedidos:
        pedido_dict = next((p for p in data_global if p["Número de Parte"] == row[0]), None)
        if not pedido_dict:
            pedido_dict = {"Número de Parte": row[0], "Nombre de la Parte": row[1]}
            data_global.append(pedido_dict)
        pedido_dict[row[2]] = row[3]

    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

@app.route('/upload', methods=['POST'])
def upload():
    global data_global
    files = request.files.getlist('files')
    
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pedidos")  # Esto borra los registros anteriores
    
    for file in files:
        try:
            datos_procesados = procesar_archivo(file)
            
            for pedido in datos_procesados:
                for semana, cantidad in pedido.items():
                    if semana not in ["Número de Parte", "Nombre de la Parte"]:
                        cantidad = int(cantidad) if str(cantidad).isdigit() else 0  # Validación de enteros
                        cantidad = min(cantidad, 2147483647)  # Límite de INTEGER en SQLite
                        cursor.execute("""
                            INSERT INTO pedidos (numero_parte, nombre_parte, semana, cantidad) 
                            VALUES (?, ?, ?, ?)
                        """, (pedido["Número de Parte"], pedido["Nombre de la Parte"], semana, cantidad))
        except Exception as e:
            print("Error procesando archivo:", e)
            conn.close()
            return str(e), 400  # Retornar error
    
    conn.commit()
    conn.close()
    
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)


