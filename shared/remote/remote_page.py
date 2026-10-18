"""📱 The one page the phone remote serves: inline, nothing loaded from outside.

The words on it come from the app (`labels`, already translated), so the
phone speaks the desk's language; the defaults below are the English ones.
Everything the server sends back is put on the page as text, never as markup.
"""
import json
import re

from shared.appearance.iconset import SVG

DEFAULT_LABELS = {
    "title": "DancePlaylist remote",
    "pin": "PIN",
    "enter": "Connect",
    "wrong": "Wrong PIN",
    "locked": "Too many wrong PINs — wait a minute",
    "offline": "No connection to the desk",
    "next": "Next",
    "jump": "Play \"%s\" now? The playing title fades out.",
    "nothing": "Nothing is playing",
    "fade": "Fade out",
    "hold": "Fade & hold",
    "announce": "Announce next dance",
    "xfade": "Crossfade",
    # The deck's own switch says "Auto" in every language, so does this one.
    "auto": "Auto",
    "manual": "Manual",
    "pads": "Cartwall",
    "stop_pads": "Stop all pads",
}

_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>__TITLE__</title>
<style>
:root { color-scheme: dark; --bg:#12161d; --card:#1d2430; --ink:#eef3fb; --dim:#8a97ab;
        --accent:#5aa0ff; --warn:#ff9800; --bad:#e05555; }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:16px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:560px; margin:0 auto; padding:16px; }
.card { background:var(--card); border-radius:14px; padding:14px 16px; margin-bottom:12px; }
#dance { color:var(--accent); font-weight:600; font-size:15px; min-height:1.2em; }
#song { font-size:22px; font-weight:700; margin:2px 0 8px; overflow-wrap:anywhere; }
.times { display:flex; justify-content:space-between; color:var(--dim);
         font-variant-numeric:tabular-nums; }
.times.ending #left { color:var(--bad); font-weight:700; }
#seek { position:relative; padding:14px 0; margin:-6px 0 -14px; touch-action:none;
        cursor:pointer; user-select:none; -webkit-user-select:none; }
.bar { height:8px; background:#2c3646; border-radius:4px; overflow:hidden; }
.bar > div { height:100%; width:0; background:var(--accent); }
#knob { position:absolute; top:50%; left:0; width:18px; height:18px; margin:-9px 0 0 -9px;
        border-radius:50%; background:var(--ink); pointer-events:none; }
#seek.drag #knob { width:26px; height:26px; margin:-13px 0 0 -13px; }
h2 { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim);
     margin:0 0 6px; font-weight:600; }
#next div { padding:3px 0; overflow-wrap:anywhere; }
#next span { color:var(--accent); margin-right:6px; }
#next div.pick { cursor:pointer; border-radius:8px; padding:6px 4px; margin:0 -4px; }
#next div.pick:active { background:#2a3444; }
.row { display:grid; gap:10px; margin-bottom:12px; }
.row.t { grid-template-columns:1fr 1.4fr 1fr; }
.row.f { grid-template-columns:1fr 1fr; }
.row.s { grid-auto-flow:column; grid-auto-columns:1fr; }
button { font:inherit; color:var(--ink); background:#2a3444; border:0; border-radius:14px;
         min-height:64px; font-size:26px; touch-action:manipulation; }
