import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime
import plotly.graph_objects as go

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema VANCAN - MINSA",
    page_icon="💉",
    layout="wide"
)

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def normalizar_texto(texto):
    """Convierte texto a mayúsculas y limpia acentos para homogeneizar la DB"""
    if not texto:
        return ""
    texto = str(texto).upper().strip()
    replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    return re.sub(r'\s+', ' ', texto)

# ==========================================
# BASE DE DATOS SQLITE Y REINDEXACIÓN DE IDs
# ==========================================
def init_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    
    # Tabla de Avances Diarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS avances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            eess TEXT,
            turno TEXT,
            brigada TEXT,
            integrante_1 TEXT,
            integrante_2 TEXT,
            responsable TEXT,
            zona TEXT,
            dosis INTEGER,
            observaciones TEXT,
            usuario_registro TEXT,
            fecha_hora_modificacion TEXT
        )
    ''')
    
    # Tabla de Establecimientos y Metas
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eess TEXT UNIQUE,
            meta_canes INTEGER
        )
    ''')

    # Precarga de referencia inicial si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM metas")
    if c.fetchone()[0] == 0:
        metas_iniciales = [
            ("C.S. CESAR LOPEZ SILVA", 1400),
            ("C.S. MOYOPAMPA", 1200),
            ("C.S. CHACLACAYO", 1500)
        ]
        c.executemany("INSERT INTO metas (eess, meta_canes) VALUES (?, ?)", metas_iniciales)

    # Tabla de Personal
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            cargo TEXT,
            dni TEXT
        )
    ''')
    
    # Precarga de referencia inicial de personal si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM personal_db")
    if c.fetchone()[0] == 0:
        personal_inicial = [
            ("TEC. JORGE CAMPOS", "TÉCNICO", ""),
            ("LIC. ETHEL ROSALES", "ENFERMERA", ""),
            ("TEC. MARINA GALAN", "TÉCNICO", ""),
            ("LIC. SARA VILLANUEVA", "ENFERMERA", "")
        ]
        c.executemany("INSERT INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", personal_inicial)

    conn.commit()
    conn.close()

def reindexar_tabla(nombre_tabla):
    """
    Reorganiza los IDs de una tabla desde el 1 consecutivamente (1, 2, 3...)
    después de realizar eliminaciones o actualizaciones masivas.
    """
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    
    if nombre_tabla == "metas":
        c.execute("SELECT eess, meta_canes FROM metas ORDER BY id ASC")
        registros = c.fetchall()
        c.execute("DELETE FROM metas")
        c.execute("DELETE FROM sqlite_sequence WHERE name='metas'")
        for item in registros:
            c.execute("INSERT INTO metas (eess, meta_canes) VALUES (?, ?)", item)
            
    elif nombre_tabla == "personal_db":
        c.execute("SELECT nombre, cargo, dni FROM personal_db ORDER BY id ASC")
        registros = c.fetchall()
        c.execute("DELETE FROM personal_db")
        c.execute("DELETE FROM sqlite_sequence WHERE name='personal_db'")
        for item in registros:
            c.execute("INSERT INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", item)
            
    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES DE CONSULTA
# ==========================================
def cargar_avances():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM avances ORDER BY id ASC", conn)
    conn.close()
    return df

def cargar_metas():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT id, eess, meta_canes FROM metas ORDER BY id ASC", conn)
    conn.close()
    return df

def cargar_personal():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT id, nombre, cargo, dni FROM personal_db ORDER BY id ASC", conn)
    conn.close()
    return df

def guardar_avance(fecha, eess, turno, brigada, integ1, integ2, resp, zona, dosis, obs, usuario):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    f_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (str(fecha), eess, turno, brigada, integ1, integ2, resp, zona, int(dosis), obs, usuario, f_mod))
    conn.commit()
    conn.close()

def obtener_eess_activos():
    df = cargar_metas()
    if not df.empty:
        return sorted(df['eess'].tolist())
    return ["C.S. CESAR LOPEZ SILVA"]

def obtener_personal_activo():
    df = cargar_personal()
    if not df.empty:
        return sorted(df['nombre'].tolist())
    return ["TEC. JORGE CAMPOS"]

LISTA_ZONAS = ["ROBLES", "ROCAS", "ROSALEDA", "ROSARIO", "ROSAS", "SAN BARTOLOME", "SAN JOSE", "SANTA INES"]
LISTA_TURNOS = ["Mañana", "Tarde"]
LISTA_BRIGADAS = [f"Brigada {i:02d}" for i in range(1, 21)]

# ==========================================
# MENÚ LATERAL
# ==========================================
st.sidebar.title("📌 VANCAN MINSA")
opcion = st.sidebar.radio("Navegación:", [
    "📝 Registrar Avance Diario",
    "📊 Dashboard y Vacunómetro",
    "⚙️ Configuración (EESS, Metas y Personal)"
])

# ==========================================
# MÓDULO 1: REGISTRO DIARIO
# ==========================================
if opcion == "📝 Registrar Avance Diario":
    st.header("📝 Registro de Avance Diario de Vacunación")
    
    eess_disponibles = obtener_eess_activos()
    personal_disponible = obtener_personal_activo()

    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_in = st.date_input("Fecha de Actividad", datetime.now())
            eess_in = st.selectbox("Centro de Salud (EESS)", eess_disponibles)
            turno_in = st.selectbox("Turno", LISTA_TURNOS)
        
        with col2:
            brigada_in = st.selectbox("Brigada", LISTA_BRIGADAS)
            responsable_in = st.text_input("Responsable de Brigada", value="MARINA GALAN")
            zona_in = st.selectbox("Zona de Intervención", LISTA_ZONAS)

        with col3:
            dosis_in = st.number_input("Canes Vacunados (Dosis)", min_value=0, step=1, value=50)
            integ1_in = st.selectbox("Integrante 1 (Obligatorio)", options=["-- Seleccionar --"] + personal_disponible)
            integ2_in = st.selectbox("Integrante 2 (Opcional)", options=["-- Ninguno --"] + personal_disponible)
            obs_in = st.text_area("Observaciones", value="")

        btn_guardar = st.form_submit_button("💾 Guardar Avance", type="primary", use_container_width=True)

        if btn_guardar:
            if integ1_in == "-- Seleccionar --":
                st.error("⚠️ Debes seleccionar al menos al Integrante 1.")
            else:
                p2 = integ2_in if integ2_in != "-- Ninguno --" else ""
                guardar_avance(fecha_in, eess_in, turno_in, brigada_in, integ1_in, p2, responsable_in, zona_in, dosis_in, obs_in, "admin")
                st.success("✅ Avance guardado correctamente.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Registros Guardados")
    df_avances = cargar_avances()
    if not df_avances.empty:
        st.dataframe(df_avances, use_container_width=True)
    else:
        st.info("No hay registros almacenados.")

# ==========================================
# MÓDULO 2: DASHBOARD
# ==========================================
elif opcion == "📊 Dashboard y Vacunómetro":
    st.header("📊 Dashboard Analítico y Vacunómetro")
    
    df_avances = cargar_avances()
    df_metas = cargar_metas()
    
    eess_disponibles = obtener_eess_activos()
    eess_sel = st.multiselect("Filtrar por Centro de Salud", eess_disponibles, default=eess_disponibles)

    if not df_metas.empty and eess_sel:
        meta_total = df_metas[df_metas['eess'].isin(eess_sel)]['meta_canes'].sum()
    else:
        meta_total = 0

    if not df_avances.empty and eess_sel:
        df_f = df_avances[df_avances['eess'].isin(eess_sel)]
        total_vacunados = df_f['dosis'].sum()
    else:
        total_vacunados = 0

    porcentaje = (total_vacunados / meta_total * 100) if meta_total > 0 else 0.0

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Total Canes Vacunados", f"{total_vacunados:,}")
        st.metric("Meta Programada", f"{meta_total:,}")
        st.metric("Cobertura (%)", f"{porcentaje:.1f} %")

    with c2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=total_vacunados,
            gauge={
                'axis': {'range': [None, max(meta_total, total_vacunados if total_vacunados > 0 else 100)]},
                'bar': {'color': "#003366"},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta_total}
            }
        ))
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MÓDULO 3: CONFIGURACIÓN
# ==========================================
elif opcion == "⚙️ Configuración (EESS, Metas y Personal)":
    st.header("⚙️ Configuración del Sistema")
    st.caption("Administra dinámicamente los Establecimientos de Salud, Metas de vacunación y Padrón de Personal.")

    tab_eess, tab_personal = st.tabs(["🏥 Establecimientos y Metas", "👥 Padrón de Personal"])

    # -------------------------------------------------------------
    # TAB 1: GESTIÓN DE ESTABLECIMIENTOS Y METAS
    # -------------------------------------------------------------
    with tab_eess:
        st.subheader("➕ 1. Agregar Nuevo Centro de Salud")
        with st.form("form_nuevo_eess", clear_on_submit=True):
            col_e1, col_e2 = st.columns(2)
            nuevo_eess_nombre = col_e1.text_input("Nombre del Centro de Salud", placeholder="Ej: C.S. MORON")
            nueva_meta = col_e2.number_input("Meta de Canes", min_value=1, value=1000, step=100)
            btn_add_eess = st.form_submit_button("➕ Registrar Centro de Salud", type="primary")

            if btn_add_eess:
                nombre_norm = normalizar_texto(nuevo_eess_nombre)
                if nombre_norm:
                    conn = sqlite3.connect('vancan_data.db')
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO metas (eess, meta_canes) VALUES (?, ?)", (nombre_norm, nueva_meta))
                        conn.commit()
                        st.success(f"✅ {nombre_norm} registrado correctamente.")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ El establecimiento ya existe en la base de datos.")
                    finally:
                        conn.close()
                    
                    reindexar_tabla("metas")
                    st.rerun()
                else:
                    st.error("⚠️ Ingrese un nombre válido.")

        st.markdown("---")
        st.subheader("📋 2. Mantenimiento de Establecimientos y Metas (Edición y Eliminación)")
        st.caption("Modifica la información directamente en las celdas de la tabla y haz clic en 'Guardar Cambios'. Para borrar, utiliza la sección inferior.")

        df_metas_db = cargar_metas()

        if not df_metas_db.empty:
            df_metas_edited = st.data_editor(
                df_metas_db,
                column_config={
                    "id": st.column_config.NumberColumn("ID (Correlativo)", disabled=True),
                    "eess": st.column_config.TextColumn("Centro de Salud / EESS", required=True),
                    "meta_canes": st.column_config.NumberColumn("Meta Canes", min_value=1, step=10, required=True)
                },
                use_container_width=True,
                hide_index=True,
                key="editor_eess_key"
            )

            col_btn_save_e, col_btn_del_e = st.columns([1, 1])
            
            with col_btn_save_e:
                if st.button("💾 Guardar Cambios en EESS", type="primary", use_container_width=True):
                    conn = sqlite3.connect('vancan_data.db')
                    c = conn.cursor()
                    for _, row in df_metas_edited.iterrows():
                        e_norm = normalizar_texto(row['eess'])
                        if e_norm:
                            c.execute("UPDATE metas SET eess = ?, meta_canes = ? WHERE id = ?", (e_norm, int(row['meta_canes']), int(row['id'])))
                    conn.commit()
                    conn.close()
                    
                    reindexar_tabla("metas")
                    st.success("✅ Establecimientos y metas actualizados correctamente.")
                    st.rerun()

            with col_btn_del_e:
                with st.expander("🗑️ Eliminar un Centro de Salud"):
                    eess_borrar = st.selectbox("Seleccione EESS a borrar:", df_metas_db['eess'].tolist(), key="select_del_eess")
                    if st.button("❌ Confirmar Eliminación de EESS"):
                        conn = sqlite3.connect('vancan_data.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM metas WHERE eess = ?", (eess_borrar,))
                        conn.commit()
                        conn.close()
                        
                        # Reindexar IDs desde 1
                        reindexar_tabla("metas")
                        
                        st.success(f"Establecimiento {eess_borrar} eliminado y los IDs fueron reindexados.")
                        st.rerun()
        else:
            st.info("No hay centros de salud registrados.")

    # -------------------------------------------------------------
    # TAB 2: GESTIÓN DE PERSONAL
    # -------------------------------------------------------------
    with tab_personal:
        st.subheader("➕ 1. Agregar Nuevo Personal")
        with st.form("form_nuevo_personal", clear_on_submit=True):
            cp1, cp2, cp3 = st.columns(3)
            p_nombre = cp1.text_input("Nombre y Apellido (Ej: TEC. PEDRO LOPEZ)")
            p_cargo = cp2.selectbox("Cargo", ["TÉCNICO", "ENFERMERA", "MÉDICO VETERINARIO", "DIGITADOR", "OTRO"])
            p_dni = cp3.text_input("DNI (Opcional)")
            btn_add_p = st.form_submit_button("➕ Registrar Personal", type="primary")

            if btn_add_p:
                p_norm = normalizar_texto(p_nombre)
                if p_norm:
                    conn = sqlite3.connect('vancan_data.db')
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", (p_norm, p_cargo, p_dni.strip()))
                        conn.commit()
                        st.success(f"✅ {p_norm} agregado al padrón.")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Este trabajador ya está registrado en el padrón.")
                    finally:
                        conn.close()
                    
                    reindexar_tabla("personal_db")
                    st.rerun()
                else:
                    st.error("⚠️ Ingrese un nombre válido.")

        st.markdown("---")
        st.subheader("📋 2. Padrón de Personal Registrado (Edición y Eliminación)")
        st.caption("Edita los nombres o cargos en la tabla y presiona 'Guardar Cambios'. Para retirar trabajadores, usa el panel desplegable.")

        df_personal_db = cargar_personal()

        if not df_personal_db.empty:
            df_personal_edited = st.data_editor(
                df_personal_db,
                column_config={
                    "id": st.column_config.NumberColumn("ID (Correlativo)", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre y Apellido", required=True),
                    "cargo": st.column_config.SelectboxColumn("Cargo", options=["TÉCNICO", "ENFERMERA", "MÉDICO VETERINARIO", "DIGITADOR", "OTRO"]),
                    "dni": st.column_config.TextColumn("DNI")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_personal_key"
            )

            col_save_p, col_del_p = st.columns([1, 1])

            with col_save_p:
                if st.button("💾 Guardar Cambios en Padrón", type="primary", use_container_width=True):
                    conn = sqlite3.connect('vancan_data.db')
                    c = conn.cursor()
                    for _, row in df_personal_edited.iterrows():
                        nom_norm = normalizar_texto(row['nombre'])
                        if nom_norm:
                            c.execute("UPDATE personal_db SET nombre = ?, cargo = ?, dni = ? WHERE id = ?", 
                                      (nom_norm, row['cargo'], str(row['dni']) if pd.notna(row['dni']) else "", int(row['id'])))
                    conn.commit()
                    conn.close()
                    
                    reindexar_tabla("personal_db")
                    st.success("✅ Padrón de personal actualizado correctamente.")
                    st.rerun()

            with col_del_p:
                with st.expander("🗑️ Eliminar un Integrante del Personal"):
                    pers_borrar = st.selectbox("Seleccione Persona a borrar:", df_personal_db['nombre'].tolist(), key="select_del_personal")
                    if st.button("❌ Confirmar Eliminación de Persona"):
                        conn = sqlite3.connect('vancan_data.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM personal_db WHERE nombre = ?", (pers_borrar,))
                        conn.commit()
                        conn.close()
                        
                        # Reindexar IDs desde 1
                        reindexar_tabla("personal_db")
                        
                        st.success(f"Trabajador {pers_borrar} eliminado y los IDs fueron reindexados.")
                        st.rerun()
        else:
            st.info("No hay personal registrado en la base de datos.")
