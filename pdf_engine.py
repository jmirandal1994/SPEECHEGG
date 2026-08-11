"""
Motor de generación de PDF para informes EEG.

Toma la plantilla PDF base de un doctor y superpone el contenido del
informe encima, usando coordenadas fijas — el mismo patrón que usaba
CardioHome (ReportLab dibuja un overlay del mismo tamaño que la hoja,
después se fusiona con la plantilla original).

CÓMO CALIBRAR LAS COORDENADAS CON TU PDF REAL:
1. Sube tu plantilla en /doctor/plantilla
2. Abre /doctor/plantilla/grid — te descarga la MISMA plantilla pero con
   una grilla roja dibujada encima, marcada cada 50 puntos, con los
   números de coordenada. Ábrela y anota dónde cae cada campo.
3. El origen (0,0) está en la esquina INFERIOR IZQUIERDA de la hoja.
   El eje X crece hacia la derecha, el eje Y crece hacia ARRIBA.
   Todo se mide en puntos PDF (1 punto = 1/72 pulgada; una hoja carta
   mide 612 x 792 puntos).
4. Edita COORDS_INFORME_EEG más abajo con los valores que anotaste:
       "nombre_del_campo": (x0, y0, x1, y1)
   donde (x0, y0) es la esquina inferior izquierda del cuadro de texto
   y (x1, y1) es la esquina superior derecha.
"""
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import simpleSplit


# =====================================================================
# COORDENADAS DE CAMPOS — valores de partida, AJÚSTALOS a tu plantilla
# real usando /doctor/plantilla/grid. (x0,y0)=esquina inf. izq.,
# (x1,y1)=esquina sup. der. del cuadro donde debe caer el texto.
# =====================================================================
COORDS_INFORME_EEG = {
    # --- Encabezado / datos del paciente (una línea) ---
    "nombre_paciente":   (50,  740, 400, 758),
    "rut_paciente":      (420, 740, 560, 758),
    "fecha_nacimiento":  (50,  718, 200, 736),
    "fecha_estudio":     (220, 718, 370, 736),
    "tipo_registro":     (390, 718, 560, 736),

    # --- Cuerpo del informe (multilínea, con auto-ajuste de tamaño) ---
    "tecnica":                (50, 640, 560, 700),
    "actividad_base":         (50, 560, 560, 630),
    "hallazgos":               (50, 440, 560, 550),
    "impresion_diagnostica":   (50, 340, 560, 430),
    "correlacion_clinica":     (50, 260, 560, 330),
    "conclusion":               (50, 160, 560, 250),
}

# Campos que se dibujan con salto de línea automático (párrafos largos).
# El resto se trata como una sola línea que se encoge si no cabe.
CAMPOS_MULTILINEA = {
    "tecnica", "actividad_base", "hallazgos",
    "impresion_diagnostica", "correlacion_clinica", "conclusion",
}

FUENTE = "Helvetica"


def _dibujar_campo_una_linea(c, texto, x0, y0, x1, y1, margen=3):
    """Dibuja texto en una sola línea, centrado verticalmente, encogiendo
    la fuente si el texto no cabe en el ancho disponible."""
    w = x1 - x0
    h = y1 - y0
    fs = 10.0
    while fs > 6 and c.stringWidth(texto, FUENTE, fs) > w - 2 * margen:
        fs -= 0.5
    c.setFont(FUENTE, fs)
    c.setFillColorRGB(0, 0, 0)
    y_pos = y0 + (h - fs) / 2
    c.drawString(x0 + margen, y_pos, texto)


def _dibujar_campo_multilinea(c, texto, x0, y0, x1, y1, margen=4):
    """Dibuja texto largo con salto de línea automático dentro del cuadro,
    encogiendo la fuente si hace falta para que quepa en el alto disponible."""
    w = x1 - x0
    h = y1 - y0
    fs = 9.5
    lh = fs * 1.35

    def _armar_lineas(tam_fuente):
        lineas = []
        for parrafo in texto.splitlines() or [""]:
            if not parrafo.strip():
                lineas.append("")
            else:
                lineas.extend(simpleSplit(parrafo, FUENTE, tam_fuente, w - 2 * margen) or [""])
        return lineas

    lineas = _armar_lineas(fs)
    while lineas and len(lineas) * lh > h - 2 * margen and fs > 6:
        fs -= 0.5
        lh = fs * 1.35
        lineas = _armar_lineas(fs)

    c.setFont(FUENTE, fs)
    c.setFillColorRGB(0, 0, 0)
    y_pos = y1 - margen - fs
    for linea in lineas:
        if y_pos < y0 + margen:
            break  # ya no cabe más texto en el cuadro
        c.drawString(x0 + margen, y_pos, linea)
        y_pos -= lh


def generar_informe_pdf(pdf_base_bytes: bytes, campos: dict) -> bytes:
    """
    Superpone 'campos' (dict nombre_campo -> texto) sobre la primera
    página de 'pdf_base_bytes', según COORDS_INFORME_EEG.
    Devuelve los bytes del PDF final.
    """
    reader_base = PdfReader(io.BytesIO(pdf_base_bytes))
    pagina_base = reader_base.pages[0]
    ancho = float(pagina_base.mediabox.width)
    alto = float(pagina_base.mediabox.height)

    buffer_overlay = io.BytesIO()
    c = rl_canvas.Canvas(buffer_overlay, pagesize=(ancho, alto))

    for nombre_campo, (x0, y0, x1, y1) in COORDS_INFORME_EEG.items():
        valor = str(campos.get(nombre_campo, "") or "").strip()
        if not valor:
            continue
        if nombre_campo in CAMPOS_MULTILINEA:
            _dibujar_campo_multilinea(c, valor, x0, y0, x1, y1)
        else:
            _dibujar_campo_una_linea(c, valor, x0, y0, x1, y1)

    c.save()
    buffer_overlay.seek(0)

    overlay_reader = PdfReader(buffer_overlay)
    writer = PdfWriter()
    for i, pagina in enumerate(reader_base.pages):
        if i == 0 and overlay_reader.pages:
            pagina.merge_page(overlay_reader.pages[0])
        writer.add_page(pagina)

    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()


def generar_pdf_con_grilla(pdf_base_bytes: bytes) -> bytes:
    """
    Devuelve el mismo PDF con una grilla roja de coordenadas dibujada
    encima (líneas cada 50pt + números), solo para CALIBRAR
    COORDS_INFORME_EEG visualmente. No usar para el informe final.
    """
    reader_base = PdfReader(io.BytesIO(pdf_base_bytes))
    pagina_base = reader_base.pages[0]
    ancho = float(pagina_base.mediabox.width)
    alto = float(pagina_base.mediabox.height)

    buffer_overlay = io.BytesIO()
    c = rl_canvas.Canvas(buffer_overlay, pagesize=(ancho, alto))
    c.setStrokeColorRGB(1, 0, 0)
    c.setFillColorRGB(1, 0, 0)
    c.setFont("Helvetica", 6)
    paso = 50

    x = 0
    while x <= ancho:
        c.line(x, 0, x, alto)
        c.drawString(x + 2, 4, str(int(x)))
        x += paso

    y = 0
    while y <= alto:
        c.line(0, y, ancho, y)
        c.drawString(2, y + 2, str(int(y)))
        y += paso

    c.save()
    buffer_overlay.seek(0)

    overlay_reader = PdfReader(buffer_overlay)
    writer = PdfWriter()
    for i, pagina in enumerate(reader_base.pages):
        if i == 0 and overlay_reader.pages:
            pagina.merge_page(overlay_reader.pages[0])
        writer.add_page(pagina)

    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()
