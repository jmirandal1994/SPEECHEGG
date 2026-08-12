-- =====================================================================
-- Migración 002: rol 'coordinadora' + jornadas asignadas por doctor
-- Corre esto en Supabase → SQL Editor (una sola vez)
-- =====================================================================

-- 1) Permitir el nuevo rol en profiles
alter table public.profiles drop constraint if exists profiles_rol_check;
alter table public.profiles add constraint profiles_rol_check
    check (rol in ('admin', 'doctor', 'coordinadora'));

-- 2) Función auxiliar, igual que es_admin()
create or replace function public.es_coordinadora()
returns boolean
language sql
security definer
stable
as $$
    select exists (
        select 1 from public.profiles
        where id = auth.uid() and rol = 'coordinadora'
    );
$$;

-- 3) Tabla de jornadas asignadas (qué día le toca informar a cada doctor)
create table if not exists public.jornadas (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references public.profiles(id) on delete cascade,
    fecha date not null,
    created_at timestamptz not null default now(),
    unique (doctor_id, fecha)
);
create index if not exists idx_jornadas_doctor_fecha on public.jornadas(doctor_id, fecha);

alter table public.jornadas enable row level security;

drop policy if exists "jornadas_select" on public.jornadas;
create policy "jornadas_select" on public.jornadas
    for select using (public.es_admin() or doctor_id = auth.uid());

drop policy if exists "jornadas_insert_admin" on public.jornadas;
create policy "jornadas_insert_admin" on public.jornadas
    for insert with check (public.es_admin());

drop policy if exists "jornadas_delete_admin" on public.jornadas;
create policy "jornadas_delete_admin" on public.jornadas
    for delete using (public.es_admin());

-- 4) La coordinadora necesita VER (no editar) informes, estudios y
--    pacientes, para poder listar y descargar los informes del día.
drop policy if exists "informes_select" on public.informes;
create policy "informes_select" on public.informes
    for select using (public.es_admin() or public.es_coordinadora() or doctor_id = auth.uid());

drop policy if exists "estudios_select" on public.estudios_eeg;
create policy "estudios_select" on public.estudios_eeg
    for select using (public.es_admin() or public.es_coordinadora() or doctor_id = auth.uid());

drop policy if exists "pacientes_select" on public.pacientes;
create policy "pacientes_select" on public.pacientes
    for select using (public.es_admin() or public.es_coordinadora() or doctor_asignado_id = auth.uid());
