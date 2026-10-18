"""P2-053 provider adapters use stubbed HTTPS only; no paid calls or secrets.

Validates provider-specific wire formats and normalized responses, plus
mandatory cross-border data approval and durable spend reservation before
a network socket can be constructed.
"""
import json
from dataclasses import replace
import pytest
from fastapi import HTTPException
from app.private_global_models import (
    SPECS, ProviderConfig, provider_config, generate_global_text,
)

FAKE_KEY="only-for-offline-tests-not-a-real-key"
PROMPT="Prepare a realistic project scope for a small inventory business."

def config(name):
    return ProviderConfig(SPECS[name],"reviewed-model-2026",FAKE_KEY)

def allowed_config(name):
    spec=SPECS[name]
    return {
        "WORKSPACE_AUTH_MODE":"oidc",
        "MAT_GLOBAL_AI_ENABLED":"1",
        "MAT_GLOBAL_AI_EGRESS_APPROVED":"1",
        "MAT_GLOBAL_AI_CROSS_BORDER_REVIEWED":"1",
        "MAT_GLOBAL_AI_PROVIDER_TERMS_REVIEWED":"1",
        "MAT_GLOBAL_AI_COST_RESERVATION_REQUIRED":"1",
        "MAT_GLOBAL_AI_ALLOWED_PROVIDERS":name,
        spec.auth_env:FAKE_KEY,
        spec.model_env:"reviewed-model-2026",
    }

def response(name):
    if name=="OPENAI":
        return {
            "status":"completed",
            "output":[{"type":"message","role":"assistant",
                       "content":[{"type":"output_text","text":"Create the first working prototype."}]}],
            "usage":{"input_tokens":23,"output_tokens":9},
        }
    if name=="ANTHROPIC":
        return {
            "stop_reason":"end_turn",
            "content":[{"type":"text","text":"Create the first working prototype."}],
            "usage":{"input_tokens":23,"output_tokens":9},
        }
    if name=="GOOGLE":
        return {
            "candidates":[{"finishReason":"STOP",
                           "content":{"parts":[{"text":"Create the first working prototype."}]}}],
            "usageMetadata":{"promptTokenCount":23,"candidatesTokenCount":9},
        }
    return {
        "choices":[{"finish_reason":"stop",
                    "message":{"role":"assistant",
                               "content":"Create the first working prototype."}}],
        "usage":{"prompt_tokens":23,"completion_tokens":9},
    }

class StubResponse:
    status=200
    def __init__(self,data):
        self.data=data
    def read(self,n):
        return json.dumps(self.data).encode("utf-8")

class HTTPSStub:
    requests=[]
    scenario="OPENAI"
    def __init__(self,host,*,timeout,context):
        spec=SPECS[self.scenario]
        assert host==spec.host and timeout==18
        assert context.check_hostname is True
        self.__class__.requests.append(("connect",host))
    def request(self,method,path,body,headers):
        spec=SPECS[self.scenario]
        assert method=="POST"
        assert path.startswith(spec.path)
        assert "http" not in path
        assert headers["Content-Type"]=="application/json"
        assert headers.get("Authorization","")=="Bearer "+FAKE_KEY \
            if self.scenario not in ("ANTHROPIC","GOOGLE") \
            else "Authorization" not in headers
        if self.scenario=="ANTHROPIC":
            assert headers["x-api-key"]==FAKE_KEY
            assert headers["anthropic-version"]=="2023-06-01"
        if self.scenario=="GOOGLE":
            assert headers["x-goog-api-key"]==FAKE_KEY
        parsed=json.loads(body)
        assert parsed.get("tools",[])==[]
        assert parsed.get("stream",False) is False
        if self.scenario=="OPENAI":
            assert parsed["store"] is False
            assert parsed["input"][0]["content"]==PROMPT
            assert parsed["instructions"]
        elif self.scenario=="ANTHROPIC":
            assert parsed["messages"][0]["content"]==PROMPT
            assert parsed["system"]
        elif self.scenario=="GOOGLE":
            assert parsed["contents"][0]["parts"][0]["text"]==PROMPT
            assert parsed["systemInstruction"]
            assert parsed["generationConfig"]["maxOutputTokens"]==400
        else:
            assert parsed["messages"][1]["content"]==PROMPT
            assert parsed["messages"][0]["role"]=="system"
        self.__class__.requests.append(("request",path))
    def getresponse(self):
        return StubResponse(response(self.scenario))
    def close(self):
        self.__class__.requests.append(("close",))

