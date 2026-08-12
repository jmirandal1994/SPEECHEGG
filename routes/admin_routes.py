from flask import Blueprint, render_template, session, g, redirect, url_for, flash, send_file, request
import io
from auth import requiere_admin
from supabase_client import get_client
from storage_helpers import existe_plantilla_doctor, obtener_plantilla_doctor
from pdf_engine import generar_pdf_con_grilla

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
        # La plantilla ya no vive en Supabase: se lee directo del repo
        # (carpeta plantillas_pdf/), ver storage_helpers.py.
        doc["tiene_plantilla"] = existe_plantilla_doctor(doc["id"])

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


@admin_bp.route("/doctores/<doctor_id>/plantilla")
@requiere_admin
def plantilla_doctor(doctor_id):
    """
    Página de estado de la plantilla PDF de un doctor. Ya no se sube
    desde aquí (el filesystem de Vercel es de solo lectura en producción):
    la plantilla se agrega directo al repo, en plantillas_pdf/<uuid>.pdf.
    Esta página solo muestra el UUID exacto a usar y si el archivo
    ya está detectado en el deployment actual.
    """
    client = _cliente_sesion()

    doctor_res = (
        client.table("profiles").select("id, nombre").eq("id", doctor_id).single().execute()
    )
    doctor = doctor_res.data
    if not doctor:
        flash("Doctor no encontrado.", "danger")
        return redirect(url_for("admin_bp.dashboard"))

    tiene_plantilla = existe_plantilla_doctor(doctor_id)

    return render_template(
        "admin_plantilla_doctor.html",
        doctor=doctor,
        tiene_plantilla=tiene_plantilla,
    )


@admin_bp.route("/doctores/<doctor_id>/plantilla/grid")
@requiere_admin
def plantilla_doctor_grid(doctor_id):
    contenido = obtener_plantilla_doctor(doctor_id)
    if not contenido:
        flash("Este doctor todavía no tiene una plantilla PDF en el repo.", "warning")
        return redirect(url_for("admin_bp.plantilla_doctor", doctor_id=doctor_id))

    pdf_con_grilla = generar_pdf_con_grilla(contenido)
    return send_file(
        io.BytesIO(pdf_con_grilla),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="plantilla_con_grilla.pdf",
    )


@admin_bp.route("/jornadas", methods=["GET", "POST"])
@requiere_admin
def jornadas():
    client = _cliente_sesion()

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        fecha = request.form.get("fecha")
        if not doctor_id or not fecha:
            flash("Selecciona un doctor y una fecha.", "danger")
            return redirect(url_for("admin_bp.jornadas"))
        try:
            client.table("jornadas").insert({"doctor_id": doctor_id, "fecha": fecha}).execute()
            flash("Jornada asignada correctamente.", "success")
        except Exception as e:
            print(f"[JORNADA ERROR] {repr(e)}")
            flash("No se pudo asignar (¿ya existía esa fecha para este doctor?).", "danger")
        return redirect(url_for("admin_bp.jornadas"))

    doctores = (
        client.table("profiles").select("id, nombre").eq("rol", "doctor").order("nombre").execute()
    ).data or []

    jornadas_res = (
        client.table("jornadas")
        .select("*, profiles(nombre)")
        .order("fecha", desc=True)
        .limit(30)
        .execute()
    )
    jornadas_lista = jornadas_res.data or []

    return render_template("admin_jornadas.html", doctores=doctores, jornadas=jornadas_lista)
