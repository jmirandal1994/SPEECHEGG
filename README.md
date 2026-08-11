# Speech Psychology · Sistema de Informes EEG

Fase 1 del proyecto: base técnica funcionando (autenticación real con
Supabase Auth, esquema de base de datos, dashboards de doctor y admin
con datos reales). Los módulos de carga de pacientes, generación de
PDF y correcciones se agregan en las siguientes iteraciones.

## 1. Crear el proyecto en Supabase

1. Ve a [supabase.com](https://supabase.com) y crea un proyecto nuevo.
2. En **SQL Editor**, pega el contenido de `sql/schema.sql` y ejecútalo.
   Esto crea todas las tablas, las políticas de seguridad (RLS) y el
   trigger que crea automáticamente un perfil cuando se registra un usuario.
3. En **Project Settings → API**, copia:
   - `Project URL` → será tu `SUPABASE_URL`
   - `anon public` key → será tu `SUPABASE_ANON_KEY`
   - `service_role` key → será tu `SUPABASE_SERVICE_KEY` (¡secreta, nunca la subas a GitHub!)

## 2. Crear el primer usuario administrador

Como todavía no hay panel para crear usuarios (eso viene en la próxima
etapa), el primer admin se crea manualmente:

1. En Supabase: **Authentication → Users → Add user** (con email y contraseña).
2. En **Table Editor → profiles**, busca la fila que se creó automáticamente
   para ese usuario (por el trigger) y cambia su columna `rol` de `doctor` a `admin`.

Los siguientes usuarios (doctores) se van a poder crear directamente
desde el panel de administrador una vez que construyamos ese módulo.

## 3. Agregar la plantilla PDF de un doctor

Las plantillas PDF NO se suben desde la web (el filesystem de Vercel es
de solo lectura en producción) — viven directo en el repo:

1. Entra a `/admin/doctores/<id>/plantilla` (o a la tabla de doctores en
   el dashboard admin) para ver el UUID exacto del doctor.
2. Sube un archivo llamado `<uuid-del-doctor>.pdf` a la carpeta
   `plantillas_pdf/` del repo, directo en GitHub.
3. Commit + push. Cuando Vercel termine de desplegar, la plantilla queda
   activa automáticamente para ese doctor.
4. Para calibrar en qué coordenadas cae cada campo del informe sobre esa
   plantilla, usa el botón "Descargar PDF con grilla de coordenadas" en
   esa misma página — te devuelve el PDF con una grilla roja numerada
   cada 50pt encima. Con esos números, ajustamos `COORDS_INFORME_EEG`
   en `pdf_engine.py`.

## 4. Configurar variables de entorno (local)

```bash
cp .env.example .env
```

Completa `.env` con los valores del paso 1, más un `SECRET_KEY` propio
(cualquier string largo y aleatorio, por ejemplo generado con
`python -c "import secrets; print(secrets.token_hex(32))"`).

## 5. Correr localmente

```bash
python3 -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://localhost:5000` — deberías ver la pantalla de login.

## 6. Subir a GitHub

```bash
git init
git add .
git commit -m "Base del proyecto: auth, esquema de BD, dashboards"
git branch -M main
git remote add origin https://github.com/tu-usuario/tu-repo.git
git push -u origin main
```

`.gitignore` ya está configurado para que `.env` (tus claves reales)
nunca se suba al repositorio.

## 7. Desplegar en Vercel

1. En [vercel.com](https://vercel.com), **Add New → Project** e importa
   el repositorio de GitHub.
2. En **Environment Variables**, agrega las mismas 4 variables del `.env`
   (`SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`).
3. Deploy. `vercel.json` ya está configurado para correr la app Flask
   como función serverless.

## Estructura del proyecto

```
app.py                  → punto de entrada, registra los blueprints
config.py                → lee variables de entorno
supabase_client.py       → cliente Supabase (por-usuario y admin)
auth.py                  → login/logout + decoradores @requiere_login / @requiere_admin
routes/
  auth_routes.py          → /login, /logout
  doctor_routes.py         → /doctor/dashboard
  admin_routes.py          → /admin/dashboard
templates/                → HTML (Jinja2)
static/css/style.css      → sistema de diseño
sql/schema.sql            → esquema completo + políticas RLS
```

## Próximos módulos (en orden sugerido)

1. Gestión de doctores desde el panel admin (crear/editar/desactivar cuentas)
2. Carga de pacientes: Excel masivo (admin) + formulario manual (doctor)
3. Plantillas PDF por doctor (subida del PDF base)
4. Generador de informe EEG → overlay de datos sobre el PDF base + marcar como informado
5. Flujo de correcciones (doctor solicita → admin resuelve)
6. Presencia en vivo con actualización automática (polling o Supabase Realtime)
