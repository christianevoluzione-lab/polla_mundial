import streamlit as st
import pandas as pd
import gspread

from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials

# ==================================
# CONFIG
# ==================================
st.set_page_config(page_title="Polla Mundial", layout="wide")
st.title("🏆 Polla Mundial 2026")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==================================
# CONEXIÓN
# ==================================
@st.cache_resource
def get_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(credentials)

client = get_client()

@st.cache_resource
def get_spreadsheet():
    return client.open_by_key("1G2fNVyWBURB1Q4LG4POU65gpv3nW5wu80ivoHUSqSUM")

spreadsheet = get_spreadsheet()

sheet = spreadsheet.worksheet("RESPUESTAS")
sheet_partidos = spreadsheet.worksheet("PARTIDOS")
sheet_config = spreadsheet.worksheet("CONFIG")
sheet_resultados = spreadsheet.worksheet("RESULTADOS")
# ==================================
# CARGA
# ==================================
@st.cache_data(ttl=600)
def cargar_todo():
    return {
        "respuestas": sheet.get_all_records(),
        "partidos": sheet_partidos.get_all_records(),
        "config": sheet_config.get_all_records(),
        "resultados": sheet_resultados.get_all_records()
    }

data = cargar_todo()

df = pd.DataFrame(data["respuestas"])
if not df.empty:
    df.columns = df.columns.str.strip()
partidos = data["partidos"]

config = {str(r["clave"]).strip(): str(r["valor"]).strip() for r in data["config"]}

# ==================================
# USUARIO
# ==================================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

nombre = nombre.strip().upper()

usuarios = df["Nombre"].astype(str).str.upper().tolist() if not df.empty else []

# Registro
if nombre not in usuarios:
    sheet.append_row([nombre])
    st.success(f"Usuario {nombre} registrado")
    st.rerun()

st.info(f"Hola {nombre}")

# ==================================
# FUNCIONES
# ==================================
def partido_abierto(pid):
    if config.get("estado") == "cerrado":
        return False
    return config.get(pid, "abierto") == "abierto"

def ya_guardado(pid):
    if df.empty or "Nombre" not in df.columns:
        return False

    fila = df[df["Nombre"].str.upper() == nombre]
    if fila.empty:
        return False

    valor = fila.iloc[0].get(pid)
    return pd.notna(valor) and str(valor).strip() != ""

# ==================================
# SESSION (CAMBIOS)
# ==================================
if "cambios" not in st.session_state:
    st.session_state["cambios"] = {}

# ==================================
# GUARDADO MASIVO
# ==================================
def guardar_masivo():

    cambios = st.session_state["cambios"]

    if not cambios:
        st.warning("No hay cambios")
        return

    nombres = df["Nombre"].astype(str).str.upper().tolist()
    columnas = df.columns.tolist()

    fila_usuario = df[df["Nombre"].str.upper() == nombre]

    updates = []

    for pid, valor in cambios.items():

        # Verificar si ya existe un pronóstico guardado
        if not fila_usuario.empty:
            valor_actual = fila_usuario.iloc[0].get(pid)

            if pd.notna(valor_actual) and str(valor_actual).strip() != "":
                continue  # No permitir sobrescribir

        fila = nombres.index(nombre) + 2
        col = columnas.index(pid) + 1

        celda = rowcol_to_a1(fila, col)

        updates.append({
            "range": celda,
            "values": [[valor]]
        })

    if not updates:
        st.warning("Todos esos partidos ya fueron guardados.")
        return

    sheet.batch_update(updates)

    st.success("✅ Pronósticos guardados")
    st.session_state["cambios"] = {}
    st.rerun(
# ==================================
# RENDER
# ==================================
def render_partido(pid, a, b):

    bloqueado = ya_guardado(pid)

    col1, col2, col3 = st.columns(3)

    if col1.button(a, key=f"{pid}_A", disabled=bloqueado):
        if partido_abierto(pid):
            st.session_state["cambios"][pid] = "A"

    if col2.button("Empate", key=f"{pid}_E", disabled=bloqueado):
        if partido_abierto(pid):
            st.session_state["cambios"][pid] = "E"

    if col3.button(b, key=f"{pid}_B", disabled=bloqueado):
        if partido_abierto(pid):
            st.session_state["cambios"][pid] = "B"

    # mostrar valor guardado
    if bloqueado:
        valor = df[df["Nombre"].str.upper() == nombre].iloc[0][pid]
        st.success(f"🔒 Guardado: {valor}")

    # mostrar selección actual (no guardada)
    elif pid in st.session_state["cambios"]:
        st.caption(f"Seleccionado: {st.session_state['cambios'][pid]}")

    if not partido_abierto(pid):
        st.caption("🔒 Partido cerrado")

    st.divider()

# ==================================
# MOSTRAR PARTIDOS
# ==================================
grupo_actual = ""

for p in partidos:

    grupo = str(p["GRUPO"]).strip()

    if grupo != grupo_actual:
        st.header(f"🏆 {grupo}")
        grupo_actual = grupo

    render_partido(
        str(p["ID"]).strip(),
        str(p["Equipo A"]).strip(),
        str(p["Equipo B"]).strip()
    )

# ==================================
# BOTÓN GUARDAR
# ==================================
st.button("💾 Guardar pronósticos", on_click=guardar_masivo)

# ==================================
# RANKING
# ==================================
def calcular_ranking():

    ranking = []

    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for r in data["resultados"] if r["Resultado"]
    }

    for _, fila in df.iterrows():

        aciertos = 0
        total = 0

        for partido, real in resultados.items():

            if partido not in df.columns:
                continue

            resp = fila.get(partido)

            if pd.notna(resp) and resp != "":
                total += 1
                if str(resp).upper() == real:
                    aciertos += 1

        porcentaje = round((aciertos / total) * 100, 2) if total else 0

        ranking.append((fila["Nombre"], aciertos, total, porcentaje))

    ranking.sort(key=lambda x: x[3], reverse=True)

    return ranking

with st.expander("🏆 Ranking"):

    ranking = calcular_ranking()

    if ranking:
        st.dataframe(pd.DataFrame(
            ranking,
            columns=["Nombre", "Aciertos", "Total", "%"]
        ))
    else:
        st.info("Sin resultados todavía")
