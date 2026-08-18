import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime
import os

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS MINSA
# ==========================================
st.set_page_config(
    page_title="Sistema VANCAN - Monitoreo MINSA",
    page_icon="🐕",
    layout="wide"
)

# Estilos CSS con colores institucionales MINSA
st.markdown("""
    <style>
    .main-header {
        background-color: #003366;
        color: white;
        padding: 15px;
        text-align: center;
        border-radius: 8px;
        margin-bottom: 25px;
    }
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #D91023;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado Principal MINSA
st.markdown("""
    <div class="main-header">
        <h2>MINISTERIO DE SALUD DEL PERÚ - VANCAN</h2>
        <h4>Sistema de Monitoreo y Control de Vacunación Canina</h4>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 2. BASE DE DATOS Y LECTURA DE ARCHIVO "ZONAS"
# ==========================================
def init_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    
    # Tabla de avances de vacunación
    c.execute('''
        CREATE TABLE IF NOT EXISTS avances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            eess TEXT,
            turno TEXT,
            brigada TEXT,
            responsable TEXT,
            zona TEXT,
            dosis INTEGER,
            observaciones TEXT,
            usuario_registro TEXT,
            fecha_hora_modificacion TEXT,
            equipo_ip TEXT
        )
    ''')
    
    # Migración/Verificación de columnas de auditoría
    c.execute("PRAGMA table_info(avances)")
    columnas_existentes = [columna[1] for columna in c.fetchall()]
    if 'usuario_registro' not in columnas_existentes:
        c.execute("ALTER TABLE avances ADD COLUMN usuario_registro TEXT DEFAULT 'desconocido'")
    if 'fecha_hora_modificacion' not in columnas_existentes:
        c.execute("ALTER TABLE avances ADD COLUMN fecha_hora_modificacion TEXT DEFAULT ''")
    if 'equipo_ip' not in columnas_existentes:
        c.execute("ALTER TABLE avances ADD COLUMN equipo_ip TEXT DEFAULT 'desconocido'")

    # Tabla para Metas Manuales por EESS
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            eess TEXT PRIMARY KEY,
            meta_canes INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Carga de lista de Zonas considerando archivo ZONAS.csv / zonas.csv
def obtener_zonas():
    archivos_posibles = ['ZONAS.csv', 'zonas.csv', 'Zonas.csv', 'ZONAS']
    
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            try:
                # Lectura tolerante a codificación UTF-8 / Latin-1
                try:
                    df_z = pd.read_csv(archivo, encoding='utf-8')
                except UnicodeDecodeError:
                    df_z = pd.read_csv(archivo, encoding='latin1')

                # Detección de columna 'ZONAS', 'ZONA', 'LUGAR', 'SECTOR' o la primera por defecto
                col_zona = None
                for c in df_z.columns:
                    if str(c).strip().upper() in ['ZONAS', 'ZONA', 'LUGAR', 'SECTOR']:
                        col_zona = c
                        break
                
                if not col_zona:
                    col_zona = df_z.columns[0]

                zonas = df_z[col_zona].dropna().unique().tolist()
                lista_limpia = sorted([str(z).strip() for z in zonas if str(z).strip() != ''])
                if lista_limpia:
                    return lista_limpia
            except Exception as e:
                print(f"Error al leer {archivo}: {e}")
                
    # Lista de respaldo si no se encuentra el archivo ZONAS.csv cargado
    return ["Sector Central", "Ñaña", "Huascata", "Los Cedros", "Santa Inés", "Ocharán", "Carapongo"]

LISTA_ZONAS = obtener_zonas()
LISTA_EESS = ["C.S. César López Silva", "C.S. Ñaña", "C.S. Morón", "C.S. Chosica"]
LISTA_TURNOS = ["Mañana", "Tarde"]

# Funciones SQLite
def guardar_registro(fecha, eess, turno, brigada, responsable, zona, dosis, obs, usuario, ip_equipo):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, eess, turno, brigada, responsable, zona, dosis, obs, usuario, fecha_hora_actual, ip_equipo))
    conn.commit()
    conn.close()

def guardar_meta(eess, meta):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO metas (eess, meta_canes) VALUES (?, ?)', (eess, meta))
    conn.commit()
    conn.close()

def cargar_datos():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM avances", conn)
    conn.close()
    
    columnas_esperadas = ['usuario_registro', 'fecha_hora_modificacion', 'equipo_ip', 'dosis', 'eess', 'zona', 'turno']
    for col in columnas_esperadas:
        if col not in df.columns:
            df[col] = '' if col != 'dosis' else 0
    return df

def cargar_metas():
    conn = sqlite3.connect('vancan_data.db')
    df_m = pd.read_sql_query("SELECT * FROM metas", conn)
    conn.close()
    return df_m

def get_remote_ip():
    try:
        headers = st.context.headers
        return headers.get("X-Forwarded-For", "Dispositivo Móvil / Web")
    except Exception:
        return "Web Client"

