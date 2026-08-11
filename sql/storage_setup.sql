-- =====================================================================
-- Speech Psychology · Bucket de Storage para informes generados
-- Corre esto en Supabase → SQL Editor, DESPUÉS de schema.sql
-- =====================================================================
-- Nota: las plantillas PDF de cada doctor YA NO usan Storage — viven
-- directo en el repo de GitHub (carpeta plantillas_pdf/), así que solo
-- necesitamos un bucket para los informes ya generados (PDFs dinámicos,
-- uno por paciente, que sí necesitan persistir más allá de una sola
-- ejecución de la función serverless).

insert into storage.buckets (id, name, public)
values ('informes-pdf', 'informes-pdf', false)
on conflict (id) do nothing;

-- El acceso a este bucket pasa siempre por el backend de Flask usando
-- la service role key (ver storage_helpers.py), así que no se necesitan
-- políticas RLS adicionales en storage.objects — el control de acceso
-- real lo hacen las rutas @requiere_login / @requiere_admin.
