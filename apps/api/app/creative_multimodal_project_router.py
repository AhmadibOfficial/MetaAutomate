"""P2-04t source-only creative project router (images + narrated video).

Plans jobs for independently approved image/video/TTS workers.
Does NOT invoke models or authorize image, voice, film or web publication.
"""
from __future__ import annotations
from hashlib import sha256
import json
import math
import re

from app.creative_multimodal_studio import FORMATS, StudioHold

PROJECT=re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
LANG=re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
ALLOWED_OUTPUTS={"images","narrated_video"}
FIELDS={
    "schema_version","project_id","project_format","outputs",
    "idea","visual_style","aspect_ratio","image_count",
    "scene_count","scene_seconds","narration_script","voice_language",
    "voice_style","human_rights_review_required",
    "distribution_authorized",
}
RATIOS={"1:1","4:5","9:16","16:9","3:2","2:3","21:9"}
def _text(value,minimum,maximum,label):
    if type(value) is not str or not minimum<=len(value.strip())<=maximum:
        raise StudioHold(f"{label} must be {minimum}-{maximum} characters")
    return value.strip()

def _chunks(text,max_chars=700):
    """Split on whitespace, never lose original words or exceed model prompt size."""
    tokens=text.split()
    result=[]
    current=""
    for token in tokens:
        if len(token)>max_chars:
            raise StudioHold("Narration contains a word longer than worker prompt limit")
        if len(current)+len(token)+(1 if current else 0)>max_chars:
            result.append(current)
            current=token
        else:
            current=(current+" "+token).strip()
    if current:
        result.append(current)
    return result

def plan(request:dict)->dict:
    if type(request) is not dict or set(request)!=FIELDS:
        raise StudioHold("Unexpected multimodal project request")
    if type(request["schema_version"]) is not int or request["schema_version"]!=1:
        raise StudioHold("Unsupported creative request schema")
    identifier=request["project_id"]
    if type(identifier) is not str or PROJECT.fullmatch(identifier) is None:
        raise StudioHold("Invalid project identifier")
    if type(request["project_format"]) is not str or request["project_format"] not in FORMATS:
        raise StudioHold("Unknown creative project class")
    outputs=request["outputs"]
    if (type(outputs) is not list or not 1<=len(outputs)<=2
        or any(type(v) is not str or v not in ALLOWED_OUTPUTS for v in outputs)
        or len(set(outputs))!=len(outputs)):
        raise StudioHold("Select images, narrated_video or both")
    idea=_text(request["idea"],20,1500,"Creative concept")
    style=_text(request["visual_style"],6,300,"Artistic style")
    ratio=request["aspect_ratio"]
    if type(ratio) is not str or ratio not in RATIOS:
        raise StudioHold("Unsupported source visual aspect ratio")
    image_count=request["image_count"]
    scene_count=request["scene_count"]
    seconds=request["scene_seconds"]
    if (type(image_count) is not int or not 0<=image_count<=12
        or type(scene_count) is not int or not 0<=scene_count<=24
        or type(seconds) not in (int,float) or not math.isfinite(seconds)):
        raise StudioHold("Invalid scene/image count or duration")
    want_images="images" in outputs
    want_video="narrated_video" in outputs
    if (want_images and image_count<1 or not want_images and image_count!=0
        or want_video and not 4<=scene_count<=24
        or not want_video and (scene_count!=0 or seconds!=0)):
        raise StudioHold("Requested media counts disagree with output types")
    runtime=scene_count*seconds
    if want_video and (not 2<=seconds<=15 or not 30<=runtime<=120):
        raise StudioHold("First narrated production requires 30-120s total, 2-15s shots")
    language=request["voice_language"]
    if type(language) is not str or LANG.fullmatch(language) is None:
        raise StudioHold("Invalid narration language")
    voice_style=_text(request["voice_style"],3,150,"Voice direction")
    narration=request["narration_script"]
    if want_video:
        script=_text(narration,25,4000,"Narration")
        chunks=_chunks(script)
    elif narration is not None:
        raise StudioHold("Image-only output must not imply speech generation")
    else:
        chunks=[]
    if (request["human_rights_review_required"] is not True
        or request["distribution_authorized"] is not False):
        raise StudioHold("Independent rights review and publication hold required")
    jobs=[]
    if want_images:
        for index in range(image_count):
            jobs.append({
                "id":f"{identifier}:image:{index+1:02}",
                "kind":"image","prompt":f"{idea}. Visual style: {style}. Ratio: {ratio}.",
                "target":"local_approved_diffusers_image_worker",
                "status":"WAITING_FOR_MODEL_LICENSE_AND_SIGNED_APPROVAL",
                "native_resolution_unverified":True,
                "output_sha256":None,"publication_authorized":False,
            })
    if want_video:
        for index in range(scene_count):
            jobs.append({
                "id":f"{identifier}:video:{index+1:02}",
                "kind":"video","prompt":f"{idea}. Scene {index+1}/{scene_count}. Style: {style}.",
                "duration_seconds":seconds,
                "target":"local_approved_short_clip_worker",
                "status":"WAITING_FOR_MODEL_LICENSE_AND_SIGNED_APPROVAL",
                "output_sha256":None,"publication_authorized":False,
            })
        for index,text in enumerate(chunks):
            jobs.append({
                "id":f"{identifier}:speech:{index+1:02}",
                "kind":"speech","text":text,"language":language,
                "voice_direction":voice_style,
                "target":"local_approved_offline_neural_speech_worker",
                "status":"WAITING_FOR_VOICE_LICENSE_AND_THREE_PARTY_SIGNATURES",
                "output_sha256":None,"publication_authorized":False,
            })
    request_sha=sha256(json.dumps(request,sort_keys=True,separators=(",",":"),
                              ensure_ascii=True,allow_nan=False).encode()).hexdigest()
    return {
        "schema_version":1,"project_id":identifier,
        "project_sha256":request_sha,
        "requested_outputs":outputs,
        "planned_visual_count":(image_count if want_images else 0)+scene_count,
        "planned_speech_chunks":len(chunks),
        "planned_video_seconds":runtime if want_video else 0,
        "jobs":jobs,
        "production_handoff":"P2-04t:creative_multimodal_studio.render"
                             if want_video else None,
        "source_model_inference_proven":False,
        "speech_model_inference_proven":False,
        "assembled_full_hd_video_produced":False,
        "status":"PLAN_ONLY_NOT_GENERATED",
        "release_authorized":False,"published":False,
    }
