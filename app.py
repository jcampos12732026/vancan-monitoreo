import streamlit as st
import pandas as pd
import sqlite3
import re
import os
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema VANCAN - MINSA",
    page_icon="💉",
    layout="wide"
)

# ==========================================
# FUNCIONES AUXILIARES DE TEXTO
# ==========================================
def normalizar_texto(texto):
    """Convierte texto a mayúsculas y limpia acentos para homogeneizar la DB"""
    if pd.isna(texto) or texto is None:
        return ""
    texto = str(texto).upper().strip()
    replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    return re.sub(r'\s+', ' ', texto)

# ==========================================
# CARGA AUTOMÁTICA E INTELIGENTE DE PERSONAL.CSV
# ==========================================
def sincronizar_personal_csv():
    """Lee personal.csv detectando automáticamente los nombres de las columnas"""
    if os.path.exists('personal.csv'):
        try:
            # Detectar separador común (coma o punto y coma)
            df_csv = None
            for sep in [',', ';', '\t']:
                try:
                    temp_df = pd.read_csv('personal.csv', sep=sep)
                    if len(temp_df.columns) >= 1 and len(temp_df) > 0:
                        df_csv = temp_df
                        break
                except Exception:
                    continue

            if df_csv is not None and not df_csv.empty:
                # 1. Identificar columna de nombres
                col_nombre = None
                for col in df_csv.columns:
                    col_upper = str(col).upper()
                    if any(k in col_upper for k in ['NOMB', 'PERS', 'INTEG', 'TRABAJ', 'EMPLEA', 'APELLID']):
                        col_nombre = col
                        break
                if not col_nombre:
                    col_nombre = df_csv.columns[0] # Tomar la primera columna si no encuentra coincidencia

                # 2. Identificar columna de cargo
                col_cargo = None
                for col in df_csv.columns:
                    if any(k in str(col).upper() for k in ['CARG', 'PROF', 'FUNCI']):
                        col_cargo = col
                        break

                # 3. Identificar columna DNI
                col_dni = None
                for col in df_csv.columns:
                    if any(k in str(col).upper() for k in ['DNI', 'DOC', 'CEDULA']):
                        col_dni = col
                        break

                conn = sqlite3.connect('vancan_data.db')
                c = conn.cursor()
                for _, row in df_csv.iterrows():
                    nom = normalizar_texto(row.get(col_nombre, ''))
                    car = normalizar_texto(row.get(col_cargo, 'TÉCNICO')) if col_cargo else 'TÉCNICO'
                    dni = str(row.get(col_dni, '')).strip() if col_dni else ''
                    
                    if car == "":
                        car = "TÉCNICO"

                    if nom and len(nom) > 2:
                        c.execute("INSERT OR REPLACE INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", (nom, car, dni))
                conn.commit()
                conn.close()
        except Exception as e:
            st.error(f"Error leyendo personal.csv: {e}")

# ==========================================
# INICIALIZACIÓN DE BASE DE DATOS
# ==========================================
def init_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    
    # 1. Tabla 'metas'
    c.execute("CREATE TABLE IF NOT EXISTS metas (eess TEXT PRIMARY KEY, meta_canes INTEGER)")
    c.execute("PRAGMA table_info(metas)")
    cols_metas = [col[1] for col in c.fetchall()]
    
    if 'eess' not in cols_metas:
        c.execute("ALTER TABLE metas ADD COLUMN eess TEXT")
    if 'meta_canes' not in cols_metas:
        c.execute("ALTER TABLE metas ADD COLUMN meta_canes INTEGER DEFAULT 0")

    c.execute("SELECT COUNT(*) FROM metas")
    if c.fetchone()[0] == 0:
        c.execute("INSERT OR IGNORE INTO metas (eess, meta_canes) VALUES (?, ?)", ("C.S. CESAR LOPEZ SILVA", 1400))

    # 2. Tabla 'personal_db'
    c.execute("CREATE TABLE IF NOT EXISTS personal_db (nombre TEXT PRIMARY KEY, cargo TEXT, dni TEXT)")
    c.execute("PRAGMA table_info(personal_db)")
    cols_personal = [col[1] for col in c.fetchall()]
    
    if 'nombre' not in cols_personal:
        c.execute("ALTER TABLE personal_db ADD COLUMN nombre TEXT")
    if 'cargo' not in cols_personal:
        c.execute("ALTER TABLE personal_db ADD COLUMN cargo TEXT DEFAULT 'TÉCNICO'")
    if 'dni' not in cols_personal:
        c.execute("ALTER TABLE personal_db ADD COLUMN dni TEXT DEFAULT ''")

    conn.commit()
    conn.close()

    # Sincronizar desde CSV al iniciar
    sincronizar_personal_csv()

    # Si sigue vacía, agregar registros por defecto
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM personal_db")
    if c.fetchone()[0] == 0:
        personal_inicial = [
            ("TEC. JORGE CAMPOS", "TÉCNICO", ""),
            ("LIC. ETHEL ROSALES", "ENFERMERA", ""),
            ("TEC. MARINA GALAN", "TÉCNICO", "")
        ]
        c.executemany("INSERT OR IGNORE INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", personal_inicial)

    # 3. Tabla 'avances'
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

    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES DE CONSULTA
