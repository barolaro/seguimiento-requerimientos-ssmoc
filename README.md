# Seguimiento de Requerimientos SSMOC

Aplicación web en Streamlit para registrar, actualizar y supervisar los requerimientos asignados a ejecutivos del SSMOC.

## Funcionalidades

- Inicio de sesión con roles `administrador`, `jefatura` y `ejecutivo`.
- Cada ejecutivo visualiza y actualiza sus propios requerimientos.
- La jefatura y el administrador visualizan todos los requerimientos.
- Registro de estado, prioridad, responsable, fecha de compromiso y actualización en texto libre.
- Historial automático con usuario, fecha y hora de cada modificación.
- Indicadores de actualización diaria y días sin movimiento.
- Filtros por ejecutivo, estado, prioridad y búsqueda por palabra clave.
- Panel especial para reuniones de seguimiento.
- Administración básica de usuarios desde Google Sheets.
- Exportación de resultados a Excel.

## Hojas requeridas en Google Sheets

La aplicación crea automáticamente estas pestañas si no existen:

### `usuarios`

| usuario | nombre | email | rol | password_hash | activo |
|---|---|---|---|---|---|
| admin | Administrador | admin@ssmoc.cl | administrador | hash bcrypt | SI |

Roles permitidos:

- `administrador`
- `jefatura`
- `ejecutivo`

### `requerimientos`

Se crea automáticamente con las columnas necesarias.

### `historial`

Se crea automáticamente y registra todas las modificaciones.

## Configuración local

1. Crear un proyecto en Google Cloud.
2. Habilitar Google Sheets API y Google Drive API.
3. Crear una cuenta de servicio y descargar la clave JSON.
4. Compartir la planilla de Google Sheets con el correo de la cuenta de servicio como editor.
5. Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml`.
6. Completar los datos de la cuenta de servicio y el identificador de la planilla.
7. Instalar dependencias:

```bash
pip install -r requirements.txt
```

8. Ejecutar:

```bash
streamlit run app.py
```

## Despliegue en Streamlit Community Cloud

1. Vincular este repositorio en Streamlit Community Cloud.
2. Definir `app.py` como archivo principal.
3. Copiar el contenido de `secrets.toml.example` en **Advanced settings > Secrets**.
4. Reemplazar los valores por las credenciales reales.

## Primer acceso

Si la pestaña `usuarios` está vacía, la aplicación crea un administrador inicial usando:

- Usuario: valor de `bootstrap.admin_user`
- Contraseña: valor de `bootstrap.admin_password`

Después del primer acceso, se recomienda crear un nuevo administrador y cambiar o eliminar las credenciales iniciales de los secretos.
