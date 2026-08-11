from flask import Blueprint, render_template, session, g, request, redirect, url_for, flash, send_file
import io
from datetime import datetime, timezone
from auth import requiere_login
from supabase_client import get_client
from storage_helpers import obtener_plantilla_doctor, subir_informe_generado
from pdf_engine import generar_informe_pdf

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


@doctor_bp.route("/estudio/<estudio_id>/informe", methods=["GET", "POST"])
@requiere_login
def informe_estudio(estudio_id):
    client = _cliente_sesion()

    estudio_res = (
        client.table("estudios_eeg")
        .select("*, pacientes(*)")
        .eq("id", estudio_id)
        .single()
        .execute()
    )
    estudio = estudio_res.data
    if not estudio:
        flash("Estudio no encontrado o no tienes acceso a él.", "danger")
        return redirect(url_for("doctor_bp.dashboard"))

    paciente = estudio.get("pacientes") or {}

    if request.method == "POST":
        campos_informe = {
            "tecnica": request.form.get("tecnica", "").strip(),
            "actividad_base": request.form.get("actividad_base", "").strip(),
            "hallazgos": request.form.get("hallazgos", "").strip(),
            "impresion_diagnostica": request.form.get("impresion_diagnostica", "").strip(),
            "correlacion_clinica": request.form.get("correlacion_clinica", "").strip(),
            "conclusion": request.form.get("conclusion", "").strip(),
        }

        plantilla_bytes = obtener_plantilla_doctor(g.user_id)
        if not plantilla_bytes:
            flash("Tu administrador todavía no ha cargado tu plantilla PDF base. "
                  "Pídele que la suba desde el panel de administración.", "warning")
            return redirect(url_for("doctor_bp.dashboard"))

        campos_pdf = dict(campos_informe)
        campos_pdf.update({
            "nombre_paciente": paciente.get("nombre_completo", ""),
            "rut_paciente": paciente.get("rut", ""),
            "fecha_nacimiento": paciente.get("fecha_nacimiento", "") or "",
            "fecha_estudio": estudio.get("fecha_estudio", "") or "",
            "tipo_registro": estudio.get("tipo_registro", "") or "",
        })

        try:
            pdf_final = generar_informe_pdf(plantilla_bytes, campos_pdf)
        except Exception as e:
            print(f"[INFORME ERROR] Falló generar_informe_pdf: {repr(e)}")
            flash("No se pudo generar el PDF. Revisa que tu plantilla sea un PDF válido de una página.", "danger")
            return redirect(url_for("doctor_bp.informe_estudio", estudio_id=estudio_id))

        informe_res = client.table("informes").upsert({
            "estudio_id": estudio_id,
            "doctor_id": g.user_id,
            **campos_informe,
            "marcado_informado": True,
            "fecha_informe": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="estudio_id").execute()

        informe_id = informe_res.data[0]["id"]
        subir_informe_generado(informe_id, pdf_final)

        client.table("informes").update({
            "pdf_generado_url": f"{informe_id}.pdf",
        }).eq("id", informe_id).execute()

        client.table("estudios_eeg").update({"estado": "informado"}).eq("id", estudio_id).execute()

        nombre_paciente_archivo = (paciente.get("nombre_completo") or "paciente").replace(" ", "_")
        nombre_archivo = f"informe_EEG_{nombre_paciente_archivo}.pdf"
        return send_file(
            io.BytesIO(pdf_final),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_archivo,
        )

    return render_template("doctor_informe_form.html", estudio=estudio, paciente=paciente)
