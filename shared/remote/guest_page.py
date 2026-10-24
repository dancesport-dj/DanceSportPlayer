"""📨 The page guests open: search the library, request a title, or write a wish
— and, on its second tab, see what plays next.

One page for every way a guest gets here: the desk's own guest server on the
Wi-Fi, or the same server behind a Cloudflare tunnel. Every address on it is
relative (`api/...`): it works under whatever host and path serves it.

The event code travels after the "#" of the address the QR code holds, so the
browser keeps it to itself; the page sends it in a header with every call.
The words come from the app (`labels`, already translated), as on the phone
remote. Everything a server sends back goes onto the page as text, never as
markup.
"""
import json

GUEST_CODE_HEADER = "X-Guest-Code"
MAX_WISH = 120

DEFAULT_LABELS = {
    "title": "Song requests",
    "now": "Now playing",
    "tab_request": "Request a song",
    "tab_next": "Up next",
    "next_empty": "Nothing lined up yet",
    "search": "Search a title or artist",
    "loading": "Loading the titles…",
    "no_hits": "No matching title — write it as a wish below",
    "request": "Request",
    "wish": "Not in the list? Write your wish:",
    "send": "Send",
    "sent": "Thank you — the DJ has your request",
    "too_many": "That was a lot of requests — please wait a few minutes",
    "closed": "Requests are closed right now",
    "old_code": "This link is out of date — scan the current QR code",
    "offline": "No connection to the DJ — try again in a moment",
}

_PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>__TITLE__</title>
<style>
:root { color-scheme: dark; --bg:#12161d; --card:#1d2430; --ink:#eef3fb; --dim:#8a97ab;
        --accent:#5aa0ff; --good:#4caf50; --bad:#e05555; }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:16px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:560px; margin:0 auto; padding:16px; }
h1 { font-size:22px; margin:4px 0 12px; }
.card { background:var(--card); border-radius:14px; padding:12px 14px; margin-bottom:12px; }
h2 { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim);
     margin:0 0 4px; font-weight:600; }
#now { overflow-wrap:anywhere; }
#now span { color:var(--accent); margin-right:6px; }
input { width:100%; font:inherit; color:var(--ink); background:#11161f; border:1px solid #2c3646;
        border-radius:10px; padding:11px 12px; }
input:focus { outline:2px solid var(--accent); border-color:transparent; }
#hits { margin-top:8px; }
.hit { display:flex; align-items:center; gap:10px; padding:8px 0; border-top:1px solid #2a3240; }
.hit:first-child { border-top:none; }
.hit div { flex:1; min-width:0; overflow-wrap:anywhere; }
.hit small { display:block; color:var(--dim); }
.hit .d { color:var(--accent); }
button { font:inherit; font-weight:600; color:#fff; background:var(--accent); border:none;
         border-radius:10px; padding:9px 14px; cursor:pointer; }
button:disabled { opacity:.45; }
.dim { color:var(--dim); }
.tabs { display:flex; gap:6px; margin-bottom:12px; }
.tabs button { flex:1; color:var(--dim); background:var(--card); }
.tabs button.on { color:#fff; background:var(--accent); }
.wishrow { display:flex; gap:8px; margin-top:6px; }
#msg { position:fixed; left:16px; right:16px; bottom:16px; max-width:528px; margin:0 auto;
       padding:12px 14px; border-radius:12px; font-weight:600; display:none; }
#msg.good { display:block; background:var(--good); }
#msg.bad { display:block; background:var(--bad); }
</style></head>
<body><main>
<h1 id="t"></h1>
<div class="card" id="nowcard" hidden><h2 id="nowh"></h2><div id="now"></div></div>
<nav class="tabs">
  <button id="tab_request" type="button" class="on"></button>
  <button id="tab_next" type="button"></button>
</nav>
<section id="pane_request">
<div class="card">
  <input id="q" type="search" autocomplete="off" enterkeyhint="search">
  <div id="hits" class="dim"></div>
</div>
<div class="card">
  <div id="wishh" class="dim"></div>
  <form class="wishrow" id="wishform">
    <input id="wish" maxlength="__MAX__" autocomplete="off">
    <button id="send" type="submit"></button>
  </form>
</div>
</section>
<section id="pane_next" hidden>
<div class="card"><div id="next" class="dim"></div></div>
</section>
<div id="msg"></div>
</main>
<script>
"use strict";
const L = __LABELS__;
const MAX_HITS = 40;
const $ = (id) => document.getElementById(id);
const hash = new URLSearchParams(location.hash.slice(1));
let code = hash.get("e") || "";
try {
  if (code) sessionStorage.setItem("guest-code", code);
  else code = sessionStorage.getItem("guest-code") || "";
} catch (e) { /* private mode: the code stays in the address only */ }
let songs = [];
let msgTimer = 0;
let nowAt = 0;

document.title = L.title;
$("t").textContent = L.title;
$("nowh").textContent = L.now;
$("tab_request").textContent = L.tab_request;
$("tab_next").textContent = L.tab_next;
$("next").textContent = L.next_empty;
$("q").placeholder = L.search;
$("hits").textContent = L.loading;
$("wishh").textContent = L.wish;
$("send").textContent = L.send;

function fold(s) {
  return s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
}

function say(text, good) {
  const m = $("msg");
  m.textContent = text;
  m.className = good ? "good" : "bad";
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => { m.className = ""; }, 4000);
}

