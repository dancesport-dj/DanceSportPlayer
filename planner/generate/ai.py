"""Optional OpenRouter LLM track suggestions + matching them to the library.

Extracted from dancesport_planner.py (logical split): the OpenRouter config/chat
helpers, prompt building, response parsing and library matching.
"""
import contextlib
import http.client
import json
import logging
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

from planner import secret_store
from planner.models import (  # auto-resolved
    DANCE_NAMES,
    TEMPO_RANGES,
)
from planner.music.library import (  # auto-resolved
    MusicLibrary,
)
from planner.music.parsing import (  # auto-resolved
    norm_title,
)
from planner.store import OPENROUTER
from planner.tls import tls_context

log = logging.getLogger("dancesport.ai")


# ── OpenAI-compatible AI suggestions (OpenRouter by default) ──────────────────
# Any OpenAI-compatible host can stand in for OpenRouter — Mammouth, for one,
# answers on https://api.mammouth.ai/v1 — so the base URL is a setting and every
# endpoint is derived from it.
DEFAULT_API_BASE = "https://openrouter.ai/api/v1"

OPENROUTER_URL = DEFAULT_API_BASE + "/chat/completions"


OPENROUTER_MODELS_URL = DEFAULT_API_BASE + "/models"


def _endpoint(base_url: str, path: str) -> str:
    """One endpoint URL from a base like 'https://api.mammouth.ai/v1'.

    A base that already names the endpoint is taken as it stands, so pasting the
    full chat URL straight out of a provider's docs works too."""
    base = (base_url or DEFAULT_API_BASE).strip().rstrip("/")
    return base if path and base.endswith(path) else base + path


_LOOPBACK = ("localhost", "127.0.0.1", "::1")


def _keyed_endpoint(base_url: str, path: str) -> str:
    """The endpoint a request that carries the API key may go to.

    The key rides in a header, so over plain http anyone on the network reads
    it. Only https leaves the machine; http is fine for a server on this one
    (a local model), where the key never does."""
    url = _endpoint(base_url, path)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" and not (parts.scheme == "http"
                                        and parts.hostname in _LOOPBACK):
        raise RuntimeError(f"Refusing to send the API key to {url}: "
                           f"the base URL must start with https://.")
    return url


def api_host(base_url: str = "") -> str:
    """The host to name in messages — 'openrouter.ai', 'api.mammouth.ai', …"""
    return urllib.parse.urlsplit(_endpoint(base_url, "")).hostname or "the AI host"


def is_openrouter(base_url: str = "") -> bool:
    """OpenRouter's extras — the ranking headers, the free-model filter — are
    meaningless on any other host, so they only go out when it really is them."""
    host = api_host(base_url)
    return host == "openrouter.ai" or host.endswith(".openrouter.ai")


# Reasonable free models to fall back to if the live list can't be fetched.
FREE_MODELS_FALLBACK: list[str] = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


KEY_NAME = 'openrouter_api_key'     # its name in the OS credential store


def load_openrouter_config() -> dict:
    """Return {'api_key', 'model', 'base_url'}: the key from the OS credential
    store (a key an older version left in the file moves there now), the rest
    from the config file, with env-var fallback for the key and the base URL."""
    cfg = {'api_key': '', 'model': FREE_MODELS_FALLBACK[0],
           'base_url': DEFAULT_API_BASE}
    stored = OPENROUTER.read()
    if isinstance(stored, dict):
        cfg.update(stored)
    kept = secret_store.get(KEY_NAME)
    if kept:
        cfg['api_key'] = kept
    elif cfg.get('api_key') and secret_store.put(KEY_NAME, cfg['api_key']):
        OPENROUTER.write({k: v for k, v in stored.items() if k != 'api_key'})
    if not cfg.get('api_key'):
        cfg['api_key'] = os.environ.get('OPENROUTER_API_KEY', '')
    if not cfg.get('base_url'):
        cfg['base_url'] = os.environ.get('OPENROUTER_BASE_URL', '') or DEFAULT_API_BASE
    return cfg


