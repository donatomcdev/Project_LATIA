# LATIA

Diario web responsivo para registrar la presión arterial sistólica y diastólica en mmHg y el pulso en latidos por minuto. Incluye historial por fecha, edición y eliminación, comentarios, gráficas y estadísticas descriptivas. Cada cuenta tiene su propio historial y puede elegir la zona horaria que usa para ingresar y consultar las lecturas.

## Desarrollo en Windows

Requisitos: Python 3.11 o posterior y PostgreSQL local. Desde PowerShell, abre `psql` con el usuario administrador de tu instalación:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U postgres -d postgres
```

Crea el rol y la base una sola vez. El comando `\password` solicita la contraseña de forma interactiva.

```sql
CREATE ROLE latia LOGIN;
\password latia
CREATE DATABASE latia OWNER latia;
\q
```

En la carpeta del proyecto, prepara el entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edita `.env`. Pon la contraseña del rol en `DATABASE_URL` y el valor generado en `SECRET_KEY`. Codifica los caracteres reservados de la contraseña para usarla en una URL (por ejemplo, `@` se escribe `%40`). `LATIA_SECURE_COOKIES=0` permite HTTP en el equipo local.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m flask --app latia crear-usuario miusuario
.\.venv\Scripts\python.exe -m flask --app latia run
```

