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

# Estilo personalizado
st.markdown("""
<style>
    .stButton button {
        font-weight: bold;
    }
    .campeon-btn {
        height: 60px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

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
# VERIFICAR Y CREAR COLUMNA DE CAMPEÓN
# ==================================
def asegurar_columna_campeon():
    """Asegura que la columna CAMPEON existe en la hoja RESPUESTAS"""
    global df
    
    # Obtener todas las columnas actuales
    columnas_actuales = sheet.row_values(1)
    columnas_actuales = [str(col).strip().upper() for col in columnas_actuales]
    
    # Verificar si CAMPEON existe (en cualquier variante)
    col_campeon_existe = False
    for col in columnas_actuales:
        if col in ["CAMPEON", "CAMPEÓN", "CAMPEON MUNDIAL"]:
            col_campeon_existe = True
            break
    
    # Si no existe, agregarla
    if not col_campeon_existe:
        st.warning("⚙️ Configurando columna para selección de campeón...")
        try:
            # Agregar columna al final
            sheet.add_cols(1)
            # Actualizar el encabezado
            nueva_col = len(columnas_actuales) + 1
            sheet.update_cell(1, nueva_col, "CAMPEON")
            
            # Recargar datos
            cargar_todo.clear()
            data.update(cargar_todo())
            df = pd.DataFrame(data["respuestas"])
            if not df.empty:
                df.columns = df.columns.str.strip()
            
            st.success("✅ Columna de campeón configurada correctamente")
            st.rerun()
            return True
        except Exception as e:
            st.error(f"❌ Error al configurar columna: {e}")
            return False
    return True

# Ejecutar verificación
asegurar_columna_campeon()

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
    sheet.append_row([nombre])
    cargar_todo.clear()
    st.success(f"✅ Usuario {nombre} registrado")
    st.rerun()

st.info(f"👋 Hola {nombre}")

# ==================================
# FUNCIONES DE CAMPEÓN
# ==================================
def obtener_campeones_disponibles():
    """Retorna la lista de equipos disponibles para campeón"""
    return ["Argentina", "Bélgica", "España", "Francia", 
            "Inglaterra", "Marruecos", "Noruega", "Suiza"]

def obtener_campeon_usuario():
    """Obtiene el campeón seleccionado por el usuario"""
    if df.empty or "Nombre" not in df.columns:
        return None
    
    fila = df[df["Nombre"].str.upper() == nombre]
    if fila.empty:
        return None
    
    # Buscar columna de campeón
    col_campeon = None
    for col in df.columns:
        if col.upper() in ["CAMPEON", "CAMPEÓN", "CAMPEON MUNDIAL"]:
            col_campeon = col
            break
    
    if col_campeon and not fila.empty:
        valor = fila.iloc[0].get(col_campeon)
        if pd.notna(valor) and str(valor).strip() != "":
            return str(valor).strip()
    return None

def guardar_campeon(equipo):
    """Guarda la selección del campeón en la hoja de cálculo"""
    if not equipo:
        return False
    
    # Verificar si el usuario ya tiene seleccionado un campeón
    if obtener_campeon_usuario():
        st.warning("⚠️ Ya tienes un campeón seleccionado. No puedes cambiarlo.")
        return False
    
    # Encontrar la columna de campeón
    col_campeon = None
    for col in df.columns:
        if col.upper() in ["CAMPEON", "CAMPEÓN", "CAMPEON MUNDIAL"]:
            col_campeon = col
            break
    
    if not col_campeon:
        st.error("❌ No se encontró la columna de campeón")
        return False
    
    # Buscar la fila del usuario
    fila_usuario = df[df["Nombre"].str.upper() == nombre]
    if fila_usuario.empty:
        return False
    
    # Obtener posición
    fila_idx = df[df["Nombre"].str.upper() == nombre].index[0] + 2
    col_idx = df.columns.get_loc(col_campeon) + 1
    
    # Guardar en la hoja
    celda = rowcol_to_a1(fila_idx, col_idx)
    sheet.update_acell(celda, equipo)
    
    # Actualizar el DataFrame global
    global df
    cargar_todo.clear()
    data.update(cargar_todo())
    df = pd.DataFrame(data["respuestas"])
    if not df.empty:
        df.columns = df.columns.str.strip()
    
    return True

# ==================================
# 🏆 SELECCIÓN DE CAMPEÓN (SIEMPRE VISIBLE)
# ==================================
st.header("🏆 Selecciona tu Campeón Mundial")

campeon_actual = obtener_campeon_usuario()
campeon_real = config.get("campeon_real", "").strip()

if campeon_actual:
    st.success(f"🏆 Has elegido a **{campeon_actual}** como campeón del mundo")
    
    if campeon_real:
        if campeon_actual.upper() == campeon_real.upper():
            st.success(f"✅ ¡ACERTASTE! El campeón fue {campeon_real} ➕ +5 puntos extra")
        else:
            st.error(f"❌ El campeón fue {campeon_real}, tú elegiste {campeon_actual}")
else:
    st.info("📌 Selecciona tu campeón para el Mundial 2026:")
    st.caption("⚠️ **Importante:** Una vez seleccionado, no podrás cambiarlo")
    
    # Mostrar botones para seleccionar campeón
    equipos = obtener_campeones_disponibles()
    
    # Crear columnas para los botones (4 columnas)
    cols = st.columns(4)
    
    for i, equipo in enumerate(equipos):
        col_idx = i % 4
        if cols[col_idx].button(
            f"🏆 {equipo}", 
            key=f"campeon_{equipo}", 
            use_container_width=True,
            type="primary"
        ):
            if guardar_campeon(equipo):
                st.success(f"✅ Has seleccionado a {equipo} como campeón")
                st.rerun()
            else:
                st.error("❌ Error al guardar la selección")
    
    st.caption("🔒 La selección de campeón es definitiva y no se puede cambiar después de guardar")

st.divider()

# ==================================
# RANKING
# ==================================
def calcular_ranking():

    ranking = []

    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for r in data["resultados"] if r["Resultado"]
    }
    
    # Obtener el campeón real
    campeon_real = config.get("campeon_real", "").strip().upper()
    
    # Obtener la columna de campeón
    col_campeon = None
    for col in df.columns:
        if col.upper() in ["CAMPEON", "CAMPEÓN", "CAMPEON MUNDIAL"]:
            col_campeon = col
            break

    for _, fila in df.iterrows():
        aciertos = 0
        total = 0
        puntos_extra = 0

        for partido, real in resultados.items():

            if partido not in df.columns:
                continue

            resp = fila.get(partido)

            if pd.notna(resp) and resp != "":
                total += 1
                if str(resp).upper() == real:
                    aciertos += 1
        
        # Verificar campeón
        if campeon_real and col_campeon:
            campeon_usuario = str(fila.get(col_campeon, "")).strip().upper()
            if campeon_usuario and campeon_usuario == campeon_real:
                puntos_extra = 5

        porcentaje = round((aciertos / total) * 100, 2) if total else 0

        ranking.append((fila["Nombre"], aciertos, total, porcentaje, puntos_extra))

    ranking.sort(key=lambda x: (x[1] + x[4]), reverse=True)

    return ranking

with st.expander("🏆 Ranking de la Polla", expanded=True):
    ranking = calcular_ranking()

    if ranking:
        df_ranking = pd.DataFrame(
            ranking,
            columns=["Nombre", "Aciertos", "Total", "%", "Puntos Extra"]
        )
        # Calcular puntaje total
        df_ranking["Puntaje Total"] = df_ranking["Aciertos"] + df_ranking["Puntos Extra"]
        # Reordenar columnas
        df_ranking = df_ranking[["Nombre", "Aciertos", "Puntos Extra", "Puntaje Total", "Total", "%"]]
        st.dataframe(df_ranking, use_container_width=True)
        
        # Mostrar líder
        if not df_ranking.empty:
            lider = df_ranking.iloc[0]
            st.success(f"🏅 **Líder:** {lider['Nombre']} con {lider['Puntaje Total']} puntos")
    else:
        st.info("📊 Sin resultados todavía")

st.divider()

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

def obtener_valor_guardado(pid):
    if df.empty or "Nombre" not in df.columns:
        return None
    
    fila = df[df["Nombre"].str.upper() == nombre]
    if fila.empty:
        return None
    
    valor = fila.iloc[0].get(pid)
    if pd.notna(valor) and str(valor).strip() != "":
        return str(valor).strip()
    return None

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
        st.warning("⚠️ No hay cambios para guardar")
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
                continue

        fila = nombres.index(nombre) + 2
        col = columnas.index(pid) + 1

        celda = rowcol_to_a1(fila, col)

        updates.append({
            "range": celda,
            "values": [[valor]]
        })

    if not updates:
        st.warning("⚠️ Todos esos partidos ya fueron guardados.")
        return

    sheet.batch_update(updates)

    for pid, valor in cambios.items():
        st.session_state[f"guardado_{pid}"] = valor

    st.success("✅ Pronósticos guardados correctamente")
    st.session_state["cambios"] = {}
    st.rerun()

# ==================================
# FUNCIÓN PARA OBTENER TÍTULO DE RONDA
# ==================================
def obtener_titulo_ronda(partido_id):
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
    try:
        pid_limpio = ''.join(filter(str.isdigit, str(pid)))
        partido_id = int(pid_limpio) if pid_limpio else 0
    except (ValueError, TypeError):
        partido_id = 0
    
    es_eliminatoria = partido_id >= 73
    bloqueado = ya_guardado(pid)
    abierto = partido_abierto(pid)
    
    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for r in data["resultados"] if r["Resultado"]
    }
    resultado_real = resultados.get(pid, None)
    valor_guardado = obtener_valor_guardado(pid)

    if f"guardado_{pid}" in st.session_state:
        st.success(f"✅ Guardado: {st.session_state[f'guardado_{pid}']}")

    if not abierto:
        st.caption("🔒 Partido cerrado")

    if bloqueado and valor_guardado:
        if resultado_real:
            if valor_guardado.upper() == resultado_real:
                st.success(f"✅ Correcto: {valor_guardado}")
            else:
                st.warning(f"❌ Incorrecto: {valor_guardado}")
        else:
            st.info(f"📝 Pronóstico: {valor_guardado}")
    
    if abierto and not bloqueado:
        if es_eliminatoria:
            col1, col2 = st.columns(2)
            
            if col1.button(a, key=f"{pid}_A", use_container_width=True):
                st.session_state["cambios"][pid] = "A"

            if col2.button(b, key=f"{pid}_B", use_container_width=True):
                st.session_state["cambios"][pid] = "B"

        else:
            col1, col2, col3 = st.columns(3)

            if col1.button(a, key=f"{pid}_A", use_container_width=True):
                st.session_state["cambios"][pid] = "A"

            if col2.button("Empate", key=f"{pid}_E", use_container_width=True):
                st.session_state["cambios"][pid] = "E"

            if col3.button(b, key=f"{pid}_B", use_container_width=True):
                st.session_state["cambios"][pid] = "B"

    if pid in st.session_state["cambios"]:
        st.caption(f"📌 Seleccionado: {st.session_state['cambios'][pid]}")

    st.divider()

# ==================================
# MOSTRAR PARTIDOS
# ==================================
st.header("📋 Pronósticos de Partidos")

grupo_actual = ""
ronda_actual = None

for p in partidos:
    pid = str(p["ID"]).strip()
    try:
        pid_limpio = ''.join(filter(str.isdigit, str(pid)))
        partido_id = int(pid_limpio) if pid_limpio else 0
    except (ValueError, TypeError):
        partido_id = 0
    
    grupo = str(p["GRUPO"]).strip()

    if partido_id < 73:
        if grupo != grupo_actual:
            st.header(f"🏆 {grupo}")
            grupo_actual = grupo
    else:
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
st.button("💾 Guardar pronósticos", on_click=guardar_masivo, type="primary", use_container_width=True)
