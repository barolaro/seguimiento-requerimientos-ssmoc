import io
import uuid
from datetime import date, datetime

import bcrypt
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Seguimiento de Requerimientos · Abastecimiento SSMOC",
    page_icon="📦",
    layout="wide",
)

USUARIOS_COLS = ["usuario", "nombre", "email", "rol", "password_hash", "activo"]
REQ_COLS = [
    "id", "fecha_creacion", "ejecutivo", "titulo", "descripcion", "estado",
    "prioridad", "fecha_compromiso", "ultima_actualizacion", "actualizado_por",
    "avance", "activo"
]
HIST_COLS = ["fecha_hora", "requerimiento_id", "usuario", "accion", "detalle"]
ESTADOS = ["Pendiente", "En ejecución", "En espera", "Observado", "Terminado"]
PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]
ROLES = ["ejecutivo", "jefatura", "administrador"]


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


@st.cache_resource
def conectar_google():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    cliente = gspread.authorize(credentials)
    return cliente.open_by_key(st.secrets["google_sheets"]["spreadsheet_id"])


def obtener_hoja(libro, nombre, columnas):
    try:
        hoja = libro.worksheet(nombre)
    except gspread.WorksheetNotFound:
        hoja = libro.add_worksheet(title=nombre, rows=2000, cols=max(len(columnas), 10))
        hoja.append_row(columnas)
    valores = hoja.get_all_values()
    if not valores:
        hoja.append_row(columnas)
    elif valores[0] != columnas:
        hoja.update("A1", [columnas])
    return hoja


def cargar_df(hoja, columnas):
    registros = hoja.get_all_records(expected_headers=columnas)
    return pd.DataFrame(registros, columns=columnas)


def inicializar():
    libro = conectar_google()
    usuarios = obtener_hoja(libro, "usuarios", USUARIOS_COLS)
    requerimientos = obtener_hoja(libro, "requerimientos", REQ_COLS)
    historial = obtener_hoja(libro, "historial", HIST_COLS)

    if len(usuarios.get_all_records()) == 0:
        admin_user = st.secrets.get("bootstrap", {}).get("admin_user", "admin")
        admin_password = st.secrets.get("bootstrap", {}).get("admin_password", "Cambiar123!")
        usuarios.append_row([
            admin_user,
            "Administrador Abastecimiento",
            "",
            "administrador",
            hash_password(admin_password),
            "SI",
        ])
    return usuarios, requerimientos, historial


def registrar_historial(hoja, req_id, usuario, accion, detalle):
    hoja.append_row([ahora(), req_id, usuario, accion, detalle])


def exportar_excel(df):
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Requerimientos")
    return salida.getvalue()


def dias_sin_actualizar(valor):
    fecha = pd.to_datetime(valor, errors="coerce")
    if pd.isna(fecha):
        return 999
    return max((pd.Timestamp.now().normalize() - fecha.normalize()).days, 0)


def semaforo(dias):
    if dias == 0:
        return "🟢 Actualizado hoy"
    if dias <= 3:
        return f"🟡 Hace {dias} día(s)"
    return f"🔴 Hace {dias} día(s)"


def cerrar_sesion():
    for clave in ["usuario", "rol", "nombre"]:
        st.session_state.pop(clave, None)
    st.rerun()


try:
    ws_usuarios, ws_req, ws_hist = inicializar()
except Exception as exc:
    st.error("No fue posible conectar con Google Sheets.")
    st.code(str(exc))
    st.info("Revise los Secrets de Streamlit y confirme que la planilla esté compartida con la cuenta de servicio.")
    st.stop()


