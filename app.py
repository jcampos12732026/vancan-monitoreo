import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y BASE DE DATOS
# ==========================================
st.set_page_config(
    page_title="Sistema de Monitoreo VANCAN",
    page_icon="🐕",
    layout="wide"
)

# Inicializar Base de Datos SQLite (Persistente y Ligera)
def init_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
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
            registro_fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Funciones de consulta BD
def guardar_registro(fecha, eess, turno, brigada, responsable, zona, dosis, obs):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, responsable, zona, dosis, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, eess, turno, brigada, responsable, zona, dosis, obs))
    conn.commit()
    conn.close()

def cargar_datos():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM avances", conn)
    conn.close()
    return df

# ==========================================
# 2. CONTROL DE ACCESO Y ROLES (SEGURIDAD)
# ==========================================
USUARIOS = {
    "brigada": {"pass": "vancan2026", "rol": "Brigadista / Digitador"},
    "coordinador": {"pass": "admin2026", "rol": "Coordinador / Editor"},
    "director": {"pass": "salud2026", "rol": "Lector / Directivo"}
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None

def login():
    st.title("🔒 Acceso al Sistema de Monitoreo - VANCAN")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        usuario = st.text_input("Usuario").strip().lower()
        clave = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if usuario in USUARIOS and USUARIOS[usuario]["pass"] == clave:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = USUARIOS[usuario]["rol"]
                st.session_state["username"] = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ==========================================
# 3. INTERFAZ PRINCIPAL & NAVEGACIÓN
# ==========================================
st.sidebar.title("🐕 VANCAN - Monitoreo")
st.sidebar.caption(f"Rol: **{st.session_state['user_role']}**")

# Menú según rol
opciones_menu = []
if st.session_state["user_role"] in ["Brigadista / Digitador", "Coordinador / Editor"]:
    opciones_menu.append("📝 Carga de Registro Diario")
if st.session_state["user_role"] in ["Coordinador / Editor", "Lector / Directivo"]:
    opciones_menu.append("📊 Dashboard Consolidado")
if st.session_state["user_role"] == "Coordinador / Editor":
    opciones_menu.append("🛠️ Gestión y Edición de Datos")

opciones_menu.append("Cerrar Sesión")
opcion = st.sidebar.radio("Navegación", opciones_menu)

if opcion == "Cerrar Sesión":
    st.session_state["logged_in"] = False
    st.rerun()

# Listas Predefinidas
LISTA_EESS = ["C.S. César López Silva", "C.S. Ñaña", "C.S. Morón", "C.S. Chosica"]
LISTA_ZONAS = ["Sector Central", "Ñaña", "Huascata", "Los Cedros", "Santa Inés", "Ocharán"]
LISTA_TURNOS = ["Mañana", "Tarde"]

# ==========================================
# MÓDULO 1: FORMULARIO DE REGISTRO
# ==========================================
if opcion == "📝 Carga de Registro Diario":
    st.header("📝 Registro Diario de Vacunación Canina")
    st.info("Ingresa los datos correspondientes al avance de tu brigada en el turno.")

    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("Fecha de la jornada", datetime.now())
            eess = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            turno = st.selectbox("Turno", LISTA_TURNOS)
            brigada = st.text_input("Código / Nombre de Brigada", placeholder="Ej. Brigada 01")

        with col2:
            responsable = st.text_input("Responsable / Digitador", placeholder="Ej. Lic. Ana Torres")
            zona = st.selectbox("Zona / Sector de Intervención", LISTA_ZONAS)
            dosis = st.number_input("Cantidad de Canes Vacunados (Dosis)", min_value=0, step=1)
        
        obs = st.text_area("Observaciones e Incidencias (Opcional)")
        
        submit = st.form_submit_button("🚀 Guardar Registro Diario", type="primary", use_container_width=True)

        if submit:
            if not brigada or not responsable:
                st.warning("⚠️ Por favor completa el código de brigada y el nombre del responsable.")
            else:
                guardar_registro(str(fecha), eess, turno, brigada, responsable, zona, int(dosis), obs)
                st.success("✅ ¡Registro guardado exitosamente!")

# ==========================================
# MÓDULO 2: DASHBOARD CONSOLIDADO
# ==========================================
elif opcion == "📊 Dashboard Consolidado":
    st.header("📊 Dashboard de Avances Diarios")
    
    df = cargar_datos()
    if df.empty:
        st.warning("Aún no hay datos registrados para mostrar el consolidado.")
    else:
        # Filtros Superiores Dinámicos
        st.subheader("🔍 Filtros de Consulta")
        f1, f2, f3, f4 = st.columns(4)
        
        eess_f = f1.multiselect("Filtrar por EESS", df['eess'].unique(), default=df['eess'].unique())
        turno_f = f2.multiselect("Filtrar por Turno", df['turno'].unique(), default=df['turno'].unique())
        zona_f = f3.multiselect("Filtrar por Zona", df['zona'].unique(), default=df['zona'].unique())
        brigada_f = f4.multiselect("Filtrar por Brigada", df['brigada'].unique(), default=df['brigada'].unique())

        # Filtrar DataFrame
        df_filtered = df[
            (df['eess'].isin(eess_f)) & 
            (df['turno'].isin(turno_f)) & 
            (df['zona'].isin(zona_f)) & 
            (df['brigada'].isin(brigada_f))
        ]

        st.markdown("---")

        # KPIs Principales
        total_canes = df_filtered['dosis'].sum()
        total_brigadas = df_filtered['brigada'].nunique()
        total_eess = df_filtered['eess'].nunique()

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("🐕 Total Canes Vacunados", f"{total_canes:,}")
        kpi2.metric("👥 Brigadas Activas", total_brigadas)
        kpi3.metric("🏥 EESS Monitoreados", total_eess)

        st.markdown("---")

        # Gráficos Analíticos
        g1, g2 = st.columns(2)

        with g1:
            st.subheader("📈 Avance Diario por Fecha")
            df_fecha = df_filtered.groupby('fecha')['dosis'].sum().reset_index()
            fig_fecha = px.bar(df_fecha, x='fecha', y='dosis', text_auto=True, color_discrete_sequence=['#2E86C1'])
            fig_fecha.update_layout(xaxis_title="Fecha", yaxis_title="Dosis Aplicadas")
            st.plotly_chart(fig_fecha, use_container_width=True)

        with g2:
            st.subheader("📍 Cobertura por Zona / Sector")
            df_zona = df_filtered.groupby('zona')['dosis'].sum().reset_index()
            fig_zona = px.pie(df_zona, names='zona', values='dosis', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_zona, use_container_width=True)

        g3, g4 = st.columns(2)

        with g3:
            st.subheader("🏆 Avance por Brigada / Equipo")
            df_brigada = df_filtered.groupby(['brigada', 'turno'])['dosis'].sum().reset_index()
            fig_brigada = px.bar(df_brigada, x='brigada', y='dosis', color='turno', barmode='group', text_auto=True)
            st.plotly_chart(fig_brigada, use_container_width=True)

        with g4:
            st.subheader("🏥 Dosis Aplicadas por EESS")
            df_eess = df_filtered.groupby('eess')['dosis'].sum().reset_index()
            fig_eess = px.bar(df_eess, x='eess', y='dosis', color='eess', text_auto=True)
            st.plotly_chart(fig_eess, use_container_width=True)

# ==========================================
# MÓDULO 3: GESTIÓN DE DATOS (EDICIÓN)
# ==========================================
elif opcion == "🛠️ Gestión y Edición de Datos":
    st.header("🛠️ Panel de Control y Auditoría de Datos")
    st.caption("Solo para coordinadores. Permite revisar la base de datos completa.")
    
    df = cargar_datos()
    st.dataframe(df, use_container_width=True)
    
    # Opción para descargar reporte consolidado en Excel/CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Base de Datos Completa (CSV)",
        data=csv,
        file_name=f"Consolidado_VANCAN_{datetime.now().strftime('%Y%m%m')}.csv",
        mime='text/csv',
        type="primary"
    )
