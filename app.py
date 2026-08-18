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

# LISTAS BASE DE OPCIONES (Cargadas de CSVs o Fallbacks)
LISTA_EESS = ["C.S. CESAR LOEPZ SILVA", "C.S. NAÑA", "C.S. MORON", "C.S. CHOSICA"]
LISTA_ZONAS = [
    "ROBLES", "ROCAS", "ROSALEDA", "ROSARIO", "ROSAS", 
    "SAN BARTOLOME", "SAN JOSE", "SANTA INES", "SANTA INES BAJO", 
    "SARA", "SAUCES", "SOL", "TACONES", "TERRA"
]
LISTA_TURNOS = ["Mañana", "Tarde"]
LISTA_BRIGADAS = [f"Brigada {i:02d}" for i in range(1, 21)]

# ==========================================
# FUNCIONES AUXILIARES DE NORMALIZACIÓN Y BASE DE DATOS
# ==========================================
def normalizar_texto(texto):
    """Limpia tildes, caracteres especiales y convierte a mayúsculas para comparar fácilmente"""
    if not texto:
        return ""
    texto = str(texto).upper().strip()
    replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"))
    for a, b in replacements:
        texto = texto.replace(a, b)
    texto = re.sub(r'[^A-Z0-9\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def init_db():
    """Inicializa la base de datos SQLite si no existe"""
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
    """Carga los datos guardados en la base de datos"""
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM avances ORDER BY id ASC", conn)
    conn.close()
    return df

def cargar_metas():
    """Carga las metas registradas manualmente en la DB"""
    conn = sqlite3.connect('vancan_data.db')
    df = pd.read_sql_query("SELECT * FROM metas", conn)
    conn.close()
    return df

def guardar_avance_db(fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro):
    """Inserta un nuevo registro de avance"""
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
    """Actualiza un registro editado en la tabla"""
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
    """Reordena correlativamente los IDs en la base de datos para no dejar huecos numéricos"""
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
    """Elimina un registro específico por ID y reordena numéricamente los restantes"""
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances WHERE id=?", (id_reg,))
    conn.commit()
    conn.close()
    reordenar_ids_db()

def vaciar_base_datos_db():
    """Elimina TODOS los registros y reinicia el autoincremento de IDs a 1"""
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM avances")
    c.execute("DELETE FROM sqlite_sequence WHERE name='avances'")
    conn.commit()
    conn.close()

def obtener_metas_csv():
    """Busca las metas desde archivos CSV locales con valores por defecto"""
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
                try:
                    df = pd.read_csv(archivo, sep=None, engine='python', encoding='utf-8')
                except Exception:
                    df = pd.read_csv(archivo, sep=None, engine='python', encoding='latin1')

                col_eess = None
                col_meta = None
                for c in df.columns:
                    c_upper = normalizar_texto(c)
                    if c_upper in ['EESS', 'ESTABLECIMIENTO', 'ESTABLECIMIENTOS', 'CENTRO DE SALUD']:
                        col_eess = c
                    elif c_upper in ['META CANES', 'META', 'DOSIS', 'CANES']:
                        col_meta = c

                if col_eess and col_meta:
                    for _, row in df.iterrows():
                        eess_nom = normalizar_texto(row[col_eess])
                        try:
                            meta_val = int(row[col_meta])
                            metas_dict[eess_nom] = meta_val
                        except ValueError:
                            pass
            except Exception as e:
                print(f"Error al leer {archivo}: {e}")
    return metas_dict

def obtener_meta_establecimiento(eess_nombre, mapa_metas):
    """Busca la meta de un EESS tolerando typos de escritura como 'LOEPZ' por 'LOPEZ'"""
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
# CONTROL DE SESIÓN Y AUTENTICACIÓN
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
    st.session_state["user_role"] = "Brigadista / Digitador"
    st.session_state["username"] = "brigada"

# BARRA LATERAL (Navegación y Perfil)
st.sidebar.title("📌 Menú VANCAN MINSA")
st.sidebar.info(f"**Usuario:** {st.session_state['username']}\n\n**Rol:** {st.session_state['user_role']}")

opciones_menu = [
    "📝 Registrar Avance Diario",
    "📊 Dashboard y Vacunómetro",
    "⚙️ Configuración / Metas"
]

opcion = st.sidebar.radio("Ir a:", opciones_menu)

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
            zona_input = st.selectbox("Zona / Lugar de Intervención", LISTA_ZONAS)

        with col3:
            dosis_input = st.number_input("Dosis Aplicadas (Canes)", min_value=0, step=1, value=50)
            integrantes_input = st.text_input("Integrantes (Separados por coma)", value="Tec. Angela, Lic. Ethel")
            observaciones_input = st.text_area("Observaciones", value="")

        btn_guardar = st.form_submit_button("💾 Guardar Registro de Avance", type="primary", use_container_width=True)

        if btn_guardar:
            guardar_avance_db(
                fecha_input, eess_input, turno_input, brigada_input, 
                integrantes_input, responsable_input, zona_input, 
                dosis_input, observaciones_input, st.session_state["username"]
            )
            st.success("✅ Registro guardado con éxito.")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Gestión y Edición de Registros Guardados")
    st.caption("Puedes editar directamente los valores en la tabla y presionar 'Guardar Cambios' o seleccionar las opciones para eliminar/vaciar registros.")
    
    df_all = cargar_datos()
    if not df_all.empty:
        if st.session_state["user_role"] == "Brigadista / Digitador":
            df_mostrar = df_all[df_all['usuario_registro'] == st.session_state["username"]].copy()
        else:
            df_mostrar = df_all.copy()

        if not df_mostrar.empty:
            # Convertir columna fecha a datetime para evitar incompatibilidad de tipos en DateColumn
            if "fecha" in df_mostrar.columns:
                df_mostrar["fecha"] = pd.to_datetime(df_mostrar["fecha"], errors='coerce')

            # 1. ORDEN DE COLUMNAS (Integrantes va después de Dosis)
            columnas_ordenadas = [
                "id", "fecha", "eess", "turno", "brigada", 
                "responsable", "zona", "dosis", "integrantes", 
                "observaciones", "usuario_registro", "fecha_hora_modificacion", "equipo_ip"
            ]
            
            cols_presentes = [c for c in columnas_ordenadas if c in df_mostrar.columns]
            df_mostrar = df_mostrar[cols_presentes]

            # OPCIONES DINÁMICAS (Conserva las listas predeterminadas + cualquier valor que ya exista en la DB)
            opts_eess = sorted(list(set(LISTA_EESS + df_mostrar['eess'].dropna().astype(str).tolist())))
            opts_turno = sorted(list(set(LISTA_TURNOS + df_mostrar['turno'].dropna().astype(str).tolist())))
            opts_brigada = sorted(list(set(LISTA_BRIGADAS + df_mostrar['brigada'].dropna().astype(str).tolist())))
            opts_zona = sorted(list(set(LISTA_ZONAS + df_mostrar['zona'].dropna().astype(str).tolist())))

            # 3. EDITOR CON OPCIONES DINÁMICAS (Soluciona el error StreamlitAPIException)
            df_edited = st.data_editor(
                df_mostrar,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "fecha": st.column_config.DateColumn("Fecha", required=True),
                    "eess": st.column_config.SelectboxColumn("EESS", options=opts_eess, required=True),
                    "turno": st.column_config.SelectboxColumn("Turno", options=opts_turno, required=True),
                    "brigada": st.column_config.SelectboxColumn("Brigada", options=opts_brigada, required=True),
                    "zona": st.column_config.SelectboxColumn("Zona / Lugar", options=opts_zona, required=True),
                    "dosis": st.column_config.NumberColumn("Dosis", min_value=0, step=1, required=True),
                    "integrantes": st.column_config.TextColumn(
                        "Integrantes (PERSONAL.csv)", 
                        help="Nombres separados por coma tomados de PERSONAL.csv",
                        required=True
                    ),
                    "observaciones": st.column_config.TextColumn("Observaciones")
                },
                disabled=["usuario_registro", "fecha_hora_modificacion", "equipo_ip"],
                use_container_width=True,
                num_rows="dynamic",
                key="editor_registros"
            )

            col_a, col_b = st.columns([1, 1])
            
            # GUARDAR CAMBIOS EDITADOS EN LA TABLA
            with col_a:
                if st.button("💾 Guardar Cambios Editados", type="primary", use_container_width=True):
                    for _, row in df_edited.iterrows():
                        actualizar_registro_db(
                            row['id'], row['fecha'], row['eess'], row['turno'], 
                            row['brigada'], str(row['integrantes']), row['responsable'], 
                            row['zona'], int(row['dosis']), str(row['observaciones'])
                        )
                    st.success("✅ Cambios actualizados correctamente en la base de datos.")
                    st.rerun()

            # 2. SECCIÓN DE ELIMINACIÓN Y VACIADO TOTAL (RESET A 0 CON REORDENAMIENTO DE IDs)
            with col_b:
                with st.expander("🗑️ Opciones de Eliminación / Limpieza de Registros"):
                    modo_eliminar = st.radio(
                        "Selecciona una acción:",
                        ["Eliminar un registro individual por ID", "🔥 Vaciar TODOS los registros (Comenzar de 0)"]
                    )
                    
                    if modo_eliminar == "Eliminar un registro individual por ID":
                        ids_disponibles = df_mostrar['id'].tolist()
                        id_eliminar = st.number_input("Ingresa el ID del registro a eliminar:", min_value=1, step=1, value=ids_disponibles[0] if ids_disponibles else 1)
                        
                        if st.button("❌ Confirmar y Eliminar Registro", type="secondary"):
                            if id_eliminar in ids_disponibles:
                                eliminar_registro_db(id_eliminar)
                                st.success(f"Registro ID {id_eliminar} eliminado. Los IDs restantes han sido reordenados automáticamente.")
                                st.rerun()
                            else:
                                st.error(f"El ID {id_eliminar} no existe o no tienes permiso para eliminarlo.")

                    elif modo_eliminar == "🔥 Vaciar TODOS los registros (Comenzar de 0)":
                        st.warning("⚠️ ¡Atención! Esta acción eliminará permanentemente TODOS los registros de la base de datos y reiniciará el contador de IDs a 1.")
                        confirmar_reset = st.checkbox("Entiendo el riesgo y deseo vaciar la base de datos por completo.")
                        
                        if st.button("🚨 VACIAR BASE DE DATOS COMPLETA", type="primary", disabled=not confirmar_reset):
                            try:
                                vaciar_base_datos_db()
                                st.success("🎉 Base de datos vaciada con éxito. Listo para comenzar de 0.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al intentar vaciar la base de datos: {e}")
        else:
            st.info("No hay registros guardados para mostrar.")
    else:
        st.info("La base de datos se encuentra vacía (0 registros).")

