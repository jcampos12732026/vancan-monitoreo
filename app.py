import os
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Sistema de Gestión y Registro Canino",
    page_icon="🐕",
    layout="wide",
)

DB_NAME = "database.db"
FILE_PERSONAL = "PERSONAL.csv"
FILE_METAS = "METAS.csv"
DEFAULT_EESS = "C.S. CESAR LOPEZ SILVA"
DEFAULT_META = 1500


# =========================================================
# 1. BASE DE DATOS Y ESTRUCTURA
# =========================================================
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla Personal
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            dni TEXT DEFAULT ''
        )
    """
    )

    # Tabla Centros de Salud y Metas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS eess_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_eess TEXT NOT NULL UNIQUE,
            meta_canes INTEGER DEFAULT 0
        )
    """
    )

    # Tabla Registro Diario de Vacunación Canina
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS registro_vacunacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            eess TEXT,
            personal TEXT,
            macho_menor1 INTEGER,
            macho_mayor1 INTEGER,
            hembra_menor1 INTEGER,
            hembra_mayor1 INTEGER,
            total_canes INTEGER
        )
    """
    )

    # Asegurar que exista el C.S. Cesar Lopez Silva
    cursor.execute(
        "INSERT OR IGNORE INTO eess_metas (nombre_eess, meta_canes) VALUES (?, ?)",
        (DEFAULT_EESS, DEFAULT_META),
    )

    conn.commit()
    conn.close()


# =========================================================
# 2. SINCRONIZACIÓN AUTOMÁTICA DESDE ARCHIVOS CSV
# =========================================================
def sync_personal_from_csv():
    """Importa registros desde PERSONAL.csv si existen y no están en la DB."""
    if os.path.exists(FILE_PERSONAL):
        try:
            try:
                df_csv = pd.read_csv(
                    FILE_PERSONAL, dtype=str, encoding="utf-8"
                )
            except Exception:
                df_csv = pd.read_csv(
                    FILE_PERSONAL, dtype=str, encoding="latin-1", sep=";"
                )

            cols = [c.upper().strip() for c in df_csv.columns]
            df_csv.columns = cols

            conn = get_connection()
            cursor = conn.cursor()

            for _, row in df_csv.iterrows():
                nombre = None
                dni = ""

                for col in df_csv.columns:
                    if (
                        "NOMBRE" in col
                        or "PERSONAL" in col
                        or "CARGO" in col
                        or "TECNICO" in col
                    ):
                        nombre = str(row[col]).strip()
                    elif "DNI" in col:
                        dni = str(row[col]).strip() if pd.notna(row[col]) else ""

                if not nombre and len(row) > 0:
                    nombre = str(row.iloc[0]).strip()

                if nombre and nombre.lower() != "nan" and len(nombre) > 0:
                    cursor.execute(
                        "INSERT OR IGNORE INTO personal (nombre, dni) VALUES (?, ?)",
                        (nombre, dni),
                    )

            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error al sincronizar {FILE_PERSONAL}: {e}")


def sync_metas_from_csv():
    """Importa registros desde METAS.csv si existen y no están en la DB."""
    if os.path.exists(FILE_METAS):
        try:
            try:
                df_csv = pd.read_csv(FILE_METAS, encoding="utf-8")
            except Exception:
                df_csv = pd.read_csv(FILE_METAS, encoding="latin-1", sep=";")

            cols = [c.upper().strip() for c in df_csv.columns]
            df_csv.columns = cols

            conn = get_connection()
            cursor = conn.cursor()

            for _, row in df_csv.iterrows():
                eess = None
                meta = 0

                for col in df_csv.columns:
                    if (
                        "EESS" in col
                        or "CENTRO" in col
                        or "ESTABLECIMIENTO" in col
                        or "NOMBRE" in col
                    ):
                        eess = str(row[col]).strip()
                    elif "META" in col or "CANES" in col:
                        try:
                            meta = (
                                int(row[col]) if pd.notna(row[col]) else 0
                            )
                        except Exception:
                            meta = 0

                if not eess and len(row) > 0:
                    eess = str(row.iloc[0]).strip()

                if eess and eess.lower() != "nan" and len(eess) > 0:
                    cursor.execute(
                        "INSERT OR IGNORE INTO eess_metas (nombre_eess, meta_canes) VALUES (?, ?)",
                        (eess, meta),
                    )

            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error al sincronizar {FILE_METAS}: {e}")


# Inicializar base de datos y realizar sincronizaciones de arranque
init_db()
sync_personal_from_csv()
sync_metas_from_csv()


# =========================================================
# 3. INTERFAZ Y NAVEGACIÓN
# =========================================================
tab_dash, tab_reg, tab_pers, tab_eess = st.tabs(
    [
        "📊 Dashboard",
        "📝 Registro Diario",
        "📋 Padrón de Personal",
        "🏥 Centros de Salud y Metas",
    ]
)

# ---------------------------------------------------------
# TAB 1: DASHBOARD
# ---------------------------------------------------------
with tab_dash:
    st.title("📊 Dashboard Situacional de Vacunación Canina")

    conn = get_connection()
    df_eess_db = pd.read_sql_query(
        "SELECT nombre_eess, meta_canes FROM eess_metas ORDER BY nombre_eess",
        conn,
    )
    df_reg = pd.read_sql_query("SELECT * FROM registro_vacunacion", conn)
    conn.close()

    lista_eess = ["TODOS LOS CENTROS DE SALUD"] + list(
        df_eess_db["nombre_eess"].unique()
    )

    # Indice por defecto: C.S. CESAR LOPEZ SILVA si existe en la lista
    index_def = 0
    for idx, item in enumerate(lista_eess):
        if DEFAULT_EESS.lower() in item.lower():
            index_def = idx
            break

    col_filt1, col_filt2 = st.columns([2, 2])
    with col_filt1:
        eess_seleccionado = st.selectbox(
            "📍 Seleccione Centro de Salud / EESS:",
            lista_eess,
            index=index_def,
        )

    # Filtrar datos
    if eess_seleccionado == "TODOS LOS CENTROS DE SALUD":
        df_filtered = df_reg.copy()
        meta_total = df_eess_db["meta_canes"].sum()
    else:
        df_filtered = df_reg[df_reg["eess"] == eess_seleccionado]
        meta_row = df_eess_db[df_eess_db["nombre_eess"] == eess_seleccionado]
        meta_total = (
            int(meta_row["meta_canes"].values[0]) if not meta_row.empty else 0
        )

    total_avance = (
        int(df_filtered["total_canes"].sum()) if not df_filtered.empty else 0
    )
    porcentaje = (
        (total_avance / meta_total * 100)
        if meta_total > 0
        else (100.0 if total_avance > 0 else 0.0)
    )

    # Métricas clave
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 Meta Programada", f"{meta_total:,} canes")
    m2.metric("🐕 Total Avance", f"{total_avance:,} canes")
    m3.metric("📈 Cobertura (%)", f"{porcentaje:.1f}%")
    m4.metric("📉 Brecha Restante", f"{max(0, meta_total - total_avance):,} canes")

    st.progress(min(1.0, porcentaje / 100.0))

    st.markdown("---")

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📊 Avance de Vacunación por Personal")
        if not df_filtered.empty:
            df_grp_pers = (
                df_filtered.groupby("personal")["total_canes"]
                .sum()
                .reset_index()
            )
            fig_pers = px.bar(
                df_grp_pers,
                x="personal",
                y="total_canes",
                text="total_canes",
                color="total_canes",
                labels={
                    "personal": "Personal Responsable",
                    "total_canes": "Canes Vacunados",
                },
                color_continuous_scale="Viridis",
            )
            fig_pers.update_traces(textposition="outside")
            st.plotly_chart(fig_pers, use_container_width=True)
        else:
            st.info("No hay registros de vacunación para el filtro seleccionado.")

    with g2:
        st.subheader("🐾 Distribución por Sexo y Edad")
        if not df_filtered.empty:
            m_m1 = df_filtered["macho_menor1"].sum()
            m_may1 = df_filtered["macho_mayor1"].sum()
            h_m1 = df_filtered["hembra_menor1"].sum()
            h_may1 = df_filtered["hembra_mayor1"].sum()

            df_demog = pd.DataFrame(
                {
                    "Categoría": [
                        "Machos < 1 año",
                        "Machos ≥ 1 año",
                        "Hembras < 1 año",
                        "Hembras ≥ 1 año",
                    ],
                    "Cantidad": [m_m1, m_may1, h_m1, h_may1],
                }
            )
            fig_pie = px.pie(
                df_demog,
                names="Categoría",
                values="Cantidad",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay registros de vacunación para el filtro seleccionado.")

# ---------------------------------------------------------
# TAB 2: REGISTRO DIARIO
# ---------------------------------------------------------
with tab_reg:
    st.title("📝 Formulario de Registro Diario de Vacunación")

    conn = get_connection()
    list_pers = pd.read_sql_query(
        "SELECT nombre FROM personal ORDER BY nombre", conn
    )["nombre"].tolist()
    list_eess = pd.read_sql_query(
        "SELECT nombre_eess FROM eess_metas ORDER BY nombre_eess", conn
    )["nombre_eess"].tolist()
    conn.close()

    with st.form("form_vacunacion", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha_reg = st.date_input("Fecha de Registro")
        with c2:
            eess_reg = st.selectbox("Centro de Salud / EESS", list_eess)
        with c3:
            pers_reg = st.selectbox("Personal Responsable", list_pers)

        st.subheader("Detalle de Canes Vacunados")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            m_menor1 = st.number_input("Machos < 1 Año", min_value=0, value=0)
        with d2:
            m_mayor1 = st.number_input("Machos ≥ 1 Año", min_value=0, value=0)
        with d3:
            h_menor1 = st.number_input("Hembras < 1 Año", min_value=0, value=0)
        with d4:
            h_mayor1 = st.number_input("Hembras ≥ 1 Año", min_value=0, value=0)

        btn_guardar_reg = st.form_submit_button(
            "💾 Registrar Vacunación", type="primary"
        )

        if btn_guardar_reg:
            total = m_menor1 + m_mayor1 + h_menor1 + h_mayor1
            if total > 0:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO registro_vacunacion 
                    (fecha, eess, personal, macho_menor1, macho_mayor1, hembra_menor1, hembra_mayor1, total_canes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(fecha_reg),
                        eess_reg,
                        pers_reg,
                        m_menor1,
                        m_mayor1,
                        h_menor1,
                        h_mayor1,
                        total,
                    ),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"✅ Registro guardado exitosamente. Total vacunas: {total}"
                )
                st.rerun()
            else:
                st.warning("⚠️ Ingrese al menos 1 can vacunado para guardar.")

# ---------------------------------------------------------
# TAB 3: PADRÓN DE PERSONAL (EDITABLE & VISIBLE COMPLETO)
# ---------------------------------------------------------
with tab_pers:
    st.subheader("📋 Padrón de Personal Registrado en DB (Editable)")
    st.caption(
        "Los cambios guardados aquí se reflejarán de inmediato en los desplegables de registro diario."
    )

    conn = get_connection()
    df_personal = pd.read_sql_query(
        "SELECT id AS ID, nombre AS 'Nombre y Cargo', dni AS 'DNI' FROM personal",
        conn,
    )
    conn.close()

    if not df_personal.empty:
        edited_personal = st.data_editor(
            df_personal,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_personal",
        )

        b1, b2 = st.columns([1, 4])
        with b1:
            if st.button("💾 Guardar Cambios en Personal", type="primary"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM personal")
                for _, row in edited_personal.iterrows():
                    nom = str(row["Nombre y Cargo"]).strip()
                    dni = (
                        str(row["DNI"]).strip() if pd.notna(row["DNI"]) else ""
                    )
                    if nom and nom.lower() != "nan":
                        cursor.execute(
                            "INSERT INTO personal (nombre, dni) VALUES (?, ?)",
                            (nom, dni),
                        )
                conn.commit()
                conn.close()
                st.success("¡Padrón de personal actualizado correctamente!")
                st.rerun()
        with b2:
            if st.button("📥 Sincronizar / Reimportar desde PERSONAL.csv"):
                sync_personal_from_csv()
                st.rerun()
    else:
        st.info("No hay personal registrado en la base de datos.")

# ---------------------------------------------------------
# TAB 4: CENTROS DE SALUD Y METAS (EDITABLE & VISIBLE COMPLETO)
# ---------------------------------------------------------
with tab_eess:
    st.subheader("🏥 Registro / Edición de Centros de Salud y Metas")

    c1, c2 = st.columns([3, 2])
    with c1:
        nuevo_eess = st.text_input(
            "Nombre del Centro de Salud / EESS", placeholder="Ej. C.S. MOYOPAMPA"
        )
    with c2:
        nueva_meta = st.number_input(
            "Meta de Canes", min_value=0, value=1500, step=50
        )

    if st.button("➕ Registrar Centro de Salud", type="primary"):
        if nuevo_eess.strip():
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO eess_metas (nombre_eess, meta_canes) VALUES (?, ?)",
                    (nuevo_eess.strip(), nueva_meta),
                )
                conn.commit()
                st.success(
                    f"Centro de Salud '{nuevo_eess}' registrado con éxito."
                )
            except sqlite3.IntegrityError:
                st.warning("El Centro de Salud ya se encuentra registrado.")
            conn.close()
            st.rerun()
        else:
            st.warning("Por favor ingrese un nombre válido.")

    st.markdown("---")
    st.subheader(
        "📋 Lista de Centros de Salud y Metas Registradas (Editable y Eliminable)"
    )
    st.caption(
        "Puedes modificar los nombres o metas directamente en la tabla y hacer clic en Guardar."
    )

    conn = get_connection()
    df_metas = pd.read_sql_query(
        "SELECT id AS ID, nombre_eess AS 'Nombre del Centro de Salud / EESS', meta_canes AS 'Meta de Canes' FROM eess_metas",
        conn,
    )
    conn.close()

    if not df_metas.empty:
        edited_metas = st.data_editor(
            df_metas,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_metas",
        )

        bm1, bm2 = st.columns([1, 4])
        with bm1:
            if st.button("💾 Guardar Cambios en Metas", type="primary"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM eess_metas")
                for _, row in edited_metas.iterrows():
                    eess = str(row["Nombre del Centro de Salud / EESS"]).strip()
                    try:
                        meta = int(row["Meta de Canes"])
                    except Exception:
                        meta = 0
                    if eess and eess.lower() != "nan":
                        cursor.execute(
                            "INSERT INTO eess_metas (nombre_eess, meta_canes) VALUES (?, ?)",
                            (eess, meta),
                        )
                conn.commit()
                conn.close()
                st.success(
                    "¡Centros de Salud y Metas actualizados correctamente!"
                )
                st.rerun()
        with bm2:
            if st.button("📥 Sincronizar / Reimportar desde METAS.csv"):
                sync_metas_from_csv()
                st.rerun()
    else:
        st.info("No hay centros de salud ni metas registradas en la base de datos.")