# ==========================================
def cargar_avances():
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM avances ORDER BY id ASC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def cargar_metas():
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM metas", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()

    for col in ['eess', 'meta_canes']:
        if col not in df.columns:
            df[col] = "" if col == 'eess' else 0

    if not df.empty and 'eess' in df.columns:
        df = df.sort_values(by='eess').reset_index(drop=True)
        df.insert(0, 'ID', range(1, len(df) + 1))
    return df

def cargar_personal():
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM personal_db", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()

    for col in ['nombre', 'cargo', 'dni']:
        if col not in df.columns:
            df[col] = ""

    if not df.empty and 'nombre' in df.columns:
        df = df.sort_values(by='nombre').reset_index(drop=True)
        df.insert(0, 'ID', range(1, len(df) + 1))
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
    if not df.empty and 'eess' in df.columns:
        lista = [str(x).strip() for x in df['eess'].dropna().unique() if str(x).strip() != ""]
        if lista:
            return sorted(lista)
    return ["C.S. CESAR LOPEZ SILVA"]

def obtener_personal_activo():
    df = cargar_personal()
    if not df.empty and 'nombre' in df.columns:
        lista = [str(x).strip() for x in df['nombre'].dropna().unique() if str(x).strip() != ""]
        if lista:
            return sorted(lista)
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
# MÓDULO 2: DASHBOARD (REGLA 50% POR INTEGRANTE)
# ==========================================
elif opcion == "📊 Dashboard y Vacunómetro":
    st.header("📊 Dashboard Analítico y Vacunómetro")
    
    df_avances = cargar_avances()
    df_metas = cargar_metas()
    
    eess_disponibles = obtener_eess_activos()
    eess_sel = st.multiselect("Filtrar por Centro de Salud", eess_disponibles, default=eess_disponibles)

    if not df_metas.empty and eess_sel and 'eess' in df_metas.columns:
        meta_total = df_metas[df_metas['eess'].isin(eess_sel)]['meta_canes'].sum()
    else:
        meta_total = 0

    if not df_avances.empty and eess_sel and 'eess' in df_avances.columns:
        df_f = df_avances[df_avances['eess'].isin(eess_sel)].copy()
        total_vacunados = df_f['dosis'].sum()
    else:
        df_f = pd.DataFrame()
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
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    if not df_f.empty:
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("🚩 Avance por Brigada")
            df_brigada = df_f.groupby('brigada')['dosis'].sum().reset_index().sort_values(by='dosis', ascending=False)
            fig_b = px.bar(df_brigada, x='brigada', y='dosis', text='dosis', title="Dosis Totales por Brigada", color='dosis', color_continuous_scale='Blues')
            fig_b.update_traces(textposition='outside')
            st.plotly_chart(fig_b, use_container_width=True)

        with col_g2:
            st.subheader("👥 Producción Individual (50% por Integrante)")
            
            filas_personal = []
            for _, row in df_f.iterrows():
                dosis = row['dosis']
                i1 = str(row['integrante_1']).strip()
                i2 = str(row['integrante_2']).strip()
                
                tiene_i2 = i2 != "" and i2 != "-- Ninguno --" and pd.notna(row['integrante_2'])

                if tiene_i2:
                    dosis_mitad = dosis / 2.0
                    filas_personal.append({'Personal': i1, 'Dosis Atribuidas': dosis_mitad})
                    filas_personal.append({'Personal': i2, 'Dosis Atribuidas': dosis_mitad})
                else:
                    filas_personal.append({'Personal': i1, 'Dosis Atribuidas': float(dosis)})

            df_pers_calc = pd.DataFrame(filas_personal)
            df_pers_resumen = df_pers_calc.groupby('Personal')['Dosis Atribuidas'].sum().reset_index().sort_values(by='Dosis Atribuidas', ascending=False)
            df_pers_resumen['Dosis Atribuidas'] = df_pers_resumen['Dosis Atribuidas'].round(1)

            fig_p = px.bar(df_pers_resumen, x='Personal', y='Dosis Atribuidas', text='Dosis Atribuidas', title="Dosis por Personal (50% asignado a cada integrante)", color='Dosis Atribuidas', color_continuous_scale='Greens')
            fig_p.update_traces(textposition='outside')
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("No hay avances registrados para mostrar gráficos.")

