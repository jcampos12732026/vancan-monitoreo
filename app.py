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
# CARGA DE ARCHIVOS CSV MAESTROS (PERSONAL Y ZONAS)
# ==========================================
def cargar_personal_csv():
    """Lee PERSONAL.csv soportando delimitadores ';' y ','"""
    archivos = ['PERSONAL.csv', 'personal.csv', 'Personal.csv', 'PERSONAL.CSV']
    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo, sep=';', encoding='utf-8')
                if 'NOMBRES' not in df.columns:
                    df = pd.read_csv(archivo, sep=',', encoding='utf-8')
                if 'NOMBRES' in df.columns:
                    return df['NOMBRES'].dropna().astype(str).str.strip().tolist()
            except Exception:
                try:
                    df = pd.read_csv(archivo, sep=';', encoding='latin1')
                    if 'NOMBRES' in df.columns:
                        return df['NOMBRES'].dropna().astype(str).str.strip().tolist()
                except Exception as e:
                    print(f"Error al leer {archivo}: {e}")
    return ["Tec. Jorge Campos", "Lic. Jorge Vasquez", "Tec. Marina Galan", "Tec. Jhosi Soto"]

def cargar_zonas_csv():
    """Lee ZONAS.csv trayendo las +80 zonas dinámicamente"""
    archivos = ['ZONAS.csv', 'zonas.csv', 'Zonas.csv', 'ZONAS.CSV']
    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                # Probar lectura con auto-detección de separador
                df = pd.read_csv(archivo, sep=None, engine='python', encoding='utf-8')
                col_target = None
                for col in df.columns:
                    if normalizar_texto(col) in ['ZONA', 'ZONAS', 'LUGAR', 'SECTOR', 'NOMBRE']:
                        col_target = col
                        break
                if not col_target and len(df.columns) > 0:
                    col_target = df.columns[0]
                
                if col_target:
                    zonas_list = df[col_target].dropna().astype(str).str.strip().unique().tolist()
                    return sorted(zonas_list)
            except Exception:
                try:
                    df = pd.read_csv(archivo, sep=None, engine='python', encoding='latin1')
                    if len(df.columns) > 0:
                        return sorted(df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist())
                except Exception as e:
                    print(f"Error leyendo {archivo}: {e}")
    
    # Lista fallback si no encuentra el archivo
    return ["ROBLES", "ROCAS", "ROSALEDA", "ROSARIO", "ROSAS", "SAN BARTOLOME", "SAN JOSE", "SANTA INES"]

LISTA_PERSONAL = cargar_personal_csv()
LISTA_ZONAS = cargar_zonas_csv()
LISTA_EESS = ["C.S. CESAR LOEPZ SILVA", "C.S. NAÑA", "C.S. MORON", "C.S. CHOSICA"]
LISTA_TURNOS = ["Mañana", "Tarde"]
LISTA_BRIGADAS = [f"Brigada {i:02d}" for i in range(1, 21)]

# ==========================================
# BASE DE DATOS SQLITE
# ==========================================
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
            integrantes TEXT,
            responsable TEXT,
            zona TEXT,
            dosis INTEGER,
            observaciones TEXT,
            usuario_registro TEXT,
            fecha_hora_modificacion TEXT,
            equipo_ip TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eess TEXT,
            meta_canes INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def cargar_datos():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM avances ORDER BY id ASC", conn)
    conn.close()
    return df

def cargar_metas():
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM metas", conn)
    conn.close()
    return df

def guardar_avance_db(fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_simulada = "10.14.14.2, 10.16"
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (str(fecha), eess, turno, brigada, integrantes, responsable, zona, int(dosis), observaciones, usuario_registro, fecha_mod, ip_simulada))
    conn.commit()
    conn.close()

def actualizar_registro_db(id_reg, fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_mod = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        UPDATE avances 
        SET fecha=?, eess=?, turno=?, brigada=?, integrantes=?, responsable=?, zona=?, dosis=?, observaciones=?, fecha_hora_modificacion=?
        WHERE id=?
    ''', (str(fecha), eess, turno, brigada, integrantes, responsable, zona, int(dosis), observaciones, fecha_mod, id_reg))
    conn.commit()
    conn.close()

def reordenar_ids_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("CREATE TABLE avances_seq AS SELECT * FROM avances ORDER BY id ASC;")
    c.execute("DELETE FROM avances;")
    c.execute("DELETE FROM sqlite_sequence WHERE name='avances';")
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        SELECT fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip
        FROM avances_seq ORDER BY id ASC;
    ''')
    c.execute("DROP TABLE avances_seq;")
    conn.commit()
    conn.close()

def eliminar_registro_db(id_reg):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances WHERE id=?", (id_reg,))
    conn.commit()
    conn.close()
    reordenar_ids_db()

