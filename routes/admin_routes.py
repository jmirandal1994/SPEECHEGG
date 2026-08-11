from flask import Blueprint, render_template, session, g
from auth import requiere_admin
from supabase_client import get_client

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


def _cliente_sesion():
    return get_client(session.get("access_token"), session.get("refresh_token"))


@admin_bp.route("/dashboard")
@requiere_admin
def dashboard():
    client = _cliente_sesion()

    doctores = (
        client.table("profiles")
        .select("id, nombre, especialidad, activo")
        .eq("rol", "doctor")
        .order("nombre")
        .execute()
    ).data or []

    presencia = (
        client.table("presencia").select("usuario_id, estado, ultima_actividad").execute()
    ).data or []
    presencia_por_usuario = {p["usuario_id"]: p for p in presencia}

    informes = (
        client.table("informes").select("doctor_id, marcado_informado").execute()
    ).data or []

    for doc in doctores:
        doc["informes_generados"] = sum(
            1 for i in informes if i["doctor_id"] == doc["id"] and i["marcado_informado"]
        )
        estado_presencia = presencia_por_usuario.get(doc["id"], {}).get("estado", "offline")
        doc["presencia"] = estado_presencia

    correcciones_pendientes = (
        client.table("correcciones").select("id", count="exact").eq("estado", "pendiente").execute()
    ).count or 0

    pacientes_sin_informar = (
        client.table("estudios_eeg").select("id", count="exact").neq("estado", "informado").execute()
    ).count or 0

    return render_template(
        "dashboard_admin.html",
        nombre=g.nombre,
        doctores=doctores,
        correcciones_pendientes=correcciones_pendientes,
        pacientes_sin_informar=pacientes_sin_informar,
    )
