from flask import Blueprint, render_template, session, g, request, redirect, url_for, flash, send_file
import io
import calendar as calendar_mod
from datetime import datetime, timezone, date, timedelta
from auth import requiere_login
from supabase_client import get_client
from storage_helpers import obtener_plantilla_doctor, subir_informe_generado
from pdf_engine import generar_informe_pdf

doctor_bp = Blueprint("doctor_bp", __name__, url_prefix="/doctor")

NOMBRES_MES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


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


@doctor_bp.route("/calendario")
@requiere_login
def calendario():
    client = _cliente_sesion()

    mes_param = request.args.get("mes")
    hoy = date.today()
    if mes_param:
        try:
            anio, mes = map(int, mes_param.split("-"))
        except ValueError:
            anio, mes = hoy.year, hoy.month
    else:
        anio, mes = hoy.year, hoy.month

    primer_dia = date(anio, mes, 1)
    ultimo_dia_num = calendar_mod.monthrange(anio, mes)[1]
    ultimo_dia = date(anio, mes, ultimo_dia_num)

    jornadas_res = (
        client.table("jornadas")
        .select("fecha")
        .eq("doctor_id", g.user_id)
        .gte("fecha", primer_dia.isoformat())
        .lte("fecha", ultimo_dia.isoformat())
        .execute()
    )
    dias_asignados = {j["fecha"] for j in (jornadas_res.data or [])}

    cal = calendar_mod.Calendar(firstweekday=0)  # semana empieza lunes
    semanas = cal.monthdatescalendar(anio, mes)

    mes_anterior_dt = primer_dia - timedelta(days=1)
    mes_siguiente_dt = ultimo_dia + timedelta(days=1)

    return render_template(
        "doctor_calendario.html",
        semanas=semanas,
        mes_actual=mes,
        dias_asignados=dias_asignados,
        mes_anterior=f"{mes_anterior_dt.year:04d}-{mes_anterior_dt.month:02d}",
        mes_siguiente=f"{mes_siguiente_dt.year:04d}-{mes_siguiente_dt.month:02d}",
        nombre_mes=f"{NOMBRES_MES[mes]} {anio}",
        hoy=hoy,
    )


@doctor_bp.route("/jornada/<fecha>", methods=["GET", "POST"])
@requiere_login
def jornada(fecha):
    client = _cliente_sesion()

    jornada_res = (
        client.table("jornadas")
        .select("*")
        .eq("doctor_id", g.user_id)
        .eq("fecha", fecha)
        .execute()
    )
    if not jornada_res.data:
        flash("No tienes esta fecha asignada como jornada.", "warning")
        return redirect(url_for("doctor_bp.calendario"))

    if request.method == "POST":
        nombre_completo = request.form.get("nombre_completo", "").strip()
        rut = request.form.get("rut", "").strip()
        fecha_nacimiento = request.form.get("fecha_nacimiento") or None
        tipo_registro = request.form.get("tipo_registro") or None

        if not nombre_completo:
            flash("El nombre del paciente es obligatorio.", "danger")
            return redirect(url_for("doctor_bp.jornada", fecha=fecha))

        paciente_res = client.table("pacientes").insert({
            "nombre_completo": nombre_completo,
            "rut": rut,
            "fecha_nacimiento": fecha_nacimiento,
            "doctor_asignado_id": g.user_id,
            "origen": "manual",
            "creado_por": g.user_id,
        }).execute()
        paciente_id = paciente_res.data[0]["id"]

        client.table("estudios_eeg").insert({
            "paciente_id": paciente_id,
            "doctor_id": g.user_id,
            "fecha_estudio": fecha,
            "tipo_registro": tipo_registro,
            "estado": "pendiente",
        }).execute()

        flash(f"Paciente {nombre_completo} agregado a la jornada.", "success")
        return redirect(url_for("doctor_bp.jornada", fecha=fecha))

    estudios_res = (
        client.table("estudios_eeg")
        .select("*, pacientes(*), informes(id, marcado_informado)")
        .eq("doctor_id", g.user_id)
        .eq("fecha_estudio", fecha)
        .order("created_at")
        .execute()
    )
    estudios = estudios_res.data or []

    return render_template("doctor_jornada.html", fecha=fecha, estudios=estudios)


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
