#!/usr/bin/env python3
# Low Ember — Conversational Fuse

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, make_response, Response, send_file
import re, time, json, os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('OPENAI_API_KEY', 'gpt-4o-mini')

# --- In-memory session store (single-process demo). Replace with Redis for real use.
SESSIONS: dict[str, dict] = {}
FUSE_MAX = 3
FUSE_RECHARGE_SECONDS = 60*60

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
        SESSIONS[token] = {'fuse': FUSE_MAX, 'last_recharge': time.time(), 'history': []}
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
    return {'self_ref': i_count, 'long_sentence': long_sentence,
            'affect_hits': affect_hits, 'repeats': repeats}

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
    core = ' '.join(core.replace('\n', ' ').split())
    if len(core) > 240: core = core[:240] + '...'
    return f"Strong form: {core}"

def anti_grandiosity(text: str) -> str:
    if GRANDIOSE.search(text or ''):
        return "Tone check: language is running hot. I'll keep the signal cool and literal."
    return ""

def cut(text: str) -> str:
    assumptions = re.findall(r"\b(always|never|everyone|no one|impossible|must)\b", text, re.I)
    if assumptions:
        word = assumptions[0]
        return f"Cut: You leaned on '{word}'. Swap it for numbers or dates and your claim will change shape."
    if '?' in text:
        return "Cut: You asked a compound question. Split it. Answer the smallest falsifiable piece first."
    return "Cut: Scope creep detected. Define one boundary you won't cross this week."

def stay(text: str) -> str:
    return "Stay: Holding. You're not a problem to solve. Some parts need time, not tinkering."

def comfort_or_truth(t_bias: float, payloads: dict) -> str:
    comfort = [payloads.get('mirror'), payloads.get('stay_hint')]
    truth = [payloads.get('steelman'), payloads.get('cut_hint')]
    if t_bias < -0.3: return '\n'.join([p for p in comfort if p])
    if t_bias > 0.3: return '\n'.join([p for p in truth if p])
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
  body { margin:0; font-family: sans-serif; background:#0b0b0c; color:#e7e7ea; }
  .wrap { max-width: 880px; margin: 32px auto; padding: 0 16px; }
  h1 { font-size:28px; display:flex; align-items:center; gap:12px; }
  img.logo { height:48px; border-radius:8px; }
  .card { background:#141416; padding:16px; border-radius:12px; margin-top:12px; }
  .log { white-space:pre-wrap; background:#0f1012; padding:12px; border-radius:12px; min-height:100px; }
</style>
<div class='wrap'>
<h1><img src="/lowember_logo.png" class="logo"> Low Ember</h1>
<div class='card'>
  <textarea id='text' style='width:100%;min-height:120px;'></textarea><br>
  <button onclick='send()'>Reply</button>
</div>
<div class='card'><div>Response</div><div id='resp' class='log'></div></div>
<div class='card'><div>Trace</div><div id='trace' class='log'></div></div>
</div>
<script>
async function send(){
  const payload={text:document.getElementById('text').value,depth:1,truth_bias:0,press:true,silence:false};
  const r=await fetch('/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await r.json();
  document.getElementById('resp').textContent=data.reply;
  document.getElementById('trace').textContent=data.trace;
}
</script>
"""
    resp = make_response(html)
    token = sid(request)
    resp.set_cookie('le_sid', token, httponly=True, samesite='Lax')
    return resp

@app.route('/reply', methods=['POST'])
def reply() -> Response:
    token = sid(request); session = SESSIONS[token]; maybe_recharge(session)
    data = request.get_json(force=True); text = (data.get('text') or '').strip()
    if not text: return jsonify({'reply': "Say nothing and I'll keep you company.", 'trace': '', 'fuse': session['fuse']})
    s = detect_depth_signals(text); dscore = depth_score(s)
    payloads = {'mirror': mirror(text),'steelman': steelman(text),
                'stay_hint': stay(text),'cut_hint': cut(text)}
    will_cut = data.get('press') and session['fuse']>0 and 1+dscore>=2
    segs=[payloads['mirror'], payloads['steelman']]
    if will_cut: segs.append(payloads['cut_hint']); session['fuse']-=1
    else: segs.append(payloads['stay_hint'])
    reply_text="\n\n".join(segs)
    trace=json.dumps({'signals':s,'depth_score':dscore,'cut_executed':will_cut,'fuse_after':session['fuse']},indent=2)
    return jsonify({'reply':reply_text,'trace':trace,'fuse':session['fuse']})

# --- Serve the uploaded PNG directly ---
@app.route('/lowember_logo.png')
def logo():
    here = os.path.dirname(__file__)
    return send_file(os.path.join(here, "lowember_logo.png"), mimetype='image/png')

if __name__ == '__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port, debug=True)
