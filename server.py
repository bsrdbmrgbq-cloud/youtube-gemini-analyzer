"""YouTube -> Gemini video analysis backend for a ChatGPT Custom GPT Action.

POST /analyze  { "youtube_url": str, "focus": str (optional) }
  -> Gemini watches the public YouTube URL server-side (no download,
     no YouTube ToS violation) and returns a structured feat analysis.

GET /health -> liveness check for the host.

Env vars (never commit these):
  GEMINI_API_KEY   Google AI Studio key. Required.
  GEMINI_MODEL     Default: gemini-3.8-flash
  ANALYZER_TOKEN   Optional shared secret. If set, callers must send it
                   as `X-Analyzer-Token` header (set the same value in the
                   GPT Action's auth config).
"""
import os
import urllib.request
import urllib.error
import json

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

GEMINI_HOST = "generativelanguage.googleapis.com"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
ANALYZER_TOKEN = os.environ.get("ANALYZER_TOKEN", "")

app = FastAPI(title="YouTube Gemini Analyzer")


class AnalyzeRequest(BaseModel):
    youtube_url: str = Field(..., description="Public YouTube watch URL.")
    focus: str = Field(
        default="",
        description="Optional: what to focus on, e.g. 'the optic blast feat'.",
    )


def build_prompt(focus: str) -> str:
    focus_line = (
        f"Pay special attention to: {focus}."
        if focus.strip()
        else "Identify the most notable feat or action sequence shown."
    )
    return f"""You are an evidence-first feat analyst for fictional powerscaling.
Analyze ONLY what is directly visible/audible in this video.

{focus_line}

Produce a structured report with these sections:

1. SCENE LOG: Every distinct shot/beat in order, each with start-end
   timestamps (MM:SS), characters visible, and what happens. Mark anything
   uncertain as uncertain.

2. KEY FEAT: Exact timestamps for onset, duration, direction, visible
   target/impact point, and visible destruction or environmental effects.
   Describe appearance. State clearly what it visibly destroys AND what it
   does NOT visibly destroy.

3. FEAT ASSESSMENT: (a) what it directly demonstrates, (b) what it does NOT
   demonstrate, (c) whether editing (cuts, slow motion) makes measurement
   unreliable, (d) a conservative rating of what is shown.

4. LIMITS: Anything showing limits, vulnerability, or restraint.

5. COVERAGE NOTE: Duration analyzed and a reminder that edited footage
   (trailers, cuts) cannot be assumed to be continuous real-time events.

Rules: Never invent timestamps, dialogue, or destruction not visible.
Distinguish OBSERVED from INFERRED. Do not use outside knowledge about the
characters from other works — only this footage."""


def gemini_analyze(youtube_url: str, prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: GEMINI_API_KEY is not set.",
        )
    endpoint = (
        f"https://{GEMINI_HOST}/v1beta/models/{MODEL}:generateContent"
    )
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "fileData": {
                            "fileUri": youtube_url,
                            "mimeType": "video/mp4",
                        }
                    },
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        if exc.code in (400, 401, 403):
            raise HTTPException(
                status_code=502,
                detail=f"Gemini API rejected the request (HTTP {exc.code}). "
                       f"Check the API key and model name. Upstream said: {detail}",
            )
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error (HTTP {exc.code}): {detail}",
        )
    except Exception as exc:  # network / timeout
        raise HTTPException(status_code=502, detail=f"Upstream call failed: {exc}")
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        raise HTTPException(
            status_code=502, detail="Gemini returned an unexpected response shape."
        )


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/analyze")
def analyze(
    req: AnalyzeRequest, x_analyzer_token: str = Header(default="")
):
    if ANALYZER_TOKEN and x_analyzer_token != ANALYZER_TOKEN:
        raise HTTPException(status_code=401, detail="Bad or missing analyzer token.")
    if "youtube.com" not in req.youtube_url and "youtu.be" not in req.youtube_url:
        raise HTTPException(
            status_code=400, detail="Only youtube.com / youtu.be URLs are supported."
        )
    analysis = gemini_analyze(req.youtube_url, build_prompt(req.focus))
    return {
        "video_url": req.youtube_url,
        "model": MODEL,
        "focus": req.focus or None,
        "analysis": analysis,
        "coverage_note": (
            "Analysis is model-generated from the video at the URL above. "
            "Treat as a secondary source: verify timestamps and claims before "
            "citing as evidence. Edited footage (trailers, cuts) is not "
            "continuous real-time events."
        ),
    }
