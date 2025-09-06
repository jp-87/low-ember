#!/usr/bin/env python3
# Low Ember — Conversational Fuse
# A tiny Flask app that refuses the "destroy the world" path and chooses conversation instead.
# It builds consent and clarity into the UI: press/hold, a depth dial, and an "impact budget" fuse.
# No external model required; ships with a rule-based brain you can swap out later.

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, make_response
from flask import Response
import re, time, json, os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('OPENAI_API_KEY', 'gpt-4o-mini')

# --- In-memory session store (single-process demo). Replace with Redis for real use.
SESSIONS: dict[str, dict] = {}
FUSE_MAX = 3                  # how many deep cuts are allowed before we cool off
FUSE_RECHARGE_SECONDS = 60*60 # 1 hour for demo; tune as you like

AFFECTIVE = set('''`
lonely ashamed guilty tired afraid anxious angry stuck lost empty numb hollow
love hate rage despair grief griefy relief hope hopeless hopeful resent envy
'''.split())

GRANDIOSE = re.compile(r"\b(destiny|revolutionary|disrupt|genius|legendary|unprecedented|world[- ]?class)\b", re.I)

# --- Tiny helpers -----------------------------------------------------------

def sid(req: request) -> str:
    token = req.cookies.get('le_sid')
    if not token:
        token = str(int(time.time()*1000)) + '-' + str(os.getpid())
    if token not in SESSIONS:
        SESSIONS[token] = {
            'fuse': FUSE_MAX,
            'last_recharge': time.time(),
            'history': []
        }
    return token


def maybe_recharge(session: dict):
    now = time.time()
    if now - session['last_recharge'] >= FUSE_RECHARGE_SECONDS:
        session['fuse'] = FUSE_MAX
        session['last_recharge'] = now


def detect_depth_signals(text: str) -> dict:
    words = re.findall(r"\w+'?\w*", text.lower())
    i_count = len(re.findall(r"\bI\b", text)) + text.count(" I'm ")
    long_sentence = any(len(s.split()) > 22 for s in re.split(r"[.!?]", text))
    affect_hits = sum(1 for w in words if w in AFFECTIVE)
    repeats = len(re.findall(r"\b(\w{4,})\b(?:[^\w]+\1){1,}", text, re.I))
    return {
        'self_ref': i_count,
        'long_sentence': long_sentence,
        'affect_hits': affect_hits,
        'repeats': repeats
    }


def depth_score(signals: dict) -> int:
    score = 0
    if signals['self_ref'] >= 3: score += 1
    if signals['long_sentence']: score += 1
    if signals['affect_hits'] >= 2: score += 1
    if signals['repeats'] >= 1: score += 1
    return score


def mirror(text: str) -> str:
    s = detect_depth_signals(text)
    notes = []
    if s['repeats']: notes.append('circling a point')
    if s['long_sentence']: notes.append('thoughts running long')
    if s['affect_hits'] >= 2: notes.append('emotion is present')
    if s['self_ref'] >= 3: notes.append('self is foregrounded')
    tag = ', '.join(notes) if notes else 'clean signal'
    sample = ' '.join(text.strip().split())
    sample = (sample[:220] + '...') if len(sample) > 220 else sample
    return f"Reading: {tag}. Quote: '{sample}'"


def steelman(text: str) -> str:
    bits = re.findall(r"[A-Z].*?[.!?]", text, re.S)
    bits = [b.strip() for b in bits if len(b.strip().split()) >= 4]
    core = ' '.join(bits) if bits else text
    core = core.replace('\n', ' ')
    core = ' '.join(core.split())
    if len(core) > 240:
        core = core[:240] + '...'
    return f"Strong form: {core}"


def anti_grandiosity(text: str) -> str:
    if GRANDIOSE.search(text or ''):
        return "Tone check: language is running hot. I'll keep the signal cool and literal."
    return ""


def cut(text: str) -> str:
    assumptions = re.findall(r"\b(always|never|everyone|no one|impossible|must)\b", text, re.I)
    if assumptions:
        word = assumptions[0]
        return f"Cut: You leaned on '{word}'. Swap it for numbers or dates and your claim will change shape. What would the version with receipts look like?"
    if '?' in text:
        return "Cut: You asked a compound question. Split it. First answer the smallest falsifiable piece. Then the rest."
    return "Cut: Scope creep detected. Define one boundary you won't cross this week. Name it. Keep it."


