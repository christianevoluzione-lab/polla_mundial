import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==================================
# CONFIG STREAMLIT
# ==================================
st.set_page_config(
    page_title="Polla Mundial 2026",
    page_icon="馃弳",
    layout="wide"
)

st.title("馃弳 Polla Mundial 2026")

# ==================================
# GOOGLE SHEETS
# ==================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(credentials)

# 鉁� MEJOR: usar ID
spreadsheet = client.open_by_key("1G2fNVyWBURB1Q4LG4POU65gpv3nW5wu80ivoHUSqSUM")

sheet = spreadsheet.sheet1
config_sheet = spreadsheet.worksheet("CONFIG")
partidos_sheet = spreadsheet.worksheet("PARTIDOS")
resultados_sheet = spreadsheet.worksheet("RESULTADOS")

# ==================================
# CACHE DATOS
# ==================================
@st.cache_data(ttl=30)
def cargar_partidos():
    return partidos_sheet.get_all_records()

@st.cache_data(ttl=30)
def cargar_config():
    config_local = {}
    data = config_sheet.get_all_records()
    for row in data:
        config_local[str(row["clave"]).strip()] = str(row["valor"]).strip()
    return config_local

@st.cache_data(ttl=10)
def cargar_dataframe():
    data = sheet.get_all_records()
    if not data:
        headers = sheet.row_values(1)
        return pd.DataFrame(columns=headers)
    df = pd.DataFrame(data)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# ==================================
# DATA
# ==================================
config = cargar_config()
partidos = cargar_partidos()
df = cargar_dataframe()

# ==================================
# FUNCIONES
# ==================================
def partido_abierto(partido_id):
    if config.get("estado", "abierto") == "cerrado":
        return False
    return config.get(partido_id, "abierto") == "abierto"

def guardar_respuesta(nombre_usuario, partido_id, valor):
    nombres = df["Nombre"].astype(str).str.upper().tolist()
    fila = nombres.index(nombre_usuario) + 2
    col = df.columns.tolist().index(partido_id) + 1
    sheet.update_cell(fila, col, valor)

# ==================================
# USUARIO
# ==================================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

nombre = nombre.strip().upper()

usuarios = []
if not df.empty and "Nombre" in df.columns:
    usuarios = df["Nombre"].astype(str).str.upper().tolist()

# REGISTRO
if nombre not in usuarios:
    nueva_fila = len(df) + 2
    sheet.update_cell(nueva_fila, 1, nombre)
    st.success(f"Usuario {nombre} registrado")
    st.cache_data.clear()
    st.rerun()

st.info(f"Bienvenido {nombre}")

# ==================================
# RENDER PARTIDO
# ==================================
def render_partido(partido_id, equipo_a, equipo_b):

    col1, col2, col3, col4 = st.columns([3,2,3,1])

    sel = st.session_state.get(partido_id, None)

    # EQUIPO A
    if col1.button(equipo_a, key=f"{partido_id}_A"):
        st.session_state[partido_id] = "A"

    # EMPATE
    if col2.button("Empate", key=f"{partido_id}_E"):
        st.session_state[partido_id] = "E"

    # EQUIPO B
    if col3.button(equipo_b, key=f"{partido_id}_B"):
        st.session_state[partido_id] = "B"

    # GUARDAR
    if col4.button("鉁�", key=f"{partido_id}_save"):
        if st.session_state.get(partido_id):
            guardar_respuesta(nombre, partido_id, st.session_state[partido_id])
            st.success("Guardado")
            st.cache_data.clear()
            st.rerun()

    st.divider()

# ==================================
# MOSTRAR PARTIDOS
# ==================================
grupo_actual = ""

for partido in partidos:

    grupo = str(partido["GRUPO"]).strip()

    if grupo and grupo != grupo_actual:
        st.header(f"馃弳 {grupo}")
        grupo_actual = grupo

    render_partido(
        str(partido["ID"]).strip(),
        str(partido["Equipo A"]).strip(),
        str(partido["Equipo B"]).strip()
    )

# ==================================
# RANKING
# ==================================
def calcular_ranking():
    ranking = []

    resultados_df = pd.DataFrame(resultados_sheet.get_all_records())
    if resultados_df.empty:
        return ranking

    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for _, r in resultados_df.iterrows()
        if r["Resultado"]
    }

    for _, fila in df.iterrows():
        nombre_jugador = fila["Nombre"]
        aciertos = 0
        evaluados = 0

        for partido, resultado_real in resultados.items():
            if partido not in df.columns:
                continue

            respuesta = fila.get(partido)

            if pd.notna(respuesta) and str(respuesta).strip() != "":
                evaluados += 1
                if str(respuesta).strip().upper() == resultado_real:
                    aciertos += 1

        porcentaje = round((aciertos / evaluados) * 100, 2) if evaluados else 0

        ranking.append((nombre_jugador, aciertos, evaluados, porcentaje))

    ranking.sort(key=lambda x: x[3], reverse=True)
    return ranking

# ==================================
# MOSTRAR RANKING
# ==================================
with st.expander("馃弳 Ranking"):

    ranking = calcular_ranking()

    if ranking:
        tabla = pd.DataFrame(
            ranking,
            columns=["Nombre", "Aciertos", "Evaluados", "%"]
        )
        st.dataframe(tabla, use_container_width=True)
    else:
        st.info("Sin resultados a煤n")
