#!/usr/bin/env python3
"""Real Chromium end-to-end test: login, create, graph, approve, revisit, logout.

Runs only against ephemeral GitHub Actions PostgreSQL.
"""
import hashlib
import os
from pathlib import Path
import secrets
from uuid import uuid4
import psycopg
from playwright.sync_api import sync_playwright, expect

BASE="http://127.0.0.1:8089"

def issue_test_identity():
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Browser test is CI-only: no changes to a user's main database")
    key="mat_dev_"+secrets.token_urlsafe(32)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO organizations(slug,name) VALUES(%s,'Chromium Browser CI') RETURNING id",
                        ("workspace-ci-"+uuid4().hex,))
            org=cur.fetchone()[0]
            cur.execute("INSERT INTO users(email,display_name) VALUES(%s,'Browser Test Owner') RETURNING id",
                        (uuid4().hex+"@example.invalid",))
            user=cur.fetchone()[0]
            cur.execute("SELECT app.set_context(%s,%s)",(org,user))
            cur.execute("INSERT INTO organization_memberships(organization_id,user_id,role) VALUES(%s,%s,'OWNER')",
                        (org,user))
            cur.execute(
                "INSERT INTO api_access_tokens(organization_id,user_id,token_sha256,label,expires_at) "
                "VALUES(%s,%s,%s,'browser-ci',now()+interval '1 day')",
                (org,user,hashlib.sha256(key.encode("ascii")).hexdigest()))
    return key,org

def main():
    key,org=issue_test_identity()
    screenshots=Path("artifacts")
    screenshots.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1440,"height":960},base_url=BASE)
        page=context.new_page()
        page.goto("/")
        expect(page.locator(".auth-story .brand-logo")).to_be_visible()
        expect(page.locator(".auth-message h1")).to_contain_text("Turn Your Vision")
        expect(page.locator("#login-view")).to_be_visible(timeout=15000)
        expect(page.locator("#workspace-shell")).to_be_hidden()
        page.locator("#login-key").fill(key)
        page.locator("#login-submit").click()
        expect(page.locator("#overview-view")).to_be_visible(timeout=15000)
        expect(page.locator("#metric-total")).to_have_text("0")
        expect(page.locator("#brand-purpose-title")).to_contain_text("impact.")
        page.locator(".create-trigger").first.click()
        expect(page.locator("#create-view")).to_be_visible()
        expect(page.locator('#capability-picker input:checked')).to_have_count(2)
        page.locator("#objective-title").fill("Increase qualified customer appointments")
        page.locator("#objective-description").fill("Improve the sales pipeline with a non-executing plan.")
        page.locator("#criterion-metric").fill("qualified appointments")
        page.locator("#criterion-target").fill("20")
        page.locator("#objective-constraints").fill("Contact only opted-in leads")
        page.locator("#create-submit").click()
        expect(page.locator("#detail-view")).to_be_visible(timeout=15000)
        expect(page.locator("#detail-title")).to_have_text("Increase qualified customer appointments")
        expect(page.locator(".graph-node")).to_have_count(5)
        expect(page.locator("#detail-review-state")).to_have_text("Pending")
        page.screenshot(path=str(screenshots/"objective-workspace.png"),full_page=True)
        objective_url=page.url
        page.locator("#review-reason").fill("Approved for planning review, not execution.")
        page.locator("#approve-plan").click()
        expect(page.locator("#detail-review-state")).to_have_text("Approved")
        expect(page.locator("#review-form")).to_be_hidden()
        page.reload()
        expect(page.locator("#detail-view")).to_be_visible(timeout=15000)
        expect(page.locator("#detail-review-state")).to_have_text("Approved")
        expect(page.locator(".graph-node")).to_have_count(5)
        page.locator("#back-to-overview").click()
        expect(page.locator("#metric-total")).to_have_text("1")
        expect(page.locator("#metric-approved")).to_have_text("1")
        page.locator("#logout-button").click()
        expect(page.locator("#login-view")).to_be_visible()
        expect(page.locator("#workspace-shell")).to_be_hidden()
        # The restricted cookie session is invalid after logout, including reload.
        page.goto(objective_url)
        expect(page.locator("#login-view")).to_be_visible()
        context.close()
        browser.close()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM objectives WHERE organization_id=%s",(org,))
            assert cur.fetchone()[0]==1
            cur.execute("SELECT count(*) FROM agent_runs")
            assert cur.fetchone()[0]==0
            cur.execute("SELECT count(*) FROM capability_executions")
            assert cur.fetchone()[0]==0
    print("PASS: Chromium sign-in, objective submission, saved DAG, review, return visit, logout; no execution")

if __name__=="__main__":
    main()
