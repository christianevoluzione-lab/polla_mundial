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
@st.cache_data(ttl=180)
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

# Consultar usuarios directamente desde Google Sheets
usuarios_actuales = [
    str(x).strip().upper()
    for x in sheet.col_values(1)[1:]
]

# Registro
if nombre not in usuarios_actuales:

    # Segunda verificación para evitar duplicados
    usuarios_actuales = [
        str(x).strip().upper()
        for x in sheet.col_values(1)[1:]
    ]

    if nombre not in usuarios_actuales:
        sheet.append_row([nombre])

    cargar_todo.clear()

    st.success(f"Usuario {nombre} registrado")
    st.rerun()

st.info(f"Hola {nombre}")
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

    ranking.sort(key=lambda x: x[1], reverse=True)

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

# ==================================
# SELECCIÓN DE CAMPEÓN
# ==================================
with st.expander("🏆 Elige tu Campeón", expanded=True):
    
    # Verificar si el usuario ya eligió campeón
    campeon_actual = ""
    if not df.empty and "CAMPEON" in df.columns:
        fila_usuario = df[df["Nombre"].str.upper() == nombre]
        if not fila_usuario.empty:
            campeon_actual = fila_usuario.iloc[0].get("CAMPEON")
            if pd.notna(campeon_actual) and str(campeon_actual).strip() != "":
                st.success(f"🏆 Tu campeón elegido: {campeon_actual}")
                st.info("Si deseas cambiarlo, selecciona otro equipo abajo.")
    
    # Lista de los 8 clasificados a cuartos de final
    equipos_cuartos = [
        "Francia 🇫🇷", 
        "Marruecos 🇲🇦", 
        "España 🇪🇸", 
        "Bélgica 🇧🇪",
        "Noruega 🇳🇴", 
        "Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿", 
        "Argentina 🇦🇷", 
        "Suiza 🇨🇭"
    ]
    
    # Selectbox para elegir campeón
    campeon_seleccionado = st.selectbox(
        "Selecciona tu campeón:",
        options=[""] + equipos_cuartos,  # Opción vacía al inicio
        key="select_campeon"
    )
    
    # Botón para guardar
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 Guardar Campeón", key="btn_guardar_campeon", use_container_width=True):
            if campeon_seleccionado and campeon_seleccionado != "":
                try:
                    # Limpiar el nombre del equipo (quitar bandera)
                    equipo_limpio = campeon_seleccionado.split(" ")[0] if " " in campeon_seleccionado else campeon_seleccionado
                    
                    # Obtener la fila del usuario
                    nombres = df["Nombre"].astype(str).str.upper().tolist()
                    fila_usuario = nombres.index(nombre) + 2
                    
                    # Obtener la columna CAMPEON
                    headers = sheet.row_values(1)
                    if "CAMPEON" not in headers:
                        headers.append("CAMPEON")
                        sheet.update_row(1, headers)
                    
                    col_campeon = headers.index("CAMPEON") + 1
                    celda = rowcol_to_a1(fila_usuario, col_campeon)
                    
                    # Guardar la elección
                    sheet.update(celda, equipo_limpio)
                    
                    cargar_todo.clear()
                    st.success(f"✅ ¡Has elegido a {equipo_limpio} como campeón!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor selecciona un equipo")
    
    with col2:
        if st.button("❌ Limpiar selección", key="btn_limpiar_campeon", use_container_width=True):
            try:
                # Obtener la fila del usuario
                nombres = df["Nombre"].astype(str).str.upper().tolist()
                fila_usuario = nombres.index(nombre) + 2
                
                # Obtener la columna CAMPEON
                headers = sheet.row_values(1)
                if "CAMPEON" not in headers:
                    headers.append("CAMPEON")
                    sheet.update_row(1, headers)
                
                col_campeon = headers.index("CAMPEON") + 1
                celda = rowcol_to_a1(fila_usuario, col_campeon)
                
                # Limpiar la elección
                sheet.update(celda, "")
                
                cargar_todo.clear()
                st.success("✅ Selección de campeón eliminada")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error al limpiar: {e}")

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

    # Guardar en session_state para mostrar mensaje después del rerun
    for pid, valor in cambios.items():
        st.session_state[f"guardado_{pid}"] = valor

    st.success("✅ Pronósticos guardados")
    st.session_state["cambios"] = {}
    st.rerun()

