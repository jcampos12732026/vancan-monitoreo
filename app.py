import os
import sqlite3
import pandas as pd
import streamlit as st

DB_NAME = "database.db"
FILE_PERSONAL = "PERSONAL.csv"
FILE_METAS = "METAS.csv"


# ---------------------------------------------------------
# 1. INICIALIZACIÓN Y CONFIGURACIÓN DE BASE DE DATOS SQLITE
# ---------------------------------------------------------
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

    # Tabla Centros de Salud / Metas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS eess_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_eess TEXT NOT NULL UNIQUE,
            meta_canes INTEGER DEFAULT 0
        )
    """
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# 2. LÓGICA DE SINCRONIZACIÓN Y CARGA DE DATOS DESDE CSV
# ---------------------------------------------------------
def sync_personal_from_csv():
    """Lee PERSONAL.csv y registra automáticamente en la DB los que no existan."""
    if os.path.exists(FILE_PERSONAL):
        try:
            # Intentar leer CSV con soporte para distintas codificaciones y separadores
            try:
                df_csv = pd.read_csv(
                    FILE_PERSONAL, dtype=str, encoding="utf-8"
                )
            except Exception:
                df_csv = pd.read_csv(
                    FILE_PERSONAL, dtype=str, encoding="latin-1", sep=";"
                )

            # Normalizar columnas
            cols = [c.upper().strip() for c in df_csv.columns]
            df_csv.columns = cols

            conn = get_connection()
            cursor = conn.cursor()

            for _, row in df_csv.iterrows():
                # Detectar nombre y DNI
                nombre = None
                dni = ""

                for col in df_csv.columns:
                    if "NOMBRE" in col or "PERSONAL" in col or "CARGO" in col:
                        nombre = str(row[col]).strip()
                    elif "DNI" in col:
                        dni = str(row[col]).strip() if pd.notna(row[col]) else ""

                if not nombre and len(row) > 0:
                    nombre = str(row.iloc[0]).strip()

                if nombre and nombre.lower() != "nan" and len(nombre) > 0:
                    # Insertar si no existe (respetando registros editados previamente)
                    cursor.execute(
                        "INSERT OR IGNORE INTO personal (nombre, dni) VALUES (?, ?)",
                        (nombre, dni),
                    )

            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error al sincronizar {FILE_PERSONAL}: {e}")


def sync_metas_from_csv():
    """Lee METAS.csv y registra automáticamente en la DB los que no existan."""
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


# ---------------------------------------------------------
# 3. INTERFAZ Y VISTAS DE USUARIO
# ---------------------------------------------------------
init_db()
sync_personal_from_csv()
sync_metas_from_csv()

st.set_page_config(layout="wide")
tab1, tab2 = st.tabs(
    ["📋 Padrón de Personal", "🏥 Centros de Salud y Metas"]
)

# --- TAB 1: PADRÓN DE PERSONAL ---
with tab1:
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
        # Data Editor para edición masiva
        edited_personal = st.data_editor(
            df_personal,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_personal",
        )

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("💾 Guardar Cambios en Personal", type="primary"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM personal")
                for _, row in edited_personal.iterrows():
                    nom = str(row["Nombre y Cargo"]).strip()
                    dni = str(row["DNI"]).strip() if pd.notna(row["DNI"]) else ""
                    if nom and nom.lower() != "nan":
                        cursor.execute(
                            "INSERT INTO personal (nombre, dni) VALUES (?, ?)",
                            (nom, dni),
                        )
                conn.commit()
                conn.close()
                st.success("¡Padrón de personal actualizado correctamente!")
                st.rerun()
        with col_btn2:
            if st.button("📥 Volver a Importar desde PERSONAL.csv"):
                sync_personal_from_csv()
                st.rerun()
    else:
        st.info("No hay personal registrado en la base de datos.")

# --- TAB 2: CENTROS DE SALUD Y METAS ---
with tab2:
    st.subheader("🏥 Registro de Nuevo Centro de Salud")
    c1, c2 = st.columns([3, 2])
    with c1:
        nuevo_eess = st.text_input(
            "Nombre del Centro de Salud / EESS", placeholder="Ej. C.S. MOYOPAMPA"
        )
    with c2:
        nueva_meta = st.number_input("Meta de Canes", min_value=0, value=1500, step=50)

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
                st.success(f"Centro de salud '{nuevo_eess}' registrado con éxito.")
            except sqlite3.IntegrityError:
                st.warning("El centro de salud ya se encuentra registrado.")
            conn.close()
            st.rerun()
        else:
            st.warning("Por favor ingrese un nombre válido.")

    st.markdown("---")
    st.subheader(
        "📋 Lista de Centros de Salud y Metas Registradas (Editable y Eliminable)"
    )
    st.caption(
        "Puedes modificar los nombres o metas en la tabla, o seleccionar un registro para eliminarlo."
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

        col_m1, col_m2 = st.columns([1, 4])
        with col_m1:
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
                st.success("¡Centros de salud y metas actualizados correctamente!")
                st.rerun()
        with col_m2:
            if st.button("📥 Volver a Importar desde METAS.csv"):
                sync_metas_from_csv()
                st.rerun()
    else:
        st.info("No hay centros de salud ni metas registradas en la base de datos.")
