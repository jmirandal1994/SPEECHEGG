# Plantillas PDF por doctor

Cada archivo en esta carpeta es la plantilla PDF base de UN doctor.

## Cómo agregar la plantilla de un doctor

1. Entra a `/admin/doctores/<id>/plantilla` en el sitio (o a la tabla de
   doctores en el dashboard admin) para ver el UUID exacto del doctor.
2. Nombra el archivo PDF exactamente así: `<uuid-del-doctor>.pdf`
   Ejemplo: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf`
3. Sube ese archivo a esta carpeta (`plantillas_pdf/`) en GitHub — igual
   que subes cualquier otro archivo del proyecto.
4. Haz commit y push. Cuando Vercel termine de desplegar, la plantilla
   va a estar disponible automáticamente para ese doctor.

## Nota técnica
El PDF debe ser de una sola página. El sistema superpone el contenido
del informe encima usando coordenadas fijas (ver `pdf_engine.py`).