# ==========================================
# MÓDULO 2: DASHBOARD Y VACUNÓMETRO (DIRECTOR)
# ==========================================
elif opcion == "📊 Dashboard y Vacunómetro":
    col_head_dash, col_btn_ref = st.columns([4, 1])
    
    with col_head_dash:
        st.header("📊 Dashboard Analítico y Vacunómetro MINSA")
    
    with col_btn_ref:
        st.write("") 
        if st.button("🔄 Actualizar Datos", type="primary", use_container_width=True, help="Haz clic para recargar los últimos avances y metas sin salir del sistema"):
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
    
    if not df.empty:
        zonas_disponibles = sorted(list(set(df['zona'].unique().tolist() + LISTA_ZONAS)))
        turnos_disponibles = df['turno'].unique().tolist()
    else:
        zonas_disponibles = LISTA_ZONAS
        turnos_disponibles = LISTA_TURNOS

    zona_sel = f2.multiselect("Zona de Intervención", zonas_disponibles, default=zonas_disponibles)
    turno_sel = f3.multiselect("Turno", turnos_disponibles, default=turnos_disponibles)

    # Filtrado de Avances
    if not df.empty:
        df_f = df[(df['eess'].isin(eess_sel)) & (df['zona'].isin(zona_sel)) & (df['turno'].isin(turno_sel))]
        total_vacunados = pd.to_numeric(df_f['dosis'], errors='coerce').fillna(0).sum()
    else:
        df_f = pd.DataFrame()
        total_vacunados = 0

    # CÁLCULO DE META CON BÚSQUEDA TOLERANTE A TYPOS
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
        # ENCABEZADO MEJORADO Y ESPACIADO
        st.markdown("<h4 style='text-align: center; color: #003366; margin-bottom: 0px;'>🎯 Avance vs Meta Programada</h4>", unsafe_allow_html=True)
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = total_vacunados,
            domain = {'x': [0, 1], 'y': [0, 1]},
            delta = {'reference': meta_filtrada, 'increasing': {'color': "green"}},
            gauge = {
                'axis': {'range': [None, max(meta_filtrada, total_vacunados if total_vacunados > 0 else 100)]},
                'bar': {'color': "#003366"},
                'steps': [
                    {'range': [0, meta_filtrada * 0.5], 'color': "#FADBD8"},
                    {'range': [meta_filtrada * 0.5, meta_filtrada * 0.85], 'color': "#FCF3CF"},
                    {'range': [meta_filtrada * 0.85, meta_filtrada], 'color': "#D4EFDF"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': meta_filtrada
                }
            }
        ))
        
        fig_gauge.update_layout(
            height=320, 
            margin=dict(l=30, r=30, t=20, b=20)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

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