if "usuario" not in st.session_state:
    st.title("📦 Seguimiento de Requerimientos")
    st.subheader("Departamento de Abastecimiento · SSMOC")
    st.caption("Acceso interno para ejecutivos, jefatura y administración.")

    with st.form("login"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        ingresar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)

    if ingresar:
        usuarios_df = cargar_df(ws_usuarios, USUARIOS_COLS)
        encontrado = usuarios_df[
            (usuarios_df["usuario"].astype(str).str.lower() == usuario.strip().lower())
            & (usuarios_df["activo"].astype(str).str.upper() == "SI")
        ]
        if encontrado.empty:
            st.error("Usuario no encontrado o inactivo.")
        else:
            fila = encontrado.iloc[0]
            if check_password(password, str(fila["password_hash"])):
                st.session_state.usuario = str(fila["usuario"])
                st.session_state.nombre = str(fila["nombre"])
                st.session_state.rol = str(fila["rol"]).lower()
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()


usuario_actual = st.session_state.usuario
nombre_actual = st.session_state.nombre
rol_actual = st.session_state.rol

with st.sidebar:
    st.title("📦 Abastecimiento")
    st.write(f"**{nombre_actual}**")
    st.caption(f"Rol: {rol_actual.title()}")

    opciones = ["Resumen", "Requerimientos", "Nuevo requerimiento", "Reunión de seguimiento"]
    if rol_actual == "administrador":
        opciones.append("Administrar usuarios")
    seccion = st.radio("Navegación", opciones)
    st.divider()
    if st.button("Cerrar sesión", use_container_width=True):
        cerrar_sesion()

req_df = cargar_df(ws_req, REQ_COLS)
if not req_df.empty:
    req_df = req_df[req_df["activo"].astype(str).str.upper() != "NO"].copy()
    req_df["dias_sin_actualizar"] = req_df["ultima_actualizacion"].apply(dias_sin_actualizar)
    req_df["semaforo"] = req_df["dias_sin_actualizar"].apply(semaforo)

usuarios_df = cargar_df(ws_usuarios, USUARIOS_COLS)
ejecutivos = usuarios_df[
    (usuarios_df["rol"].astype(str).str.lower() == "ejecutivo")
    & (usuarios_df["activo"].astype(str).str.upper() == "SI")
]["usuario"].astype(str).tolist()

if rol_actual == "ejecutivo" and not req_df.empty:
    visible_df = req_df[req_df["ejecutivo"].astype(str) == usuario_actual].copy()
else:
    visible_df = req_df.copy()


