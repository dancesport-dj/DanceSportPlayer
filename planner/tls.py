"""🔒 The TLS setup every HTTPS request of the app goes through.

The system's root certificates plus certifi's. Python on macOS has no CA
file of its own, so checking a server's certificate failed there without
certifi ("certificate verify failed"); the system store stays in, since on
Windows it holds the roots a virus scanner's https check signs with.

No ssl import at the top: a player build without error reports drops the
module (dancesport.spec), and the modules importing this must load there.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ssl import SSLContext


def tls_context() -> SSLContext | None:
    """An ssl.SSLContext for urlopen's `context`, or None in a build without
    ssl — urllib then fails an https URL with its own OSError."""
    try:
        import ssl
    except ImportError:
        return None
    ctx = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        return ctx
    ctx.load_verify_locations(certifi.where())
    return ctx