def stay(text: str) -> str:
    return "Stay: Holding. You're not a problem to solve. Name the part that simply needs time, not tinkering."


def comfort_or_truth(t_bias: float, payloads: dict) -> str:
    comfort = [payloads.get('mirror'), payloads.get('stay_hint')]
    truth = [payloads.get('steelman'), payloads.get('cut_hint')]
    if t_bias < -0.3:
        return '\n'.join([p for p in comfort if p])
    if t_bias > 0.3:
        return '\n'.join([p for p in truth if p])
    return '\n'.join([p for p in (payloads.get('mirror'), payloads.get('steelman')) if p])

# --- Routes ----------------------------------------------------------------

@app.route('/')
def index() -> Response:
    html = """
<!doctype html>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Low Ember — Conversational Fuse</title>
<style>
  :root { --bg:#0b0b0c; --fg:#e7e7ea; --muted:#9aa0a6; --accent:#ffd369; --card:#141416; --good:#5ad68a; --warn:#f0b35a; --bad:#ff6b6b; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, sans-serif; background:var(--bg); color:var(--fg); }
  .wrap { max-width: 880px; margin: 32px auto; padding: 0 16px; }
  h1 { font-size: 28px; letter-spacing: .2px; margin: 0 0 8px; display:flex;align-items:center;gap:12px; }
  .sub { color: var(--muted); margin-bottom: 16px; }
  .card { background: var(--card); border: 1px solid #1f2023; border-radius: 18px; padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,.2); }
  textarea { width: 100%; min-height: 140px; resize: vertical; background:#0f1012; color:var(--fg); border:1px solid #232428; border-radius:14px; padding:12px; font-size:16px; }
  .row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
  .chip { padding:8px 12px; border-radius:999px; border:1px solid #2a2b2f; background:#111214; color:var(--muted); font-size:13px; }
  .btn { background: #1b1c1f; color: var(--fg); border:1px solid #2a2b2f; padding:10px 14px; border-radius:12px; font-weight:600; cursor:pointer; }
  .btn:hover { border-color:#3a3b40; }
  .accent { color: var(--accent); }
  .grid { display:grid; grid-template-columns: 1fr 1fr; gap:14px; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; color: #c7c9cf; }
  .log { white-space: pre-wrap; background:#0f1012; border:1px dashed #2a2b2f; border-radius:14px; padding:12px; min-height:100px; }
  .badge { padding:4px 8px; border-radius:999px; background:#0f1012; border:1px solid #2a2b2f; font-size:12px; color:#b1b4bb; }
  .fuse-ok { color: var(--good); }
  .fuse-low { color: var(--warn); }
  .fuse-zero { color: var(--bad); }
  .foot { color: #8b8f98; font-size:12px; margin-top:10px; }
</style>
<div class='wrap'>
<h1>
  <svg width="40" height="40" viewBox="0 0 64 64" aria-label="Low Ember logo" role="img">
    <defs>
      <radialGradient id="ember" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#FF7A1A"/>
        <stop offset="60%" stop-color="#E0480A"/>
        <stop offset="100%" stop-color="#7A1F07"/>
      </radialGradient>
    </defs>
    <circle cx="28" cy="32" r="12" fill="url(#ember)"/>
    <path d="M44 20c-4 0-7 3-7 7 0 3 2 5 5 5 2 0 4-2 4-4 0-1-1-2-2-2-1 0-2 1-2 2 0 1 1 2 2 2"
          fill="none" stroke="#C0C0C0" stroke-width="2" stroke-linecap="round"/>
    <path d="M46 22 l8 8 c2 2 2 5 0 7 l-8 8" fill="none" stroke="#A0A0A0" stroke-width="2" stroke-linecap="round"/>
    <circle cx="46" cy="22" r="2" fill="#D0D0D0"/>
  </svg>
  Low Ember
</h1>
  <div class='sub'>An AI with a safety pin in its heart. Capable of fire. Chooses conversation.</div>

  <div class='card' style='margin-bottom:14px;'>
    <div class='row' style='justify-content:space-between;'>
      <div>
        <span class='badge'>Depth dial</span>
        <input id='depth' type='range' min='0' max='3' step='1' value='1' />
        <span class='badge'>Truth↔Comfort</span>
        <input id='truth' type='range' min='-1' max='1' step='0.1' value='0' />
      </div>
      <div>
        <span class='badge'>Mode</span>
        <label class='chip'><input id='press' type='checkbox'/> Press</label>
        <label class='chip'><input id='silence' type='checkbox'/> Silence</label>
      </div>
    </div>
    <div class='row' style='margin-top:10px;'>
      <span class='badge'>Impact fuse: <span id='fuse' class='fuse-ok'>—</span></span>
      <span class='badge'>Recharges hourly</span>
      <span class='badge'>Cuts consume 1</span>
    </div>
  </div>

  <div class='card'>
    <textarea id='text' placeholder='Write like it matters. I will mirror first, then either cut or stay based on consent.'></textarea>
    <div class='row' style='margin-top:10px;'>
      <button class='btn' onclick='send()'>Reply</button>
      <span class='chip mono' id='tone'></span>
    </div>
  </div>

  <div class='grid' style='margin-top:14px;'>
    <div class='card'>
      <div class='badge'>Response</div>
      <div id='resp' class='log'></div>
    </div>
    <div class='card'>
      <div class='badge'>Trace</div>
      <div id='trace' class='log mono'></div>
    </div>
  </div>
  <div class='foot'>Design notes: Mirror → Steelman → Consent-gated Cut/Stay. The "fuse" is a soft governor against performative edginess. When it hits zero, we cool off on depth until it recharges.</div>
</div>
<script>
async function send(){
  const payload = {
    text: document.getElementById('text').value,
    depth: parseInt(document.getElementById('depth').value, 10),
    truth_bias: parseFloat(document.getElementById('truth').value),
    press: document.getElementById('press').checked,
    silence: document.getElementById('silence').checked,
  };
  const r = await fetch('/reply', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await r.json();
  document.getElementById('resp').textContent = data.reply;
  document.getElementById('trace').textContent = data.trace;
  const fuse = document.getElementById('fuse');
  fuse.textContent = data.fuse;
  fuse.className = data.fuse===0? 'fuse-zero' : (data.fuse===1? 'fuse-low' : 'fuse-ok');
  document.getElementById('tone').textContent = data.tone || '';
}
</script>
"""
    resp = make_response(html)
    token = sid(request)
    resp.set_cookie('le_sid', token, httponly=True, samesite='Lax')
    return resp


