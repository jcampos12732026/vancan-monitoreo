import streamlit as st
import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# CONFIGURACIÓN INICIAL DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema VANCAN - MINSA",
    page_icon="💉",
    layout="wide"
)

# ==========================================
# FUNCIONES AUXILIARES DE LIMPIEZA
# ==========================================
def normalizar_texto(texto):
    """Limpia tildes, caracteres especiales y convierte a mayúsculas"""
    if not texto:
        return ""
    texto = str(texto).upper().strip()
    replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

# ==========================================
# BASE DE DATOS SQLITE (INICIALIZACIÓN TOTAL)
# ==========================================
def init_db():
    """Inicializa todas las tablas de la base de datos para evitar errores de consulta"""
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    
    # 1. Tabla de Avances
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
            fecha_hora_modificacion TEXT,
            equipo_ip TEXT
        )
    ''')
    
    # Migración por si existe la columna antigua 'integrantes'
    c.execute("PRAGMA table_info(avances)")
    cols = [col[1] for col in c.fetchall()]
    if 'integrantes' in cols and 'integrante_1' not in cols:
        c.execute("ALTER TABLE avances ADD COLUMN integrante_1 TEXT")
        c.execute("ALTER TABLE avances ADD COLUMN integrante_2 TEXT")
        c.execute("UPDATE avances SET integrante_1 = integrantes")
    
    # 2. Tabla de Metas
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eess TEXT UNIQUE,
            meta_canes INTEGER
        )
    ''')
    
    # 3. Tabla de Personal
    c.execute('''
        CREATE TABLE IF NOT EXISTS personal_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            dni TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Se ejecuta al arrancar el script siempre
init_db()

# ==========================================
# FUNCIONES SQLITE BLINDADAS
# ==========================================
def cargar_datos():
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM avances ORDER BY id ASC", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def cargar_metas():
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM metas ORDER BY id ASC", conn)
    except Exception:
        df = pd.DataFrame(columns=['id', 'eess', 'meta_canes'])
    finally:
        conn.close()
    return df

def cargar_personal_db():
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM personal_db ORDER BY id ASC", conn)
    except Exception:
        df = pd.DataFrame(columns=['id', 'nombre', 'dni'])
    finally:
        conn.close()
    return df

def guardar_avance_db(fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones, usuario_registro):
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_simulada = "10.14.14.2, 10.16"
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (str(fecha), eess, turno, brigada, integrante_1, integrante_2, responsable, zona, int(dosis), observaciones, usuario_registro, fecha_mod, ip_simulada))
    conn.commit()
    conn.close()

def actualizar_registro_db(id_reg, fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones):
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        UPDATE avances 
        SET fecha=?, eess=?, turno=?, brigada=?, integrante_1=?, integrante_2=?, responsable=?, zona=?, dosis=?, observaciones=?, fecha_hora_modificacion=?
        WHERE id=?
    ''', (str(fecha), eess, turno, brigada, integrante_1, integrante_2, responsable, zona, int(dosis), observaciones, fecha_mod, id_reg))
    conn.commit()
    conn.close()

