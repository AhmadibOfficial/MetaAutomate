"""P2-054 first-party multi-agent runtime: real offline execution acceptance.

Tests use stdlib unittest + a temporary SQLite DB; no accounts, model,
paid provider, external network, or customer data are accessed.
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app import owned_multiagent_runtime as engine


class OwnedRuntimeAcceptance(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.db=Path(self.dir.name)/"jobs.sqlite3"
        self.clock=[1_000_000.0]
        self.runtime=engine.Runtime(self.db,now=lambda:self.clock[0])
        self.payload=engine.demo_payload()
        self.tenant="retail_demo"
        self.key="stock-20261018-acceptance"
        self.actor="retail-owner-001"

    def tearDown(self):
        self.dir.cleanup()

    def submit(self,payload=None,key=None,budget=engine.REQUIRED_CREDITS):
        return self.runtime.submit(
            self.tenant,key or self.key,payload or self.payload,
            actor=self.actor,budget=budget
        )

    def test_end_to_end_four_agents_do_real_work(self):
        job=self.submit()
        self.assertEqual(self.runtime.work_until_idle(self.tenant),4)
        result=self.runtime.report(self.tenant,job)
        self.assertEqual(result["state"],"COMPLETED")
        self.assertEqual(result["spent_units"],6)
        self.assertEqual(result["budget_units"],6)
        self.assertTrue(all(s["state"]=="DONE" for s in result["stage_status"]))
        inventory=result["outputs"]["inventory"]
        business=result["outputs"]["business"]
        copy=result["outputs"]["creative"]
        audit=result["outputs"]["verifier"]
        self.assertEqual(inventory["rows"][0]["reorder_units"],13)
        self.assertEqual(inventory["rows"][1]["reorder_units"],0)
        self.assertEqual(business["estimated_replenishment_minor"],13*125000)
        self.assertEqual(business["existing_stock_minor"],
                         7*125000 + 25*78000)
        self.assertEqual(business["reorder_skus"],1)
        self.assertIn("1 product lines",copy["draft_message"])
        self.assertFalse(copy["publication_authorized"])
        self.assertEqual(audit["verification"],"PASS")
        self.assertEqual(audit["inventory_digest"],engine.digest(
            engine.canonical(inventory)))
        self.assertFalse(audit["neural_inference_performed"])
        chain=self.runtime.verify_evidence(self.tenant,job)
        self.assertTrue(chain["verified"])
        self.assertGreaterEqual(chain["events"],10)
        self.assertEqual(len(chain["final_sha256"]),64)
        self.assertEqual(result["third_party_model_calls"],0)
        self.assertEqual(result["paid_api_cost"],0)

    def test_durable_restart_and_replay_protection(self):
        job=self.submit()
        self.runtime.work_once(self.tenant)
        recovered=engine.Runtime(self.db,now=lambda:self.clock[0])
        self.assertEqual(recovered.submit(
            self.tenant,self.key,self.payload,actor=self.actor,budget=6),job)
        self.assertEqual(recovered.work_until_idle(self.tenant),3)
        self.assertEqual(recovered.report(self.tenant,job)["state"],"COMPLETED")
        changed=engine.demo_payload()
        changed["items"][0]["on_hand"]=0
        with self.assertRaisesRegex(ValueError,"Idempotency"):
            recovered.submit(self.tenant,self.key,changed,
                             actor=self.actor,budget=6)

    def test_tenant_bound_access_and_evidence(self):
        job=self.submit()
        self.runtime.work_until_idle()
        with self.assertRaises(KeyError):
            self.runtime.report("another_tenant",job)
        with self.assertRaises(KeyError):
            self.runtime.verify_evidence("another_tenant",job)

    def test_budget_and_input_policy_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"credits"):
            self.submit(budget=5)
        malformed=dict(self.payload)
        malformed["extra_connection_url"]="https://unknown.example/"
        with self.assertRaisesRegex(ValueError,"Unexpected input"):
            self.submit(payload=malformed)
        malformed=dict(self.payload)
        malformed["items"]=self.payload["items"]*41
        with self.assertRaisesRegex(ValueError,"80"):
            self.submit(payload=malformed)
        malformed=dict(self.payload)
        malformed["requested_external_action"]="MAKE_PAYMENT"
        with self.assertRaises(ValueError):
            self.submit(payload=malformed)
        self.assertIsNone(self.runtime.claim())

    def test_approval_requires_separate_human_but_still_never_executes(self):
        request=dict(self.payload)
        request["requested_external_action"]="ORDER_STOCK"
        job=self.submit(payload=request)
        self.assertEqual(self.runtime.work_until_idle(self.tenant),4)
        result=self.runtime.report(self.tenant,job)
        self.assertEqual(result["state"],"AWAITING_APPROVAL")
        self.assertEqual(result["external_approval"]["state"],"PENDING")
        with self.assertRaisesRegex(ValueError,"self-approve"):
            self.runtime.approval(
                self.tenant,job,self.actor,
                "Please buy these stock items now",True)
        approved=self.runtime.approval(
            self.tenant,job,"second_reviewer",
            "Cost estimates independently checked for the pilot",True)
        self.assertEqual(approved,"APPROVED_NOT_EXECUTED")
        result=self.runtime.report(self.tenant,job)
        self.assertEqual(result["state"],"APPROVED_NOT_EXECUTED")
        self.assertFalse(result["external_action_executed"])
        self.assertTrue(self.runtime.verify_evidence(self.tenant,job)["verified"])

    def test_independent_reviewer_can_reject(self):
        request=dict(self.payload)
        request["requested_external_action"]="PUBLISH_CAMPAIGN"
        job=self.submit(payload=request)
        self.runtime.work_until_idle()
        self.assertEqual(self.runtime.approval(
            self.tenant,job,"independent_reviewer",
            "The campaign claims require additional review",False),"REJECTED")
        self.assertFalse(self.runtime.report(self.tenant,job)["external_action_executed"])

    def test_retry_then_recover_after_transient_specialist_failure(self):
        original=engine.AGENTS["creative"]
        tries=[0]
        def transient(payload,context):
            tries[0]+=1
            if tries[0]==1:
                raise OSError("temporary offline failure")
            return original(payload,context)
        engine.AGENTS["creative"]=transient
        try:
            job=self.submit()
            self.assertEqual(self.runtime.work_until_idle(self.tenant),3)
            stages=self.runtime.report(self.tenant,job)["stage_status"]
            self.assertEqual(stages[2]["state"],"READY")
            self.assertEqual(stages[2]["attempts"],1)
            self.assertEqual(stages[2]["error"],"OSError")
            self.assertEqual(stages[3]["state"],"READY")
            self.clock[0]+=3
            self.assertEqual(self.runtime.work_until_idle(self.tenant),2)
            self.assertEqual(self.runtime.report(self.tenant,job)["state"],"COMPLETED")
            self.assertEqual(self.runtime.report(self.tenant,job)["spent_units"],6)
            self.assertEqual(tries[0],2)
        finally:
            engine.AGENTS["creative"]=original

    def test_dead_letter_after_third_failure(self):
        original=engine.AGENTS["creative"]
        engine.AGENTS["creative"]=lambda payload,context: (_ for _ in ()).throw(
            RuntimeError("synthetic specialist test failure"))
        try:
            job=self.submit()
            for _ in range(3):
                self.runtime.work_until_idle(self.tenant)
                self.clock[0]+=100
            report=self.runtime.report(self.tenant,job)
            self.assertEqual(report["state"],"FAILED")
            self.assertEqual(report["stage_status"][2]["state"],"DEAD")
            self.assertEqual(report["stage_status"][2]["attempts"],3)
            self.assertEqual(report["spent_units"],3)
            self.assertTrue(self.runtime.verify_evidence(self.tenant,job)["verified"])
        finally:
            engine.AGENTS["creative"]=original

    def test_competing_workers_cannot_claim_same_active_task(self):
        job=self.submit()
        competing=engine.Runtime(self.db,now=lambda:self.clock[0])
        first=self.runtime.claim(self.tenant)
        self.assertEqual(first["run_id"],job)
        self.assertIsNone(competing.claim(self.tenant))
        result,sha=self.runtime._run_agent(first)
        self.runtime._settle(first,result,sha,None)
        second=competing.claim(self.tenant)
        self.assertEqual(second["seq"],1)
        self.assertNotEqual(first["claim_id"],second["claim_id"])
        self.assertIsNone(self.runtime.claim(self.tenant))

    def test_expired_worker_lease_reclaims_task_and_rejects_stale_result(self):
        job=self.submit()
        old=self.runtime.claim(self.tenant)
        self.assertEqual(old["seq"],0)
        self.clock[0]+=engine.LEASE_SECONDS+1
        new=self.runtime.claim(self.tenant)
        self.assertEqual(new["seq"],0)
        self.assertNotEqual(new["claim_id"],old["claim_id"])
        with self.assertRaisesRegex(ValueError,"Stale worker lease"):
            self.runtime._settle(old,"{}",engine.digest(b"{}"),None)
        output,checksum=self.runtime._run_agent(new)
        self.runtime._settle(new,output,checksum,None)
        self.assertEqual(self.runtime.work_until_idle(self.tenant),3)
        self.assertEqual(self.runtime.report(self.tenant,job)["state"],"COMPLETED")

    def test_integrity_validation_detects_tampering(self):
        job=self.submit()
        self.runtime.work_until_idle(self.tenant)
        with self.runtime.txn() as db:
            db.execute("UPDATE steps SET output_json='{}' "
                       "WHERE run_id=? AND seq=0",(job,))
        with self.assertRaisesRegex(ValueError,"integrity"):
            self.runtime.report(self.tenant,job)
        with self.runtime.txn() as db:
            db.execute("UPDATE evidence SET body='{}' "
                       "WHERE run_id=? AND id=(SELECT min(id) FROM evidence WHERE run_id=?)",
                       (job,job))
        self.assertFalse(self.runtime.verify_evidence(self.tenant,job)["verified"])

    def test_local_cli_generates_actual_durable_artifact_and_enforces_consent(self):
        script=Path(__file__).resolve().parents[1]/"scripts"/"run_owned_multiagent_demo.py"
        report=Path(self.dir.name)/"report.json"
        cmd=[sys.executable,str(script),"--db",str(self.db),
             "--tenant","demo_cli","--request-key","cli-20261018-unique",
             "--output",str(report)]
        first=subprocess.run(cmd,capture_output=True,text=True,check=True)
        receipt=json.loads(first.stdout)
        self.assertEqual(receipt["state"],"COMPLETED")
        self.assertEqual(receipt["agents_completed"],4)
        self.assertTrue(receipt["evidence_chain_valid"])
        self.assertEqual(receipt["paid_provider_calls"],0)
        data=json.loads(report.read_text())
        self.assertEqual(data["run"]["outputs"]["verifier"]["verification"],"PASS")
        second=subprocess.run(cmd,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(second.stdout)["run_id"],receipt["run_id"])
        user_input=Path(self.dir.name)/"user.json"
        user_input.write_text(json.dumps(self.payload))
        unauthorized=subprocess.run(
            cmd+["--input-json",str(user_input)],
            capture_output=True,text=True)
        self.assertNotEqual(unauthorized.returncode,0)
        self.assertIn("--authorized-data",unauthorized.stderr)

    def test_interop_markers_do_not_claim_full_protocol_support(self):
        manifest=engine.agent_manifest()
        self.assertFalse(manifest["a2a_protocol_implemented"])
        self.assertFalse(manifest["mcp_network_server_implemented"])
        self.assertEqual([x["id"] for x in manifest["agents"]],
                         list(engine.AGENT_ORDER))
        descriptors=engine.mcp_tool_descriptors()
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in descriptors))
        self.assertTrue(all(t["inputSchema"]["type"]=="object" for t in descriptors))


if __name__=="__main__":
    unittest.main()
