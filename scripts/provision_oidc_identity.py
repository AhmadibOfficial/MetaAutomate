#!/usr/bin/env python3
"""Explicit administrator provisioning for SSO identities.

Use ONLY after independently verifying OIDC issuer+subject with the provider.
Run in an ephemeral admin container; no privileged DB credentials in the API.
"""
import argparse
import hashlib
import os
import re
import sys

import psycopg


def main():
    parser = argparse.ArgumentParser(description="Provision a verified identity for a private MetaAutomate tenant")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization", required=True, help="Tenant slug, e.g. metaautomate-internal")
    parser.add_argument("--role", choices=["OWNER","ADMIN","OPERATOR","VIEWER"], default="OWNER")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve adding this identity")
    args = parser.parse_args()

    if not args.approve:
        parser.error("--approve is required before modifying the identity database")
    if (not args.issuer.startswith("https://") or len(args.issuer) > 512
            or not args.subject or len(args.subject) > 512):
        parser.error("Issuer must use HTTPS and subject must be an OIDC opaque identifier")
    configured_issuer = os.environ.get("OIDC_ISSUER", "").rstrip("/")
    if args.issuer.rstrip("/") != configured_issuer:
        parser.error("Issuer must exactly match the configured trusted OIDC_ISSUER")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,62}", args.organization):
        parser.error("Invalid organization slug")
    if "@" not in args.email or len(args.email) > 254:
        parser.error("Invalid email")

    digest=hashlib.sha256(args.subject.encode("utf-8")).hexdigest()
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT organization_id,user_id,status FROM oidc_identities "
                "WHERE issuer=%s AND subject_sha256=%s",
                (configured_issuer,digest),
            )
            previous=cur.fetchone()
            if previous:
                raise SystemExit("Identity already provisioned; refusing to retarget or silently reactivate it")
            cur.execute(
                "INSERT INTO organizations(slug,name) VALUES(%s,%s) "
                "ON CONFLICT(slug) DO UPDATE SET name=organizations.name RETURNING id",
                (args.organization,args.organization.replace("-"," ").title()),
            )
            org=cur.fetchone()[0]
            cur.execute(
                "INSERT INTO users(email,display_name) VALUES(%s,%s) "
                "ON CONFLICT(email) DO UPDATE SET display_name=users.display_name RETURNING id",
                (args.email,args.email.split("@")[0]),
            )
            user=cur.fetchone()[0]
            cur.execute("SELECT app.set_context(%s,%s)",(org,user))
            cur.execute(
                "INSERT INTO organization_memberships(organization_id,user_id,role,status) "
                "VALUES(%s,%s,%s,'ACTIVE') "
                "ON CONFLICT(organization_id,user_id) DO UPDATE SET "
                "role=EXCLUDED.role,status='ACTIVE'",
                (org,user,args.role),
            )
            cur.execute(
                "INSERT INTO oidc_identities(organization_id,user_id,issuer,subject_sha256) "
                "VALUES(%s,%s,%s,%s)",(org,user,configured_issuer,digest),
            )
    print("PASS: verified OIDC subject mapped to authorized tenant and user")
    print("Issuer:",configured_issuer)
    print("Organization:",args.organization)
    print("Role:",args.role)
    print("Raw OIDC subject was not printed or stored")


if __name__ == "__main__":
    main()
