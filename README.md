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

Abre [LATIA local](http://127.0.0.1:5000) e inicia sesión con la cuenta creada. El historial empieza vacío. Chart.js se sirve desde los archivos estáticos de la aplicación.

## Publicación con Supabase

Flask consulta PostgreSQL directamente por SQLAlchemy. Mantén el esquema `latia` fuera de los esquemas expuestos por la Data API. Supabase ofrece la conexión directa para servidores con IPv6 y el pooler de sesión para redes con solo IPv4. [Conexiones a PostgreSQL en Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)

1. Guarda las cadenas de conexión en los secretos del servidor. Usa `MIGRATION_DATABASE_URL` para la cuenta que ejecutará Alembic y `DATABASE_URL` para un rol de aplicación con permisos limitados. Configura TLS con `sslmode=verify-full` y el certificado raíz correspondiente mediante `sslrootcert`. [SSL en Supabase](https://supabase.com/docs/guides/platform/ssl-enforcement)
2. Ejecuta `python -m alembic upgrade head` con el rol de migraciones. Si `MIGRATION_DATABASE_URL` está ausente, Alembic usa `DATABASE_URL`.
3. Crea el rol de ejecución `latia_app` con contraseña segura y otorga solo los permisos de abajo con el propietario del esquema. Apunta `DATABASE_URL` a ese rol antes de crear la primera cuenta con `flask --app latia crear-usuario`.
4. Configura una `SECRET_KEY` exclusiva y activa `LATIA_SECURE_COOKIES=1`. Ejecuta `waitress-serve --call --listen=127.0.0.1:8000 latia:create_app` detrás de un proxy HTTPS que transmita el esquema de la solicitud desde una IP de confianza. Configura Waitress para confiar solo en ese proxy y en su cabecera `X-Forwarded-Proto`. Aplica límites de intentos de acceso en el proxy para `POST /acceso`. [Configuración de Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html)

```sql
GRANT USAGE ON SCHEMA latia TO latia_app;
GRANT SELECT, INSERT ON latia.accounts TO latia_app;
GRANT UPDATE (username, timezone, password_hash, session_version, profile_photo, pressure_ranges) ON latia.accounts TO latia_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON latia.readings TO latia_app;
GRANT USAGE ON SEQUENCE latia.accounts_id_seq, latia.readings_id_seq TO latia_app;
```

Esta primera versión captura cada medición por separado. Las gráficas y los resúmenes usan las lecturas del período seleccionado y presentan valores descriptivos.
