"""Auto-loaded at interpreter startup (Python imports `sitecustomize` if it's on
sys.path). Used ONLY during the OpenL3 build, whose setup.py downloads model
weights with stdlib `urllib` and fails behind a corporate TLS-intercepting proxy
(`CERTIFICATE_VERIFY_FAILED`).

We relax the stdlib default HTTPS context so that one build-time download works.
This does NOT affect pip — pip uses its own vendored urllib3/certifi stack. The
traffic goes through the same corporate proxy that already MITMs every
connection, so this only skips a verification that the proxy makes meaningless
anyway.

Being on PYTHONPATH is not enough: a shell that kept it set after the install
would run every later Python — the app's API calls included — unverified. The
build has to ask for it by name with DANCEPLAYLIST_INSECURE_BUILD_TLS=1, and it
says so on stderr whenever it acts.
"""
import os
import sys

if os.environ.get("DANCEPLAYLIST_INSECURE_BUILD_TLS") == "1":
    try:
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        sys.stderr.write("_build_shims: HTTPS certificate checks are OFF "
                         "for this process (DANCEPLAYLIST_INSECURE_BUILD_TLS=1)\n")
    except Exception:
        pass
