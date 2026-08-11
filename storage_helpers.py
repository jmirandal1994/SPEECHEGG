"""
Acceso a los PDFs del proyecto:
- Las plantillas BASE de cada doctor viven en el repo, en la carpeta
  plantillas_pdf/ (se suben directo a GitHub, ver plantillas_pdf/README.md).
  Vercel despliega el filesystem como solo-lectura, así que estos archivos
  se leen directo del código desplegado — nunca se escriben en runtime.
- Los informes YA GENERADOS (dinámicos, uno por paciente) sí necesitan
  persistir más allá de una sola ejecución, así que esos van a Supabase
  Storage (bucket informes-pdf) a través del cliente admin (service role).
"""
from pathlib import Path
from supabase_client import get_admin_client

PLANTILLAS_DIR = Path(__file__).resolve().parent / "plantillas_pdf"
BUCKET_INFORMES = "informes-pdf"


def obtener_plantilla_doctor(doctor_id: str) -> bytes | None:
    """Lee la plantilla PDF base de un doctor desde el repo. None si no existe."""
    ruta = PLANTILLAS_DIR / f"{doctor_id}.pdf"
    if not ruta.exists():
        return None
    return ruta.read_bytes()


def existe_plantilla_doctor(doctor_id: str) -> bool:
    return (PLANTILLAS_DIR / f"{doctor_id}.pdf").exists()


def subir_informe_generado(informe_id: str, contenido_pdf: bytes) -> str:
    """Sube el PDF final ya generado de un informe a Supabase Storage."""
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
