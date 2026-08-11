"""
Acceso a Supabase Storage para las plantillas PDF de cada doctor y los
informes ya generados. Todo pasa por el cliente admin (service role) —
son documentos clínicos, así que el control de acceso lo hacen las
rutas de Flask (@requiere_login / @requiere_admin), no políticas
públicas de Storage.
"""
from supabase_client import get_admin_client

BUCKET_PLANTILLAS = "plantillas-pdf"
BUCKET_INFORMES = "informes-pdf"


def subir_plantilla_doctor(doctor_id: str, contenido_pdf: bytes) -> str:
    """Sube (o reemplaza) la plantilla PDF base de un doctor."""
    admin = get_admin_client()
    path = f"{doctor_id}.pdf"
    admin.storage.from_(BUCKET_PLANTILLAS).upload(
        path,
        contenido_pdf,
        {"content-type": "application/pdf", "upsert": "true"},
    )
    return path


def descargar_plantilla_doctor(doctor_id: str) -> bytes | None:
    """Descarga la plantilla PDF base de un doctor, o None si no tiene."""
    admin = get_admin_client()
    try:
        return admin.storage.from_(BUCKET_PLANTILLAS).download(f"{doctor_id}.pdf")
    except Exception:
        return None


def subir_informe_generado(informe_id: str, contenido_pdf: bytes) -> str:
    """Sube el PDF final ya generado de un informe."""
    admin = get_admin_client()
    path = f"{informe_id}.pdf"
    admin.storage.from_(BUCKET_INFORMES).upload(
        path,
        contenido_pdf,
        {"content-type": "application/pdf", "upsert": "true"},
    )
    return path


def descargar_informe(informe_id: str) -> bytes | None:
    """Descarga el PDF final ya generado de un informe."""
    admin = get_admin_client()
    try:
        return admin.storage.from_(BUCKET_INFORMES).download(f"{informe_id}.pdf")
    except Exception:
        return None
