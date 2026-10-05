"""Optional OpenRouter LLM track suggestions + matching them to the library.

Extracted from dancesport_planner.py (logical split): the OpenRouter config/chat
helpers, prompt building, response parsing and library matching.
"""
import logging

from difflib import SequenceMatcher
import json
import os
import re
import urllib.parse
import urllib.request, urllib.error
from planner.store import OPENROUTER
from planner.models import (  # auto-resolved
    DANCE_NAMES,
    TEMPO_RANGES,
)
from planner.parsing import (  # auto-resolved
    _norm_title,
)
from planner.library import (  # auto-resolved
    MusicLibrary,
)

log = logging.getLogger("dancesport.ai")


# ── OpenAI-compatible AI suggestions (OpenRouter by default) ──────────────────
# Any OpenAI-compatible host can stand in for OpenRouter — Mammouth, for one,
# answers on https://api.mammouth.ai/v1 — so the base URL is a setting and every
# endpoint is derived from it.
DEFAULT_API_BASE = "https://openrouter.ai/api/v1"

OPENROUTER_URL        = DEFAULT_API_BASE + "/chat/completions"


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


def load_openrouter_config() -> dict:
    """Return {'api_key', 'model', 'base_url'} from the config file, with env-var
    fallback for the key and the base URL."""
    cfg = {'api_key': '', 'model': FREE_MODELS_FALLBACK[0],
           'base_url': DEFAULT_API_BASE}
    stored = OPENROUTER.read()
    if isinstance(stored, dict):
        cfg.update(stored)
    if not cfg.get('api_key'):
        cfg['api_key'] = os.environ.get('OPENROUTER_API_KEY', '')
    if not cfg.get('base_url'):
        cfg['base_url'] = os.environ.get('OPENROUTER_BASE_URL', '') or DEFAULT_API_BASE
    return cfg


def save_openrouter_config(api_key: str, model: str, base_url: str = '') -> None:
    OPENROUTER.write({'api_key': api_key, 'model': model,
                      'base_url': (base_url or '').strip() or DEFAULT_API_BASE})


def openrouter_chat(api_key: str, model: str, system: str, user: str,
                    timeout: int = 60, base_url: str = '') -> str:
    """Call an OpenAI-compatible chat endpoint and return the reply text."""
    if not api_key:
        raise RuntimeError(f"No API key set for {api_host(base_url)}.")
    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user',   'content': user},
        ],
        'temperature': 0.7,
    }).encode('utf-8')
    host = api_host(base_url)
    req = urllib.request.Request(_keyed_endpoint(base_url, '/chat/completions'),
                                 data=body, method='POST')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('Content-Type', 'application/json')
    if is_openrouter(base_url):
        req.add_header('HTTP-Referer', 'https://localhost/danceplaylist')
        req.add_header('X-Title', 'Dancesport Playlist Planner')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode('utf-8', 'replace')[:300]
        raise RuntimeError(f"{host} HTTP {ex.code}: {detail}") from ex
    try:
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as ex:
        # A wrong base URL usually answers with something that is not a chat
        # completion at all — say so instead of dying on a KeyError.
        raise RuntimeError(f"{host} sent no answer: "
                           f"{json.dumps(data)[:300]}") from ex


def openrouter_free_models(api_key: str = '', timeout: int = 30,
                           base_url: str = '') -> list[str]:
    """Fetch the live model list.

    On OpenRouter only the free ones come back (price 0 or ':free'); any other
    host prices nothing in that list, so every id it names is offered."""
    req = urllib.request.Request(_keyed_endpoint(base_url, '/models'))
    if api_key:
        req.add_header('Authorization', f'Bearer {api_key}')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    free_only = is_openrouter(base_url)
    free: list[str] = []
    for m in data.get('data', []):
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
    ctx  = "; ".join(bits) if bits else "general dancesport competition"
    user = f"Suggest {n} songs. Context: {ctx}."
    return system, user


def parse_ai_suggestions(text: str) -> list[dict[str, str]]:
    """Parse the model reply into a list of {'artist', 'title'} dicts (lenient)."""
    out: list[dict[str, str]] = []
    m = re.search(r'\[.*\]', text, re.DOTALL)
    raw = m.group(0) if m else text
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            for it in data:
                if isinstance(it, dict):
                    title  = str(it.get('title') or it.get('song') or '').strip()
                    artist = str(it.get('artist') or it.get('by') or '').strip()
                    if title:
                        out.append({'artist': artist, 'title': title})
            if out:
                return out
    except Exception:
        pass
    # Fallback: parse "Artist - Title" lines
    for line in text.splitlines():
        line = line.strip().lstrip('-*0123456789. \t')
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
    index = [(_norm_title(e.title), e) for e in lib.entries]
    results: list[dict[str, object]] = []
    for s in suggestions:
        target = _norm_title(s.get('title', ''))
        best, best_r = None, 0.0
        if target:
            for nt, e in index:
                if not nt:
                    continue
                r = SequenceMatcher(None, target, nt).ratio()
                if target in nt or nt in target:
                    r = max(r, 0.9)
                if r > best_r:
                    best_r, best = r, e
        owned = best is not None and best_r >= threshold
        results.append({'suggestion': s, 'entry': best if owned else None, 'ratio': best_r})
    return results
