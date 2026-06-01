import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==================================
# CONFIG STREAMLIT
# ==================================
st.set_page_config(
    page_title="Polla Mundial 2026",
    page_icon="🏆",
    layout="wide"
)

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

spreadsheet = client.open("polla_mundial")

sheet = spreadsheet.sheet1
config_sheet = spreadsheet.worksheet("CONFIG")
partidos_sheet = spreadsheet.worksheet("PARTIDOS")
resultados_sheet = spreadsheet.worksheet("RESULTADOS")

# ==================================
# CONFIG
# ==================================
config = {}

try:
    config_data = config_sheet.get_all_records()

    for row in config_data:
        config[str(row["clave"]).strip()] = str(row["valor"]).strip()

except Exception:
    pass


def partido_abierto(partido_id):

    if config.get("estado", "abierto") == "cerrado":
        return False

    return config.get(partido_id, "abierto") == "abierto"


# ==================================
# CARGAR PARTIDOS
# ==================================
partidos = partidos_sheet.get_all_records()

# ==================================
# ASEGURAR CABECERAS RESPUESTAS
# ==================================
headers = sheet.row_values(1)

if not headers:

    headers = ["Nombre"]

    for partido in partidos:
        headers.append(str(partido["ID"]).strip())

    sheet.update("A1", [headers])

else:

    cambios = False

    if "Nombre" not in headers:
        headers.insert(0, "Nombre")
        cambios = True

    for partido in partidos:

        partido_id = str(partido["ID"]).strip()

        if partido_id not in headers:
            headers.append(partido_id)
            cambios = True

    if cambios:
        sheet.update("A1", [headers])


# ==================================
# CARGAR RESPUESTAS
# ==================================
def cargar_dataframe():

    data = sheet.get_all_records()

    if len(data) == 0:

        headers_local = sheet.row_values(1)

        return pd.DataFrame(columns=headers_local)

    df_local = pd.DataFrame(data)

    df_local.columns = [
        str(c).strip()
        for c in df_local.columns
    ]

    return df_local


df = cargar_dataframe()

# ==================================
# USUARIO
# ==================================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

nombre = nombre.strip().upper()

# ==================================
# REGISTRAR USUARIO
# ==================================
usuarios = []

if not df.empty and "Nombre" in df.columns:

    usuarios = (
        df["Nombre"]
        .astype(str)
        .str.upper()
        .tolist()
    )

if nombre not in usuarios:

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
def guardar_respuesta(nombre_usuario, partido_id, valor):

    data = sheet.get_all_records()

    nombres = [
        str(r["Nombre"]).upper()
        for r in data
    ]

    fila = nombres.index(nombre_usuario) + 2

    columnas = sheet.row_values(1)

    col = columnas.index(partido_id) + 1

    sheet.update_cell(
        fila,
        col,
        valor
    )


# ==================================
# RENDER PARTIDO
# ==================================
def render_partido(partido_id, equipo_a, equipo_b):

    key_sel = f"{partido_id}_sel"
    key_lock = f"{partido_id}_lock"

    if key_sel not in st.session_state:
        st.session_state[key_sel] = None

    if key_lock not in st.session_state:
        st.session_state[key_lock] = False

    # Cargar selección previa
    if (
        not df.empty
        and "Nombre" in df.columns
        and partido_id in df.columns
    ):

        fila = df[
            df["Nombre"]
            .astype(str)
            .str.upper() == nombre
        ]

        if not fila.empty:

            valor = fila[partido_id].values[0]

            if pd.notna(valor) and valor != "":

                st.session_state[key_sel] = valor
                st.session_state[key_lock] = True

    col1, col2, col3, col4 = st.columns([3, 1, 3, 1])

    with col1:

        if st.session_state[key_sel] == "A":
            st.success(equipo_a)

        else:

            if st.button(
                equipo_a,
                key=f"{partido_id}_A"
            ):

                if (
                    not st.session_state[key_lock]
                    and partido_abierto(partido_id)
                ):
                    st.session_state[key_sel] = "A"

    with col2:
        st.markdown("### VS")

    with col3:

        if st.session_state[key_sel] == "B":
            st.success(equipo_b)

        else:

            if st.button(
                equipo_b,
                key=f"{partido_id}_B"
            ):

                if (
                    not st.session_state[key_lock]
                    and partido_abierto(partido_id)
                ):
                    st.session_state[key_sel] = "B"

    with col4:

        if (
            not st.session_state[key_lock]
            and partido_abierto(partido_id)
        ):

            if st.button(
                "✅",
                key=f"{partido_id}_save"
            ):

                if st.session_state[key_sel]:

                    guardar_respuesta(
                        nombre,
                        partido_id,
                        st.session_state[key_sel]
                    )

                    st.success("Pronóstico guardado")

                    st.rerun()

    if st.session_state[key_sel] == "E":

        st.success("EMPATE")

    else:

        if st.button(
            "Empate",
            key=f"{partido_id}_empate"
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
# MOSTRAR PARTIDOS
# ==================================
grupo_actual = ""

for partido in partidos:

    grupo = str(partido["GRUPO"]).strip()

    if grupo and grupo != grupo_actual:

        st.header(f"🏆 {grupo}")

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

    try:

        resultados_df = pd.DataFrame(
            resultados_sheet.get_all_records()
        )

    except Exception:

        return ranking

    if resultados_df.empty:
        return ranking

    resultados = {}

    for _, row in resultados_df.iterrows():

        partido = str(row["ID"]).strip()
        resultado = str(row["Resultado"]).strip().upper()

        if resultado:
            resultados[partido] = resultado

    if not resultados:
        return ranking

    for _, fila in df.iterrows():

        nombre_jugador = fila["Nombre"]

        aciertos = 0
        evaluados = 0

        for partido, resultado_real in resultados.items():

            if partido not in df.columns:
                continue

            respuesta = fila.get(partido)

            if pd.isna(respuesta) or str(respuesta).strip() == "":
                continue

            evaluados += 1

            if str(respuesta).strip().upper() == resultado_real:
                aciertos += 1

        porcentaje = 0

        if evaluados > 0:
            porcentaje = round(
                (aciertos / evaluados) * 100,
                2
            )

        ranking.append(
            (
                nombre_jugador,
                aciertos,
                evaluados,
                porcentaje
            )
        )

    ranking.sort(
        key=lambda x: x[3],
        reverse=True
    )

    return ranking

# ==================================
# RANKING COMPLETO
# ==================================

with st.expander("🏆 Ver Ranking Completo"):

    ranking = calcular_ranking()

    if ranking:

        tabla = pd.DataFrame(
            ranking,
            columns=[
                "Nombre",
                "Aciertos",
                "Partidos Evaluados",
                "% Acierto"
            ]
        )

        tabla.index = tabla.index + 1

        st.dataframe(
            tabla,
            use_container_width=True
        )

    else:

        st.info(
            "Todavía no existen resultados para calcular el ranking."
        )
