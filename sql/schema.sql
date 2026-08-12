-- =====================================================================
-- Speech Psychology · Sistema de Informes EEG
-- Esquema inicial de base de datos (Supabase / Postgres)
-- =====================================================================
-- Cómo aplicarlo: Supabase Dashboard → SQL Editor → pegar y ejecutar
-- (o vía Supabase CLI: supabase db push)
-- =====================================================================

-- Extensión para generar UUIDs
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- 1) PROFILES — extiende auth.users con datos de doctor/admin
-- ---------------------------------------------------------------------
create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    nombre text not null,
    rol text not null check (rol in ('admin', 'doctor', 'coordinadora')),
    especialidad text,
    activo boolean not null default true,
    created_at timestamptz not null default now()
);

comment on table public.profiles is 'Perfil de cada usuario (doctor o admin), 1:1 con auth.users';

-- ---------------------------------------------------------------------
-- 2) PACIENTES
-- ---------------------------------------------------------------------
create table public.pacientes (
    id uuid primary key default gen_random_uuid(),
    nombre_completo text not null,
    rut text,
    fecha_nacimiento date,
    sexo text check (sexo in ('M', 'F', 'Otro')),
    telefono text,
    email text,
    doctor_asignado_id uuid references public.profiles(id) on delete set null,
    origen text not null default 'manual' check (origen in ('excel', 'manual')),
    creado_por uuid references public.profiles(id),
    created_at timestamptz not null default now()
);

create index idx_pacientes_doctor on public.pacientes(doctor_asignado_id);

-- ---------------------------------------------------------------------
-- 3) ESTUDIOS EEG — cada examen/registro de un paciente
-- ---------------------------------------------------------------------
create table public.estudios_eeg (
    id uuid primary key default gen_random_uuid(),
    paciente_id uuid not null references public.pacientes(id) on delete cascade,
    doctor_id uuid references public.profiles(id) on delete set null,
    fecha_estudio date not null default current_date,
    tipo_registro text check (tipo_registro in ('vigilia', 'sueno', 'privacion_sueno', 'video_eeg', 'ambulatorio')),
    estado text not null default 'pendiente' check (estado in ('pendiente', 'en_proceso', 'informado')),
    archivo_registro_url text,
    created_at timestamptz not null default now()
);

create index idx_estudios_doctor on public.estudios_eeg(doctor_id);
create index idx_estudios_estado on public.estudios_eeg(estado);

-- ---------------------------------------------------------------------
-- 4) PLANTILLAS PDF — una plantilla base por doctor
-- ---------------------------------------------------------------------
create table public.plantillas_pdf (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null unique references public.profiles(id) on delete cascade,
    nombre_archivo text not null,
    url_pdf_base text not null,
    actualizado_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 5) INFORMES — contenido clínico + PDF final
-- ---------------------------------------------------------------------
create table public.informes (
    id uuid primary key default gen_random_uuid(),
    estudio_id uuid not null references public.estudios_eeg(id) on delete cascade,
    doctor_id uuid references public.profiles(id),
    tecnica text,
    actividad_base text,
    hallazgos text,
    impresion_diagnostica text,
    correlacion_clinica text,
    conclusion text,
    pdf_generado_url text,
    marcado_informado boolean not null default false,
    fecha_informe timestamptz,
    created_at timestamptz not null default now()
);

create index idx_informes_doctor on public.informes(doctor_id);
create index idx_informes_marcado on public.informes(marcado_informado);
alter table public.informes add constraint informes_estudio_id_unique unique (estudio_id);

-- ---------------------------------------------------------------------
-- 6) CORRECCIONES — flujo doctor <-> admin
-- ---------------------------------------------------------------------
create table public.correcciones (
    id uuid primary key default gen_random_uuid(),
    informe_id uuid not null references public.informes(id) on delete cascade,
    solicitado_por uuid references public.profiles(id),
    motivo text not null,
    estado text not null default 'pendiente' check (estado in ('pendiente', 'resuelta')),
    respuesta_admin text,
    resuelto_por uuid references public.profiles(id),
    created_at timestamptz not null default now(),
    resolved_at timestamptz
);

-- ---------------------------------------------------------------------
-- 7) PRESENCIA — estado en vivo de cada usuario
-- ---------------------------------------------------------------------
create table public.presencia (
    usuario_id uuid primary key references public.profiles(id) on delete cascade,
    estado text not null default 'offline' check (estado in ('online', 'informando', 'offline')),
    ultima_actividad timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 8) CARGAS EXCEL — bitácora de subidas masivas de pacientes
-- ---------------------------------------------------------------------
create table public.cargas_excel (
    id uuid primary key default gen_random_uuid(),
    admin_id uuid references public.profiles(id),
    archivo_nombre text,
    cantidad_registros integer not null default 0,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 9) JORNADAS — días asignados a cada doctor para informar
-- ---------------------------------------------------------------------
create table public.jornadas (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references public.profiles(id) on delete cascade,
    fecha date not null,
    created_at timestamptz not null default now(),
    unique (doctor_id, fecha)
);
create index idx_jornadas_doctor_fecha on public.jornadas(doctor_id, fecha);

