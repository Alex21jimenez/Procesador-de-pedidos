import pandas as pd
import tkinter as tk
from tkinter import filedialog
from flask import Flask, render_template, request
import locale

# Configurar idioma en español


app = Flask(__name__)

data_global = []
meses_global = []

def procesar_archivo(file_path):
    df = pd.read_excel(file_path)
    columnas_interes = ["LIN03", "REF02", "FST01", "FST04", "FST09"]
    df_limpio = df[columnas_interes].copy()
    df_limpio.loc[:, "FST04"] = pd.to_datetime(df_limpio["FST04"], format="%Y%m%d")
    df_limpio.loc[:, "Semana"] = df_limpio["FST04"].dt.to_period("W").astype(str)
    meses_traduccion = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}
df_limpio.loc[:, "Mes"] = df_limpio["FST04"].dt.strftime('%B').map(meses_traduccion)

    df_pivot = df_limpio.pivot_table(index=["LIN03", "REF02"], 
                                     columns="Semana", 
                                     values="FST01", 
                                     aggfunc="sum", 
                                     fill_value=0)
    df_pivot.reset_index(inplace=True)
    semanas_numeros = [str(pd.to_datetime(semana.split("/")[0]).weekofyear) for semana in df_pivot.columns[2:]]
    meses = [pd.to_datetime(semana.split("/")[0]).strftime('%B').capitalize() for semana in df_pivot.columns[2:]]
    df_pivot.columns = ["Número de Parte", "Nombre de la Parte"] + semanas_numeros
    meses_global.clear()
    meses_global.extend(meses)
    return df_pivot.to_dict(orient='records')

@app.route('/')
def index():
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", meses=meses_global, logo_url="/static/logo.jpg")

@app.route('/upload', methods=['POST'])
def upload():
    global data_global
    files = request.files.getlist('files')
    for file in files:
        datos_procesados = procesar_archivo(file)
        data_global.extend(datos_procesados)
    return render_template('table.html', data=data_global, header="FASO - Procesador de Pedidos", meses=meses_global, logo_url="/static/logo.jpg")

if __name__ == '__main__':
    app.run(debug=True)



