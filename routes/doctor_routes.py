from flask import Blueprint, render_template, session, g
from auth import requiere_login
from supabase_client import get_client

doctor_bp = Blueprint("doctor_bp", __name__, url_prefix="/doctor")


def _cliente_sesion():
    return get_client(session.get("access_token"), session.get("refresh_token"))


@doctor_bp.route("/dashboard")
@requiere_login
def dashboard():
    client = _cliente_sesion()

    # Marcamos presencia como "online" (heartbeat simple; se reforzará
    # con un ping periódico desde el frontend más adelante).
    client.table("presencia").upsert({
        "usuario_id": g.user_id,
        "estado": "online",
    }).execute()

    informes_generados = (
        client.table("informes")
        .select("id", count="exact")
        .eq("doctor_id", g.user_id)
        .eq("marcado_informado", True)
        .execute()
    )
    estudios_pendientes = (
        client.table("estudios_eeg")
        .select("id", count="exact")
        .eq("doctor_id", g.user_id)
        .neq("estado", "informado")
        .execute()
    )

    return render_template(
        "dashboard_doctor.html",
        nombre=g.nombre,
        total_informes=informes_generados.count or 0,
        total_pendientes=estudios_pendientes.count or 0,
    )
