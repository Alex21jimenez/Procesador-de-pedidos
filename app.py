import pandas as pd
import sqlite3
import os
from flask import Flask, render_template, request

app = Flask(__name__)

data_global = []
meses_global = []

# Diccionario para traducir los meses a español
MESES_TRADUCCION = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

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
    df = pd.read_excel(file, dtype=str)
    columnas_interes = ["LIN03", "REF02", "FST01", "FST04", "FST09"]
    df_limpio = df[columnas_interes].copy()
    df_limpio["FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d")
    df_limpio["Semana"] = df_limpio["FST04"].dt.to_period("W").astype(str)
    df_limpio["Mes"] = df_limpio["FST04"].dt.strftime('%B').apply(lambda x: MESES_TRADUCCION.get(x, x))
    
    df_pivot = df_limpio.pivot_table(index=["LIN03", "REF02"],
                                     columns="Semana",
                                     values="FST01",
                                     aggfunc="sum",
                                     fill_value=0)
    df_pivot.reset_index(inplace=True)
    semanas_numeros = [str(pd.to_datetime(semana.split("/")[0]).weekofyear) for semana in df_pivot.columns[2:]]
    meses = [MESES_TRADUCCION.get(pd.to_datetime(semana.split("/")[0]).strftime('%B'), pd.to_datetime(semana.split("/")[0]).strftime('%B')) for semana in df_pivot.columns[2:]]
    
    df_pivot.columns = ["Número de Parte", "Nombre de la Parte"] + semanas_numeros
    
    meses_global.clear()
    meses_global.extend(meses)
    
    return df_pivot.to_dict(orient='records')

@app.route('/')
def index():
    global data_global

    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT numero_parte, nombre_parte, semana, cantidad FROM pedidos")
    pedidos = cursor.fetchall()
    conn.close()

    data_global = [
        {"Número de Parte": row[0], "Nombre de la Parte": row[1], "Semana": row[2], "Cantidad": row[3]} 
        for row in pedidos
    ]

    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", meses=meses_global, logo_url="/static/logo.jpg")

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
            data_global.extend(datos_procesados)

            # Insertar datos en la base de datos
            for pedido in datos_procesados:
                cursor.execute("""
                    INSERT INTO pedidos (numero_parte, nombre_parte, semana, cantidad) 
                    VALUES (?, ?, ?, ?)
                """, (pedido["Número de Parte"], pedido["Nombre de la Parte"], pedido.get("Semana", 0), pedido.get("Cantidad", 0)))
        except Exception as e:
            print("Error procesando archivo:", e)
            conn.close()
            return str(e), 400  # Retornar error
    
    conn.commit()
    conn.close()
    
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", meses=meses_global, logo_url="/static/logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)