# ==========================================
# MÓDULO 3: CONFIGURACIÓN Y GESTIÓN DE PERSONAL
# ==========================================
elif opcion == "⚙️ Configuración (EESS, Metas y Personal)":
    st.header("⚙️ Configuración del Sistema")

    tab_eess, tab_personal = st.tabs(["🏥 Establecimientos y Metas", "👥 Padrón de Personal"])

    with tab_eess:
        st.subheader("➕ Agregar Nuevo Centro de Salud")
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
                    c.execute("INSERT OR REPLACE INTO metas (eess, meta_canes) VALUES (?, ?)", (nombre_norm, nueva_meta))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {nombre_norm} registrado.")
                    st.rerun()

        st.markdown("---")
        df_metas_db = cargar_metas()
        if not df_metas_db.empty:
            st.dataframe(df_metas_db, use_container_width=True)

    with tab_personal:
        st.subheader("📁 Cargar / Actualizar desde Archivo `personal.csv`")
        uploaded_csv = st.file_uploader("Subir archivo personal.csv", type=["csv"])
        
        if uploaded_csv is not None:
            try:
                df_up = pd.read_csv(uploaded_csv)
                st.write("Vista previa:", df_up.head(3))
                if st.button("📥 Importar a Base de Datos"):
                    df_up.to_csv("personal.csv", index=False)
                    sincronizar_personal_csv()
                    st.success("✅ Personal sincronizado exitosamente.")
                    st.rerun()
            except Exception as ex:
                st.error(f"Error al procesar archivo: {ex}")

        st.markdown("---")
        st.subheader("📋 Padrón de Personal Registrado")
        df_personal_db = cargar_personal()

        if not df_personal_db.empty:
            df_personal_edited = st.data_editor(
                df_personal_db,
                column_config={
                    "ID": st.column_config.NumberColumn("N°", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre y Apellido", required=True),
                    "cargo": st.column_config.SelectboxColumn("Cargo", options=["TÉCNICO", "ENFERMERA", "MÉDICO VETERINARIO", "DIGITADOR", "OTRO"]),
                    "dni": st.column_config.TextColumn("DNI")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_personal_key"
            )

            if st.button("💾 Guardar Cambios en Padrón", type="primary"):
                conn = sqlite3.connect('vancan_data.db')
                c = conn.cursor()
                for _, row in df_personal_edited.iterrows():
                    nom_norm = normalizar_texto(row['nombre'])
                    if nom_norm:
                        c.execute("INSERT OR REPLACE INTO personal_db (nombre, cargo, dni) VALUES (?, ?, ?)", 
                                  (nom_norm, str(row['cargo']), str(row['dni']) if pd.notna(row['dni']) else ""))
                conn.commit()
                conn.close()
                st.success("✅ Padrón actualizado correctamente.")
                st.rerun()
        else:
            st.info("No hay personal registrado.")