@pytest.mark.parametrize("provider",list(SPECS))
def test_all_six_international_provider_wire_contracts(provider):
    HTTPSStub.scenario=provider
    HTTPSStub.requests=[]
    conf=provider_config(provider,allowed_config(provider))
    result=generate_global_text(
        PROMPT,"PROJECT_SCOPE",conf,
        external_transfer_approved=True,spend_reservation_verified=True,
        transport=HTTPSStub,
    )
    assert result.provider==provider
    assert result.model=="reviewed-model-2026"
    assert result.text=="Create the first working prototype."
    assert result.input_tokens==23
    assert result.output_tokens==9
    assert HTTPSStub.requests[0]==("connect",SPECS[provider].host)
    assert HTTPSStub.requests[-1]==("close",)

@pytest.mark.parametrize("provider",list(SPECS))
def test_no_spend_reservation_or_transfer_consent_means_zero_network(provider):
    HTTPSStub.scenario=provider
    HTTPSStub.requests=[]
    cfg=config(provider)
    for transfer,reserve in [(False,False),(True,False),(False,True)]:
        with pytest.raises(HTTPException) as e:
            generate_global_text(PROMPT,"PROJECT_SCOPE",cfg,
                external_transfer_approved=transfer,
                spend_reservation_verified=reserve,transport=HTTPSStub)
        assert e.value.status_code==403
    assert HTTPSStub.requests==[]

def test_disabled_provider_and_wrong_region_rejected():
    settings=allowed_config("GOOGLE")
    settings["MAT_GLOBAL_AI_ALLOWED_PROVIDERS"]="OPENAI"
    with pytest.raises(HTTPException):
        provider_config("GOOGLE",settings)
    settings=allowed_config("QWEN_INTL")
    settings["WORKSPACE_AUTH_MODE"]="dev_key"
    with pytest.raises(HTTPException):
        provider_config("QWEN_INTL",settings)
    settings=allowed_config("OPENAI")
    settings.pop("MAT_GLOBAL_AI_EGRESS_APPROVED")
    with pytest.raises(HTTPException):
        provider_config("OPENAI",settings)

@pytest.mark.parametrize("name",list(SPECS))
def test_provider_never_accepts_injected_model_name(name):
    settings=allowed_config(name)
    settings[SPECS[name].model_env]="safe?model=https://attacker.test"
    with pytest.raises(HTTPException):
        provider_config(name,settings)

def test_provider_keys_are_missing_by_default():
    for p in SPECS:
        with pytest.raises(HTTPException) as exc:
            provider_config(p,{})
        assert exc.value.status_code==503

@pytest.mark.parametrize("name",list(SPECS))
def test_unsafe_response_or_tool_use_rejected(name):
    bad=response(name)
    if name=="OPENAI":
        bad["output"]=[{"type":"tool_call","name":"send_email"}]
    elif name=="ANTHROPIC":
        bad["content"]=[{"type":"tool_use","name":"publish"}]
    elif name=="GOOGLE":
        bad["candidates"][0]["content"]["parts"]=[{"functionCall":{"name":"publish"}}]
    else:
        bad["choices"][0]["message"]["tool_calls"]=[{"function":{"name":"publish"}}]
    class Bad(HTTPSStub):
        scenario=name
        def getresponse(self):
            return StubResponse(bad)
    with pytest.raises(HTTPException) as exc:
        generate_global_text(PROMPT,"PROJECT_SCOPE",config(name),
            external_transfer_approved=True,spend_reservation_verified=True,
            transport=Bad)
    assert exc.value.status_code==502

def test_incomplete_response_cannot_be_claimed_completed():
    bad=response("OPENAI")
    bad["status"]="incomplete"
    class Incomplete(HTTPSStub):
        scenario="OPENAI"
        def getresponse(self):
            return StubResponse(bad)
    with pytest.raises(HTTPException) as exc:
        generate_global_text(PROMPT,"PROJECT_SCOPE",config("OPENAI"),
            external_transfer_approved=True,spend_reservation_verified=True,
            transport=Incomplete)
    assert exc.value.status_code==502

def test_model_returned_usage_is_claim_not_billing_proof():
    bad=response("OPENAI")
    bad["usage"]={"input_tokens":"many","output_tokens":99999999}
    class NoUsage(HTTPSStub):
        scenario="OPENAI"
        def getresponse(self):
            return StubResponse(bad)
    result=generate_global_text(PROMPT,"PROJECT_SCOPE",config("OPENAI"),
        external_transfer_approved=True,spend_reservation_verified=True,
        transport=NoUsage)
    assert result.input_tokens is None
    assert result.output_tokens is None
