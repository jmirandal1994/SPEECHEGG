import os


class Config:
    """
    Toda la configuración sensible viene de variables de entorno.
    En local: usa un archivo .env (ver .env.example).
    En Vercel: configúralas en Project Settings → Environment Variables.
    NUNCA escribas claves reales directamente en este archivo.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
    # La service key bypassea RLS. Se usa SOLO en el backend, para
    # operaciones de administrador (crear usuarios, subir Excel, etc).
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

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