def save_openrouter_config(api_key: str | None, model: str, base_url: str = '',
                           ask_first: bool | None = None) -> None:
    """Write the config. `ask_first` puts this model ahead of the claude CLI;
    a save that leaves it out keeps what is stored. `api_key=None` leaves the
    key where it is: one that came from the environment must not be copied into
    the store by a change of model (#38)."""
    stored = OPENROUTER.read()
    cfg = dict(stored) if isinstance(stored, dict) else {}
    cfg.update({'model': model,
                'base_url': (base_url or '').strip() or DEFAULT_API_BASE})
    # In the OS credential store when there is one; the file only as a fallback.
    if api_key is None:
        pass
    elif not api_key:
        secret_store.delete(KEY_NAME)
        cfg.pop('api_key', None)
    elif secret_store.put(KEY_NAME, api_key):
        cfg.pop('api_key', None)
    else:
        cfg['api_key'] = api_key
    if ask_first is not None:
        cfg['ask_first'] = ask_first
    OPENROUTER.write(cfg)


# How long a model may go without a word or a thought. A guess with room in it:
# a model that hides its reasoning stays this quiet before it answers.
NO_OUTPUT_SECS = 180


class NoOutput(TimeoutError):
    """The host stopped sending anything that is part of the answer."""


def _kept(conn_class, socks: list):
    """`conn_class`, noting every socket it opens in `socks`. The connection
    itself is no use for that: it hands its socket to the response as soon as
    the headers are in, and a stop has to reach a stream too."""
    def make(*args, **kwargs):
        conn = conn_class(*args, **kwargs)
        opened = conn.connect

        def connect():
            opened()
            socks.append(conn.sock)

        conn.connect = connect
        return conn
    return make


class _KeptHttp(urllib.request.HTTPHandler):
    def __init__(self, socks: list):
        super().__init__()
        self.socks = socks

    def http_open(self, req):
        return self.do_open(_kept(http.client.HTTPConnection, self.socks), req)


class _KeptHttps(urllib.request.HTTPSHandler):
    def __init__(self, socks: list):
        self.tls = tls_context()
        super().__init__(context=self.tls)
        self.socks = socks

    def https_open(self, req):
        return self.do_open(_kept(http.client.HTTPSConnection, self.socks), req,
                            context=self.tls)


def _read(req, timeout: float, take, cancel=None):
    """What `take` makes of the response `req` gets. Setting `cancel` (a
    threading.Event) shuts the request's socket: the wait for the answer ends at
    once with an OSError, and the host sees the client leave instead of writing a
    reply nobody reads. Without one it is a plain urlopen."""
    if cancel is None:
        with urllib.request.urlopen(req, timeout=timeout,  # nosec B310: user's endpoint
                                    context=tls_context()) as resp:
            return take(resp)
    socks: list = []
    done = threading.Event()

    def cut():
        # Until the request is over: a stop during the connect finds no
        # socket yet, so it is cut on a later look.
        while not done.wait(0.1):
            if not cancel.is_set():
                continue
            for sock in socks:
                with contextlib.suppress(OSError):
                    sock.shutdown(socket.SHUT_RDWR)

    threading.Thread(target=cut, name="ai-stop", daemon=True).start()
    opener = urllib.request.build_opener(_KeptHttp(socks), _KeptHttps(socks))
    try:
        with opener.open(req, timeout=timeout) as resp:  # nosec B310: user's endpoint
            return take(resp)
    finally:
        done.set()


def _stream_reply(resp, host: str, deadline: float, stall: float) -> dict:
    """The chat completion a streamed reply adds up to. Only the model's own
    words and thinking count as output: a host keeps the line alive with comment
    lines however stuck the model behind it is."""
    started = heard = time.monotonic()
    parts: list[str] = []
    finish = None
    ended = False
    for raw in iter(resp.readline, b''):
        now = time.monotonic()
        line = raw.decode('utf-8', 'replace').strip()
        if line == 'data: [DONE]':
            ended = True
            break
        if line.startswith('data:'):
            try:
                data = json.loads(line[5:])
            except ValueError:
                raise ConnectionError(f"{host} cut the answer off") from None
            choice = (data.get('choices') or [{}])[0]
            if 'error' in data or 'error' in choice:
                return data
            delta = choice.get('delta') or {}
            parts.append(delta.get('content') or '')
            if parts[-1] or delta.get('reasoning') or delta.get('reasoning_content'):
                heard = now
            finish = choice.get('finish_reason') or finish
        if now - heard > stall:
            raise NoOutput(f"{host} sent no output for {stall:g} s")
        if now - started > deadline:
            raise NoOutput(f"{host} did not finish within {deadline:g} s")
    if not ended and finish is None:
        raise ConnectionError(f"{host} cut the answer off")
    return {'choices': [{'message': {'content': ''.join(parts)},
                         'finish_reason': finish}]}


