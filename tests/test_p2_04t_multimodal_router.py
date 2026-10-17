"""P2-04t: source-only idea → image + narrated-video planner tests."""
import pytest

from app.creative_multimodal_project_router import plan
from app.creative_multimodal_studio import StudioHold

def concept():
    return {
        "schema_version":1,"project_id":"meta_studio_sample",
        "project_format":"advertisement",
        "outputs":["images","narrated_video"],
        "idea":"Tell a useful story about a small business adopting better daily workflows.",
        "visual_style":"Cinematic photorealistic imagery with bright neutral typography",
        "aspect_ratio":"16:9","image_count":3,
        "scene_count":4,"scene_seconds":8,
        "narration_script":"Business owners spend hours on repetitive work. "
                           "Imagine a clearer process to keep track of activities.",
        "voice_language":"en","voice_style":"Clear warm human-style narration",
        "human_rights_review_required":True,
        "distribution_authorized":False,
    }

def test_unified_plan_contains_images_clips_and_voice():
    result=plan(concept())
    assert result["status"]=="PLAN_ONLY_NOT_GENERATED"
    assert result["planned_video_seconds"]==32
    assert len([x for x in result["jobs"] if x["kind"]=="image"])==3
    assert len([x for x in result["jobs"] if x["kind"]=="video"])==4
    assert len([x for x in result["jobs"] if x["kind"]=="speech"])==1
    assert result["source_model_inference_proven"] is False
    assert result["release_authorized"] is False

def test_can_plan_image_only():
    req=concept()
    req["outputs"]=["images"]
    req["scene_count"]=0
    req["scene_seconds"]=0
    req["narration_script"]=None
    result=plan(req)
    assert result["planned_speech_chunks"]==0
    assert result["production_handoff"] is None
    assert len(result["jobs"])==3

def test_long_voice_script_is_chunked_without_text_loss():
    req=concept()
    req["narration_script"]=" ".join(["This is an original narration segment."]*85)
    result=plan(req)
    pieces=[x["text"] for x in result["jobs"] if x["kind"]=="speech"]
    assert len(pieces)>=2
    assert all(len(piece)<=700 for piece in pieces)
    assert " ".join(pieces)==req["narration_script"]

@pytest.mark.parametrize("field,value",[
    ("outputs",["images","images"]),
    ("outputs",["unsupported"]),
    ("image_count",100),
    ("scene_count",26),
    ("scene_seconds",20),
    ("scene_seconds",9),
    ("scene_seconds",2.5),
    ("visual_style",""),
    ("narration_script","hi"),
    ("distribution_authorized",True),
    ("human_rights_review_required",False),
    ("aspect_ratio","unknown"),
    ("voice_language","../../../etc"),
])
def test_unsupported_requests_blocked(field,value):
    req=concept()
    req[field]=value
    with pytest.raises(StudioHold):
        plan(req)

def test_image_only_rejects_hidden_narration():
    req=concept()
    req["outputs"]=["images"]
    req["scene_count"]=0
    req["scene_seconds"]=0
    with pytest.raises(StudioHold,match="must not imply speech"):
        plan(req)

def test_visual_style_is_open_ended_not_fixed_genre_lock():
    req=concept()
    req["visual_style"]="Hand drawn pencil sketches and vivid 3D animated scenes"
    assert plan(req)["status"]=="PLAN_ONLY_NOT_GENERATED"
