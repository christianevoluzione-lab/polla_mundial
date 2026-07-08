import streamlit as st
import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
import time

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
    usuarios_actuales = [
        str(x).strip().upper()
        for x in sheet.col_values(1)[1:]
    ]

    if nombre not in usuarios_actuales:
        # Asegurarse de que la columna CAMPEON existe
        headers = sheet.row_values(1)
        if "CAMPEON" not in headers:
            # Agregar columna CAMPEON si no existe
            sheet.update_cell(1, len(headers) + 1, "CAMPEON")
        
        sheet.append_row([nombre])
        # Inicializar la columna CAMPEON con vacío para este usuario
        fila_usuario = len(usuarios_actuales) + 2
        col_campeon = len(headers) + 1 if "CAMPEON" not in headers else headers.index("CAMPEON") + 1
        sheet.update_cell(fila_usuario, col_campeon, "")

    cargar_todo.clear()
    st.success(f"Usuario {nombre} registrado")
    st.rerun()

st.info(f"Hola {nombre}")

# ==================================
# MODAL PARA ESCOGER CAMPEÓN (CON BOTONES FUNCIONALES)
# ==================================
def mostrar_modal_campeon():
    """Muestra un modal para que el usuario elija su campeón con botones"""
    
    # Verificar si el usuario ya eligió campeón
    if not df.empty and "CAMPEON" in df.columns:
        fila_usuario = df[df["Nombre"].str.upper() == nombre]
        if not fila_usuario.empty:
            campeon_actual = fila_usuario.iloc[0].get("CAMPEON")
            if pd.notna(campeon_actual) and str(campeon_actual).strip() != "":
                return  # Ya eligió campeón
    
    # LISTA DE LOS 8 CLASIFICADOS A CUARTOS DE FINAL
    equipos_cuartos = [
        "Francia", "Marruecos", "España", "Bélgica",
        "Noruega", "Inglaterra", "Argentina", "Suiza"
    ]
    
    # Diccionario de banderas para los equipos
    banderas = {
        "Francia": "🇫🇷",
        "Marruecos": "🇲🇦",
        "España": "🇪🇸",
        "Bélgica": "🇧🇪",
        "Noruega": "🇳🇴",
        "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "Argentina": "🇦🇷",
        "Suiza": "🇨🇭"
    }
    
    # CSS para el modal funcional
    modal_style = """
    <style>
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        backdrop-filter: blur(5px);
        pointer-events: none;
    }
    .modal-content {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 40px;
        border-radius: 25px;
        max-width: 750px;
        width: 95%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        text-align: center;
        animation: slideIn 0.4s ease-out;
        border: 2px solid rgba(255,255,255,0.1);
        pointer-events: auto;
        position: relative;
    }
    @keyframes slideIn {
        from {
            transform: translateY(-50px) scale(0.95);
            opacity: 0;
        }
        to {
            transform: translateY(0) scale(1);
            opacity: 1;
        }
    }
    .modal-title {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #ffffff;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .modal-subtitle {
        color: #a8c8ff;
        font-size: 16px;
        margin-bottom: 20px;
    }
    .modal-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin: 20px 0;
    }
    .modal-team-btn {
        background: rgba(255,255,255,0.08);
        color: #ffffff;
        border: 2px solid rgba(255,255,255,0.15);
        padding: 15px 20px;
        font-size: 18px;
        font-weight: 600;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        width: 100%;
        text-align: center;
        font-family: inherit;
    }
    .modal-team-btn:hover {
        background: rgba(255,215,0,0.2);
        border-color: #ffd700;
        transform: scale(1.05);
        box-shadow: 0 8px 25px rgba(255,215,0,0.2);
    }
    .modal-team-btn:active {
        transform: scale(0.95);
    }
    .modal-close-btn {
        background: rgba(255,255,255,0.05);
        color: #aaa;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 12px 30px;
        font-size: 15px;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s;
        font-family: inherit;
        margin-top: 10px;
    }
    .modal-close-btn:hover {
        background: rgba(255,255,255,0.1);
        color: #fff;
    }
    .modal-emojis {
        font-size: 40px;
        margin-bottom: 5px;
    }
    .bandera {
        font-size: 28px;
        margin-right: 8px;
    }
    .close-icon {
        position: absolute;
        top: 15px;
        right: 20px;
        font-size: 28px;
        color: #888;
        cursor: pointer;
        transition: all 0.3s;
        background: none;
        border: none;
        font-family: inherit;
    }
    .close-icon:hover {
        color: #fff;
        transform: rotate(90deg);
    }
    @media (max-width: 600px) {
        .modal-grid {
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .modal-team-btn {
            font-size: 14px;
            padding: 12px 10px;
        }
        .modal-content {
            padding: 20px;
            max-height: 95vh;
        }
        .modal-title {
            font-size: 22px;
        }
    }
    </style>
    """
    
    st.markdown(modal_style, unsafe_allow_html=True)
    
    # Mostrar modal si no ha elegido campeón
    if "mostrar_modal" not in st.session_state:
        st.session_state.mostrar_modal = True
    
    if st.session_state.mostrar_modal:
        # Contenedor del modal con HTML
        st.markdown("""
        <div class="modal-overlay" id="modal-overlay">
            <div class="modal-content">
                <button class="close-icon" onclick="document.getElementById('btn_cerrar_modal').click();">✕</button>
                <div class="modal-emojis">
                    🏆🌍⚽
                </div>
                <div class="modal-title">
                    ESCOGE TU CAMPEÓN
                </div>
                <div class="modal-subtitle">
                    Selecciona el equipo que crees que ganará el Mundial 2026
                </div>
                <div class="modal-grid">
        """, unsafe_allow_html=True)
        
        # Crear botones para cada equipo
        cols = st.columns(2)
        for idx, equipo in enumerate(equipos_cuartos):
            bandera = banderas.get(equipo, "⚽")
            col = cols[idx % 2]
            with col:
                if st.button(f"{bandera} {equipo}", 
                           key=f"btn_campeon_{equipo}",
                           use_container_width=True,
                           type="primary"):
                    guardar_campeon(equipo)
        
        st.markdown("""
                </div>
                <button class="modal-close-btn" onclick="document.getElementById('btn_cerrar_modal_visible').click();">
                    ⏭️ Saltar por ahora
                </button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de cerrar modal (Streamlit)
        if st.button("Cerrar modal", key="btn_cerrar_modal", hidden=True):
            st.session_state.mostrar_modal = False
            st.session_state.campeon_confirmado = False
            st.rerun()
        
        # Botón visible para cerrar
        if st.button("⏭️ Saltar por ahora", key="btn_cerrar_modal_visible", use_container_width=True):
            st.session_state.mostrar_modal = False
            st.session_state.campeon_confirmado = False
            st.rerun()
        
        st.stop()

def guardar_campeon(equipo):
    """Función para guardar el campeón elegido"""
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
        
        # Guardar la elección
        sheet.update(celda, equipo)
        
        # Actualizar estado
        st.session_state.mostrar_modal = False
        st.session_state.campeon_guardado = equipo
        st.session_state.campeon_confirmado = True
        
        cargar_todo.clear()
        st.success(f"✅ ¡Has elegido a {equipo} como campeón!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Ejecutar el modal al inicio (si no ha elegido campeón)
if "campeon_confirmado" not in st.session_state:
    mostrar_modal_campeon()
else:
    # Si ya confirmó pero recargó la página, verificar si realmente guardó
    if not df.empty and "CAMPEON" in df.columns:
        fila_usuario = df[df["Nombre"].str.upper() == nombre]
        if not fila_usuario.empty:
            campeon_actual = fila_usuario.iloc[0].get("CAMPEON")
            if pd.isna(campeon_actual) or str(campeon_actual).strip() == "":
                # Si no está guardado en la hoja, mostrar modal de nuevo
                st.session_state.campeon_confirmado = False
                st.rerun()
            else:
                # Mostrar confirmación
                banderas = {
                    "Francia": "🇫🇷",
                    "Marruecos": "🇲🇦",
                    "España": "🇪🇸",
                    "Bélgica": "🇧🇪",
                    "Noruega": "🇳🇴",
                    "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
                    "Argentina": "🇦🇷",
                    "Suiza": "🇨🇭"
                }
                bandera = banderas.get(str(campeon_actual).strip(), "🏆")
                st.success(f"{bandera} Tu campeón elegido: {campeon_actual}")

# ==================================
# RANKING
# ==================================
def calcular_ranking():

    ranking = []

    resultados = {
        str(r["ID"]).strip(): str(r["Resultado"]).strip().upper()
        for r in data["resultados"] if r["Resultado"]
    }
    
    # Obtener el campeón real (debería estar en CONFIG o RESULTADOS)
    campeon_real = config.get("CAMPEON_REAL", "").strip().upper()

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

        porcentaje = round((aciertos / total) * 100, 2) if total else 0
        
        # Verificar si acertó el campeón (5 puntos extra)
        if "CAMPEON" in df.columns and campeon_real:
            campeon_elegido = fila.get("CAMPEON")
            if pd.notna(campeon_elegido) and str(campeon_elegido).strip().upper() == campeon_real:
                puntos_extra = 5

        ranking.append((fila["Nombre"], aciertos, total, porcentaje, puntos_extra, aciertos + puntos_extra))

    ranking.sort(key=lambda x: x[5], reverse=True)

    return ranking

with st.expander("🏆 Ranking"):

    ranking = calcular_ranking()

    if ranking:
        df_ranking = pd.DataFrame(
            ranking,
            columns=["Nombre", "Aciertos", "Total", "%", "Extra", "Total Puntos"]
        )
        # Resaltar al usuario actual
        st.dataframe(
            df_ranking,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre"),
                "Aciertos": st.column_config.NumberColumn("Aciertos"),
                "Total": st.column_config.NumberColumn("Total"),
                "%": st.column_config.NumberColumn("%"),
                "Extra": st.column_config.NumberColumn("Extra (Campeón)", help="5 puntos extra por acertar el campeón"),
                "Total Puntos": st.column_config.NumberColumn("Total Puntos", help="Aciertos + Extra")
            },
            hide_index=True
        )
    else:
        st.info("Sin resultados todavía")

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