# ==========================================
# 3. CONTROL DE ACCESO (LOGIN)
# ==========================================
USUARIOS = {
    "brigada": {"pass": "vancan2026", "rol": "Brigadista / Digitador"},
    "coordinador": {"pass": "admin2026", "rol": "Coordinador / Editor"},
    "director": {"pass": "salud2026", "rol": "Lector / Directivo"}
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None

if not st.session_state["logged_in"]:
    st.subheader("🔒 Acceso al Sistema VANCAN")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        user_input = st.text_input("Usuario").strip().lower()
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user_input in USUARIOS and USUARIOS[user_input]["pass"] == pass_input:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = USUARIOS[user_input]["rol"]
                st.session_state["username"] = user_input
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrecta")
    st.stop()

# ==========================================
# 4. NAVEGACIÓN Y SIDEBAR
# ==========================================
st.sidebar.markdown(f"**Usuario:** `{st.session_state['username']}`")
st.sidebar.markdown(f"**Rol:** `{st.session_state['user_role']}`")
st.sidebar.markdown(f"**Zonas Cargadas (ZONAS):** `{len(LISTA_ZONAS)}`")
st.sidebar.markdown("---")

opciones = []
if st.session_state["user_role"] in ["Brigadista / Digitador", "Coordinador / Editor"]:
    opciones.append("📝 Registrar Avance Diario")
if st.session_state["user_role"] in ["Coordinador / Editor", "Lector / Directivo"]:
    opciones.append("📊 Dashboard y Vacunómetro")
if st.session_state["user_role"] == "Coordinador / Editor":
    opciones.append("🎯 Configuración Manual de Metas")
    opciones.append("🕵️ Auditoría y Gestión de Datos")

opciones.append("Cerrar Sesión")
opcion = st.sidebar.radio("Menú Principal", opciones)

if opcion == "Cerrar Sesión":
    st.session_state["logged_in"] = False
    st.rerun()

# ==========================================
# MÓDULO 1: REGISTRO DE AVANCE DIARIO
# ==========================================
if opcion == "📝 Registrar Avance Diario":
    st.header("📝 Carga Diario de Vacunación Canina")
    
    with st.form("form_carga", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha de Intervención", datetime.now())
            eess = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            turno = st.selectbox("Turno", LISTA_TURNOS)
            brigada = st.text_input("Código de Brigada / Equipo", placeholder="Ej. Brigada 05")
        
        with col2:
            responsable = st.text_input("Responsable del Registro", placeholder="Ej. Lic. Carlos Mendoza")
            # Selección con buscador dinámico de los 100+ lugares cargados desde ZONAS
            zona = st.selectbox("Zona / Lugar de Intervención (Buscador activo)", LISTA_ZONAS)
            dosis = st.number_input("Canes Vacunados (Dosis)", min_value=0, step=1)

        obs = st.text_area("Observaciones o Incidencias")
        
        btn_guardar = st.form_submit_button("🚀 Guardar Registro", type="primary", use_container_width=True)

        if btn_guardar:
            if not brigada or not responsable:
                st.warning("⚠️ Debes ingresar la brigada y el responsable.")
            else:
                ip_cli = get_remote_ip()
                guardar_registro(str(fecha), eess, turno, brigada, responsable, zona, int(dosis), obs, st.session_state["username"], ip_cli)
                st.success("✅ ¡Registro guardado exitosamente!")

    st.subheader("📋 Mis registros ingresados")
    df_all = cargar_datos()
    if not df_all.empty:
        df_propios = df_all[df_all['usuario_registro'] == st.session_state["username"]]
        cols_mostrar = [c for c in ['fecha', 'eess', 'turno', 'brigada', 'zona', 'dosis', 'fecha_hora_modificacion'] if c in df_propios.columns]
        st.dataframe(df_propios[cols_mostrar], use_container_width=True)
    else:
        st.info("Aún no se registran datos en esta sesión.")

# ==========================================
# MÓDULO 2: DASHBOARD Y VACUNÓMETRO
# ==========================================
elif opcion == "📊 Dashboard y Vacunómetro":
    st.header("📊 Dashboard Analítico y Vacunómetro MINSA")
    
    df = cargar_datos()
    df_metas = cargar_metas()

    if df.empty:
        st.info("Aún no hay registros de vacunación en el sistema.")
    else:
        st.subheader("🔍 Filtros de Visualización")
        f1, f2, f3 = st.columns(3)
        
        eess_disponibles = df['eess'].unique().tolist()
        zonas_disponibles = sorted(df['zona'].unique().tolist())
        turnos_disponibles = df['turno'].unique().tolist()

        eess_sel = f1.multiselect("Establecimiento de Salud", eess_disponibles, default=eess_disponibles)
        zona_sel = f2.multiselect("Zona de Intervención", zonas_disponibles, default=zonas_disponibles)
        turno_sel = f3.multiselect("Turno", turnos_disponibles, default=turnos_disponibles)

        df_f = df[(df['eess'].isin(eess_sel)) & (df['zona'].isin(zona_sel)) & (df['turno'].isin(turno_sel))]

        total_vacunados = pd.to_numeric(df_f['dosis'], errors='coerce').fillna(0).sum()

        # Suma de la meta manual según los EESS seleccionados
        if not df_metas.empty:
            meta_filtrada = df_metas[df_metas['eess'].isin(eess_sel)]['meta_canes'].sum()
        else:
            meta_filtrada = 0

        pct_avance = (total_vacunados / meta_filtrada * 100) if meta_filtrada > 0 else 0.0

        st.markdown("---")

        # SECCIÓN VACUNÓMETRO
        c_vac1, c_vac2 = st.columns([1, 2])
        
        with c_vac1:
            st.markdown("### 💉 Vacunómetro de Avance")
            st.metric("Total Vacunados", f"{int(total_vacunados):,} canes")
            st.metric("Meta Manual Total", f"{int(meta_filtrada):,} canes" if meta_filtrada > 0 else "Sin Meta Definida")
            st.metric("% Cobertura Alcanzado", f"{pct_avance:.1f} %" if meta_filtrada > 0 else "N/A")

        with c_vac2:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = total_vacunados,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Avance vs Meta Manual Asignada", 'font': {'size': 18}},
                delta = {'reference': meta_filtrada, 'increasing': {'color': "green"}},
                gauge = {
                    'axis': {'range': [None, max(meta_filtrada, total_vacunados if total_vacunados>0 else 100)]},
                    'bar': {'color': "#003366"},
                    'steps': [
                        {'range': [0, meta_filtrada*0.5], 'color': "#FADBD8"},
                        {'range': [meta_filtrada*0.5, meta_filtrada*0.85], 'color': "#FCF3CF"},
                        {'range': [meta_filtrada*0.85, meta_filtrada], 'color': "#D4EFDF"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': meta_filtrada
                    }
                }
            ))
            fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown("---")

        # Gráficos por Zonas y Brigadas
        g1, g2 = st.columns(2)

        with g1:
            st.subheader("📍 Cobertura por Zona de Intervención")
            df_z = df_f.groupby('zona')['dosis'].sum().reset_index()
            df_z = df_z.sort_values(by='dosis', ascending=True)
            fig_z = px.bar(
                df_z, x='dosis', y='zona', orientation='h', 
                text='dosis',
                color_discrete_sequence=['#003366'],
                labels={'dosis': 'Canes Vacunados', 'zona': 'Zona'}
            )
            fig_z.update_layout(height=max(400, len(df_z)*25))
            st.plotly_chart(fig_z, use_container_width=True)

        with g2:
            st.subheader("👥 Avance por Brigada y Turno")
            df_b = df_f.groupby(['brigada', 'turno'])['dosis'].sum().reset_index()
            fig_b = px.bar(df_b, x='brigada', y='dosis', color='turno', barmode='group', text_auto=True,
                           color_discrete_map={'Mañana': '#003366', 'Tarde': '#D91023'})
            st.plotly_chart(fig_b, use_container_width=True)

# ==========================================
# MÓDULO 3: CONFIGURACIÓN MANUAL DE METAS
# ==========================================
elif opcion == "🎯 Configuración Manual de Metas":
    st.header("🎯 Definición Manual de Metas por Establecimiento")
    st.info("Ingresa o actualiza manualmente la meta de canes a vacunar para cada Establecimiento de Salud.")

    col_form, col_tabla = st.columns([1, 1])

    with col_form:
        with st.form("form_metas"):
            eess_m = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            meta_val = st.number_input("Meta de Canes (Número entero)", min_value=1, value=1000, step=50)
            btn_m = st.form_submit_button("💾 Guardar / Actualizar Meta", type="primary")

            if btn_m:
                guardar_meta(eess_m, meta_val)
                st.success(f"✅ Meta de {meta_val:,} canes registrada para {eess_m}")
                st.rerun()

    with col_tabla:
        st.subheader("📋 Metas Configuradas Actuales")
        df_m_curr = cargar_metas()
        if not df_m_curr.empty:
            st.dataframe(df_m_curr, use_container_width=True)
        else:
            st.warning("Aún no se han configurado metas manuales para ningún EESS.")

# ==========================================
# MÓDULO 4: AUDITORÍA Y CONTROL DE DATOS
# ==========================================
elif opcion == "🕵️ Auditoría y Gestión de Datos":
    st.header("🕵️ Auditoría y Control de Cambios")
    st.caption("Muestra la fecha/hora exacta de registro/modificación, el usuario y la IP o dispositivo de origen.")

    df_aud = cargar_datos()
    st.dataframe(df_aud, use_container_width=True)

    csv_data = df_aud.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte de Auditoría (CSV)",
        data=csv_data,
        file_name=f"Auditoria_VANCAN_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime='text/csv',
        type="primary"
    )
