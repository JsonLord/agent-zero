#!/usr/bin/env python3
"""Secret-safe, non-destructive OpenOperator Hugging Face acceptance smoke."""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.request

BASE=os.getenv("OPENOPERATOR_BASE_URL","https://leon4gr45-openoperator.hf.space").rstrip("/")
HF_TOKEN=os.getenv("HF_TOKEN","").strip(); API_KEY=os.getenv("SPYNEL_AGENT_ZERO_API_KEY","").strip()
TIMEOUT=float(os.getenv("OPENOPERATOR_SMOKE_TIMEOUT","30")); POLL=float(os.getenv("SPYNEL_POLL_INTERVAL","2"))
results=[]

def request(path,payload=None,*,api=False):
    headers={"Accept":"application/json"}
    if HF_TOKEN: headers["Authorization"]="Bearer "+HF_TOKEN
    if api:
        if not API_KEY: raise RuntimeError("SPYNEL_AGENT_ZERO_API_KEY is not configured")
        headers["X-API-KEY"]=API_KEY
    data=None
    if payload is not None: data=json.dumps(payload).encode(); headers["Content-Type"]="application/json"
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT) as response:
            raw=response.read().decode(errors="replace"); return response.status,json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code,{"error":"HTTP error"}

def report(name,state,detail=""):
    results.append((name,state)); print(f"{name}: {state}"+(f" ({detail})" if detail else ""))

def poll(context_id):
    deadline=time.monotonic()+TIMEOUT
    while time.monotonic()<deadline:
        code,data=request("/api/api_poll",{"context_id":context_id},api=True)
        if code!=200:return False,data
        if data.get("requires_attention"):return False,data
        if data.get("status") in {"completed","complete"}:return True,data
        if data.get("status") in {"failed","blocked","cancelled","partially_verified"}:return False,data
        time.sleep(max(.25,min(POLL,float(data.get("next_poll_after") or POLL))))
    return False,{"error":"finite timeout"}

def main():
    code,data=request("/health"); report("health","PASS" if code==200 and data.get("status")=="ok" else "FAIL")
    code,data=request("/api/settings_get",{})
    if code in {401,403} or code==302: report("settings","BLOCKED","browser authentication/CSRF required")
    elif code==200:
        additional=data.get("additional",{}); settings=data.get("settings",{})
        report("settings","PASS")
        report("runtime","PASS" if additional.get("is_dockerized") and not additional.get("is_development",False) else "FAIL","dockerized production expected")
        report("root password capability","PASS" if additional.get("root_password_supported") is False else "FAIL","unsupported expected")
        serialized=json.dumps(data)
        report("API key","PASS" if "************" in serialized and "BLABLADOR_API_KEY" not in serialized else "FAIL","configured/masked")
        report("compatible provider","PASS" if '"provider": "other"' in serialized or '"provider":"other"' in serialized else "BLOCKED","model presets may require authenticated plugin API")
    else: report("settings","FAIL")
    if not API_KEY:
        report("chat","BLOCKED","SPYNEL_AGENT_ZERO_API_KEY absent")
        report("delegation","BLOCKED","SPYNEL_AGENT_ZERO_API_KEY absent")
    else:
        code,data=request("/api/api_message",{"message":"hi","agent_profile":"spynel","async":True},api=True)
        ok,final=poll(str(data.get("context_id"))) if code==200 and data.get("context_id") else (False,data)
        report("chat","PASS" if ok and final.get("result") else "FAIL")
        code,unknown=request("/api/api_message",{"message":"inspect this","agent_profile":"definitely-not-real","async":True},api=True)
        report("unknown profile safety","PASS" if code==404 and not unknown.get("context_id") else "FAIL")
        code,delegated=request("/api/plugins/_goal/delegate",{"objective":"Inspect runtime mode and return a read-only summary.","agent_profile":"reviewer","idempotency_key":"hf-smoke-reviewer"},api=True)
        report("delegation","PASS" if code==200 and delegated.get("context_id") and delegated.get("goal_id") else "FAIL")
    code,_=request("/api/agent_profile_create",{})
    report("profile-create protection","PASS" if code in {302,401,403} else "FAIL")
    for label in ("specialist profiles","Spynel","Paperclip skill"):
        report(label,"BLOCKED","requires authenticated browser metadata or completed delegated inspection")
    mandatory={"health","chat","delegation","unknown profile safety","profile-create protection"}
    return 1 if any(state!="PASS" for name,state in results if name in mandatory) else 0

if __name__=="__main__": raise SystemExit(main())