def _take_reply(resp, host: str, deadline: float, stall: float) -> dict:
    """The chat completion in `resp`, whether the host streamed it or not."""
    kind = getattr(resp, 'headers', {}).get('Content-Type', '')
    if 'text/event-stream' in kind:
        return _stream_reply(resp, host, deadline, stall)
    return json.loads(resp.read().decode('utf-8'))


def openrouter_chat(api_key: str, model: str, system: str, user: str,
                    timeout: int = 60, base_url: str = '', cancel=None) -> str:
    """Call an OpenAI-compatible chat endpoint and return the reply text.

    The reply streams, so a model that stops producing raises NoOutput well
    before `timeout`, which limits the whole answer. Setting `cancel` (a
    threading.Event) cuts a request still on the wire."""
    if not api_key:
        raise RuntimeError(f"No API key set for {api_host(base_url)}.")
    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user',   'content': user},
        ],
        'temperature': 0.7,
        'stream': True,
    }).encode('utf-8')
    host = api_host(base_url)
    req = urllib.request.Request(_keyed_endpoint(base_url, '/chat/completions'),
                                 data=body, method='POST')
    req.add_unredirected_header('Authorization', f'Bearer {api_key}')
    req.add_header('Content-Type', 'application/json')
    if is_openrouter(base_url):
        req.add_header('HTTP-Referer', 'https://localhost/danceplaylist')
        req.add_header('X-Title', 'Dancesport Playlist Planner')
    stall = min(NO_OUTPUT_SECS, timeout)
    try:
        data = _read(req, stall, lambda resp: _take_reply(resp, host, timeout, stall),
                     cancel)
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode('utf-8', 'replace')[:300]
        raise RuntimeError(f"{host} HTTP {ex.code}: {detail}") from ex
    except NoOutput:
        raise
    except TimeoutError as ex:
        raise NoOutput(f"{host} sent no output for {stall:g} s") from ex
    try:
        choice = data['choices'][0] if 'error' not in data else data
        # A host that fails after it has started still answers 200, with the
        # error in the body: report it like the HTTP error it is.
        err = choice.get('error')
        if isinstance(err, dict):
            code = f"HTTP {err['code']}" if err.get('code') else "error"
            raise RuntimeError(f"{host} {code}: {str(err.get('message', ''))[:300]}")
        content = choice['message']['content']
    except (KeyError, IndexError, TypeError, AttributeError) as ex:
        # A wrong base URL usually answers with something that is not a chat
        # completion at all — say so instead of dying on a KeyError.
        raise RuntimeError(f"{host} sent no answer: "
                           f"{json.dumps(data)[:300]}") from ex
    if not content:
        # A reply cut at the token limit, or filtered, can come back as null.
        raise RuntimeError(f"{host} sent an empty answer (finish_reason: "
                           f"{choice.get('finish_reason') or 'none given'})")
    return content


def _model_rows(api_key: str, timeout: int, base_url: str) -> list[dict]:
    """The host's /models answer, one dict per model."""
    req = urllib.request.Request(_keyed_endpoint(base_url, '/models'))
    if api_key:
        req.add_unredirected_header('Authorization', f'Bearer {api_key}')
    with urllib.request.urlopen(req, timeout=timeout,  # nosec B310: user's endpoint
                                context=tls_context()) as resp:
        raw = resp.read()
    try:
        rows = json.loads(raw.decode('utf-8')).get('data', [])
        if isinstance(rows, list) and all(isinstance(m, dict) for m in rows):
            return rows
    except (ValueError, AttributeError):
        pass
    raise ConnectionError(f"{api_host(base_url)} sent no model list")


def openrouter_models(api_key: str = '', timeout: int = 30,
                      base_url: str = '') -> list[str]:
    """Every model id the host names, exactly as it names them."""
    rows = _model_rows(api_key, timeout, base_url)
    return sorted({m.get('id', '') for m in rows} - {''})


