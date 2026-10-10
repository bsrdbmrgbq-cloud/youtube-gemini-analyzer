# YouTube Gemini Analyzer — ChatGPT Plugin (Custom GPT Action)

Paste a YouTube URL into ChatGPT, get back a timestamped video analysis
powered by Gemini. Gemini processes public YouTube URLs server-side, so
nothing is downloaded and YouTube's terms are respected.

## What you need

- A Google AI Studio API key (free at aistudio.google.com → Get API key).
- A Render account (free tier works) — or Railway / Fly.io.
- ChatGPT Plus (required to create Custom GPTs with Actions).

## Step 1 — Deploy the backend

**Option A: Render (recommended, ~5 minutes)**

1. Push this folder to a GitHub repo.
2. In Render: New → Web Service → connect the repo.
3. Render detects `render.yaml`. In the dashboard, set the secret env var:
   `GEMINI_API_KEY` = your key (never commit it).
4. Deploy. Note your public URL, e.g.
   `https://youtube-gemini-analyzer.onrender.com`.
5. Render auto-generates `ANALYZER_TOKEN`. Copy it from the env vars page —
   you'll need it in Step 2.

**Option B: local / other hosts**

```
pip install -r requirements.txt
GEMINI_API_KEY=your_key uvicorn server:app --host 0.0.0.0 --port 8000
```

The host must be publicly reachable over HTTPS for ChatGPT to call it.

## Step 2 — Create the Custom GPT

1. In ChatGPT: Explore GPTs → Create → Configure.
2. Name it e.g. "Video Feat Analyzer". Paste `gpt-instructions.md` into
   the Instructions box.
3. Scroll to Actions → Create new action → paste `openapi.yaml`, but first
   replace `https://REPLACE-WITH-YOUR-RENDER-URL` with your real backend URL.
4. Authentication: choose Custom Header, name `X-Analyzer-Token`, value =
   the `ANALYZER_TOKEN` from Render. (If you skipped the token, choose None —
   but anyone with your URL could then use your Gemini quota.)
5. Save. Test: "Analyze this: <a YouTube URL> — focus on the fight scene."

## Costs

- Gemini free tier: generous; YouTube URL ingestion included. Paid usage is
  roughly $0.10–0.50 per hour of footage on Flash-class models — a 1-minute
  teaser costs a fraction of a cent.
- Render free tier: fine for occasional use (spins down when idle; first
  request after idle takes ~30s).

## Limits (honest)

- Public YouTube videos only. Private, deleted, age-restricted, or
  livestream URLs usually fail at Gemini's side.
- Output is model-generated: a secondary source. Verify timestamps before
  citing as evidence.
- Trailers are edited marketing, not the film. The GPT is instructed to say so.
