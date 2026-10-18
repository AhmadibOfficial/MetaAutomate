"""P2-054: first-party MCP/A2A in-process interoperability boundary.

MCP 2026-07-28 style request/result envelopes for two approved read-only
tools. A2A-inspired task status mapping and skill metadata. Neither opens
a network listener, processes third-party credentials, nor claims full remote
MCP/A2A protocol compliance (streaming, negotiation, auth, transports).
A future authenticated host must inject the trusted tenant independently.
"""
from __future__ import annotations

from uuid import UUID

from .owned_multiagent_runtime import Runtime, canonical, mcp_tool_descriptors

def _err(ident,code:int,message:str)->dict:
    return {"jsonrpc":"2.0","id":ident,
            "error":{"code":code,"message":message}}

def catalog()->list[dict]:
    tools=list(mcp_tool_descriptors())
    tools.extend([
        {"name":"metaautomate.get_run",
         "title":"Get Verified Workflow",
         "description":"Read one tenant workflow with artifact checks.",
         "inputSchema":{
             "type":"object","properties":{"run_id":{"type":"string","format":"uuid"}},
             "required":["run_id"],"additionalProperties":False,
         },
         "annotations":{"readOnlyHint":True,"destructiveHint":False}},
        {"name":"metaautomate.verify_evidence",
         "title":"Verify Task Evidence",
         "description":"Verify hash chain from tenant workflow events.",
         "inputSchema":{
             "type":"object","properties":{"run_id":{"type":"string","format":"uuid"}},
             "required":["run_id"],"additionalProperties":False,
         },
         "annotations":{"readOnlyHint":True,"destructiveHint":False}},
    ])
    return tools

def private_mcp_dispatch(
    request:dict,runtime:Runtime,*,trusted_tenant:str,
    authenticated:bool,
)->dict:
    """Do not export as unauthenticated HTTP. Reject all action tool calls.

    The _meta field is required by MCP 2026-07-28; this in-process method
    does not constitute a complete MCP server.
    """
    if type(request) is not dict:
        return _err(None,-32600,"Invalid request object")
    ident=request.get("id")
    if (request.get("jsonrpc")!="2.0" or type(ident) not in (str,int)
        or request.get("method") not in ("tools/list","tools/call")
        or not authenticated or not trusted_tenant):
        return _err(ident,-32600,"Invalid or unauthenticated MCP request")
    params=request.get("params")
    if type(params) is not dict:
        return _err(ident,-32602,"Invalid params")
    meta=params.get("_meta")
    if (type(meta) is not dict or
        type(meta.get("io.modelcontextprotocol/clientInfo")) is not dict or
        not meta.get("io.modelcontextprotocol/clientInfo",{}).get("name")):
        return _err(ident,-32602,"Client metadata required")
    if request["method"]=="tools/list":
        if set(params)!={"_meta"}:
            return _err(ident,-32602,"Unsupported tools/list params")
        # Only supported read-only tool names are advertised by this RPC.
        available=[t for t in catalog()
                   if t["name"] in ("metaautomate.get_run",
                                     "metaautomate.verify_evidence")]
        return {"jsonrpc":"2.0","id":ident,
                "result":{"resultType":"complete","tools":available}}
    if set(params)!={"_meta","name","arguments"}:
        return _err(ident,-32602,"Unexpected tool call fields")
    name=params.get("name")
    arguments=params.get("arguments")
    if name not in ("metaautomate.get_run","metaautomate.verify_evidence"):
        return _err(ident,-32601,"Tool not exposed for execution")
    if type(arguments) is not dict or set(arguments)!={"run_id"}:
        return _err(ident,-32602,"Only a workflow ID is supported")
    try:
        run_id=str(UUID(arguments["run_id"]))
    except (TypeError,ValueError,AttributeError):
        return _err(ident,-32602,"Invalid workflow identifier")
    try:
        if name=="metaautomate.get_run":
            data=runtime.report(trusted_tenant,run_id)
        else:
            data=runtime.verify_evidence(trusted_tenant,run_id)
    except KeyError:
        return _err(ident,-32004,"Workflow not found")
    except ValueError:
        return _err(ident,-32009,"Stored evidence failed verification")
    return {
        "jsonrpc":"2.0","id":ident,
        "result":{"resultType":"complete",
                  "content":[{"type":"text","text":canonical(data).decode("utf-8")}],
                  "isError":False}
    }

def a2a_task_view(runtime:Runtime,tenant:str,run_id:str)->dict:
    """Produce A2A-inspired offline task metadata, not an A2A endpoint."""
    run=runtime.report(tenant,run_id)
    mapping={
        "QUEUED":"submitted","RUNNING":"working",
        "COMPLETED":"completed",
        "AWAITING_APPROVAL":"input-required",
        "APPROVED_NOT_EXECUTED":"completed",
        "REJECTED":"rejected","FAILED":"failed",
    }
    return {
        "id":run_id,
        "status":{"state":mapping[run["state"]]},
        "contextId":tenant,
        "artifacts":[
            {"artifactId":step["agent"]+":"+str(step["seq"]),
             "name":step["agent"],
             "metadata":{"sha256":step["output_sha"]}}
            for step in run["stage_status"] if step["output_sha"]
        ],
        "metaautomate":{
            "offline_mapping_only":True,
            "a2a_wire_protocol_implemented":False,
            "external_action_executed":False,
        },
    }
