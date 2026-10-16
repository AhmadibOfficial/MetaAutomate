#!/bin/sh
# Ephemeral GitHub Actions Docker fixture. No private staging or real data.
set -eu

test "$(id -u)" -ne 0 || { echo "FAILED: worker is root"; exit 1; }
test ! -e /var/run/docker.sock || { echo "FAILED: Docker control mounted"; exit 1; }
test ! -d /run/secrets || { echo "FAILED: secrets mounted"; exit 1; }

# Docker internal network permits sealed database access, but NOT a default route.
if awk 'NR>1 && $2=="00000000" { found=1 } END { exit found ? 0 : 1 }' /proc/net/route; then
  echo "FAILED: worker has a default IPv4 route"; exit 1
fi
if [ -f /proc/net/ipv6_route ] && awk '($1=="00000000000000000000000000000000" && $2=="00") { found=1 } END { exit found ? 0 : 1 }' /proc/net/ipv6_route; then
  echo "FAILED: worker has a default IPv6 route"; exit 1
fi
if ( touch /forbidden-rehearsal-write ) 2>/dev/null; then
  echo "FAILED: container root FS is writable"; exit 1
fi

export PGHOST=postgres
export PGDATABASE=f05_ci_rehearsal
export PGCONNECT_TIMEOUT=3
export PGOPTIONS='-c row_security=on'

export PGUSER=ci_academy PGPASSWORD=ci_dummy_academy_only
academy="$(psql -v ON_ERROR_STOP=1 -Atqc 'SELECT workspace FROM public.synthetic_stage_events ORDER BY workspace')"
[ "$academy" = "academy_demo" ] || { echo "FAILED: Academy tenant escape"; exit 1; }
academy_count="$(psql -v ON_ERROR_STOP=1 -Atqc 'SELECT count(*) FROM public.synthetic_stage_events')"
[ "$academy_count" = "1" ] || { echo "FAILED: Academy saw other tenant"; exit 1; }

export PGUSER=ci_bespoke PGPASSWORD=ci_dummy_bespoke_only
bespoke="$(psql -v ON_ERROR_STOP=1 -Atqc 'SELECT workspace FROM public.synthetic_stage_events ORDER BY workspace')"
[ "$bespoke" = "bespoke_demo" ] || { echo "FAILED: Bespoke tenant escape"; exit 1; }
bespoke_count="$(psql -v ON_ERROR_STOP=1 -Atqc 'SELECT count(*) FROM public.synthetic_stage_events')"
[ "$bespoke_count" = "1" ] || { echo "FAILED: Bespoke saw other tenant"; exit 1; }

# A distinct signed-in tenant role may not become the other tenant.
if psql -v ON_ERROR_STOP=1 -Atqc 'SET ROLE ci_academy' >/dev/null 2>&1; then
  echo "FAILED: tenant role escalation"; exit 1
fi
if psql -v ON_ERROR_STOP=1 -Atqc "INSERT INTO public.synthetic_stage_events VALUES ('ci_academy','academy_demo','FOREIGN_WRITE')" >/dev/null 2>&1; then
  echo "FAILED: RLS blocked-tenant insert succeeded"; exit 1
fi

# A sealed worker must be unable to reach a public IP; together with the
# no-default-route assertions this rules out ordinary Internet egress.
export PGHOST=1.1.1.1
if psql -v ON_ERROR_STOP=1 -Atqc 'SELECT 1' >/dev/null 2>&1; then
  echo "FAILED: public network connection succeeded"; exit 1
fi

echo "PASS F05: two fictional tenants isolated by forced RLS; role escalation and foreign writes denied"
echo "PASS F05: nonroot readonly worker, no default network route, no public IP connectivity"
echo "SOURCE REHEARSAL ONLY: no private staging host, true workforce SSO, customer data, offhost backup, or live agent"
