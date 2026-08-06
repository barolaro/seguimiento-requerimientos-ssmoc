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
    initial_sidebar_state="expanded",
)

CSS = """
<style>
:root{--azul:#164e73;--azul2:#1f6fa5;--fondo:#f4f6f8;--texto:#25364a;--muted:#6f7d8d;--borde:#d7dee6}
.stApp{background:var(--fondo);color:var(--texto)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#164e73,#0b3049)}
[data-testid="stSidebar"] *{color:white}
[data-testid="stSidebar"] .stRadio label{padding:.45rem .6rem;border-radius:8px}
[data-testid="stSidebar"] .stRadio label:hover{background:rgba(255,255,255,.10)}
.block-container{max-width:1500px;padding-top:1.5rem;padding-bottom:3rem}
h1,h2,h3{color:#25364a}
.hero{background:#164e73;color:white;padding:22px 28px;border-radius:16px;margin-bottom:18px;box-shadow:0 8px 22px rgba(0,0,0,.08)}
.hero h1{color:white;margin:0;font-size:30px}.hero p{margin:5px 0 0;opacity:.86}
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:16px 0 22px}
.kpi{background:white;border:1px solid #e0e7ee;border-radius:14px;padding:17px;box-shadow:0 4px 14px rgba(0,0,0,.06)}
.kpi span{font-size:13px;color:#6f7d8d}.kpi strong{display:block;font-size:30px;margin-top:7px;color:#25364a}
.panel{background:white;border:1px solid #e0e7ee;border-radius:14px;padding:18px;box-shadow:0 4px 14px rgba(0,0,0,.06);margin-bottom:16px}
.alerta{background:#fff4e5;border-left:4px solid #e48b00;padding:12px 14px;border-radius:0 10px 10px 0;margin-bottom:12px}
.login-wrap{max-width:470px;margin:7vh auto;background:white;padding:30px;border-radius:22px;box-shadow:0 20px 60px rgba(0,0,0,.16)}
.login-title{text-align:center;color:#164e73;font-size:28px;font-weight:800}.login-sub{text-align:center;color:#6f7d8d;margin-bottom:20px}
div.stButton>button{border-radius:9px;font-weight:700;border:0}
div.stButton>button[kind="primary"]{background:#1f6fa5;color:white}
[data-testid="stMetric"]{background:white;border:1px solid #e0e7ee;padding:14px;border-radius:14px;box-shadow:0 4px 14px rgba(0,0,0,.05)}
[data-testid="stDataFrame"]{background:white;border-radius:12px;overflow:hidden}
[data-baseweb="input"],[data-baseweb="select"]{border-radius:9px}
@media(max-width:1000px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

USUARIOS_COLS = ["usuario","nombre","email","rol","password_hash","activo"]
REQ_COLS = ["id","fecha_creacion","ejecutivo","titulo","descripcion","estado","prioridad",
            "fecha_compromiso","ultima_actualizacion","actualizado_por","avance","activo"]
HIST_COLS = ["fecha_hora","requerimiento_id","usuario","accion","detalle"]
ESTADOS = ["Pendiente","En ejecución","En espera","Observado","Terminado"]
PRIORIDADES = ["Baja","Media","Alta","Crítica"]
ROLES = ["ejecutivo","jefatura","administrador"]

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False

@st.cache_resource
def conectar_google():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = dict(st.secrets["gcp_service_account"])
    key = str(info.get("private_key","")).replace("\\n","\n").strip()
    if key and not key.endswith("\n"):
        key += "\n"
    info["private_key"] = key
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(credentials).open_by_key(
        st.secrets["google_sheets"]["spreadsheet_id"]
    )

def obtener_hoja(libro, nombre, columnas):
    try:
        hoja = libro.worksheet(nombre)
    except gspread.WorksheetNotFound:
        hoja = libro.add_worksheet(title=nombre, rows=2000, cols=max(len(columnas),10))
        hoja.append_row(columnas)
    vals = hoja.get_all_values()
    if not vals:
        hoja.append_row(columnas)
    elif vals[0] != columnas:
        hoja.update("A1",[columnas])
    return hoja

def cargar_df(hoja, columnas):
    return pd.DataFrame(hoja.get_all_records(expected_headers=columnas), columns=columnas)

def inicializar():
    libro = conectar_google()
    usuarios = obtener_hoja(libro,"usuarios",USUARIOS_COLS)
    req = obtener_hoja(libro,"requerimientos",REQ_COLS)
    hist = obtener_hoja(libro,"historial",HIST_COLS)
    if len(usuarios.get_all_records()) == 0:
        admin_user = st.secrets.get("bootstrap",{}).get("admin_user","admin")
        admin_pass = st.secrets.get("bootstrap",{}).get("admin_password","Cambiar123!")
        usuarios.append_row([admin_user,"Administrador Abastecimiento","","administrador",hash_password(admin_pass),"SI"])
    return usuarios, req, hist

def registrar_historial(hoja, req_id, usuario, accion, detalle):
    hoja.append_row([ahora(), req_id, usuario, accion, detalle])

def dias_sin_actualizar(v):
    f = pd.to_datetime(v, errors="coerce")
    return 999 if pd.isna(f) else max((pd.Timestamp.now().normalize()-f.normalize()).days,0)

def exportar_excel(df):
    b = io.BytesIO()
    with pd.ExcelWriter(b, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Requerimientos")
    return b.getvalue()

def hero(titulo, subtitulo):
    st.markdown(f'<div class="hero"><h1>{titulo}</h1><p>{subtitulo}</p></div>', unsafe_allow_html=True)

try:
    ws_usuarios, ws_req, ws_hist = inicializar()
except Exception as exc:
    st.error("No fue posible conectar con Google Sheets.")
    st.code(str(exc))
    st.stop()

if "usuario" not in st.session_state:
    st.markdown('<div class="login-wrap"><div class="login-title">Seguimiento de Requerimientos</div><div class="login-sub">Departamento de Abastecimiento · SSMOC</div>', unsafe_allow_html=True)
    with st.form("login"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
    st.markdown('<div style="text-align:center;color:#6f7d8d;font-size:12px;margin-top:15px">Desarrollado por Bayron Retamal Gonzalez</div></div>', unsafe_allow_html=True)
    if entrar:
        u = cargar_df(ws_usuarios, USUARIOS_COLS)
        encontrado = u[(u.usuario.astype(str).str.lower()==usuario.strip().lower()) & (u.activo.astype(str).str.upper()=="SI")]
        if encontrado.empty:
            st.error("Usuario no encontrado o inactivo.")
        else:
            fila = encontrado.iloc[0]
            if check_password(password, str(fila.password_hash)):
                st.session_state.usuario = str(fila.usuario)
                st.session_state.nombre = str(fila.nombre)
                st.session_state.rol = str(fila.rol).lower()
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()

usuario_actual = st.session_state.usuario
nombre_actual = st.session_state.nombre
rol_actual = st.session_state.rol

with st.sidebar:
    st.markdown("## 📦 Abastecimiento SSMOC")
    st.markdown(f"**{nombre_actual}**")
    st.caption(f"Rol: {rol_actual.title()}")
    opciones = ["Resumen","Requerimientos","Nuevo requerimiento","Reunión de seguimiento"]
    if rol_actual == "administrador":
        opciones.append("Administrar usuarios")
    seccion = st.radio("Navegación", opciones, label_visibility="collapsed")
    st.divider()
    if st.button("Cerrar sesión", use_container_width=True):
        for k in ["usuario","nombre","rol"]:
            st.session_state.pop(k,None)
        st.rerun()

req_df = cargar_df(ws_req, REQ_COLS)
if not req_df.empty:
    req_df = req_df[req_df.activo.astype(str).str.upper()!="NO"].copy()
    req_df["dias_sin_actualizar"] = req_df.ultima_actualizacion.apply(dias_sin_actualizar)
usuarios_df = cargar_df(ws_usuarios, USUARIOS_COLS)
ejecutivos = usuarios_df[(usuarios_df.rol.astype(str).str.lower()=="ejecutivo") & (usuarios_df.activo.astype(str).str.upper()=="SI")].usuario.astype(str).tolist()
visible = req_df[req_df.ejecutivo.astype(str)==usuario_actual].copy() if rol_actual=="ejecutivo" and not req_df.empty else req_df.copy()

if seccion == "Resumen":
    hero("Resumen ejecutivo","Estado general de los requerimientos del Departamento de Abastecimiento.")
    total=len(visible)
    vals = {
        "Total":total,
        "Pendientes":len(visible[visible.estado=="Pendiente"]) if total else 0,
        "En ejecución":len(visible[visible.estado=="En ejecución"]) if total else 0,
        "Terminados":len(visible[visible.estado=="Terminado"]) if total else 0,
        "Sin actualizar":len(visible[visible.dias_sin_actualizar>7]) if total else 0,
    }
    st.markdown('<div class="kpi-grid">' + ''.join(f'<div class="kpi"><span>{k}</span><strong>{v}</strong></div>' for k,v in vals.items()) + '</div>', unsafe_allow_html=True)
    if visible.empty:
        st.info("Todavía no existen requerimientos registrados.")
    else:
        c1,c2=st.columns([1.15,.85])
        with c1:
            st.markdown('<div class="panel"><h3>Distribución por estado</h3>', unsafe_allow_html=True)
            est=visible.groupby("estado").size().reset_index(name="cantidad").set_index("estado")
            st.bar_chart(est)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="panel"><h3>Alertas prioritarias</h3>', unsafe_allow_html=True)
            alertas=visible[(visible.estado!="Terminado") & ((visible.dias_sin_actualizar>7) | visible.prioridad.isin(["Alta","Crítica"]))]
            if alertas.empty:
                st.success("No hay alertas prioritarias.")
            else:
                for _,r in alertas.head(5).iterrows():
                    st.markdown(f'<div class="alerta"><b>{r.titulo}</b><br><small>{r.ejecutivo} · {r.estado} · {r.dias_sin_actualizar} días sin actualización</small></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

elif seccion == "Requerimientos":
    hero("Requerimientos","Gestión, filtros y actualización de cada requerimiento.")
    if visible.empty:
        st.info("No hay requerimientos para mostrar.")
    else:
        c1,c2,c3,c4=st.columns([2,1,1,1])
        q=c1.text_input("Buscar",placeholder="ID, título, descripción o avance")
        f_estado=c2.multiselect("Estado",ESTADOS)
        f_prioridad=c3.multiselect("Prioridad",PRIORIDADES)
        f_exec=c4.multiselect("Ejecutivo",sorted(visible.ejecutivo.astype(str).unique())) if rol_actual!="ejecutivo" else []
        f=visible.copy()
        if q:
            mask=f[["id","titulo","descripcion","avance"]].astype(str).apply(lambda x:x.str.contains(q,case=False,na=False)).any(axis=1)
            f=f[mask]
        if f_estado:f=f[f.estado.isin(f_estado)]
        if f_prioridad:f=f[f.prioridad.isin(f_prioridad)]
        if f_exec:f=f[f.ejecutivo.isin(f_exec)]
        st.dataframe(f[["id","titulo","ejecutivo","estado","prioridad","fecha_compromiso","ultima_actualizacion"]],use_container_width=True,hide_index=True)
        st.download_button("Descargar Excel",exportar_excel(f),f"requerimientos_{date.today():%Y%m%d}.xlsx")
        st.markdown("### Actualizar requerimiento")
        elegido=st.selectbox("Seleccione",f.id.astype(str).tolist())
        actual=f[f.id.astype(str)==elegido].iloc[0]
        with st.form("actualizar"):
            a,b=st.columns(2)
            estado=a.selectbox("Estado",ESTADOS,index=ESTADOS.index(str(actual.estado)) if str(actual.estado) in ESTADOS else 0)
            prioridad=b.selectbox("Prioridad",PRIORIDADES,index=PRIORIDADES.index(str(actual.prioridad)) if str(actual.prioridad) in PRIORIDADES else 1)
            compromiso=st.date_input("Fecha compromiso",value=pd.to_datetime(actual.fecha_compromiso,errors="coerce").date() if not pd.isna(pd.to_datetime(actual.fecha_compromiso,errors="coerce")) else date.today())
            avance=st.text_area("Nueva actualización")
            guardar=st.form_submit_button("Guardar actualización",type="primary")
        if guardar and avance.strip():
            filas=ws_req.get_all_values(); encabezado=filas[0]; idc=encabezado.index("id")
            fila=next((i+1 for i,x in enumerate(filas[1:],start=1) if len(x)>idc and x[idc]==elegido),None)
            if fila:
                cambios={"estado":estado,"prioridad":prioridad,"fecha_compromiso":compromiso.isoformat(),"ultima_actualizacion":ahora(),"actualizado_por":usuario_actual,"avance":avance.strip()}
                for col,val in cambios.items():ws_req.update_cell(fila,encabezado.index(col)+1,val)
                registrar_historial(ws_hist,elegido,usuario_actual,"Actualización",avance.strip())
                st.success("Requerimiento actualizado.")
                st.rerun()

elif seccion == "Nuevo requerimiento":
    hero("Nuevo requerimiento","Registre y asigne una nueva gestión.")
    responsables=ejecutivos if rol_actual in ["jefatura","administrador"] else [usuario_actual]
    if not responsables:
        st.warning("Primero debe crear un ejecutivo.")
    else:
        with st.form("nuevo",clear_on_submit=True):
            c1,c2=st.columns(2)
            responsable=c1.selectbox("Ejecutivo",responsables)
            prioridad=c2.selectbox("Prioridad",PRIORIDADES,index=1)
            titulo=st.text_input("Título")
            descripcion=st.text_area("Descripción")
            compromiso=st.date_input("Fecha compromiso",value=date.today())
            avance=st.text_area("Gestión inicial")
            crear=st.form_submit_button("Crear requerimiento",type="primary")
        if crear and titulo.strip() and descripcion.strip():
            rid=f"REQ-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
            ws_req.append_row([rid,ahora(),responsable,titulo.strip(),descripcion.strip(),"Pendiente",prioridad,compromiso.isoformat(),ahora(),usuario_actual,avance.strip(),"SI"])
            registrar_historial(ws_hist,rid,usuario_actual,"Creación",f"Asignado a {responsable}")
            st.success(f"Requerimiento {rid} creado.")
            st.rerun()

elif seccion == "Reunión de seguimiento":
    hero("Reunión de seguimiento","Vista ejecutiva para la revisión periódica de jefatura.")
    if visible.empty:
        st.info("No hay requerimientos.")
    else:
        resumen=visible.groupby("ejecutivo").agg(total=("id","count"),terminados=("estado",lambda s:(s=="Terminado").sum()),en_ejecucion=("estado",lambda s:(s=="En ejecución").sum()),sin_actualizar=("dias_sin_actualizar",lambda s:(s>7).sum())).reset_index()
        st.dataframe(resumen,use_container_width=True,hide_index=True)
        st.markdown("### Pendientes de revisión")
        pendientes=visible[visible.estado!="Terminado"].sort_values(["dias_sin_actualizar"],ascending=False)
        st.dataframe(pendientes[["ejecutivo","id","titulo","estado","prioridad","fecha_compromiso","avance"]],use_container_width=True,hide_index=True)

elif seccion == "Administrar usuarios":
    hero("Administración de usuarios","Cree y gestione perfiles del sistema.")
    st.dataframe(usuarios_df[["usuario","nombre","email","rol","activo"]],use_container_width=True,hide_index=True)
    with st.form("crear_usuario",clear_on_submit=True):
        a,b=st.columns(2)
        nuevo_usuario=a.text_input("Usuario")
        nuevo_nombre=b.text_input("Nombre completo")
        nuevo_email=a.text_input("Correo")
        nuevo_rol=b.selectbox("Rol",ROLES)
        nueva_clave=st.text_input("Contraseña inicial",type="password")
        crear=st.form_submit_button("Crear usuario",type="primary")
    if crear:
        existentes=usuarios_df.usuario.astype(str).str.lower().tolist()
        if nuevo_usuario.strip().lower() in existentes:
            st.error("Ese usuario ya existe.")
        elif not nuevo_usuario.strip() or not nuevo_nombre.strip() or len(nueva_clave)<8:
            st.error("Complete los campos y use una contraseña de al menos 8 caracteres.")
        else:
            ws_usuarios.append_row([nuevo_usuario.strip(),nuevo_nombre.strip(),nuevo_email.strip(),nuevo_rol,hash_password(nueva_clave),"SI"])
            st.success("Usuario creado.")
            st.rerun()
