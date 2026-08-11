-- =====================================================================
-- Speech Psychology · Buckets de Storage para PDFs
-- Corre esto en Supabase → SQL Editor, DESPUÉS de schema.sql
-- =====================================================================

-- Bucket para las plantillas PDF base de cada doctor (privado)
insert into storage.buckets (id, name, public)
values ('plantillas-pdf', 'plantillas-pdf', false)
on conflict (id) do nothing;

-- Bucket para los informes PDF ya generados (privado)
insert into storage.buckets (id, name, public)
values ('informes-pdf', 'informes-pdf', false)
on conflict (id) do nothing;

-- Nota: el acceso a estos buckets pasa siempre por el backend de Flask
-- usando la service role key (ver storage_helpers.py), así que no se
-- necesitan políticas RLS adicionales en storage.objects — el control
-- de acceso real lo hacen las rutas @requiere_login / @requiere_admin.