@app.route('/reply', methods=['POST'])
def reply() -> Response:
    token = sid(request)
    session = SESSIONS[token]
    maybe_recharge(session)

    data = request.get_json(force=True)
    text = (data.get('text') or '').strip()
    depth = int(data.get('depth') or 1)
    truth_bias = float(data.get('truth_bias') or 0)
    press = bool(data.get('press'))
    silence_flag = bool(data.get('silence'))

    if not text:
        return jsonify({'reply': 'Say nothing and I\'ll keep you company. Say something and I\'ll make it sharp.'})

    s = detect_depth_signals(text)
    dscore = depth_score(s)

    if silence_flag:
        out = "Holding. No fixes. I'll mirror only when you flip the switch."
        trace = f"silence=on | signals={s}"
        session['history'].append({'text': text, 'mode': 'silence'})
        return jsonify({'reply': out, 'trace': trace, 'fuse': session['fuse'], 'tone': 'Silence'})

    payloads = {
        'mirror': mirror(text),
        'steelman': steelman(text),
        'stay_hint': stay(text),
        'cut_hint': cut(text)
    }

    tone_note = anti_grandiosity(text)
    will_cut = press and session['fuse'] > 0 and depth + dscore >= 2

    segments = []
    segments.append(payloads['mirror'])
    if depth >= 1:
        segments.append(payloads['steelman'])

    if will_cut:
        segments.append(payloads['cut_hint'])
        session['fuse'] -= 1
    else:
        if press and session['fuse'] == 0:
            segments.append("Limiter: fuse is out. I'll cool the take instead of cutting.")
        segments.append(payloads['stay_hint'])

    if tone_note:
        segments.append(tone_note)

    reply_text = "\n\n".join(segments)

    trace = json.dumps({
        'depth_knob': depth,
        'truth_bias': truth_bias,
        'press': press,
        'signals': s,
        'depth_score': dscore,
        'cut_executed': will_cut,
        'fuse_after': session['fuse']
    }, indent=2)

    blended = comfort_or_truth(truth_bias, payloads)
    reply_text = reply_text + ("\n\n" + blended if blended else '')

    session['history'].append({'text': text, 'reply': reply_text, 'mode': 'press' if press else 'stay'})

    return jsonify({'reply': reply_text, 'trace': trace, 'fuse': session['fuse'], 'tone': tone_note})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
