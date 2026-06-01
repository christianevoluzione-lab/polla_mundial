import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide")
st.title("🏆 Polla Mundial 2026")

# ==============================
# CONEXIÓN GOOGLE SHEETS
# ==============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(credentials)

sheet = client.open("polla_mundial").sheet1
config_sheet = client.open("polla_mundial").worksheet("CONFIG")

# ==============================
# CARGAR CONFIG
# ==============================
config_data = config_sheet.get_all_records()
config = {row["clave"]: row["valor"] for row in config_data}

def partido_abierto(partido_id):
    if config.get("estado") == "cerrado":
        return False
    return config.get(partido_id, "abierto") == "abierto"

# ==============================
# CARGAR RESPUESTAS
# ==============================
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ==============================
# USUARIO
# ==============================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

# ==============================
# FUNCIÓN GUARDAR
# ==============================
def guardar_respuesta(nombre, partido, valor):
    data = sheet.get_all_records()
    nombres = [row["Nombre"] for row in data]

    if nombre in nombres:
        fila = nombres.index(nombre) + 2
    else:
        fila = len(data) + 2
        sheet.update_cell(fila, 1, nombre)

    columnas = sheet.row_values(1)
    col = columnas.index(partido) + 1

    sheet.update_cell(fila, col, valor)

# ==============================
# FUNCION PARTIDO
# ==============================
def render_partido(partido_id, equipo_a, equipo_b):

    key_sel = f"{partido_id}_sel"
    key_lock = f"{partido_id}_lock"

    if key_sel not in st.session_state:
        st.session_state[key_sel] = None

    if key_lock not in st.session_state:
        st.session_state[key_lock] = False

    # cargar si ya existe
    if nombre in df["Nombre"].values:
        fila = df[df["Nombre"] == nombre]
        valor = fila[partido_id].values[0]

        if pd.notna(valor):
            st.session_state[key_sel] = valor
            st.session_state[key_lock] = True

    col1, col2, col3, col4 = st.columns([3,1,3,1])

    # botón A
    with col1:
        if st.session_state[key_sel] == "A":
            st.markdown(f"<div style='background-color:#00e600;padding:8px;text-align:center'>{equipo_a}</div>", unsafe_allow_html=True)
        else:
            if st.button(equipo_a, key=key_sel+"A") and not st.session_state[key_lock] and partido_abierto(partido_id):
                st.session_state[key_sel] = "A"

    # VS
    with col2:
        st.markdown("<center>vs</center>", unsafe_allow_html=True)

    # botón B
    with col3:
        if st.session_state[key_sel] == "B":
            st.markdown(f"<div style='background-color:#00e600;padding:8px;text-align:center'>{equipo_b}</div>", unsafe_allow_html=True)
        else:
            if st.button(equipo_b, key=key_sel+"B") and not st.session_state[key_lock] and partido_abierto(partido_id):
                st.session_state[key_sel] = "B"

    # guardar
    with col4:
        if not st.session_state[key_lock] and partido_abierto(partido_id):
            if st.button("✅", key=key_sel+"save") and st.session_state[key_sel]:
                guardar_respuesta(nombre, partido_id, st.session_state[key_sel])
                st.session_state[key_lock] = True

    # empate
    if st.session_state[key_sel] == "E":
        st.markdown("<div style='background-color:#00e600;padding:5px;text-align:center'>Empate</div>", unsafe_allow_html=True)
    else:
        if st.button("Empate", key=key_sel+"E") and not st.session_state[key_lock] and partido_abierto(partido_id):
            st.session_state[key_sel] = "E"

    if not partido_abierto(partido_id):
        st.caption("🔒 Partido cerrado")

    st.divider()

# ==============================
# PARTIDOS (ejemplo grupo A)
# ==============================
partidos = [
("P1","México","Sudáfrica"),
("P2","Corea","Checa"),
("P3","Checa","Sudáfrica")
]

for p in partidos:
    render_partido(p[0], p[1], p[2])

# ==============================
# RANKING
# ==============================
def calcular_puntos():
    ranking = []

    for _, fila in df.iterrows():
        nombre = fila["Nombre"]
        puntos = 0

        for col in df.columns:
            if col == "Nombre":
                continue

            if col in df.columns and pd.notna(fila[col]):
                puntos += 1

        ranking.append((nombre, puntos))

    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking

st.header("🏆 Ranking")

ranking = calcular_puntos()
tabla = pd.DataFrame(ranking, columns=["Nombre", "Puntos"])

st.dataframe(tabla, use_container_width=True)