-- =====================================================================
-- ROW LEVEL SECURITY
-- Regla general: doctor ve/edita solo lo suyo. Admin ve/edita todo.
-- =====================================================================

alter table public.profiles enable row level security;
alter table public.pacientes enable row level security;
alter table public.estudios_eeg enable row level security;
alter table public.plantillas_pdf enable row level security;
alter table public.informes enable row level security;
alter table public.correcciones enable row level security;
alter table public.presencia enable row level security;
alter table public.cargas_excel enable row level security;
alter table public.jornadas enable row level security;

-- Función auxiliar: ¿el usuario actual es admin?
create or replace function public.es_admin()
returns boolean
language sql
security definer
stable
as $$
    select exists (
        select 1 from public.profiles
        where id = auth.uid() and rol = 'admin'
    );
$$;

-- Función auxiliar: ¿el usuario actual es la coordinadora?
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

-- profiles: cualquier usuario autenticado puede ver todos los perfiles
-- (se necesita para mostrar nombres de doctores), pero solo admin edita.
create policy "profiles_select_authenticated" on public.profiles
    for select using (auth.role() = 'authenticated');
create policy "profiles_update_admin_o_propio" on public.profiles
    for update using (public.es_admin() or id = auth.uid());
create policy "profiles_insert_admin" on public.profiles
    for insert with check (public.es_admin());

-- pacientes: doctor ve los suyos, admin y coordinadora ven todos
create policy "pacientes_select" on public.pacientes
    for select using (public.es_admin() or public.es_coordinadora() or doctor_asignado_id = auth.uid());
create policy "pacientes_insert" on public.pacientes
    for insert with check (public.es_admin() or doctor_asignado_id = auth.uid());
create policy "pacientes_update" on public.pacientes
    for update using (public.es_admin() or doctor_asignado_id = auth.uid());

-- estudios_eeg: mismo criterio via doctor_id
create policy "estudios_select" on public.estudios_eeg
    for select using (public.es_admin() or public.es_coordinadora() or doctor_id = auth.uid());
create policy "estudios_insert" on public.estudios_eeg
    for insert with check (public.es_admin() or doctor_id = auth.uid());
create policy "estudios_update" on public.estudios_eeg
    for update using (public.es_admin() or doctor_id = auth.uid());

-- plantillas_pdf: doctor ve/edita la suya, admin todas
create policy "plantillas_select" on public.plantillas_pdf
    for select using (public.es_admin() or doctor_id = auth.uid());
create policy "plantillas_upsert" on public.plantillas_pdf
    for insert with check (public.es_admin() or doctor_id = auth.uid());
create policy "plantillas_update" on public.plantillas_pdf
    for update using (public.es_admin() or doctor_id = auth.uid());

-- informes: doctor ve/edita los suyos, admin y coordinadora ven todos (coordinadora solo lectura)
create policy "informes_select" on public.informes
    for select using (public.es_admin() or public.es_coordinadora() or doctor_id = auth.uid());
create policy "informes_insert" on public.informes
    for insert with check (public.es_admin() or doctor_id = auth.uid());
create policy "informes_update" on public.informes
    for update using (public.es_admin() or doctor_id = auth.uid());

-- correcciones: doctor ve las que solicitó, admin ve todas
create policy "correcciones_select" on public.correcciones
    for select using (public.es_admin() or solicitado_por = auth.uid());
create policy "correcciones_insert" on public.correcciones
    for insert with check (solicitado_por = auth.uid() or public.es_admin());
create policy "correcciones_update_admin" on public.correcciones
    for update using (public.es_admin());

-- presencia: todos los autenticados pueden leer (para el panel en vivo del admin),
-- cada usuario solo puede escribir su propia fila
create policy "presencia_select_authenticated" on public.presencia
    for select using (auth.role() = 'authenticated');
create policy "presencia_upsert_propio" on public.presencia
    for insert with check (usuario_id = auth.uid());
create policy "presencia_update_propio" on public.presencia
    for update using (usuario_id = auth.uid());

-- cargas_excel: solo admin
create policy "cargas_excel_admin" on public.cargas_excel
    for all using (public.es_admin());

-- jornadas: doctor ve las suyas, admin ve/asigna todas
create policy "jornadas_select" on public.jornadas
    for select using (public.es_admin() or doctor_id = auth.uid());
create policy "jornadas_insert_admin" on public.jornadas
    for insert with check (public.es_admin());
create policy "jornadas_delete_admin" on public.jornadas
    for delete using (public.es_admin());

-- =====================================================================
-- Trigger: crear fila en profiles automáticamente al crear un usuario
-- en auth.users (el rol/nombre se completa luego desde el panel admin)
-- =====================================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
    insert into public.profiles (id, nombre, rol)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'nombre', new.email),
        coalesce(new.raw_user_meta_data->>'rol', 'doctor')
    );
    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
