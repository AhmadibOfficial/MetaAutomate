"""P2-054 in-process MCP/A2A compatibility boundaries, no network calls."""
import json
import tempfile
import unittest
from pathlib import Path

from app.owned_multiagent_runtime import Runtime,demo_payload
from app.owned_agent_interop import (
    private_mcp_dispatch,a2a_task_view,catalog
)

META={"io.modelcontextprotocol/protocolVersion":"2026-07-28",
      "io.modelcontextprotocol/clientCapabilities":{},
      "io.modelcontextprotocol/clientInfo":{
          "name":"MetaAutomate local test caller","version":"1.0.0"
      }}

class Interop(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.run=Runtime(Path(self.tmp.name)/"agents.sqlite3")
        self.tenant="demo_tenant"
        self.id=self.run.submit(self.tenant,"interoperability-20261018",
                                demo_payload(),actor="test_owner",budget=6)
        self.run.work_until_idle(self.tenant)
    def tearDown(self):self.tmp.cleanup()

    def msg(self,method,params):
        return {"jsonrpc":"2.0","id":7,"method":method,"params":params}

    def call(self,msg,tenant="demo_tenant",authenticated=True):
        return private_mcp_dispatch(msg,self.run,trusted_tenant=tenant,
                                    authenticated=authenticated)

    def test_tool_list_is_read_only_and_no_action_discovery(self):
        result=self.call(self.msg("tools/list",{"_meta":META}))
        self.assertEqual(result["result"]["resultType"],"complete")
        names=[x["name"] for x in result["result"]["tools"]]
        self.assertEqual(names,["metaautomate.get_run",
                                "metaautomate.verify_evidence"])
        self.assertTrue(all(t["annotations"]["readOnlyHint"]
                            for t in result["result"]["tools"]))
        self.assertNotIn("purchase",str(result).lower())

    def test_verified_run_and_evidence_are_real(self):
        params={"_meta":META,"name":"metaautomate.get_run",
                "arguments":{"run_id":self.id}}
        result=self.call(self.msg("tools/call",params))
        self.assertFalse(result["result"]["isError"])
        content=json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(content["state"],"COMPLETED")
        self.assertEqual(content["outputs"]["verifier"]["verification"],"PASS")
        params["name"]="metaautomate.verify_evidence"
        evidence=json.loads(self.call(self.msg("tools/call",params))[
            "result"]["content"][0]["text"])
        self.assertTrue(evidence["verified"])
        self.assertGreater(evidence["events"],1)

    def test_cross_tenant_denied(self):
        result=self.call(self.msg("tools/call",{
            "_meta":META,"name":"metaautomate.get_run",
            "arguments":{"run_id":self.id}
        }),tenant="other_tenant")
        self.assertEqual(result["error"]["code"],-32004)

    def test_never_act_on_untrusted_model_tool_name(self):
        result=self.call(self.msg("tools/call",{
            "_meta":META,"name":"metaautomate.purchase_stock",
            "arguments":{"run_id":self.id}
        }))
        self.assertEqual(result["error"]["code"],-32601)

    def test_no_unauthenticated_external_calls(self):
        result=self.call(self.msg("tools/list",{"_meta":META}),
                         authenticated=False)
        self.assertEqual(result["error"]["code"],-32600)
        missing_meta=self.call(self.msg("tools/list",{}))
        self.assertEqual(missing_meta["error"]["code"],-32602)
        forged_tenant=self.call(self.msg("tools/call",{
            "_meta":META,"name":"metaautomate.get_run",
            "arguments":{"run_id":self.id,"tenant":"other_tenant"}
        }))
        self.assertEqual(forged_tenant["error"]["code"],-32602)

    def test_task_snapshot_maps_state_without_claiming_remote_support(self):
        payload=a2a_task_view(self.run,self.tenant,self.id)
        self.assertEqual(payload["status"]["state"],"completed")
        self.assertEqual(len(payload["artifacts"]),4)
        self.assertFalse(payload["metaautomate"]["a2a_wire_protocol_implemented"])
        self.assertFalse(payload["metaautomate"]["external_action_executed"])


if __name__=="__main__":
    unittest.main()
