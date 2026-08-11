import os
import re


def _limpiar_supabase_url(url: str | None) -> str | None:
    """
    Normaliza SUPABASE_URL por si quedó con rutas o barras de más
    (ej: '.../rest/v1/' en vez de solo el dominio base).
    """
    if not url:
        return url
    url = url.strip().rstrip("/")
    for sufijo in ("/rest/v1", "/auth/v1"):
        if url.endswith(sufijo):
            url = url[: -len(sufijo)]
    return url.rstrip("/")


class Config:
    """
    Toda la configuración sensible viene de variables de entorno.
    En local: usa un archivo .env (ver .env.example).
    En Vercel: configúralas en Project Settings → Environment Variables.
    NUNCA escribas claves reales directamente en este archivo.
    """
    SECRET_KEY = (os.environ.get("SECRET_KEY") or "").strip() or None

    SUPABASE_URL = _limpiar_supabase_url(os.environ.get("SUPABASE_URL"))
    SUPABASE_ANON_KEY = (os.environ.get("SUPABASE_ANON_KEY") or "").strip() or None
    # La service key bypassea RLS. Se usa SOLO en el backend, para
    # operaciones de administrador (crear usuarios, subir Excel, etc).
    SUPABASE_SERVICE_KEY = (os.environ.get("SUPABASE_SERVICE_KEY") or "").strip() or None

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB máx. por archivo subido


def validate_config():
    """Falla rápido y con un mensaje claro si falta configuración crítica."""
    faltantes = [
        var for var in ("SECRET_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY")
        if not getattr(Config, var)
    ]
    if faltantes:
        raise RuntimeError(
            f"Faltan variables de entorno requeridas: {', '.join(faltantes)}. "
            "Revisa tu archivo .env (local) o la configuración de Vercel (producción)."
        )
    print(f"[CONFIG] SUPABASE_URL normalizada en uso: {Config.SUPABASE_URL}")

    # Validación de formato JWT (mismo patrón que usa la librería supabase-py),
    # para detectar claves mal copiadas ANTES de que fallen a mitad del login.
    patron_jwt = r"^[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*$"
    for nombre_var in ("SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY"):
        valor = getattr(Config, nombre_var)
        es_valido = bool(re.match(patron_jwt, valor))
        print(f"[CONFIG] {nombre_var}: largo={len(valor)}, formato_jwt_valido={es_valido}, "
              f"empieza_con='{valor[:6]}', termina_con='{valor[-6:]}'")
        if not es_valido:
            print(f"[CONFIG] ADVERTENCIA: {nombre_var} no tiene formato JWT válido. "
                  "Revisa que no tenga espacios/saltos de línea ocultos, o que sea la clave legacy (empieza con 'eyJ'), no la nueva 'sb_...'.")
