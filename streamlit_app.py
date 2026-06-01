import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==================================
# CONFIG STREAMLIT
# ==================================
st.set_page_config(layout="wide")
st.title("🏆 Polla Mundial 2026")

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

sheet = client.open("polla_mundial").sheet1
config_sheet = client.open("polla_mundial").worksheet("CONFIG")

# ==================================
# CONFIG
# ==================================
config_data = config_sheet.get_all_records()

config = {}

for row in config_data:
    config[str(row["clave"]).strip()] = str(row["valor"]).strip()

def partido_abierto(partido_id):

    if config.get("estado", "abierto") == "cerrado":
        return False

    return config.get(partido_id, "abierto") == "abierto"

# ==================================
# CARGAR DATOS
# ==================================
def cargar_dataframe():

    data = sheet.get_all_records()

    if len(data) == 0:

        headers = sheet.row_values(1)

        if not headers:
            headers = ["Nombre"]

        return pd.DataFrame(columns=headers)

    df = pd.DataFrame(data)

    df.columns = [str(c).strip() for c in df.columns]

    return df

df = cargar_dataframe()

# ==================================
# USUARIO
# ==================================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

nombre = nombre.strip().upper()

# ==================================
# ASEGURAR COLUMNA NOMBRE
# ==================================
headers = sheet.row_values(1)

if not headers:

    sheet.update(
        "A1",
        [["Nombre"]]
    )

    headers = ["Nombre"]

if "Nombre" not in headers:

    headers.insert(0, "Nombre")

    sheet.delete_rows(1)

    sheet.insert_row(headers, 1)

# ==================================
# REGISTRAR USUARIO SI NO EXISTE
# ==================================
usuarios_existentes = []

if not df.empty and "Nombre" in df.columns:
    usuarios_existentes = (
        df["Nombre"]
        .astype(str)
        .str.upper()
        .tolist()
    )

if nombre not in usuarios_existentes:

    nueva_fila = len(sheet.get_all_values()) + 1

    sheet.update_cell(
        nueva_fila,
        1,
        nombre
    )

    st.success(f"Bienvenido {nombre}")

    st.rerun()

# ==================================
# RECARGAR
# ==================================
df = cargar_dataframe()

# ==================================
# GUARDAR RESPUESTA
# ==================================
def guardar_respuesta(nombre, partido, valor):

    data = sheet.get_all_records()

    nombres = [
        str(row["Nombre"]).upper()
        for row in data
    ]

    if nombre in nombres:

        fila = nombres.index(nombre) + 2

    else:

        fila = len(data) + 2

        sheet.update_cell(
            fila,
            1,
            nombre
        )

    columnas = sheet.row_values(1)

    if partido not in columnas:

        st.error(
            f"No existe la columna {partido}"
        )

        return

    col = columnas.index(partido) + 1

    sheet.update_cell(
        fila,
        col,
        valor
    )

# ==================================
# PARTIDOS
# ==================================
def render_partido(partido_id, equipo_a, equipo_b):

    key_sel = f"{partido_id}_sel"
    key_lock = f"{partido_id}_lock"

    if key_sel not in st.session_state:
        st.session_state[key_sel] = None

    if key_lock not in st.session_state:
        st.session_state[key_lock] = False

    # Recuperar selección previa
    if (
        not df.empty
        and "Nombre" in df.columns
        and nombre in df["Nombre"].astype(str).str.upper().values
        and partido_id in df.columns
    ):

        fila = df[
            df["Nombre"]
            .astype(str)
            .str.upper() == nombre
        ]

        valor = fila[partido_id].values[0]

        if pd.notna(valor) and valor != "":

            st.session_state[key_sel] = valor
            st.session_state[key_lock] = True

    col1, col2, col3, col4 = st.columns([3,1,3,1])

    # Equipo A
    with col1:

        if st.session_state[key_sel] == "A":

            st.success(equipo_a)

        else:

            if st.button(
                equipo_a,
                key=key_sel + "A"
            ):

                if (
                    not st.session_state[key_lock]
                    and partido_abierto(partido_id)
                ):
                    st.session_state[key_sel] = "A"

    # VS
    with col2:
        st.markdown("### VS")

    # Equipo B
    with col3:

        if st.session_state[key_sel] == "B":

            st.success(equipo_b)

        else:

            if st.button(
                equipo_b,
                key=key_sel + "B"
            ):

                if (
                    not st.session_state[key_lock]
                    and partido_abierto(partido_id)
                ):
                    st.session_state[key_sel] = "B"

    # Guardar
    with col4:

        if (
            not st.session_state[key_lock]
            and partido_abierto(partido_id)
        ):

            if st.button(
                "✅",
                key=key_sel + "save"
            ):

                if st.session_state[key_sel]:

                    guardar_respuesta(
                        nombre,
                        partido_id,
                        st.session_state[key_sel]
                    )

                    st.success("Pronóstico guardado")

                    st.rerun()

    # Empate
    if st.session_state[key_sel] == "E":

        st.success("EMPATE")

    else:

        if st.button(
            "Empate",
            key=key_sel + "E"
        ):

            if (
                not st.session_state[key_lock]
                and partido_abierto(partido_id)
            ):
                st.session_state[key_sel] = "E"

    if not partido_abierto(partido_id):
        st.caption("🔒 Partido cerrado")

    st.divider()

# ==================================
# PARTIDOS
# ==================================
partidos = [
    ("P1", "México", "Sudáfrica"),
    ("P2", "Corea", "Checa"),
    ("P3", "Checa", "Sudáfrica"),
]

for partido in partidos:

    render_partido(
        partido[0],
        partido[1],
        partido[2]
    )

# ==================================
# RANKING
# ==================================
def calcular_puntos():

    ranking = []

    if df.empty:
        return ranking

    for _, fila in df.iterrows():

        nombre_jugador = fila["Nombre"]

        puntos = 0

        for col in df.columns:

            if col == "Nombre":
                continue

            if pd.notna(fila[col]) and fila[col] != "":
                puntos += 1

        ranking.append(
            (
                nombre_jugador,
                puntos
            )
        )

    ranking.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return ranking

st.header("🏆 Ranking")

ranking = calcular_puntos()

if ranking:

    tabla = pd.DataFrame(
        ranking,
        columns=["Nombre", "Puntos"]
    )

    st.dataframe(
        tabla,
        use_container_width=True
    )

else:

    st.info(
        "Todavía no hay participantes."
    )