def openrouter_free_models(api_key: str = '', timeout: int = 30,
                           base_url: str = '') -> list[str]:
    """Fetch the live model list.

    On OpenRouter only the free ones come back (price 0 or ':free'); any other
    host prices nothing in that list, so every id it names is offered."""
    free_only = is_openrouter(base_url)
    free: list[str] = []
    for m in _model_rows(api_key, timeout, base_url):
        mid = m.get('id', '')
        if not mid:
            continue
        if not free_only:
            free.append(mid)
            continue
        pricing = m.get('pricing', {}) or {}
        try:
            is_free = mid.endswith(':free') or (
                float(pricing.get('prompt', 1)) == 0
                and float(pricing.get('completion', 1)) == 0
            )
        except (TypeError, ValueError):
            is_free = mid.endswith(':free')
        if is_free:
            free.append(mid)
    return sorted(set(free))


def build_track_prompt(dance: str | None = None, seed_title: str | None = None,
                       theme: str | None = None, n: int = 12) -> tuple[str, str]:
    """Build (system, user) prompts asking the model for dancesport song suggestions."""
    system = (
        "You are a ballroom and latin dancesport music expert. "
        "Recommend real, well-known songs that fit the request and work for the dance. "
        "Respond ONLY with a JSON array of objects, each having \"artist\" and \"title\". "
        "No commentary, no markdown fences."
    )
    bits: list[str] = []
    if dance:
        bits.append(f"Dance: {DANCE_NAMES.get(dance, dance)}")
        rng = TEMPO_RANGES.get(dance, {}).get('S')
        if rng:
            bits.append(f"tempo about {rng[0]}-{rng[1]} bars per minute")
    if theme:
        bits.append(f"Theme/mood: {theme}")
    if seed_title:
        bits.append(f"Similar in style and feel to: \"{seed_title}\"")
    ctx = "; ".join(bits) if bits else "general dancesport competition"
    user = f"Suggest {n} songs. Context: {ctx}."
    return system, user


_LIST_MARK = re.compile(r'^(?:[-*•]+|\d+[.)])\s*')


def _first_json_list(text: str):
    """The first JSON list in the reply, read from its own '[' to its own
    ']' — a '[note]' after it no longer spoils it. The whole text when
    there is none, so the error names what was wrong."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r'\[', text):
        try:
            data, _end = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(data, list):
            return data
    return json.loads(text)


def parse_ai_suggestions(text: str) -> list[dict[str, str]]:
    """Parse the model reply into a list of {'artist', 'title'} dicts (lenient)."""
    out: list[dict[str, str]] = []
    try:
        data = _first_json_list(text)
        if isinstance(data, list):
            for it in data:
                if isinstance(it, dict):
                    title = str(it.get('title') or it.get('song') or '').strip()
                    artist = str(it.get('artist') or it.get('by') or '').strip()
                    if title:
                        out.append({'artist': artist, 'title': title})
            if out:
                return out
    except Exception as e:
        log.debug("🤖 AI reply is no JSON list, reading it line by line\n"
                  "error: %s", e)
    # Fallback: parse "Artist - Title" lines
    for line in text.splitlines():
        # A bullet or a '1.' / '1)' numbering — not the digits of '10cc'.
        line = _LIST_MARK.sub('', line.strip())
        if not line:
            continue
        if ' - ' in line:
            artist, title = line.split(' - ', 1)
            out.append({'artist': artist.strip(), 'title': title.strip()})
        elif len(line) > 2:
            out.append({'artist': '', 'title': line})
    return out


def match_suggestions_to_library(
    lib: MusicLibrary,
    suggestions: list[dict[str, str]],
    threshold: float = 0.6,
) -> list[dict[str, object]]:
    """Fuzzy-match AI suggestions against the local library.

    Returns a list of {'suggestion', 'entry' (or None if not owned), 'ratio'}.
    """
    index = [(norm_title(e.title), e) for e in lib.entries]
    results: list[dict[str, object]] = []
    for s in suggestions:
        target = norm_title(s.get('title', ''))
        best, best_r = None, 0.0
        if target:
            sm = SequenceMatcher(None)
            sm.set_seq1(target)
            for nt, e in index:
                if not nt:
                    continue
                contains = target in nt or nt in target
                sm.set_seq2(nt)
                # Upper bounds of ratio(): a title that cannot beat the best so
                # far skips the full match (same result, about half the time).
                if not contains and (sm.real_quick_ratio() <= best_r
                                     or sm.quick_ratio() <= best_r):
                    continue
                r = sm.ratio()
                if contains:
                    r = max(r, 0.9)
                if r > best_r:
                    best_r, best = r, e
        owned = best is not None and best_r >= threshold
        results.append({'suggestion': s, 'entry': best if owned else None, 'ratio': best_r})
    return results
