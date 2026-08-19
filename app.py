import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import date

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="Sistema VANCAN - MINSA",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado
st.markdown("""
    <style>
    .main-header {
        background-color: #1f2937;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 25px;
        border-left: 5px solid #ef4444;
    }
    .footer-cherry {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #9ca3af;
        text-align: center;
        padding: 8px;
        font-size: 12px;
        border-top: 1px solid #374151;
        z-index: 999;
    }
    .block-container {
        padding-bottom: 60px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ENCABEZADO INSTITUCIONAL CON BANNER
# ==========================================
def render_header():
    col_img, col_txt = st.columns([1, 4])
    with col_img:
        # Intenta cargar la imagen si existe localmente, si no muestra banner estilizado
        if os.path.exists("banner_diris.png"):
            st.image("banner_diris.png", use_container_width=True)
        else:
            st.markdown("### 🏛️ **PERÚ - MINSA**\n*DIRIS Lima Este*")
    with col_txt:
        st.markdown("""
            <div class="main-header">
                <h2 style='margin:0;'>SISTEMA DE CONTROL Y SEGUIMIENTO VANCAN</h2>
                <p style='margin:0; color:#d1d5db;'>Dirección de Redes Integradas de Salud - Lima Este | Gestión Sanitaria</p>
            </div>
        """, unsafe_allow_html=True)

render_header()

# ==========================================
# 3. BASE DE DATOS Y RUTA CSV
# ==========================================
DB_NAME = "vancan.db"
CSV_ZONAS = "ZONAS.csv"
CSV_PERSONAL = "PERSONAL.csv"

def init_sqlite():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabla Registros Diarios
    c.execute('''CREATE TABLE IF NOT EXISTS avances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    eess TEXT,
                    turno TEXT,
                    brigada TEXT,
                    responsable TEXT,
                    zona TEXT,
                    dosis INTEGER,
                    integrante_1 TEXT,
                    integrante_2 TEXT,
                    observaciones TEXT,
                    usuario_registro TEXT,
                    fecha_hora_modificacion TEXT
                )''')
    # Tabla EESS y Metas
    c.execute('''CREATE TABLE IF NOT EXISTS eess_metas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eess TEXT UNIQUE,
                    meta INTEGER
                )''')
    # Tabla Personal
    c.execute('''CREATE TABLE IF NOT EXISTS personal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    cargo TEXT,
                    eess TEXT
                )''')
    conn.commit()
    conn.close()

init_sqlite()

def get_connection():
    return sqlite3.connect(DB_NAME)

# Sincronización Inicial CSV -> SQLite
def sync_csv_to_sqlite():
    conn = get_connection()
    # Cargar EESS/Metas
    if os.path.exists(CSV_ZONAS):
        try:
            df_z = pd.read_csv(CSV_ZONAS)
            for _, r in df_z.iterrows():
                eess_val = str(r.get('EESS', '')).strip()
                meta_val = int(r.get('META', 0)) if pd.notnull(r.get('META')) else 0
                if eess_val:
                    conn.execute("INSERT OR IGNORE INTO eess_metas (eess, meta) VALUES (?, ?)", (eess_val, meta_val))
        except Exception as e:
            pass
            
    # Cargar Personal
    if os.path.exists(CSV_PERSONAL):
        try:
            df_p = pd.read_csv(CSV_PERSONAL)
            for _, r in df_p.iterrows():
                nom_val = str(r.get('NOMBRE', '')).strip()
                car_val = str(r.get('CARGO', '')).strip()
                eess_val = str(r.get('EESS', '')).strip()
                if nom_val:
                    conn.execute("INSERT OR IGNORE INTO personal (nombre, cargo, eess) VALUES (?, ?, ?)", (nom_val, car_val, eess_val))
        except Exception as e:
            pass

    conn.commit()
    conn.close()

sync_csv_to_sqlite()

# Sobrescribir CSVs desde BD SQLite
def sync_sqlite_to_csv():
    conn = get_connection()
    # EESS/Metas -> CSV
    df_eess = pd.read_sql("SELECT eess AS EESS, meta AS META FROM eess_metas", conn)
    df_eess.to_csv(CSV_ZONAS, index=False)
    
    # Personal -> CSV
    df_pers = pd.read_sql("SELECT nombre AS NOMBRE, cargo AS CARGO, eess AS EESS FROM personal", conn)
    df_pers.to_csv(CSV_PERSONAL, index=False)
    conn.close()

# ==========================================
# 4. NAVEGACIÓN PRINCIPAL
# ==========================================
menu = st.sidebar.radio("📌 MENÚ PRINCIPAL", ["📊 Dashboard de Salida", "📝 Registrar Avance Diario", "⚙️ Configuración (Metas y Personal)"])

# ==========================================
# MODULO 1: DASHBOARD DE SALIDA
# ==========================================
if menu == "📊 Dashboard de Salida":
    st.title("📊 Dashboard Situacional VANCAN")
    
    conn = get_connection()
    df_eess_all = pd.read_sql("SELECT eess FROM eess_metas", conn)
    lista_eess = df_eess_all['eess'].tolist() if not df_eess_all.empty else ["C.S. CESAR LOPEZ SILVA"]
    
    # Asegurar preselección de C.S. CESAR LOPEZ SILVA
    idx_default = 0
    for idx, name in enumerate(lista_eess):
        if "CESAR LOPEZ SILVA" in name.upper():
            idx_default = idx
            break

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        eess_selected = st.selectbox("🏥 Seleccionar Establecimiento de Salud:", lista_eess, index=idx_default)
    
    # Consultar Meta
    meta_row = pd.read_sql("SELECT meta FROM eess_metas WHERE eess = ?", conn, params=(eess_selected,))
    meta_eess = meta_row['meta'].values[0] if not meta_row.empty else 0
    
    # Consultar Avances
    df_avances = pd.read_sql("SELECT * FROM avances WHERE eess = ?", conn, params=(eess_selected,))
    conn.close()

    total_dosis = df_avances['dosis'].sum() if not df_avances.empty else 0
    porcentaje = (total_dosis / meta_eess * 100) if meta_eess > 0 else 0.0

    # KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("🎯 Meta Establecida", f"{meta_eess:,} dosis")
    kpi2.metric("🐕 Dosis Aplicadas", f"{total_dosis:,} dosis")
    kpi3.metric("📈 Avance de Meta", f"{porcentaje:.2f}%")

    st.progress(min(porcentaje / 100, 1.0))
    st.markdown("---")

    if not df_avances.empty:
        st.subheader("📋 Resumen de Avance Diario")
        st.dataframe(df_avances[['fecha', 'turno', 'brigada', 'zona', 'dosis', 'integrante_1', 'integrante_2', 'observaciones']], use_container_width=True)

# ==========================================
# MODULO 2: REGISTRAR AVANCE DIARIO
# ==========================================
elif menu == "📝 Registrar Avance Diario":
    st.title("📝 Registro y Edición de Avance Diario")

    conn = get_connection()
    eess_list = pd.read_sql("SELECT eess FROM eess_metas", conn)['eess'].tolist()
    pers_list = pd.read_sql("SELECT nombre FROM personal", conn)['nombre'].tolist()
    conn.close()

    with st.expander("➕ **Ingresar Nuevo Registro de Avance**", expanded=False):
        with st.form("form_nuevo_avance"):
            c1, c2, c3 = st.columns(3)
            fecha_reg = c1.date_input("Fecha", date.today())
            eess_reg = c2.selectbox("EESS", eess_list if eess_list else ["C.S. CESAR LOPEZ SILVA"])
            turno_reg = c3.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

            c4, c5, c6 = st.columns(3)
            brigada_reg = c4.text_input("Brigada (Ej. Brigada 01)", "Brigada 01")
            resp_reg = c5.selectbox("Responsable", pers_list if pers_list else ["Sin Datos"])
            zona_reg = c6.text_input("Zona / Sector", "ALAMOS")

            c7, c8, c9 = st.columns(3)
            dosis_reg = c7.number_input("Dosis Aplicadas", min_value=0, value=0)
            int1_reg = c8.selectbox("Integrante 1", pers_list if pers_list else ["Sin Datos"])
            int2_reg = c9.selectbox("Integrante 2", pers_list if pers_list else ["Sin Datos"])

            obs_reg = st.text_input("Observaciones", "")
            btn_guardar = st.form_submit_button("💾 Guardar Registro")

            if btn_guardar:
                conn = get_connection()
                conn.execute("""
                    INSERT INTO avances (fecha, eess, turno, brigada, responsable, zona, dosis, integrante_1, integrante_2, observaciones, usuario_registro, fecha_hora_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'brigada', datetime('now', 'localtime'))
                """, (str(fecha_reg), eess_reg, turno_reg, brigada_reg, resp_reg, zona_reg, dosis_reg, int1_reg, int2_reg, obs_reg))
                conn.commit()
                conn.close()
                st.success("✅ Registro de avance guardado correctamente.")
                st.rerun()

    st.subheader("📑 Gestión y Edición de Registros Guardados")
    st.caption("Puedes editar directamente las celdas o eliminar filas desde la tabla interactiva inferior.")

    conn = get_connection()
    df_registros = pd.read_sql("SELECT * FROM avances ORDER BY id DESC", conn)
    conn.close()

    if not df_registros.empty:
        edited_df = st.data_editor(
            df_registros,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_avances"
        )

        if st.button("💾 Guardar Cambios en Registros"):
            conn = get_connection()
            conn.execute("DELETE FROM avances")
            for _, row in edited_df.iterrows():
                if pd.notnull(row['eess']):
                    conn.execute("""
                        INSERT INTO avances (id, fecha, eess, turno, brigada, responsable, zona, dosis, integrante_1, integrante_2, observaciones, usuario_registro, fecha_hora_modificacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                    """, (row['id'], str(row['fecha']), str(row['eess']), str(row['turno']), str(row['brigada']), str(row['responsable']), str(row['zona']), int(row['dosis']), str(row['integrante_1']), str(row['integrante_2']), str(row['observaciones']), str(row['usuario_registro'])))
            conn.commit()
            conn.close()
            st.success("✅ ¡Tabla de Avances actualizada con éxito!")
            st.rerun()

# ==========================================
# MODULO 3: CONFIGURACIÓN (METAS Y PERSONAL)
# ==========================================
elif menu == "⚙️ Configuración (Metas y Personal)":
    st.title("⚙️ Configuración de Metas, EESS y Personal")
    
    tab_eess, tab_personal = st.tabs(["🏥 Gestión de EESS y Metas", "👥 Gestión de Padrón de Personal"])

    # ------------------------------------
    # TAB 1: EESS Y METAS
    # ------------------------------------
    with tab_eess:
        st.subheader("➕ Ingreso Manual de Nuevo EESS / Meta")
        with st.form("form_nuevo_eess"):
            c1, c2 = st.columns(2)
            nuevo_eess = c1.text_input("Nombre del Centro de Salud / EESS")
            nueva_meta = c2.number_input("Meta de Dosis Programada", min_value=0, value=0)
            btn_add_eess = st.form_submit_button("➕ Agregar EESS")

            if btn_add_eess and nuevo_eess:
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO eess_metas (eess, meta) VALUES (?, ?)", (nuevo_eess.strip().upper(), nueva_meta))
                    conn.commit()
                    conn.close()
                    sync_sqlite_to_csv() # Sincronizar a CSV
                    st.success(f"✅ Centro de Salud '{nuevo_eess}' guardado en BD y CSV.")
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ El EESS ya existe o hubo un error en la inserción.")

        st.markdown("---")
        st.subheader("📋 Editar / Eliminar EESS y Metas Ingresadas")
        st.caption("Modifica celdas directamente o elimina filas seleccionándolas. Todo se sincroniza con el archivo CSV de origen.")

        conn = get_connection()
        df_eess_metas = pd.read_sql("SELECT id, eess AS EESS, meta AS META FROM eess_metas", conn)
        conn.close()

        edited_eess = st.data_editor(
            df_eess_metas,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_eess_metas"
        )

        if st.button("💾 Guardar Cambios en EESS y Metas"):
            conn = get_connection()
            conn.execute("DELETE FROM eess_metas")
            for _, row in edited_eess.iterrows():
                if pd.notnull(row['EESS']) and str(row['EESS']).strip() != "":
                    conn.execute("INSERT INTO eess_metas (id, eess, meta) VALUES (?, ?, ?)", (row['id'], str(row['EESS']).strip(), int(row['META'])))
            conn.commit()
            conn.close()
            sync_sqlite_to_csv() # Actualización de .CSV
            st.success("✅ Cambios guardados en SQLite y sobrescritos en ZONAS.csv")
            st.rerun()

    # ------------------------------------
    # TAB 2: PADRÓN DE PERSONAL
    # ------------------------------------
    with tab_personal:
        st.subheader("➕ Ingreso Manual de Nuevo Personal")
        with st.form("form_nuevo_personal"):
            c1, c2, c3 = st.columns(3)
            p_nombre = c1.text_input("Nombre y Apellidos (Ej. Tec. Juan Perez)")
            p_cargo = c2.selectbox("Cargo", ["Tec. Enfermería", "Lic. Enfermería", "Auxiliar", "Médico Veterinario", "Digitador", "Otro"])
            
            conn = get_connection()
            lista_centros = pd.read_sql("SELECT eess FROM eess_metas", conn)['eess'].tolist()
            conn.close()
            
            p_eess = c3.selectbox("Asignado a EESS", lista_centros if lista_centros else ["C.S. CESAR LOPEZ SILVA"])
            btn_add_pers = st.form_submit_button("➕ Agregar Personal")

            if btn_add_pers and p_nombre:
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO personal (nombre, cargo, eess) VALUES (?, ?, ?)", (p_nombre.strip(), p_cargo, p_eess))
                    conn.commit()
                    conn.close()
                    sync_sqlite_to_csv() # Sincronizar a CSV
                    st.success(f"✅ Personal '{p_nombre}' guardado en BD y CSV.")
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ El nombre de personal ya se encuentra registrado.")

        st.markdown("---")
        st.subheader("📋 Editar / Eliminar Personal del Padrón")
        st.caption("Modifica celdas directamente o elimina filas. Se mantendrá actualizado el archivo PERSONAL.csv")

        conn = get_connection()
        df_personal = pd.read_sql("SELECT id, nombre AS NOMBRE, cargo AS CARGO, eess AS EESS FROM personal", conn)
        conn.close()

        edited_personal = st.data_editor(
            df_personal,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_personal"
        )

        if st.button("💾 Guardar Cambios en Padrón de Personal"):
            conn = get_connection()
            conn.execute("DELETE FROM personal")
            for _, row in edited_personal.iterrows():
                if pd.notnull(row['NOMBRE']) and str(row['NOMBRE']).strip() != "":
                    conn.execute("INSERT INTO personal (id, nombre, cargo, eess) VALUES (?, ?, ?, ?)", (row['id'], str(row['NOMBRE']).strip(), str(row['CARGO']), str(row['EESS'])))
            conn.commit()
            conn.close()
            sync_sqlite_to_csv() # Actualización de .CSV
            st.success("✅ Cambios guardados en SQLite y sobrescritos en PERSONAL.csv")
            st.rerun()

# ==========================================
# 5. PIE DE PÁGINA INSTITUCIONAL (CHERRY)
# ==========================================
st.markdown("""
    <div class="footer-cherry">
        <b>Ministerio de Salud (MINSA) - DIRIS Lima Este</b> | Sistema VANCAN v2.4 | Desarrollado para la Gestión Sanitaria e Inmunizaciones
    </div>
""", unsafe_allow_html=True)
