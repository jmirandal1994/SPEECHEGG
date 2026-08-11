-- =====================================================================
-- Migración: agrega restricción única a informes.estudio_id
-- Solo necesario si ya habías corrido schema.sql ANTES de este cambio
-- (un informe por estudio EEG — permite usar upsert al generar el PDF)
-- =====================================================================
alter table public.informes add constraint informes_estudio_id_unique unique (estudio_id);