Abre [LATIA local](http://127.0.0.1:5000). Si creaste una cuenta por consola, usa **Acceso para cuentas existentes**. El historial empieza vacío. Chart.js se sirve desde los archivos estáticos de la aplicación.

## Acceso por código de correo

Configura `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` en `.env`. En Supabase Auth habilita el proveedor de correo y el registro. Configura la plantilla de Magic Link con `{{ .Token }}` para enviar el código de seis dígitos y fija su vigencia en 600 segundos. Para habilitar el envío a usuarios externos, configura SMTP con un remitente verificado. Reinicia Flask después de cambiar la configuración. [Acceso por código](https://supabase.com/docs/guides/auth/auth-email-passwordless) · [SMTP personalizado](https://supabase.com/docs/guides/auth/auth-smtp)

Para probar con PostgreSQL local, usa un proyecto de autenticación separado del de producción. **Acceder con código** lleva a elegir un nombre de usuario la primera vez. Las cuentas anteriores pueden entrar con sus credenciales y usar **Perfil → Vincular correo** para conservar sus lecturas. Después de vincularlo, la cuenta accede por código. La reversión de la migración de acceso requiere que todas las cuentas tengan un método de acceso compatible con la versión anterior.

## Publicación con Supabase

Flask consulta PostgreSQL directamente por SQLAlchemy. Mantén el esquema `latia` fuera de los esquemas expuestos por la Data API. Supabase ofrece la conexión directa para servidores con IPv6 y el pooler de sesión para redes con solo IPv4. [Conexiones a PostgreSQL en Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)

Para preparar la conexión desde Windows, usa un archivo separado `.env.supabase`. Si aún no existe, copia `.env.example`, sustituye la conexión local por los valores de Supabase y configura estas variables:

| Variable | Valor |
| --- | --- |
| `MIGRATION_DATABASE_URL` | Cadena de **Connect → Session pooler** para el usuario propietario del esquema. |
| `DATABASE_URL` | Cadena del mismo proyecto para el rol `latia_app`. Con el pooler, el usuario tiene el formato `latia_app.<referencia-del-proyecto>`. |
| `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` | URL del proyecto y clave publicable del mismo proyecto. |
| `SECRET_KEY` | Clave propia del entorno. Genera una con el comando de la sección de desarrollo. |
| `LATIA_SECURE_COOKIES` | `1` con HTTPS. Usa `0` únicamente en una prueba por HTTP en localhost. |

Descarga el certificado raíz desde la configuración de la base de datos y añade `sslmode=verify-full` y `sslrootcert` a ambas cadenas. Usa la ruta al certificado con caracteres reservados codificados para URL. Conserva `.env.supabase` fuera de Git. Si la aplicación debe conservar cuentas y lecturas locales, prepara su traslado antes de cambiar la conexión. Alembic prepara la estructura de destino.

1. Guarda las cadenas de conexión en los secretos del servidor. Usa `MIGRATION_DATABASE_URL` para la cuenta que ejecutará Alembic y `DATABASE_URL` para un rol de aplicación con permisos limitados. Configura TLS con `sslmode=verify-full` y el certificado raíz correspondiente mediante `sslrootcert`. [SSL en Supabase](https://supabase.com/docs/guides/platform/ssl-enforcement)
2. Ejecuta `python -m alembic upgrade head` con el rol de migraciones. Si `MIGRATION_DATABASE_URL` está ausente, Alembic usa `DATABASE_URL`.
3. Crea el rol de ejecución `latia_app` con contraseña segura y otorga solo los permisos de abajo con el propietario del esquema. Apunta `DATABASE_URL` a ese rol antes de crear la primera cuenta con `flask --app latia crear-usuario`.
4. Configura una `SECRET_KEY` exclusiva y activa `LATIA_SECURE_COOKIES=1`. Ejecuta `waitress-serve --call --listen=127.0.0.1:8000 latia:create_app` detrás de un proxy HTTPS que transmita el esquema de la solicitud desde una IP de confianza. Configura Waitress para confiar solo en ese proxy y en su cabecera `X-Forwarded-Proto`. Aplica límites de intentos de acceso en el proxy a los POST de `/acceso`, `/acceso/codigo` y `/acceso/anterior`. [Configuración de Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html)

```sql
GRANT USAGE ON SCHEMA latia TO latia_app;
GRANT SELECT, INSERT ON latia.accounts TO latia_app;
GRANT UPDATE (username, timezone, password_hash, auth_user_id, session_version, profile_photo, pressure_ranges) ON latia.accounts TO latia_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON latia.readings TO latia_app;
GRANT USAGE ON SEQUENCE latia.accounts_id_seq, latia.readings_id_seq TO latia_app;
```

Para ejecutar las migraciones usando explícitamente el perfil de Supabase en Windows:

```powershell
.\.venv\Scripts\python.exe -m dotenv -f .env.supabase run -- .\.venv\Scripts\python.exe -m alembic upgrade head
```

Una vez concedidos los permisos al rol de aplicación, puedes iniciar Flask con ese mismo perfil para una prueba local:

```powershell
.\.venv\Scripts\python.exe -m dotenv -f .env.supabase run -- .\.venv\Scripts\python.exe -m flask --app latia run
```

Configura el SMTP personalizado antes de preparar la plantilla de código si el proyecto usa el plan Free y está sujeto al cambio de junio de 2026. Para la prueba funcional usa una cuenta de prueba, verifica la recepción del código y comprueba que pueda guardar y volver a consultar una lectura de ejemplo. [Personalización de plantillas en Free](https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier) · [SMTP personalizado](https://supabase.com/docs/guides/auth/auth-smtp)

## Despliegue en Render

El Blueprint `render.yaml` ejecuta Flask con Waitress y usa Supabase para PostgreSQL y el acceso por correo. Configura una instancia Free en Ohio para la primera prueba. En ese plan, la aplicación puede tardar en responder al abrirla tras un período de inactividad. [Límites del plan Free](https://render.com/docs/free)

1. Completa primero las migraciones y los permisos de `latia_app` en Supabase según la sección anterior. Ejecuta Alembic desde el equipo de administración con `MIGRATION_DATABASE_URL`. Render solo necesita la conexión del rol de aplicación.
2. Sube los cambios del repositorio a GitHub. En Render, abre **New → Blueprint** y selecciona el repositorio y la rama que contiene `render.yaml`. Si ya tienes un servicio de LATIA en Render, revisa su configuración antes de crear otro. [Configurar un Blueprint](https://render.com/docs/infrastructure-as-code)
3. Proporciona `DATABASE_URL`, `SUPABASE_URL` y `SUPABASE_PUBLISHABLE_KEY` en Render. Usa la cadena del rol `latia_app` del **Session pooler** y cambia el parámetro del certificado a `sslrootcert=/etc/secrets/supabase.crt`. Mantén `sslmode=verify-full`. Render genera `SECRET_KEY` y activa las cookies seguras mediante el Blueprint.
4. En **Environment → Secret Files**, añade `supabase.crt` con el contenido del certificado raíz que descargaste de Supabase. Guarda los cambios para desplegar con el certificado disponible. [Archivos secretos en Render](https://render.com/docs/configure-environment-variables#secret-files)
5. Abre la URL HTTPS que entrega Render. La comprobación de salud verifica que Flask sirva `/acceso`. Para comprobar también Supabase, entra con una cuenta de prueba, guarda una lectura ficticia y vuelve a consultarla.

Esta primera versión captura cada medición por separado. Las gráficas y los resúmenes usan las lecturas del período seleccionado y presentan valores descriptivos.
