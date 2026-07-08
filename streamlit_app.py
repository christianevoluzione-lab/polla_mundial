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
# CARGA DE DATOS
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

# Convertir a DataFrame
df = pd.DataFrame(data["respuestas"])
if not df.empty:
    df.columns = df.columns.str.strip()
partidos = data["partidos"]
config = {str(r["clave"]).strip(): str(r["valor"]).strip() for r in data["config"]}

# ==================================
# ENCONTRAR COLUMNA DE CAMPEÓN (SIN IMPORTAR MAYÚSCULAS)
# ==================================
col_campeon = None
for col in df.columns:
    if col.upper() == "CAMPEON":
        col_campeon = col
        break

# Si no se encuentra, crear una
if col_campeon is None:
    try:
        sheet.add_cols(1)
        sheet.update_cell(1, len(df.columns) + 1, "CAMPEON")
        cargar_todo.clear()
        data = cargar_todo()
        df = pd.DataFrame(data["respuestas"])
        if not df.empty:
            df.columns = df.columns.str.strip()
        col_campeon = "CAMPEON"
        st.rerun()
    except Exception as e:
        st.error(f"Error creando columna: {e}")

# ==================================
# USUARIO
# ==================================
nombre = st.text_input("Ingresa tu nombre")

if not nombre:
    st.stop()

nombre = nombre.strip().upper()

# Registrar usuario si no existe
usuarios_actuales = [str(x).strip().upper() for x in sheet.col_values(1)[1:]]

if nombre not in usuarios_actuales:
    sheet.append_row([nombre])
    cargar_todo.clear()
    st.success(f"✅ Usuario {nombre} registrado")
    st.rerun()

st.info(f"👋 Hola {nombre}")

# ==================================
# 🏆 SELECCIÓN DE CAMPEÓN
# ==================================
st.header("🏆 Selecciona tu Campeón Mundial")

# Obtener selección actual
campeon_usuario = None
if col_campeon and not df.empty and "Nombre" in df.columns:
    fila_usuario = df[df["Nombre"].str.upper() == nombre]
    if not fila_usuario.empty:
        valor = fila_usuario.iloc[0].get(col_campeon)
        if pd.notna(valor) and str(valor).strip() != "":
            campeon_usuario = str(valor).strip()

# Mostrar estado actual
if campeon_usuario:
    st.success(f"🏆 Has elegido a **{campeon_usuario}** como campeón")
    
    # Verificar si acertó
    campeon_real = config.get("campeon_real", "").strip()
    if campeon_real:
        if campeon_usuario.upper() == campeon_real.upper():
            st.success("✅ ¡ACERTASTE EL CAMPEÓN! +5 puntos extra")
        else:
            st.error(f"❌ El campeón fue {campeon_real}, tú elegiste {campeon_usuario}")
else:
    st.info("📌 Selecciona tu campeón para el Mundial 2026:")
    st.caption("⚠️ **Importante:** Una vez seleccionado, no podrás cambiarlo")
    
    # Equipos disponibles
    equipos = ["Argentina", "Bélgica", "España", "Francia", 
               "Inglaterra", "Marruecos", "Noruega", "Suiza"]
    
    # Botones en 4 columnas
    cols = st.columns(4)
    
    for i, equipo in enumerate(equipos):
        col_idx = i % 4
        if cols[col_idx].button(
            f"🏆 {equipo}", 
            key=f"campeon_{equipo}", 
            use_container_width=True,
            type="primary"
        ):
            # Guardar selección
            try:
                if col_campeon and not df.empty and "Nombre" in df.columns:
                    idx_usuario = df[df["Nombre"].str.upper() == nombre].index
                    if not idx_usuario.empty:
                        fila = idx_usuario[0] + 2
                        col = df.columns.get_loc(col_campeon) + 1
                        celda = rowcol_to_a1(fila, col)
                        sheet.update_acell(celda, equipo)
                        st.success(f"✅ Has seleccionado a {equipo} como campeón")
                        st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

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
    
    campeon_real = config.get("campeon_real", "").strip().upper()

    for _, fila in df.iterrows():
        aciertos = 0
        total = 0
        puntos_extra = 0

        # Calcular aciertos de partidos
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
            campeon_usuario_val = str(fila.get(col_campeon, "")).strip().upper()
            if campeon_usuario_val and campeon_usuario_val == campeon_real:
                puntos_extra = 5

        porcentaje = round((aciertos / total) * 100, 2) if total else 0
        ranking.append((fila["Nombre"], aciertos, total, porcentaje, puntos_extra))

    ranking.sort(key=lambda x: (x[1] + x[4]), reverse=True)
    return ranking

with st.expander("🏆 Ranking", expanded=True):
    ranking = calcular_ranking()
    
    if ranking:
        df_ranking = pd.DataFrame(ranking, columns=["Nombre", "Aciertos", "Total", "%", "Puntos Extra"])
        df_ranking["Puntaje Total"] = df_ranking["Aciertos"] + df_ranking["Puntos Extra"]
        df_ranking = df_ranking[["Nombre", "Aciertos", "Puntos Extra", "Puntaje Total", "Total", "%"]]
        st.dataframe(df_ranking, use_container_width=True)
        
        if not df_ranking.empty:
            lider = df_ranking.iloc[0]
            st.success(f"🏅 **Líder:** {lider['Nombre']} con {lider['Puntaje Total']} puntos")
    else:
        st.info("📊 Sin resultados")

st.divider()

# ==================================
# FUNCIONES DE PARTIDOS
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
# SESSION STATE
# ==================================
if "cambios" not in st.session_state:
    st.session_state["cambios"] = {}

# ==================================
# GUARDAR PRONÓSTICOS
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
        if not fila_usuario.empty:
            valor_actual = fila_usuario.iloc[0].get(pid)
            if pd.notna(valor_actual) and str(valor_actual).strip() != "":
                continue
        
        fila = nombres.index(nombre) + 2
        col = columnas.index(pid) + 1
        celda = rowcol_to_a1(fila, col)
        updates.append({"range": celda, "values": [[valor]]})
    
    if not updates:
        st.warning("⚠️ Todos esos partidos ya fueron guardados")
        return
    
    sheet.batch_update(updates)
    for pid, valor in cambios.items():
        st.session_state[f"guardado_{pid}"] = valor
    
    st.success("✅ Pronósticos guardados correctamente")
    st.session_state["cambios"] = {}
    st.rerun()

# ==================================
# TÍTULOS DE RONDA
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
    return None

# ==================================
# RENDER PARTIDO
# ==================================
def render_partido(pid, a, b):
    try:
        pid_limpio = ''.join(filter(str.isdigit, str(pid)))
        partido_id = int(pid_limpio) if pid_limpio else 0
    except:
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
    except:
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
