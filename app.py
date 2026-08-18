import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
        margin-bottom: 20px;
    }
    .footer-text {
        text-align: center;
        color: #555;
        font-weight: bold;
        padding: 15px;
        margin-top: 30px;
        border-top: 2px solid #003366;
        font-size: 0.9em;
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

# Encabezado con soporte para Logo Institucional
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    logo_path = None
    for ext in ['logo.png', 'logo.jpg', 'logo.jpeg', 'LOGO.PNG', 'LOGO.JPG']:
        if os.path.exists(ext):
            logo_path = ext
            break
    
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("🏛️ **MINSA**")

with col_titulo:
    st.markdown("""
        <div class="main-header">
            <h2>MINISTERIO DE SALUD DEL PERÚ - VANCAN</h2>
            <h4>Sistema de Monitoreo y Control de Vacunación Canina</h4>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LECTURA DE ARCHIVOS CSV (PERSONAL, ZONAS Y METAS)
# ==========================================

# Carga de Personal desde PERSONAL.csv (NOMBRE, DNI)
def obtener_personal():
    archivos_posibles = ['PERSONAL.csv', 'personal.csv', 'Personal.csv']
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            try:
                try:
                    df_p = pd.read_csv(archivo, encoding='utf-8')
                except UnicodeDecodeError:
                    df_p = pd.read_csv(archivo, encoding='latin1')

                col_nombre = None
                for c in df_p.columns:
                    if str(c).strip().upper() in ['NOMBRE', 'NOMBRES', 'PERSONAL']:
                        col_nombre = c
                        break
                
                if col_nombre:
                    nombres = df_p[col_nombre].dropna().unique().tolist()
                    lista_limpia = sorted([str(n).strip() for n in nombres if str(n).strip() != ''])
                    if lista_limpia:
                        return lista_limpia
            except Exception as e:
                print(f"Error al leer {archivo}: {e}")
                
    return ["Lic. Ethel", "Lic. Sara", "Lic. Amanda", "Tec. Angela", "Tec. Violeta", 
            "Lic. Carlos Mendoza", "Lic. María Torres", "Tec. Juan Pérez", "Tec. Rosa Gómez", "Lic. Ana Ramos"]

# Carga de Zonas desde ZONAS.csv
def obtener_zonas():
    archivos_posibles = ['ZONAS.csv', 'zonas.csv', 'Zonas.csv']
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            try:
                try:
                    df_z = pd.read_csv(archivo, encoding='utf-8')
                except UnicodeDecodeError:
                    df_z = pd.read_csv(archivo, encoding='latin1')

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
                
    return ["Sector Central", "Ñaña", "Huascata", "Los Cedros", "Santa Inés", "Ocharán", "Carapongo"]

# Carga de Metas desde METAS.csv
METAS_PREDETERMINADAS_DEFAULT = {
    "C.S. César López Silva": 1400,
    "C.S. Ñaña": 2200,
    "C.S. Morón": 2800,
    "C.S. Chosica": 4000
}

def obtener_metas_csv():
    metas_dict = METAS_PREDETERMINADAS_DEFAULT.copy()
    archivos_posibles = ['METAS.csv', 'metas.csv', 'Metas.csv']
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            try:
                try:
                    df_m = pd.read_csv(archivo, encoding='utf-8')
                except UnicodeDecodeError:
                    df_m = pd.read_csv(archivo, encoding='latin1')

                col_eess = None
                col_meta = None
                for c in df_m.columns:
                    c_upper = str(c).strip().upper()
                    if c_upper in ['EESS', 'ESTABLECIMIENTO', 'ESTABLECIMIENTO_SALUD']:
                        col_eess = c
                    elif c_upper in ['META_CANES', 'META', 'DOSIS', 'CANES']:
                        col_meta = c

                if col_eess and col_meta:
                    for _, row in df_m.iterrows():
                        eess_nom = str(row[col_eess]).strip()
                        try:
                            meta_val = int(row[col_meta])
                            metas_dict[eess_nom] = meta_val
                        except ValueError:
                            pass
            except Exception as e:
                print(f"Error al leer {archivo}: {e}")
    return metas_dict

METAS_PREDETERMINADAS = obtener_metas_csv()
LISTA_PERSONAL = obtener_personal()
LISTA_ZONAS = obtener_zonas()
LISTA_EESS = list(METAS_PREDETERMINADAS.keys())
LISTA_TURNOS = ["Mañana", "Tarde"]
LISTA_BRIGADAS = [f"Brigada {i:02d}" for i in range(1, 11)]

# ==========================================
# 3. BASE DE DATOS E INICIALIZACIÓN
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
            eess TEXT PRIMARY KEY,
            meta_canes INTEGER
        )
    ''')
    
    # Pre-alimentación de metas iniciales
    c.execute("SELECT COUNT(*) FROM metas")
    if c.fetchone()[0] == 0:
        for eess_nombre, meta_valor in METAS_PREDETERMINADAS.items():
            c.execute("INSERT INTO metas (eess, meta_canes) VALUES (?, ?)", (eess_nombre, meta_valor))
            
    conn.commit()
    conn.close()

init_db()

def guardar_registro(fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, obs, usuario, ip_equipo):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    str_integrantes = ", ".join(integrantes) if isinstance(integrantes, list) else str(integrantes)
    
    c.execute('''
        INSERT INTO avances (fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, observaciones, usuario_registro, fecha_hora_modificacion, equipo_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, eess, turno, brigada, str_integrantes, responsable, zona, dosis, obs, usuario, fecha_hora_actual, ip_equipo))
    conn.commit()
    conn.close()

def actualizar_registro_db(id_reg, fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, obs):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    fecha_hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        UPDATE avances 
        SET fecha=?, eess=?, turno=?, brigada=?, integrantes=?, responsable=?, zona=?, dosis=?, observaciones=?, fecha_hora_modificacion=?
        WHERE id=?
    ''', (fecha, eess, turno, brigada, integrantes, responsable, zona, dosis, obs, fecha_hora_actual, id_reg))
    conn.commit()
    conn.close()

def eliminar_registro_db(id_reg):
    conn = sqlite3.connect('vancan_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM avances WHERE id=?', (id_reg,))
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
    return df

def cargar_metas():
    conn = sqlite3.connect('vancan_data.db')
    df_m = pd.read_sql_query("SELECT * FROM metas", conn)
    conn.close()
    return df_m

def get_remote_ip():
    try:
        return st.context.headers.get("X-Forwarded-For", "Dispositivo Móvil / Web")
    except Exception:
        return "Web Client"

# ==========================================
# 4. CONTROL DE ACCESO (LOGIN)
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

    st.markdown("""
        <div class="footer-text">
            Elaborado por Servicio de Enfermería del C.S. César López Silva / RIS Chaclacayo Chosica / DIRIS Lima Este / MINSA PERÚ
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. NAVEGACIÓN Y SIDEBAR
# ==========================================
st.sidebar.markdown(f"**Usuario:** `{st.session_state['username']}`")
st.sidebar.markdown(f"**Rol:** `{st.session_state['user_role']}`")
st.sidebar.markdown(f"**Personal Cargado:** `{len(LISTA_PERSONAL)}`")
st.sidebar.markdown(f"**Zonas Cargadas:** `{len(LISTA_ZONAS)}`")
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
    st.header("📝 Carga Diaria de Vacunación Canina")
    
    with st.form("form_carga", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha de Intervención", datetime.now())
            eess = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            turno = st.selectbox("Turno", LISTA_TURNOS)
            brigada = st.selectbox("Seleccionar Brigada", LISTA_BRIGADAS)
            
            # RESTRICCIÓN DE MÁXIMO 2 SELECCIONES POR BRIGADA
            integrantes_sel = st.multiselect(
                "Integrantes de la Brigada (Máximo 2 personas)",
                options=LISTA_PERSONAL,
                max_selections=2,
                help="Selecciona hasta 2 personas para dividir en partes iguales la vacunación"
            )
        
        with col2:
            responsable = st.text_input("Responsable del Registro", placeholder="Ej. Lic. Carlos Mendoza")
            zona = st.selectbox("Zona / Lugar", LISTA_ZONAS)
            dosis = st.number_input("Canes Vacunados (Dosis)", min_value=0, step=1)

        obs = st.text_area("Observaciones o Incidencias")
        
        btn_guardar = st.form_submit_button("🚀 Guardar Registro", type="primary", use_container_width=True)

        if btn_guardar:
            if not responsable or not integrantes_sel:
                st.warning("⚠️ Debes ingresar el responsable e integrantes de la brigada (mínimo 1, máximo 2).")
            else:
                ip_cli = get_remote_ip()
                guardar_registro(str(fecha), eess, turno, brigada, integrantes_sel, responsable, zona, int(dosis), obs, st.session_state["username"], ip_cli)
                st.success("✅ ¡Registro guardado exitosamente!")

    st.markdown("---")
    st.subheader("📋 Gestión y Edición de Registros Guardados")
    st.caption("Puedes editar directamente los valores en la tabla y presionar 'Guardar Cambios' o seleccionar la opción para eliminar un registro.")
    
    df_all = cargar_datos()
    if not df_all.empty:
        if st.session_state["user_role"] == "Brigadista / Digitador":
            df_mostrar = df_all[df_all['usuario_registro'] == st.session_state["username"]].copy()
        else:
            df_mostrar = df_all.copy()

        if not df_mostrar.empty:
            df_edited = st.data_editor(
                df_mostrar,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "brigada": st.column_config.SelectboxColumn("Brigada", options=LISTA_BRIGADAS, required=True),
                    "turno": st.column_config.SelectboxColumn("Turno", options=LISTA_TURNOS, required=True),
                    "eess": st.column_config.SelectboxColumn("EESS", options=LISTA_EESS, required=True),
                    "dosis": st.column_config.NumberColumn("Dosis", min_value=0, step=1, required=True)
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
                    st.success("✅ Cambios actualizados correctamente en la base de datos.")
                    st.rerun()

            with col_b:
                with st.expander("🗑️ Eliminar un registro"):
                    id_eliminar = st.number_input("Ingresa el ID del registro a eliminar:", min_value=1, step=1)
                    if st.button("❌ Confirmar y Eliminar Registro", type="secondary"):
                        eliminar_registro_db(id_eliminar)
                        st.success(f"Registro ID {id_eliminar} eliminado correctamente.")
                        st.rerun()

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

        if not df_metas.empty:
            df_metas_filtradas = df_metas[df_metas['eess'].isin(eess_sel)]
            meta_filtrada = df_metas_filtradas['meta_canes'].sum()
        else:
            meta_filtrada = 0

        if meta_filtrada == 0:
            meta_filtrada = sum([METAS_PREDETERMINADAS.get(e, 1000) for e in eess_sel])

        pct_avance = (total_vacunados / meta_filtrada * 100) if meta_filtrada > 0 else 0.0

        st.markdown("---")

        c_vac1, c_vac2 = st.columns([1, 2])
        
        with c_vac1:
            st.markdown("### 💉 Vacunómetro de Avance")
            st.metric("Total Vacunados", f"{int(total_vacunados):,} canes")
            st.metric("Meta Programada Total", f"{int(meta_filtrada):,} canes")
            st.metric("% Cobertura Alcanzado", f"{pct_avance:.1f} %")

        with c_vac2:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = total_vacunados,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Avance vs Meta Programada", 'font': {'size': 18}},
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

        # CÁLCULO DE PRODUCCIÓN POR PERSONA (DIVISIÓN EN PARTES IGUALES POR BRIGADA)
        prod_por_persona = {}
        
        for _, row in df_f.iterrows():
            dosis_total = float(row['dosis'])
            raw_integrantes = str(row['integrantes'])
            
            # Limpieza y separación de integrantes
            lista_int = [i.strip() for i in raw_integrantes.split(',') if i.strip() != '']
            cant_int = len(lista_int)
            
            if cant_int > 0:
                dosis_individual = dosis_total / cant_int
                for persona in lista_int:
                    prod_por_persona[persona] = prod_por_persona.get(persona, 0.0) + dosis_individual

        # SECCIÓN DE RANKING DE PRODUCCIÓN ACUMULADA POR PERSONAL
        st.subheader("🏆 Ranking de Producción por Personal (Producción Acumulada)")
        st.caption("Las dosis de la brigada son divididas en partes iguales (50/50) entre sus integrantes para calcular la producción individual de cada vacunador.")

        if prod_por_persona:
            df_prod = pd.DataFrame(list(prod_por_persona.items()), columns=['Personal', 'Dosis Acumuladas'])
            df_prod['Dosis Acumuladas'] = df_prod['Dosis Acumuladas'].round(1)
            df_prod = df_prod.sort_values(by='Dosis Acumuladas', ascending=True)

            fig_prod = px.bar(
                df_prod,
                x='Dosis Acumuladas',
                y='Personal',
                orientation='h',
                text='Dosis Acumuladas',
                color='Dosis Acumuladas',
                color_continuous_scale='Blues',
                title="Producción Individual Acumulada por Integrante de Salud"
            )
            fig_prod.update_layout(height=max(350, len(df_prod)*30), showlegend=False)
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
            st.info("No hay datos de integrantes para generar el ranking de producción.")

        st.markdown("---")

        st.subheader("📈 Avance Diario y Progreso Acumulado de Vacunación")
        
        df_f['fecha'] = pd.to_datetime(df_f['fecha'])
        df_diario = df_f.groupby('fecha')['dosis'].sum().reset_index().sort_values('fecha')
        df_diario['acumulado'] = df_diario['dosis'].cumsum()

        fig_comb = make_subplots(specs=[[{"secondary_y": True}]])

        fig_comb.add_trace(
            go.Bar(
                x=df_diario['fecha'].dt.strftime('%Y-%m-%d'),
                y=df_diario['dosis'],
                name="Dosis Diarias (Barras)",
                marker_color='#003366',
                text=df_diario['dosis'],
                textposition='auto'
            ),
            secondary_y=False
        )

        fig_comb.add_trace(
            go.Scatter(
                x=df_diario['fecha'].dt.strftime('%Y-%m-%d'),
                y=df_diario['acumulado'],
                name="Progreso Acumulado (Línea)",
                mode='lines+markers+text',
                line=dict(color='#D91023', width=3),
                text=df_diario['acumulado'],
                textposition='top center'
            ),
            secondary_y=True
        )

        fig_comb.update_layout(
            title_text="Evolución Diaria y Progreso Acumulado de Canes Vacunados",
            xaxis_title="Fecha de Intervención",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig_comb.update_yaxes(title_text="<b>Dosis Vacunadas x Día</b>", secondary_y=False)
        fig_comb.update_yaxes(title_text="<b>Progreso Acumulado Total</b>", secondary_y=True)

        st.plotly_chart(fig_comb, use_container_width=True)

        st.markdown("---")

        g1, g2 = st.columns(2)

        with g1:
            st.subheader("📍 Cobertura por Zona de Intervención")
            df_z = df_f.groupby('zona')['dosis'].sum().reset_index().sort_values(by='dosis', ascending=True)
            fig_z = px.bar(
                df_z, x='dosis', y='zona', orientation='h', text='dosis',
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
    st.header("🎯 Definición y Gestión de Metas por Establecimiento")
    st.info("Configura individualmente o sube masivamente las metas asignadas a los Establecimientos de Salud.")

    col_form, col_tabla = st.columns([1, 1])

    with col_form:
        st.subheader("✍️ Registro Manual Individual")
        with st.form("form_metas"):
            eess_m = st.selectbox("Establecimiento de Salud (EESS)", LISTA_EESS)
            meta_val = st.number_input("Meta de Canes (Número entero)", min_value=1, value=1400, step=50)
            btn_m = st.form_submit_button("💾 Guardar / Actualizar Meta", type="primary")

            if btn_m:
                guardar_meta(eess_m, meta_val)
                st.success(f"✅ Meta de {meta_val:,} canes registrada para {eess_m}")
                st.rerun()

        st.markdown("---")
        st.subheader("📁 Carga Masiva mediante Archivo CSV")
        file_metas = st.file_uploader("Subir archivo METAS.csv", type=["csv"])
        if file_metas is not None:
            try:
                df_up = pd.read_csv(file_metas)
                if 'eess' in df_up.columns and 'meta_canes' in df_up.columns:
                    for _, row in df_up.iterrows():
                        guardar_meta(str(row['eess']).strip(), int(row['meta_canes']))
                    st.success("✅ Metas cargadas masivamente con éxito.")
                    st.rerun()
                else:
                    st.error("El archivo CSV debe contener las columnas: 'eess' y 'meta_canes'")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")

    with col_tabla:
        st.subheader("📋 Metas Configuradas Actuales")
        df_m_curr = cargar_metas()
        if not df_m_curr.empty:
            st.dataframe(df_m_curr, use_container_width=True)
        else:
            st.warning("Aún no se han configurado metas manuales.")

# ==========================================
# MÓDULO 4: AUDITORÍA Y CONTROL DE DATOS
# ==========================================
elif opcion == "🕵️ Auditoría y Gestión de Datos":
    st.header("🕵️ Auditoría y Control de Cambios")
    st.caption("Muestra fecha/hora exacta de modificación, usuario, integrantes de la brigada y dispositivo de origen.")

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

# ==========================================
# PIE DE PÁGINA (CHERRY MINSA)
# ==========================================
st.markdown("""
    <div class="footer-text">
        Elaborado por Servicio de Enfermería del C.S. César López Silva / RIS Chaclacayo Chosica / DIRIS Lima Este / MINSA PERÚ
    </div>
""", unsafe_allow_html=True)