def vaciar_base_datos_db():
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances")
    c.execute("DELETE FROM sqlite_sequence WHERE name='avances'")
    conn.commit()
    conn.close()

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
# CONTROL DE SESIÓN Y NAVEGACIÓN
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
    st.caption("Completa el formulario para ingresar la producción de las brigadas de campo.")

    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_input = st.date_input("Fecha de Actividad", datetime.now())
            eess_input = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            turno_input = st.selectbox("Turno", LISTA_TURNOS)
        
        with col2:
            brigada_input = st.selectbox("Brigada", LISTA_BRIGADAS)
            responsable_input = st.text_input("Responsable de Brigada", value="MARINA")
            zona_input = st.selectbox("Zona / Lugar de Intervención (ZONAS.CSV)", LISTA_ZONAS)

        with col3:
            dosis_input = st.number_input("Dosis Aplicadas (Canes)", min_value=0, step=1, value=50)
            
            # SELECCIÓN MÚLTIPLE DE HASTA 2 INTEGRANTES
            integrantes_sel = st.multiselect(
                "Integrantes (PERSONAL.CSV - Máx 2)", 
                options=LISTA_PERSONAL,
                default=LISTA_PERSONAL[:2] if len(LISTA_PERSONAL) >= 2 else LISTA_PERSONAL,
                max_selections=2,
                help="Selecciona hasta 2 integrantes leídos desde PERSONAL.CSV"
            )
            observaciones_input = st.text_area("Observaciones", value="")

        btn_guardar = st.form_submit_button("💾 Guardar Registro de Avance", type="primary", use_container_width=True)

        if btn_guardar:
            if not integrantes_sel:
                st.error("⚠️ Debes seleccionar al menos un integrante de la lista.")
            else:
                integrantes_str = ", ".join(integrantes_sel)
                guardar_avance_db(
                    fecha_input, eess_input, turno_input, brigada_input, 
                    integrantes_str, responsable_input, zona_input, 
                    dosis_input, observaciones_input, st.session_state["username"]
                )
                st.success(f"✅ Registro guardado con éxito. Integrantes: {integrantes_str}")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Gestión y Edición de Registros Guardados")
    st.caption("Los listados desplegables se alimentan directamente de tus archivos maestros reales (ZONAS.CSV, PERSONAL.CSV, etc.).")
    
    df_all = cargar_datos()
    if not df_all.empty:
        df_mostrar = df_all if st.session_state["user_role"] != "Brigadista / Digitador" else df_all[df_all['usuario_registro'] == st.session_state["username"]].copy()

        if not df_mostrar.empty:
            if "fecha" in df_mostrar.columns:
                df_mostrar["fecha"] = pd.to_datetime(df_mostrar["fecha"], errors='coerce')

            columnas_ordenadas = [
                "id", "fecha", "eess", "turno", "brigada", 
                "responsable", "zona", "dosis", "integrantes", 
                "observaciones", "usuario_registro", "fecha_hora_modificacion", "equipo_ip"
            ]
            cols_presentes = [c for c in columnas_ordenadas if c in df_mostrar.columns]
            df_mostrar = df_mostrar[cols_presentes]

            # OPCIONES REALES BASADAS EN CSV Y DATOS EXISTENTES
            opts_eess = sorted(list(set(LISTA_EESS + df_mostrar['eess'].dropna().astype(str).tolist())))
            opts_turno = sorted(list(set(LISTA_TURNOS + df_mostrar['turno'].dropna().astype(str).tolist())))
            opts_brigada = sorted(list(set(LISTA_BRIGADAS + df_mostrar['brigada'].dropna().astype(str).tolist())))
            opts_zona = sorted(list(set(LISTA_ZONAS + df_mostrar['zona'].dropna().astype(str).tolist())))

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
                    "integrantes": st.column_config.TextColumn("Integrantes (PERSONAL.CSV)", required=True),
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
                            row['brigada'], str(row['integrantes']), row['responsable'], 
                            row['zona'], int(row['dosis']), str(row['observaciones'])
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
# MÓDULO 2: DASHBOARD, VACUNÓMETRO Y GRÁFICOS
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

    # SECCIÓN VACUNÓMETRO Y VELOCÍMETRO
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

    # GRÁFICOS ANALÍTICOS (POR DÍA Y POR PERSONA CON DIVISIÓN ENTRE INTEGRANTES DE BRIGADA)
    if not df_f.empty:
        g1, g2 = st.columns(2)

        # 1. GRÁFICO POR DÍA (FECHA)
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

        # 2. GRÁFICO POR PERSONA (PRODUCCIÓN DIVIDIDA ENTRE INTEGRANTES DE BRIGADA)
        with g2:
            st.markdown("### 👤 Producción Individual por Persona")
            st.caption("💡 Si la brigada es de 2 personas, las dosis del registro se dividen por igual (50% a cada integrante).")

            registros_personas = []
            for _, row in df_f.iterrows():
                integrantes_lista = [i.strip() for i in str(row['integrantes']).split(',') if i.strip()]
                cant_integrantes = len(integrantes_lista)
                
                if cant_integrantes > 0:
                    dosis_por_persona = float(row['dosis']) / cant_integrantes
                    for p in integrantes_lista:
                        registros_personas.append({'persona': p, 'dosis_individual': dosis_por_persona})
                else:
                    registros_personas.append({'persona': 'No especificado', 'dosis_individual': float(row['dosis'])})

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
        st.info("No hay datos para mostrar los gráficos analíticos con los filtros seleccionados.")

# ==========================================
# MÓDULO 3: CONFIGURACIÓN Y METAS
# ==========================================
elif opcion == "⚙️ Configuración / Metas":
    st.header("⚙️ Configuración del Sistema y Metas")
    st.caption("Gestiona las metas de vacunación por establecimiento de salud.")

    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()

    with st.form("form_metas"):
        eess_meta = st.selectbox("Selecciona Establecimiento", LISTA_EESS)
        meta_val = st.number_input("Meta de Canes", min_value=1, value=1400, step=50)
        btn_meta = st.form_submit_button("Guardar Meta")

        if btn_meta:
            c.execute("DELETE FROM metas WHERE eess=?", (eess_meta,))
            c.execute("INSERT INTO metas (eess, meta_canes) VALUES (?, ?)", (eess_meta, meta_val))
            conn.commit()
            st.success(f"Meta actualizada para {eess_meta}: {meta_val:,} canes")
            st.rerun()

    st.subheader("📋 Metas Actualmente Registradas")
    df_m = cargar_metas()
    if not df_m.empty:
        st.dataframe(df_m, use_container_width=True)
    else:
        st.info("Usando metas automáticas desde archivos CSV.")
    conn.close()