if seccion == "Resumen":
    st.title("Resumen ejecutivo")
    st.caption("Estado general de los requerimientos del Departamento de Abastecimiento.")

    total = len(visible_df)
    pendientes = len(visible_df[visible_df["estado"] == "Pendiente"]) if total else 0
    ejecucion = len(visible_df[visible_df["estado"] == "En ejecución"]) if total else 0
    terminados = len(visible_df[visible_df["estado"] == "Terminado"]) if total else 0
    sin_movimiento = len(visible_df[visible_df["dias_sin_actualizar"] > 7]) if total else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Pendientes", pendientes)
    c3.metric("En ejecución", ejecucion)
    c4.metric("Terminados", terminados)
    c5.metric("Sin movimiento +7 días", sin_movimiento)

    if total:
        st.subheader("Distribución por estado")
        estados_df = visible_df.groupby("estado").size().reset_index(name="cantidad").set_index("estado")
        st.bar_chart(estados_df)

        st.subheader("Requerimientos que requieren atención")
        atencion = visible_df[
            (visible_df["estado"] != "Terminado")
            & ((visible_df["dias_sin_actualizar"] > 7) | (visible_df["prioridad"].isin(["Alta", "Crítica"])))
        ].sort_values(["dias_sin_actualizar", "prioridad"], ascending=[False, True])
        st.dataframe(
            atencion[["id", "ejecutivo", "titulo", "estado", "prioridad", "fecha_compromiso", "semaforo"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Todavía no existen requerimientos registrados.")


elif seccion == "Nuevo requerimiento":
    st.title("Nuevo requerimiento")
    st.caption("Registre un nuevo requerimiento y asigne su responsable.")

    responsables = ejecutivos if rol_actual in ["jefatura", "administrador"] else [usuario_actual]
    if not responsables:
        st.warning("Primero debe crear al menos un usuario con rol ejecutivo.")
    else:
        with st.form("nuevo_req", clear_on_submit=True):
            responsable = st.selectbox("Ejecutivo responsable", responsables)
            titulo = st.text_input("Título del requerimiento")
            descripcion = st.text_area("Descripción")
            prioridad = st.selectbox("Prioridad", PRIORIDADES, index=1)
            compromiso = st.date_input("Fecha de compromiso", value=date.today())
            avance = st.text_area("Gestión inicial o avance")
            guardar = st.form_submit_button("Guardar requerimiento", type="primary")

        if guardar:
            if not titulo.strip() or not descripcion.strip():
                st.error("Debe completar el título y la descripción.")
            else:
                req_id = f"REQ-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
                ws_req.append_row([
                    req_id, ahora(), responsable, titulo.strip(), descripcion.strip(), "Pendiente",
                    prioridad, compromiso.isoformat(), ahora(), usuario_actual, avance.strip(), "SI"
                ])
                registrar_historial(ws_hist, req_id, usuario_actual, "Creación", f"Requerimiento creado y asignado a {responsable}.")
                st.success(f"Requerimiento {req_id} creado correctamente.")
                st.cache_data.clear()


elif seccion == "Requerimientos":
    st.title("Requerimientos")

    if visible_df.empty:
        st.info("No hay requerimientos para mostrar.")
    else:
        f1, f2, f3, f4 = st.columns(4)
        texto = f1.text_input("Buscar", placeholder="ID, título, descripción o avance")
        estados = f2.multiselect("Estado", ESTADOS)
        prioridades = f3.multiselect("Prioridad", PRIORIDADES)
        responsables = f4.multiselect("Ejecutivo", sorted(visible_df["ejecutivo"].astype(str).unique())) if rol_actual != "ejecutivo" else []

        filtrado = visible_df.copy()
        if texto:
            mascara = filtrado[["id", "titulo", "descripcion", "avance"]].astype(str).apply(
                lambda col: col.str.contains(texto, case=False, na=False)
            ).any(axis=1)
            filtrado = filtrado[mascara]
        if estados:
            filtrado = filtrado[filtrado["estado"].isin(estados)]
        if prioridades:
            filtrado = filtrado[filtrado["prioridad"].isin(prioridades)]
        if responsables:
            filtrado = filtrado[filtrado["ejecutivo"].isin(responsables)]

        st.dataframe(
            filtrado[["id", "ejecutivo", "titulo", "estado", "prioridad", "fecha_compromiso", "ultima_actualizacion", "semaforo"]],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Descargar vista en Excel",
            data=exportar_excel(filtrado.drop(columns=["dias_sin_actualizar", "semaforo"], errors="ignore")),
            file_name=f"requerimientos_abastecimiento_{date.today():%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.divider()
        st.subheader("Actualizar requerimiento")
        elegido = st.selectbox("Seleccione un requerimiento", filtrado["id"].astype(str).tolist())
        actual = filtrado[filtrado["id"].astype(str) == elegido].iloc[0]

        with st.form("editar_req"):
            st.write(f"**{actual['titulo']}**")
            nuevo_estado = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(str(actual["estado"])) if str(actual["estado"]) in ESTADOS else 0)
            nueva_prioridad = st.selectbox("Prioridad", PRIORIDADES, index=PRIORIDADES.index(str(actual["prioridad"])) if str(actual["prioridad"]) in PRIORIDADES else 1)
            nueva_fecha = st.date_input("Fecha de compromiso", value=pd.to_datetime(actual["fecha_compromiso"], errors="coerce").date() if not pd.isna(pd.to_datetime(actual["fecha_compromiso"], errors="coerce")) else date.today())
            nuevo_avance = st.text_area("Nueva actualización", placeholder="Describa la gestión realizada desde la última actualización")
            guardar_cambio = st.form_submit_button("Guardar actualización", type="primary")

        if guardar_cambio:
            if not nuevo_avance.strip():
                st.error("Debe registrar una actualización de avance.")
            else:
                filas = ws_req.get_all_values()
                encabezado = filas[0]
                id_col = encabezado.index("id")
                fila_hoja = next((i + 1 for i, fila in enumerate(filas[1:], start=1) if len(fila) > id_col and fila[id_col] == elegido), None)
                if fila_hoja:
                    cambios = {
                        "estado": nuevo_estado,
                        "prioridad": nueva_prioridad,
                        "fecha_compromiso": nueva_fecha.isoformat(),
                        "ultima_actualizacion": ahora(),
                        "actualizado_por": usuario_actual,
                        "avance": nuevo_avance.strip(),
                    }
                    for columna, valor in cambios.items():
                        ws_req.update_cell(fila_hoja, encabezado.index(columna) + 1, valor)
                    detalle = f"Estado: {actual['estado']} → {nuevo_estado}. Prioridad: {actual['prioridad']} → {nueva_prioridad}. Avance: {nuevo_avance.strip()}"
                    registrar_historial(ws_hist, elegido, usuario_actual, "Actualización", detalle)
                    st.success("Requerimiento actualizado correctamente.")
                    st.rerun()


elif seccion == "Reunión de seguimiento":
    st.title("Reunión de seguimiento")
    st.caption("Vista preparada para la revisión periódica de la jefatura.")

    if visible_df.empty:
        st.info("No existen requerimientos registrados.")
    else:
        resumen = visible_df.groupby("ejecutivo").agg(
            total=("id", "count"),
            terminados=("estado", lambda s: (s == "Terminado").sum()),
            en_ejecucion=("estado", lambda s: (s == "En ejecución").sum()),
            pendientes=("estado", lambda s: (s == "Pendiente").sum()),
            sin_actualizar_7_dias=("dias_sin_actualizar", lambda s: (s > 7).sum()),
        ).reset_index()
        st.dataframe(resumen, use_container_width=True, hide_index=True)

        st.subheader("Detalle pendiente de revisión")
        pendientes_df = visible_df[visible_df["estado"] != "Terminado"].sort_values(
            ["ejecutivo", "dias_sin_actualizar"], ascending=[True, False]
        )
        st.dataframe(
            pendientes_df[["ejecutivo", "id", "titulo", "estado", "prioridad", "fecha_compromiso", "avance", "semaforo"]],
            use_container_width=True,
            hide_index=True,
        )


elif seccion == "Administrar usuarios":
    st.title("Administración de usuarios")
    st.dataframe(
        usuarios_df[["usuario", "nombre", "email", "rol", "activo"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Crear usuario")
    with st.form("crear_usuario", clear_on_submit=True):
        nuevo_usuario = st.text_input("Usuario")
        nuevo_nombre = st.text_input("Nombre completo")
        nuevo_email = st.text_input("Correo")
        nuevo_rol = st.selectbox("Rol", ROLES)
        nueva_password = st.text_input("Contraseña inicial", type="password")
        crear = st.form_submit_button("Crear usuario", type="primary")

    if crear:
        existente = usuarios_df[usuarios_df["usuario"].astype(str).str.lower() == nuevo_usuario.strip().lower()]
        if existente.shape[0] > 0:
            st.error("Ese nombre de usuario ya existe.")
        elif not nuevo_usuario.strip() or not nuevo_nombre.strip() or len(nueva_password) < 8:
            st.error("Complete los campos obligatorios. La contraseña debe tener al menos 8 caracteres.")
        else:
            ws_usuarios.append_row([
                nuevo_usuario.strip(), nuevo_nombre.strip(), nuevo_email.strip(), nuevo_rol,
                hash_password(nueva_password), "SI"
            ])
            st.success("Usuario creado correctamente.")
            st.rerun()
