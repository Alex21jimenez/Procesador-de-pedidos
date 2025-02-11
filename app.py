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
            semana INTEGER,
            cantidad INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Llamamos a la función para crear la base de datos si no existe
init_db()

def procesar_archivo(file):
    try:
        df = pd.read_excel(file, dtype=str)
        columnas_interes = ["LIN03", "REF02", "FST01", "FST04"]
        
        if not set(columnas_interes).issubset(df.columns):
            raise ValueError("Las columnas esperadas no están presentes en el archivo.")
        
        df_limpio = df[columnas_interes].copy()
        df_limpio["FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d", errors='coerce')
        
        # Manejo de valores inválidos
        df_limpio = df_limpio.dropna(subset=["FST04"])
        
        df_limpio["Semana"] = df_limpio["FST04"].dt.strftime("%U")  # Semana del año en números
        
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

    except Exception as e:
        print("Error procesando archivo:", e)
        return []

@app.route('/')
def index():
    global data_global

    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT numero_parte, nombre_parte, semana, cantidad FROM pedidos")
    pedidos = cursor.fetchall()
    conn.close()

    data_global = []
    pedidos_dict = {}

    for row in pedidos:
        numero_parte, nombre_parte, semana, cantidad = row
        if numero_parte not in pedidos_dict:
            pedidos_dict[numero_parte] = {
                "Número de Parte": numero_parte,
                "Nombre de la Parte": nombre_parte
            }
        pedidos_dict[numero_parte][semana] = cantidad

    data_global = list(pedidos_dict.values())

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

            if not datos_procesados:
                continue  # Si hubo un error en el archivo, lo omitimos

            data_global.extend(datos_procesados)

            for pedido in datos_procesados:
                for semana, cantidad in pedido.items():
                    if semana not in ["Número de Parte", "Nombre de la Parte"]:
                        cursor.execute("""
                            INSERT INTO pedidos (numero_parte, nombre_parte, semana, cantidad) 
                            VALUES (?, ?, ?, ?)
                        """, (pedido["Número de Parte"], pedido["Nombre de la Parte"], semana, cantidad))
        except Exception as e:
            print("Error procesando archivo:", e)
            conn.rollback()
            conn.close()
            return str(e), 400
    
    conn.commit()
    conn.close()
    
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", semanas=semanas_global, logo_url="/static/logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)

