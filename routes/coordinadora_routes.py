from flask import Blueprint, render_template, session, g, request, send_file, flash, redirect, url_for
import io
from auth import requiere_coordinadora
from supabase_client import get_client
from storage_helpers import descargar_informe

coordinadora_bp = Blueprint("coordinadora_bp", __name__, url_prefix="/coordinadora")


def _cliente_sesion():
    return get_client(session.get("access_token"), session.get("refresh_token"))


@coordinadora_bp.route("/dashboard")
@requiere_coordinadora
def dashboard():
    client = _cliente_sesion()

    fecha_filtro = (request.args.get("fecha") or "").strip()

    informes_res = (
        client.table("informes")
        .select(
            "id, fecha_informe, marcado_informado,"
            "estudios_eeg(fecha_estudio, tipo_registro, pacientes(nombre_completo, rut)),"
            "profiles(nombre)"
        )
        .eq("marcado_informado", True)
        .order("fecha_informe", desc=True)
        .execute()
    )
    informes = informes_res.data or []

    # Filtro por fecha de estudio (se hace en Python: el volumen esperado
    # de informes diarios es bajo, así que no hace falta optimizar esto
    # con un filtro server-side sobre la tabla embebida).
    if fecha_filtro:
        informes = [
            i for i in informes
            if (i.get("estudios_eeg") or {}).get("fecha_estudio") == fecha_filtro
        ]

    return render_template(
        "coordinadora_dashboard.html",
        nombre=g.nombre,
        informes=informes,
        fecha_filtro=fecha_filtro,
    )


@coordinadora_bp.route("/informe/<informe_id>/descargar")
@requiere_coordinadora
def descargar(informe_id):
    contenido = descargar_informe(informe_id)
    if not contenido:
        flash("No se encontró el PDF de este informe.", "danger")
        return redirect(url_for("coordinadora_bp.dashboard"))

    return send_file(
        io.BytesIO(contenido),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"informe_EEG_{informe_id}.pdf",
    )
