-- Fictional, ephemeral CI-only tenant isolation data. Not a production migration.
\set ON_ERROR_STOP on

CREATE ROLE ci_academy LOGIN PASSWORD 'ci_dummy_academy_only' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE ci_bespoke LOGIN PASSWORD 'ci_dummy_bespoke_only' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE TABLE public.synthetic_stage_events (
    tenant_role TEXT NOT NULL,
    workspace TEXT NOT NULL,
    note TEXT NOT NULL,
    CHECK (tenant_role IN ('ci_academy','ci_bespoke')),
    CHECK (workspace IN ('academy_demo','bespoke_demo'))
);

INSERT INTO public.synthetic_stage_events (tenant_role,workspace,note) VALUES
    ('ci_academy','academy_demo','FICTIONAL_01'),
    ('ci_bespoke','bespoke_demo','FICTIONAL_02');

REVOKE ALL ON public.synthetic_stage_events FROM PUBLIC;
GRANT SELECT,INSERT ON public.synthetic_stage_events TO ci_academy,ci_bespoke;
ALTER TABLE public.synthetic_stage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.synthetic_stage_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_role_self ON public.synthetic_stage_events
   FOR ALL TO ci_academy,ci_bespoke
   USING (tenant_role = CURRENT_USER)
   WITH CHECK (tenant_role = CURRENT_USER);