function call(path, body) {
  const opt = { headers: { "__HEADER__": code }, cache: "no-store" };
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  return fetch(path, opt);
}

function refusal(status) {
  if (status === 429) return L.too_many;
  if (status === 410) return L.closed;
  if (status === 403) return L.old_code;
  return L.offline;
}

function render() {
  const words = fold($("q").value).split(/\\s+/).filter(Boolean);
  const box = $("hits");
  box.textContent = "";
  if (!words.length) return;
  const found = [];
  for (const s of songs) {
    if (words.every((w) => s.key.includes(w))) {
      found.push(s);
      if (found.length >= MAX_HITS) break;
    }
  }
  if (!found.length) { box.textContent = L.no_hits; return; }
  for (const s of found) {
    const row = document.createElement("div");
    row.className = "hit";
    const text = document.createElement("div");
    text.textContent = s.title;
    const sub = document.createElement("small");
    const dance = document.createElement("span");
    dance.className = "d";
    dance.textContent = s.dance;
    sub.append(dance, s.artist && s.dance ? " · " : "", s.artist);
    text.append(sub);
    const btn = document.createElement("button");
    btn.textContent = L.request;
    btn.onclick = () => send({ song: s.id }, btn);
    row.append(text, btn);
    box.append(row);
  }
}

async function send(body, btn) {
  btn.disabled = true;
  try {
    const r = await call("api/request", body);
    if (r.ok) { say(L.sent, true); return true; }
    say(refusal(r.status), false);
  } catch (e) {
    say(L.offline, false);
  } finally {
    btn.disabled = false;
  }
  return false;
}

async function loadSongs() {
  try {
    const r = await call("api/catalog");
    if (!r.ok) { $("hits").textContent = refusal(r.status); return; }
    const data = await r.json();
    songs = (data.songs || []).map(([id, title, artist, dance]) => ({
      id, title, artist, dance, key: fold([title, artist, dance].join(" ")) }));
    $("hits").textContent = "";
    render();
  } catch (e) {
    $("hits").textContent = L.offline;
    setTimeout(loadSongs, 5000);
  }
}

function renderNext(next) {
  const box = $("next");
  box.textContent = "";
  if (!next.length) { box.textContent = L.next_empty; return; }
  for (const [dance, title] of next) {
    const row = document.createElement("div");
    row.className = "hit";
    const text = document.createElement("div");
    text.textContent = title;
    const sub = document.createElement("small");
    sub.className = "d";
    sub.textContent = dance;
    text.append(sub);
    row.append(text);
    box.append(row);
  }
}

async function loadNow() {
  nowAt = Date.now();
  try {
    const r = await call("api/now");
    if (r.ok) {
      const now = await r.json();
      const box = $("now");
      box.textContent = "";
      if (now.title) {
        const d = document.createElement("span");
        d.textContent = now.dance || "";
        box.append(d, now.title);
      }
      $("nowcard").hidden = !now.title;
      renderNext(now.next || []);
    }
  } catch (e) { /* the next poll tries again */ }
}

function show(next) {
  $("tab_request").className = next ? "" : "on";
  $("tab_next").className = next ? "on" : "";
  $("pane_request").hidden = next;
  $("pane_next").hidden = !next;
  // Fresh on the switch, but flipping back and forth must not spend the
  // read budget the server gives each guest.
  if (next && Date.now() - nowAt > 5000) loadNow();
}

$("tab_request").addEventListener("click", () => show(false));
$("tab_next").addEventListener("click", () => show(true));
$("q").addEventListener("input", render);
$("wishform").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = $("wish").value.trim();
  if (text && await send({ text }, $("send"))) $("wish").value = "";
});
loadSongs();
loadNow();
setInterval(loadNow, 20000);
</script>
</body></html>
"""


def page_html(labels: dict) -> str:
    words = {**DEFAULT_LABELS, **{k: str(v) for k, v in labels.items()}}
    # Inside a <script>: a "</" in a translation must not end it.
    blob = json.dumps(words, ensure_ascii=False).replace("</", "<\\/")
    title = (words["title"].replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))
    return (_PAGE.replace("__TITLE__", title).replace("__LABELS__", blob)
            .replace("__HEADER__", GUEST_CODE_HEADER).replace("__MAX__", str(MAX_WISH)))