button:active { filter:brightness(1.4); }
button.small { font-size:16px; min-height:52px; }
button.warn { background:#5a3a12; }
button { display:flex; align-items:center; justify-content:center; gap:.4em; }
button svg { width:1.35em; height:1.35em; flex:none; }
button > span { display:flex; align-items:center; }
.fade { color:#d8a0a0; } .panic { color:#e58080; }
button.on { background:#1f4f8a; outline:2px solid var(--accent); }
#pads { display:grid; grid-template-columns:repeat(auto-fill,minmax(96px,1fr)); gap:8px; }
#pads button { font-size:14px; min-height:58px; padding:6px; overflow-wrap:anywhere; }
#pads button.live { outline:3px solid var(--warn); }
#login { text-align:center; }
#login button { display:inline-flex; }   /* a flex box ignores text-align */
#login input { font:inherit; font-size:28px; text-align:center; letter-spacing:.3em;
               /* 8 digits, each with its letter spacing, the padding and the caret */
               width:calc(10ch + 8 * .3em); max-width:100%; box-sizing:border-box;
               padding:8px; border-radius:10px; border:1px solid #3a475b; background:#0e1218;
               color:var(--ink); margin:10px 0; }
#msg { color:var(--warn); min-height:1.3em; text-align:center; }
.hidden { display:none !important; }
</style></head>
<body><main>
<section id="login" class="card hidden">
  <h2 id="l_pin"></h2>
  <input id="pin" inputmode="numeric" autocomplete="off" maxlength="8">
  <div><button id="go" class="small"></button></div>
</section>
<div id="desk" class="hidden">
  <section class="card">
    <div id="dance"></div><div id="song"></div>
    <div class="times" id="times"><span id="played"></span><span id="left"></span></div>
    <div id="seek"><div class="bar"><div id="fill"></div></div><div id="knob"></div></div>
  </section>
  <div class="row t">
    <button data-cmd="prev" aria-label="previous">__I_prev__</button>
    <button data-cmd="toggle" aria-label="play/pause"><span id="i_play">__I_play_circle__</span><span
      id="i_pause" class="hidden">__I_pause_circle__</span></button>
    <button data-cmd="next" aria-label="next">__I_next__</button>
  </div>
  <div class="row f">
    <button data-cmd="fade" class="small"><span class="fade">__I_fade_out__</span><span
      id="b_fade"></span></button>
    <button data-cmd="hold" class="small warn"><span class="panic">__I_panic__</span><span
      id="b_hold"></span></button>
  </div>
  <div class="row"><button data-cmd="announce" class="small" id="b_announce"
    aria-pressed="false">__I_speak__<span id="l_announce"></span></button></div>
  <div class="row s"><button data-cmd="advance" class="small" id="b_advance"
    aria-pressed="false"><span id="i_auto">__I_next__</span><span id="i_manual"
    class="hidden">__I_hand__</span><span id="l_advance"></span></button>
    <button data-cmd="xfade" class="small hidden" id="b_xfade"
      aria-pressed="false">__I_shuffle__<span id="l_xfade"></span></button></div>
  <section class="card"><h2 id="l_next"></h2><div id="next"></div></section>
  <section class="card" id="padcard"><h2 id="l_pads"></h2><div id="pads"></div>
    <div style="margin-top:8px"><button data-cmd="stop_pads" class="small"
      style="width:100%">__I_stop__<span id="b_stop"></span></button></div></section>
</div>
<div id="msg"></div>
</main>
<script>
"use strict";
const L = __LABELS__;
const $ = (id) => document.getElementById(id);
let pin = "";
try { pin = localStorage.getItem("dp_pin") || ""; } catch (e) {}
function savePin(v) { pin = v; try { v ? localStorage.setItem("dp_pin", v)
                                      : localStorage.removeItem("dp_pin"); } catch (e) {} }
// The desk's QR code carries the PIN after the "#": a browser never sends
// that part, so it reaches this page only. Kept, then wiped from the bar.
const fromQr = /^#pin=([0-9]{1,8})$/.exec(location.hash);
if (fromQr) { savePin(fromQr[1]); history.replaceState(null, "", location.pathname); }
$("l_pin").textContent = L.pin; $("go").textContent = L.enter;
$("l_next").textContent = L.next; $("l_pads").textContent = L.pads;
$("b_fade").textContent = L.fade;
$("b_hold").textContent = L.hold;
$("l_announce").textContent = L.announce;
$("l_xfade").textContent = L.xfade;
$("b_stop").textContent = L.stop_pads;
document.title = L.title;
function show(loggedIn, msg) {
  $("login").classList.toggle("hidden", loggedIn);
  $("desk").classList.toggle("hidden", !loggedIn);
  $("msg").textContent = msg || "";
}
function refused(status) {
  if (status === 401) { savePin(""); show(false, L.wrong); return true; }
  if (status === 429) { show(false, L.locked); return true; }
  return false;
}
async function call(method, path, body) {
  const r = await fetch(path, { method, cache: "no-store",
    headers: Object.assign({ "X-Remote-Pin": pin },
                           body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined });
  return r;
}
let padsKey = "";
// A drag on the bar: the fill follows the finger, the poll leaves it alone
// until the desk has seeked, and only the release is sent.
let held = null;
function showBar(f) {
  const pc = (100 * Math.max(0, Math.min(1, f))).toFixed(1) + "%";
  $("fill").style.width = pc; $("knob").style.left = pc;
}
function render(s) {
  $("dance").textContent = s.dance || "";
  $("song").textContent = s.title || L.nothing;
  $("played").textContent = s.played || "";
  $("left").textContent = s.left || "";
  $("times").classList.toggle("ending", !!s.ending);
  $("i_play").classList.toggle("hidden", !!s.playing);
  $("i_pause").classList.toggle("hidden", !s.playing);
  $("b_announce").classList.toggle("on", !!s.announce);
  $("b_announce").setAttribute("aria-pressed", s.announce ? "true" : "false");
  const auto = !!s.advance;
  $("b_advance").classList.toggle("on", auto);
  $("b_advance").setAttribute("aria-pressed", auto ? "true" : "false");
  $("i_auto").classList.toggle("hidden", !auto);
  $("i_manual").classList.toggle("hidden", auto);
  $("l_advance").textContent = auto ? L.auto : L.manual;
  // null: titles cannot cross (Manual, or a pause), and the desk hides it too
  const xf = s.xfade;
  $("b_xfade").classList.toggle("hidden", xf === null || xf === undefined);
  $("b_xfade").classList.toggle("on", !!xf);
  $("b_xfade").setAttribute("aria-pressed", xf ? "true" : "false");
  if (held === null) showBar(s.fraction || 0);
  const nx = $("next"); nx.replaceChildren();
  (s.next || []).forEach(([dance, title], i) => {
    const d = document.createElement("div"), sp = document.createElement("span");
    sp.textContent = dance; d.append(sp, document.createTextNode(title));
    // A tap plays it now, so the phone asks first: a finger scrolling past
    // must not cut the running title off.
    d.className = "pick";
    d.addEventListener("click", () => {
      if (confirm(L.jump.replace("%s", () => title))) send({ cmd: "jump", to: i, title });
    });
    nx.append(d);
  });
  const pads = s.pads || [];
  $("padcard").classList.toggle("hidden", pads.length === 0);
  const key = JSON.stringify(pads.map((p) => [p.label, p.colour]));
  if (key !== padsKey) {
    padsKey = key;
    const box = $("pads"); box.replaceChildren();
    pads.forEach((p, i) => {
      const b = document.createElement("button");
      b.textContent = p.label;
      if (/^#[0-9a-fA-F]{3,8}$/.test(p.colour || "")) b.style.background = p.colour;
      b.addEventListener("click", () => send({ cmd: "pad", pad: i }));
      box.append(b);
    });
  }
  [...$("pads").children].forEach((b, i) => b.classList.toggle("live", !!(pads[i] || {}).live));
}
async function poll() {
  if (!pin) { show(false); return; }
  try {
    const r = await call("GET", "/api/state");
    if (refused(r.status)) return;
    if (r.ok) { render(await r.json()); show(true); }
  } catch (e) { $("msg").textContent = L.offline; }
}
async function send(body) {
  try {
    const r = await call("POST", "/api/cmd", body);
    if (!refused(r.status)) await poll();
  } catch (e) { $("msg").textContent = L.offline; }
}
document.querySelectorAll("button[data-cmd]").forEach((b) =>
  b.addEventListener("click", () => send({ cmd: b.dataset.cmd })));
const seek = $("seek");
function barAt(e) {
  const r = seek.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
}
seek.addEventListener("pointerdown", (e) => {
  seek.setPointerCapture(e.pointerId); seek.classList.add("drag");
  held = barAt(e); showBar(held);
});
seek.addEventListener("pointermove", (e) => {
  if (held !== null && seek.classList.contains("drag")) { held = barAt(e); showBar(held); }
});
seek.addEventListener("pointerup", (e) => {
  if (!seek.classList.contains("drag")) return;
  seek.classList.remove("drag"); held = barAt(e); showBar(held);
  send({ cmd: "seek", to: held }).finally(() => { held = null; });
});
seek.addEventListener("pointercancel", () => { seek.classList.remove("drag"); held = null; });
$("go").addEventListener("click", () => { savePin($("pin").value.trim()); poll(); });
$("pin").addEventListener("keydown", (e) => { if (e.key === "Enter") $("go").click(); });
poll(); setInterval(poll, 1000);
</script></body></html>
"""


# The big player card's own artwork (shared/appearance/iconset.py), so the phone's
# buttons look like the desk's — not like whatever emoji the phone draws.
_ICON_SLOT = re.compile(r"__I_([a-z_]+?)__")


def _svg(name: str) -> str:
    view_box, body = SVG[name]
    return (f'<svg viewBox="{view_box}" fill="currentColor" aria-hidden="true">'
            f'{body}</svg>')


def page_html(labels: dict) -> str:
    words = {**DEFAULT_LABELS, **{k: str(v) for k, v in labels.items()}}
    # Inside a <script>: a "</" in a translation must not end it.
    blob = json.dumps(words, ensure_ascii=False).replace("</", "<\\/")
    title = (words["title"].replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))
    page = _ICON_SLOT.sub(lambda m: _svg(m.group(1)), _PAGE)
    return page.replace("__TITLE__", title).replace("__LABELS__", blob)