def reordenar_ids_db():
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("CREATE TABLE avances_seq AS SELECT * FROM avances ORDER BY id ASC;")
    c.execute("DELETE FROM avances;")
    c.execute("DELETE FROM sqlite_sequence WHERE name='avances';")
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        SELECT fecha, eess, turno, brigada, integrante_1, integrante_2, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip
        FROM avances_seq ORDER BY id ASC;
    ''')
    c.execute("DROP TABLE avances_seq;")
    conn.commit()
    conn.close()

def eliminar_registro_db(id_reg):
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances WHERE id=?", (id_reg,))
    conn.commit()
    conn.close()
    reordenar_ids_db()

def vaciar_base_datos_db():
    init_db()
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances")
    c.execute("DELETE FROM sqlite_sequence WHERE name='avances'")
    conn.commit()
    conn.close()

# ==========================================
# CARGA DE DATOS COMPLEMENTARIOS (CSV + DB)
# ==========================================
def cargar_personal_completo():
    """Combina datos de PERSONAL.csv con los registrados en la DB"""
    personal_set = set()
    
    # 1. Desde la base de datos
    df_p = cargar_personal_db()
    if not df_p.empty and 'nombre' in df_p.columns:
        for n in df_p['nombre'].dropna().astype(str).tolist():
            if n.strip():
                personal_set.add(n.strip())

    # 2. Desde el archivo CSV
    archivos = ['PERSONAL.csv', 'personal.csv', 'Personal.csv', 'PERSONAL.CSV']
    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo, sep=';', encoding='utf-8')
                if 'NOMBRES' not in df.columns:
                    df = pd.read_csv(archivo, sep=',', encoding='utf-8')
                if 'NOMBRES' in df.columns:
                    for n in df['NOMBRES'].dropna().astype(str).str.strip().tolist():
                        personal_set.add(n)
            except Exception:
                try:
                    df = pd.read_csv(archivo, sep=';', encoding='latin1')
                    if 'NOMBRES' in df.columns:
                        for n in df['NOMBRES'].dropna().astype(str).str.strip().tolist():
                            personal_set.add(n)
                except Exception as e:
                    print(f"Error leyendo {archivo}: {e}")
                    
    resultado = sorted(list(personal_set))
    return resultado if resultado else ["Tec. Jorge Campos", "Lic. Jorge Vasquez", "Tec. Marina Galan"]

def cargar_zonas_csv():
    """Lee ZONAS.csv trayendo las zonas dinámicamente"""
    archivos = ['ZONAS.csv', 'zonas.csv', 'Zonas.csv', 'ZONAS.CSV']
    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo, sep=None, engine='python', encoding='utf-8')
                col_target = None
                for col in df.columns:
                    if normalizar_texto(col) in ['ZONA', 'ZONAS', 'LUGAR', 'SECTOR', 'NOMBRE']:
                        col_target = col
                        break
                if not col_target and len(df.columns) > 0:
                    col_target = df.columns[0]
                
                if col_target:
                    return sorted(df[col_target].dropna().astype(str).str.strip().unique().tolist())
            except Exception:
                try:
                    df = pd.read_csv(archivo, sep=None, engine='python', encoding='latin1')
                    if len(df.columns) > 0:
                        return sorted(df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist())
                except Exception as e:
                    print(f"Error leyendo {archivo}: {e}")
    
    return ["ROBLES", "ROCAS", "ROSALEDA", "ROSARIO", "ROSAS", "SAN BARTOLOME", "SAN JOSE", "SANTA INES"]

LISTA_PERSONAL = cargar_personal_completo()
LISTA_ZONAS = cargar_zonas_csv()
LISTA_EESS = ["C.S. CESAR LOEPZ SILVA", "C.S. NAÑA", "C.S. MORON", "C.S. CHOSICA"]
LISTA_TURNOS = ["Mañana", "Tarde"]
LISTA_BRIGADAS = [f"Brigada {i:02d}" for i in range(1, 21)]

def obtener_metas_csv():
    metas_dict = {
        "CS CESAR LOPEZ SILVA": 1400,
        "CS NANA": 2200,
        "CS MORON": 2800,
        "CS CHOSICA": 4000
    }
    archivos_posibles = ['METAS.csv', 'metas.csv', 'Metas.csv']
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo, sep=None, engine='python', encoding='utf-8')
                col_eess, col_meta = None, None
                for c in df.columns:
                    c_upper = normalizar_texto(c)
                    if c_upper in ['EESS', 'ESTABLECIMIENTO', 'ESTABLECIMIENTOS', 'CENTRO DE SALUD']:
                        col_eess = c
                    elif c_upper in ['META CANES', 'META', 'DOSIS', 'CANES']:
                        col_meta = c
                if col_eess and col_meta:
                    for _, row in df.iterrows():
                        metas_dict[normalizar_texto(row[col_eess])] = int(row[col_meta])
            except Exception as e:
                print(f"Error meta CSV: {e}")
    return metas_dict

def obtener_meta_establecimiento(eess_nombre, mapa_metas):
    eess_norm = normalizar_texto(eess_nombre)
    if eess_norm in mapa_metas:
        return mapa_metas[eess_norm]
    if "CESAR" in eess_norm or "LOPEZ" in eess_norm or "LOEPZ" in eess_norm or "SILVA" in eess_norm:
        return mapa_metas.get("CS CESAR LOPEZ SILVA", 1400)
    elif "NANA" in eess_norm:
        return mapa_metas.get("CS NANA", 2200)
    elif "MORON" in eess_norm:
        return mapa_metas.get("CS MORON", 2800)
    elif "CHOSICA" in eess_norm:
        return mapa_metas.get("CS CHOSICA", 4000)
    return 1000

# ==========================================
# NAVEGACIÓN Y MENÚ LATERAL
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
    st.session_state["user_role"] = "Brigadista / Digitador"
    st.session_state["username"] = "brigada"

st.sidebar.title("📌 Menú VANCAN MINSA")
st.sidebar.info(f"**Usuario:** {st.session_state['username']}\n\n**Rol:** {st.session_state['user_role']}")

opcion = st.sidebar.radio("Ir a:", [
    "📝 Registrar Avance Diario",
    "📊 Dashboard y Vacunómetro",
    "⚙️ Configuración / Metas"
])

# ==========================================
# MÓDULO 1: REGISTRO Y GESTIÓN DE AVANCE
# ==========================================
if opcion == "📝 Registrar Avance Diario":
    st.header("📝 Registro de Avances Diario de Vacunación Canina")
    st.caption("Completa el formulario seleccionando al Integrante 1 e Integrante 2 de la brigada.")

    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_input = st.date_input("Fecha de Actividad", datetime.now())
            eess_input = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            turno_input = st.selectbox("Turno", LISTA_TURNOS)
        
        with col2:
            brigada_input = st.selectbox("Brigada", LISTA_BRIGADAS)
            responsable_input = st.text_input("Responsable de Brigada", value="MARINA")
            zona_input = st.selectbox("Zona / Lugar (ZONAS.CSV)", LISTA_ZONAS)

        with col3:
            dosis_input = st.number_input("Dosis Aplicadas (Canes)", min_value=0, step=1, value=50)
            
            integ1_sel = st.selectbox("Integrante 1 (Obligatorio)", options=["-- Seleccionar --"] + LISTA_PERSONAL, index=1 if len(LISTA_PERSONAL)>0 else 0)
            integ2_sel = st.selectbox("Integrante 2 (Opcional)", options=["-- Ninguno --"] + LISTA_PERSONAL, index=2 if len(LISTA_PERSONAL)>1 else 0)
            
            observaciones_input = st.text_area("Observaciones", value="")

        btn_guardar = st.form_submit_button("💾 Guardar Registro de Avance", type="primary", use_container_width=True)

        if btn_guardar:
            if integ1_sel == "-- Seleccionar --":
                st.error("⚠️ Debes seleccionar al menos el Integrante 1.")
            else:
                p1 = integ1_sel
                p2 = integ2_sel if integ2_sel != "-- Ninguno --" else ""
                guardar_avance_db(
                    fecha_input, eess_input, turno_input, brigada_input, 
                    p1, p2, responsable_input, zona_input, 
                    dosis_input, observaciones_input, st.session_state["username"]
                )
                st.success(f"✅ Registro guardado con éxito. Integrantes: {p1} / {p2 if p2 else 'Solo'}")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Gestión y Edición de Registros Guardados")
    st.caption("Puedes editar directamente Integrante 1 e Integrante 2 desde las columnas desglosadas.")
    
    df_all = cargar_datos()
    if not df_all.empty:
        df_mostrar = df_all if st.session_state["user_role"] != "Brigadista / Digitador" else df_all[df_all['usuario_registro'] == st.session_state["username"]].copy()

        if not df_mostrar.empty:
            if "fecha" in df_mostrar.columns:
                df_mostrar["fecha"] = pd.to_datetime(df_mostrar["fecha"], errors='coerce')

            columnas_ordenadas = [
                "id", "fecha", "eess", "turno", "brigada", 
                "responsable", "zona", "dosis", "integrante_1", "integrante_2",
                "observaciones", "usuario_registro", "fecha_hora_modificacion", "equipo_ip"
            ]
            cols_presentes = [c for c in columnas_ordenadas if c in df_mostrar.columns]
            df_mostrar = df_mostrar[cols_presentes]

            opts_eess = sorted(list(set(LISTA_EESS + df_mostrar['eess'].dropna().astype(str).tolist())))
            opts_turno = sorted(list(set(LISTA_TURNOS + df_mostrar['turno'].dropna().astype(str).tolist())))
            opts_brigada = sorted(list(set(LISTA_BRIGADAS + df_mostrar['brigada'].dropna().astype(str).tolist())))
            opts_zona = sorted(list(set(LISTA_ZONAS + df_mostrar['zona'].dropna().astype(str).tolist())))
            opts_personal = sorted(list(set([""] + LISTA_PERSONAL + df_mostrar['integrante_1'].dropna().astype(str).tolist() + df_mostrar['integrante_2'].dropna().astype(str).tolist())))

            df_edited = st.data_editor(
                df_mostrar,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "fecha": st.column_config.DateColumn("Fecha", required=True),
                    "eess": st.column_config.SelectboxColumn("EESS", options=opts_eess, required=True),
                    "turno": st.column_config.SelectboxColumn("Turno", options=opts_turno, required=True),
                    "brigada": st.column_config.SelectboxColumn("Brigada", options=opts_brigada, required=True),
                    "zona": st.column_config.SelectboxColumn("Zona (ZONAS.CSV)", options=opts_zona, required=True),
                    "dosis": st.column_config.NumberColumn("Dosis", min_value=0, step=1, required=True),
                    "integrante_1": st.column_config.SelectboxColumn("Integrante 1", options=opts_personal, required=True),
                    "integrante_2": st.column_config.SelectboxColumn("Integrante 2", options=opts_personal, required=False),
                    "observaciones": st.column_config.TextColumn("Observaciones")
                },
                disabled=["usuario_registro", "fecha_hora_modificacion", "equipo_ip"],
                use_container_width=True,
                num_rows="dynamic",
                key="editor_registros"
            )

            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("💾 Guardar Cambios Editados", type="primary", use_container_width=True):
                    for _, row in df_edited.iterrows():
                        actualizar_registro_db(
                            row['id'], row['fecha'], row['eess'], row['turno'], 
                            row['brigada'], str(row['integrante_1']), str(row['integrante_2']) if pd.notna(row['integrante_2']) else "", 
                            row['responsable'], row['zona'], int(row['dosis']), str(row['observaciones'])
                        )
                    st.success("✅ Registros actualizados correctamente.")
                    st.rerun()

            with col_b:
                with st.expander("🗑️ Opciones de Eliminación / Limpieza de Registros"):
                    modo_eliminar = st.radio("Acción:", ["Eliminar registro individual por ID", "🔥 Vaciar TODOS los registros"])
                    if modo_eliminar == "Eliminar registro individual por ID":
                        ids_disponibles = df_mostrar['id'].tolist()
                        id_eliminar = st.number_input("ID a eliminar:", min_value=1, step=1, value=ids_disponibles[0] if ids_disponibles else 1)
                        if st.button("❌ Confirmar Eliminación"):
                            eliminar_registro_db(id_eliminar)
                            st.success(f"ID {id_eliminar} eliminado y correlativo reordenado.")
                            st.rerun()
                    else:
                        st.warning("⚠️ Eliminará todos los datos. Reinicia ID a 1.")
                        conf = st.checkbox("Confirmar vaciado completo")
                        if st.button("🚨 VACIAR BASE DE DATOS", disabled=not conf):
                            vaciar_base_datos_db()
                            st.rerun()
    else:
        st.info("No hay registros guardados en la base de datos.")

# ==========================================
# MÓDULO 2: DASHBOARD Y VACUNÓMETRO
# ==========================================
elif opcion == "📊 Dashboard y Vacunómetro":
    col_head_dash, col_btn_ref = st.columns([4, 1])
    with col_head_dash:
        st.header("📊 Dashboard Analítico y Vacunómetro MINSA")
    with col_btn_ref:
        st.write("") 
        if st.button("🔄 Actualizar Datos", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df = cargar_datos()
    df_metas_db = cargar_metas()
    mapa_metas = obtener_metas_csv()
    if not df_metas_db.empty:
        for _, r in df_metas_db.iterrows():
            mapa_metas[normalizar_texto(r['eess'])] = int(r['meta_canes'])

    st.subheader("🔍 Filtros de Visualización")
    f1, f2, f3 = st.columns(3)
    
    eess_disponibles = LISTA_EESS
    eess_sel = f1.multiselect("Establecimiento de Salud", eess_disponibles, default=eess_disponibles)
    
    zonas_disponibles = sorted(list(set(df['zona'].unique().tolist() + LISTA_ZONAS))) if not df.empty else LISTA_ZONAS
    turnos_disponibles = df['turno'].unique().tolist() if not df.empty else LISTA_TURNOS

    zona_sel = f2.multiselect("Zona de Intervención", zonas_disponibles, default=zonas_disponibles)
    turno_sel = f3.multiselect("Turno", turnos_disponibles, default=turnos_disponibles)

    if not df.empty:
        df_f = df[(df['eess'].isin(eess_sel)) & (df['zona'].isin(zona_sel)) & (df['turno'].isin(turno_sel))].copy()
        total_vacunados = pd.to_numeric(df_f['dosis'], errors='coerce').fillna(0).sum()
    else:
        df_f = pd.DataFrame()
        total_vacunados = 0

    meta_filtrada = sum([obtener_meta_establecimiento(e, mapa_metas) for e in eess_sel])
    pct_avance = (total_vacunados / meta_filtrada * 100) if meta_filtrada > 0 else 0.0

    st.markdown("---")

    c_vac1, c_vac2 = st.columns([1, 2])
    with c_vac1:
        st.markdown("### 💉 Vacunómetro de Avance")
        st.metric("Total Vacunados", f"{int(total_vacunados):,} canes")
        st.metric("Meta Programada Total", f"{int(meta_filtrada):,} canes")
        st.metric("% Cobertura Alcanzado", f"{pct_avance:.1f} %")

    with c_vac2:
        st.markdown("<h4 style='text-align: center; color: #003366;'>🎯 Avance vs Meta Programada</h4>", unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_vacunados,
            delta={'reference': meta_filtrada, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [None, max(meta_filtrada, total_vacunados if total_vacunados > 0 else 100)]},
                'bar': {'color': "#003366"},
                'steps': [
                    {'range': [0, meta_filtrada * 0.5], 'color': "#FADBD8"},
                    {'range': [meta_filtrada * 0.5, meta_filtrada * 0.85], 'color': "#FCF3CF"},
                    {'range': [meta_filtrada * 0.85, meta_filtrada], 'color': "#D4EFDF"}
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': meta_filtrada}
            }
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=30, r=30, t=10, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("---")

    if not df_f.empty:
        g1, g2 = st.columns(2)

        with g1:
            st.markdown("### 📅 Avance Diario de Vacunación")
            df_diario = df_f.groupby('fecha')['dosis'].sum().reset_index()
            df_diario['fecha'] = pd.to_datetime(df_diario['fecha']).dt.strftime('%Y-%m-%d')
            df_diario = df_diario.sort_values('fecha')

            fig_diario = px.bar(
                df_diario, 
                x='fecha', 
                y='dosis', 
                text='dosis',
                labels={'fecha': 'Fecha', 'dosis': 'Canes Vacunados'},
                title="Producción Total por Día",
                color_discrete_sequence=['#006699']
            )
            fig_diario.update_traces(textposition='outside')
            st.plotly_chart(fig_diario, use_container_width=True)

        with g2:
            st.markdown("### 👤 Producción Individual por Persona")
            st.caption("💡 Las dosis registradas se dividen equitativamente entre Integrante 1 e Integrante 2.")

            registros_personas = []
            for _, row in df_f.iterrows():
                p1 = str(row.get('integrante_1', '')).strip()
                p2 = str(row.get('integrante_2', '')).strip()
                
                if not p1 and 'integrantes' in row and pd.notna(row['integrantes']):
                    partes = [x.strip() for x in str(row['integrantes']).split(',') if x.strip()]
                    p1 = partes[0] if len(partes) > 0 else ""
                    p2 = partes[1] if len(partes) > 1 else ""

                integrantes_activos = [p for p in [p1, p2] if p and p.lower() not in ['none', 'nan', 'null', '']]
                cant = len(integrantes_activos)
                
                if cant > 0:
                    dosis_persona = float(row['dosis']) / cant
                    for p in integrantes_activos:
                        registros_personas.append({'persona': p, 'dosis_individual': dosis_persona})

            if registros_personas:
                df_personas = pd.DataFrame(registros_personas)
                df_personas_agg = df_personas.groupby('persona')['dosis_individual'].sum().reset_index()
                df_personas_agg['dosis_individual'] = df_personas_agg['dosis_individual'].round(1)
                df_personas_agg = df_personas_agg.sort_values('dosis_individual', ascending=True)

                fig_personas = px.bar(
                    df_personas_agg, 
                    y='persona', 
                    x='dosis_individual', 
                    orientation='h',
                    text='dosis_individual',
                    labels={'persona': 'Integrante de Brigada', 'dosis_individual': 'Producción (Dosis)'},
                    title="Producción Equitativa por Integrante",
                    color_discrete_sequence=['#2E8B57']
                )
                fig_personas.update_traces(textposition='outside')
                st.plotly_chart(fig_personas, use_container_width=True)
            else:
                st.info("No hay datos de integrantes para el gráfico.")
    else:
        st.info("No hay datos para mostrar los gráficos analíticos con los filtros seleccionados.")

# ==========================================
# MÓDULO 3: CONFIGURACIÓN, METAS Y PERSONAL
# ==========================================
elif opcion == "⚙️ Configuración / Metas":
    st.header("⚙️ Configuración del Sistema")
    st.caption("Administra las Metas por Establecimiento y el Padrón de Personal.")

    tab_metas, tab_personal = st.tabs(["🎯 Gestor de Metas", "👥 Gestor de Personal"])

    # 1. TAB METAS
    with tab_metas:
        st.subheader("➕ Agregar / Actualizar Meta")
        
        with st.form("form_metas"):
            c1, c2 = st.columns(2)
            eess_meta = c1.selectbox("Establecimiento de Salud", LISTA_EESS)
            meta_val = c2.number_input("Meta de Canes", min_value=1, value=1400, step=50)
            btn_meta = st.form_submit_button("Guardar Meta", type="primary")

            if btn_meta:
                init_db()
                conn = sqlite3.connect('vancan_data.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO metas (eess, meta_canes) VALUES (?, ?)", (eess_meta, meta_val))
                conn.commit()
                conn.close()
                st.success(f"Meta guardada correctamente para {eess_meta}: {meta_val:,} canes")
                st.rerun()

        st.markdown("---")
        st.subheader("📋 Metas Registradas (Editable)")
        st.caption("Puedes editar o eliminar registros directamente en la tabla.")
        
        df_m = cargar_metas()
        if not df_m.empty:
            df_m_edited = st.data_editor(
                df_m,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "eess": st.column_config.SelectboxColumn("Establecimiento", options=LISTA_EESS, required=True),
                    "meta_canes": st.column_config.NumberColumn("Meta Canes", min_value=1, step=10, required=True)
                },
                use_container_width=True,
                num_rows="dynamic",
                key="editor_metas"
            )

            if st.button("💾 Guardar Cambios en Metas", type="primary"):
                init_db()
                conn = sqlite3.connect('vancan_data.db')
                c = conn.cursor()
                c.execute("DELETE FROM metas")
                for _, r in df_m_edited.iterrows():
                    c.execute("INSERT INTO metas (id, eess, meta_canes) VALUES (?, ?, ?)", (r['id'], r['eess'], int(r['meta_canes'])))
                conn.commit()
                conn.close()
                st.success("✅ Metas actualizadas correctamente.")
                st.rerun()
        else:
            st.info("No hay metas manuales registradas aún en la base de datos.")

    # 2. TAB PERSONAL
    with tab_personal:
        st.subheader("➕ Agregar Nuevo Personal al Padrón")

        with st.form("form_personal"):
            col_p1, col_p2 = st.columns(2)
            nom_pers = col_p1.text_input("Nombre y Cargo (Ej: Tec. Maria Perez)", value="")
            dni_pers = col_p2.text_input("DNI (Opcional)", value="")
            btn_pers = st.form_submit_button("Guardar Personal", type="primary")

            if btn_pers:
                if nom_pers.strip():
                    init_db()
                    conn = sqlite3.connect('vancan_data.db')
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO personal_db (nombre, dni) VALUES (?, ?)", (nom_pers.strip(), dni_pers.strip()))
                        conn.commit()
                        st.success(f"✅ {nom_pers.strip()} agregado exitosamente al padrón.")
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Este nombre ya existe en el padrón registrado.")
                    finally:
                        conn.close()
                    st.rerun()
                else:
                    st.error("⚠️ Ingrese un nombre válido.")

        st.markdown("---")
        st.subheader("📋 Padrón de Personal Registrado en DB (Editable)")
        st.caption("Los cambios guardados aquí se reflejarán de inmediato en los desplegables de registro diario.")

        df_p = cargar_personal_db()
        if not df_p.empty:
            df_p_edited = st.data_editor(
                df_p,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre y Cargo", required=True),
                    "dni": st.column_config.TextColumn("DNI")
                },
                use_container_width=True,
                num_rows="dynamic",
                key="editor_personal"
            )

            if st.button("💾 Guardar Cambios en Personal", type="primary"):
                init_db()
                conn = sqlite3.connect('vancan_data.db')
                c = conn.cursor()
                c.execute("DELETE FROM personal_db")
                for _, r in df_p_edited.iterrows():
                    c.execute("INSERT INTO personal_db (id, nombre, dni) VALUES (?, ?, ?)", (r['id'], str(r['nombre']).strip(), str(r['dni']).strip()))
                conn.commit()
                conn.close()
                st.success("✅ Padrón de personal actualizado correctamente.")
                st.rerun()
        else:
            st.info("Aún no has agregado personal manual a la DB. (Se están leyendo los del CSV si existen).")
