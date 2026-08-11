from supabase import create_client, Client
from config import Config


def get_client(access_token: str | None = None, refresh_token: str | None = None) -> Client:
    """
    Cliente 'a nombre del usuario'. Si se pasa el access_token de su sesión,
    todas las queries respetan Row Level Security como ese usuario
    (un doctor solo ve sus propios pacientes, por ejemplo).
    """
    client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
    if access_token:
        client.postgrest.auth(access_token)
        client.auth.set_session(access_token, refresh_token or "")
    return client


def get_admin_client() -> Client:
    """
    Cliente con la service role key: se salta RLS por completo.
    Úsalo únicamente para operaciones administrativas de servidor
    (crear cuentas de doctor, cargas masivas por Excel, etc),
    nunca para responder directamente con datos de un usuario específico.
    """
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
