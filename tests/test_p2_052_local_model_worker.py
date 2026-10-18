"""P2-052: actual text model call is local-only, uninstalled in these tests."""
import json
import pytest
from fastapi import HTTPException

from app.private_model_worker import configured_model,generate_text,LocalModel

def config():
    return {
        "WORKSPACE_AUTH_MODE":"oidc",
        "MAT_LOCAL_MODEL_ENABLED":"1",
        "MAT_LOCAL_MODEL_LICENSE_REVIEWED":"1",
        "MAT_LOCAL_MODEL_POLICY_REVIEWED":"1",
        "MAT_LOCAL_MODEL_ISOLATION_APPROVED":"1",
        "MAT_LOCAL_MODEL_URL":"http://127.0.0.1:11434/v1/chat/completions",
        "MAT_LOCAL_MODEL_ID":"reviewed-model",
        "MAT_LOCAL_MODEL_CHECKPOINT_SHA256":"b"*64,
    }

def test_no_private_model_enabled_by_default():
    with pytest.raises(HTTPException) as e:
        configured_model({},isolation_probe=lambda:True)
    assert e.value.status_code==503

def test_runtime_requires_real_kernel_guard():
    with pytest.raises(HTTPException) as e:
        configured_model(config(),isolation_probe=lambda:False)
    assert e.value.status_code==503
    cfg=configured_model(config(),isolation_probe=lambda:True)
    assert cfg.port==11434
    assert cfg.digest=="b"*64

@pytest.mark.parametrize("address",[
    "https://remote-model.example/v1/chat/completions",
    "http://127.0.0.1:11434@remote.example/v1/chat/completions",
    "http://localhost:11434/v1/chat/completions",
    "http://127.0.0.2:11434/v1/chat/completions",
    "http://127.0.0.1:0/v1/chat/completions",
    "http://127.0.0.1:invalid/v1/chat/completions",
    "http://127.0.0.1:11434/other",
    "http://127.0.0.1:11434/v1/chat/completions?q=secret",
])
def test_remote_and_unsafe_model_endpoints_rejected(address):
    cfg=config()
    cfg["MAT_LOCAL_MODEL_URL"]=address
    with pytest.raises(HTTPException):
        configured_model(cfg,isolation_probe=lambda:True)

class FakeReply:
    def __init__(self,data,status=200):
        self.data=data
        self.status=status
    def read(self,n):
        return json.dumps(self.data).encode()

class Stub:
    calls=[]
    output={"choices":[{"message":{"role":"assistant",
       "content":"First interview prospective users, then implement a small inventory flow."}}]}
    def __init__(self,host,port,timeout):
        assert host=="127.0.0.1" and port==11434 and timeout==20
        self.calls.append("connect")
    def request(self,verb,path,body,headers):
        self.calls.append("request")
        assert verb=="POST" and path=="/v1/chat/completions"
        data=json.loads(body)
        assert data["stream"] is False
        assert data["max_tokens"]==420
        assert len(data["messages"])==2
        assert data["messages"][0]["role"]=="system"
        assert "no tools" in data["messages"][0]["content"].lower()
        assert data["messages"][1]["role"]=="user"
        assert "tools" not in data
    def getresponse(self):
        return FakeReply(type(self).output)
    def close(self):
        self.calls.append("close")

def test_real_local_http_completion_contract_with_mock_adapter():
    Stub.calls=[]
    cfg=LocalModel(11434,"reviewed-model","b"*64)
    result=generate_text("Create an inventory product prototype for small shops",
                         "PROJECT_SCOPE",cfg,connector=Stub)
    assert result.startswith("First interview")
    assert Stub.calls==["connect","request","close"]

def test_model_cannot_return_tool_calls():
    Stub.output={"choices":[{"message":{
        "role":"assistant","content":"Done",
        "tool_calls":[{"function":{"name":"publish"}}]}}]}
    with pytest.raises(HTTPException) as e:
        generate_text("Create an original campaign script with user consent",
                      "VIDEO_SCRIPT",LocalModel(11434,"reviewed-model","a"*64),
                      connector=Stub)
    assert e.value.status_code==502
    Stub.output={"choices":[{"message":{"role":"assistant",
       "content":"First interview prospective users, then implement a small inventory flow."}}]}

def test_unsafe_model_request_rejected_without_http():
    with pytest.raises(HTTPException):
        generate_text("short","VIDEO_SCRIPT",LocalModel(11434,"approved","b"*64),connector=Stub)