# ==================================
# FUNCIÓN PARA OBTENER TÍTULO DE RONDA
# ==================================
def obtener_titulo_ronda(partido_id):
    """
    Devuelve el título de la ronda según el número de partido
    """
    if 73 <= partido_id <= 88:
        return "🏆 16AVOS DE FINAL"
    elif 89 <= partido_id <= 96:
        return "🏆 OCTAVOS DE FINAL"
    elif 97 <= partido_id <= 100:
        return "🏆 CUARTOS DE FINAL"
    elif 101 <= partido_id <= 102:
        return "🏆 SEMIFINALES"
    elif partido_id == 103:
        return "🥉 TERCER PUESTO"
    elif partido_id == 104:
        return "🏆 FINAL"
    else:
        return None

# ==================================
# RENDER
# ==================================
def render_partido(pid, a, b):
    # Limpiar el ID para obtener solo el número
    try:
        pid_limpio = ''.join(filter(str.isdigit, str(pid)))
        partido_id = int(pid_limpio) if pid_limpio else 0
    except (ValueError, TypeError):
        partido_id = 0
    
    bloqueado = ya_guardado(pid)
    
    # Obtener resultados reales
    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for r in data["resultados"] if r["Resultado"]
    }
    resultado_real = resultados.get(pid, None)

    # DETERMINAR SI ES PARTIDO DE ELIMINACIÓN DIRECTA (P73 EN ADELANTE)
    es_eliminatoria = partido_id >= 73

    # 🔥 Mostrar mensaje de guardado si existe en session_state
    if f"guardado_{pid}" in st.session_state:
        st.success(f"✅ Guardado: {st.session_state[f'guardado_{pid}']}")
        # Eliminar el mensaje después de mostrarlo para que no se acumule
        # del st.session_state[f"guardado_{pid}"]

    if es_eliminatoria:
        # PARTIDOS 73+: SOLO 2 BOTONES (A y B) - SIN EMPATE
        col1, col2 = st.columns(2)
        
        if col1.button(a, key=f"{pid}_A", disabled=bloqueado, use_container_width=True):
            if partido_abierto(pid):
                st.session_state["cambios"][pid] = "A"

        if col2.button(b, key=f"{pid}_B", disabled=bloqueado, use_container_width=True):
            if partido_abierto(pid):
                st.session_state["cambios"][pid] = "B"

    else:
        # PARTIDOS 1-72: 3 BOTONES (A, Empate, B)
        col1, col2, col3 = st.columns(3)

        if col1.button(a, key=f"{pid}_A", disabled=bloqueado, use_container_width=True):
            if partido_abierto(pid):
                st.session_state["cambios"][pid] = "A"

        if col2.button("Empate", key=f"{pid}_E", disabled=bloqueado, use_container_width=True):
            if partido_abierto(pid):
                st.session_state["cambios"][pid] = "E"

        if col3.button(b, key=f"{pid}_B", disabled=bloqueado, use_container_width=True):
            if partido_abierto(pid):
                st.session_state["cambios"][pid] = "B"

    # 🔥 MOSTRAR PREDICCIÓN GUARDADA CON COLORES SEGÚN ESTADO
    if bloqueado:
        valor = df[df["Nombre"].str.upper() == nombre].iloc[0][pid]
        valor_str = str(valor).upper() if pd.notna(valor) else ""
        
        if resultado_real:
            # Si hay resultado real, mostrar si acertó o falló
            if valor_str == resultado_real:
                st.success(f"✅ Correcto: {valor_str}")  # VERDE
            else:
                st.warning(f"❌ Incorrecto: {valor_str}")  # NARANJA CLARO
        else:
            # Si no hay resultado real aún, mostrar en AZUL
            st.info(f"📝 Pronóstico: {valor_str}")  # AZUL

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

# Variable para controlar que no se repitan los títulos de ronda
ronda_actual = None

for p in partidos:

    # Obtener ID limpio
    pid = str(p["ID"]).strip()
    try:
        pid_limpio = ''.join(filter(str.isdigit, str(pid)))
        partido_id = int(pid_limpio) if pid_limpio else 0
    except (ValueError, TypeError):
        partido_id = 0
    
    grupo = str(p["GRUPO"]).strip()

    # Mostrar título de grupo solo para partidos de fase de grupos (1-72)
    if partido_id < 73:
        if grupo != grupo_actual:
            st.header(f"🏆 {grupo}")
            grupo_actual = grupo
    else:
        # Para partidos de eliminación (73+), mostrar título de ronda UNA SOLA VEZ
        titulo_ronda = obtener_titulo_ronda(partido_id)
        if titulo_ronda and titulo_ronda != ronda_actual:
            st.header(titulo_ronda)
            ronda_actual = titulo_ronda

    render_partido(
        pid,
        str(p["Equipo A"]).strip(),
        str(p["Equipo B"]).strip()
    )

# ==================================
# BOTÓN GUARDAR
# ==================================
st.button("💾 Guardar pronósticos", on_click=guardar_masivo)
