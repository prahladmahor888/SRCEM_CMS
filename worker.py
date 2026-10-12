import os
import traceback
import hashlib
import struct

# Polyfill hashlib.pbkdf2_hmac for Pyodide WebAssembly environment
if not hasattr(hashlib, "pbkdf2_hmac"):
    def _pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        if isinstance(password, str):
            password = password.encode("utf-8")
        if isinstance(salt, str):
            salt = salt.encode("utf-8")
        digest_mod = getattr(hashlib, hash_name, None)
        if digest_mod is None:
            digest_mod = lambda data=b"": hashlib.new(hash_name, data)
        digest_size = digest_mod().digest_size
        if dklen is None:
            dklen = digest_size
        block_size = digest_mod().block_size
        if len(password) > block_size:
            key = digest_mod(password).digest()
        else:
            key = password.ljust(block_size, b"\0")
        ipad = bytes(b ^ 0x36 for b in key)
        opad = bytes(b ^ 0x5C for b in key)
        inner_base = digest_mod(ipad)
        outer_base = digest_mod(opad)
        blocks = (dklen + digest_size - 1) // digest_size
        res = bytearray()
        for block_num in range(1, blocks + 1):
            h = inner_base.copy()
            h.update(salt + struct.pack(">I", block_num))
            inner_d = h.digest()
            h2 = outer_base.copy()
            h2.update(inner_d)
            u = h2.digest()
            t = bytearray(u)
            for _ in range(iterations - 1):
                h = inner_base.copy()
                h.update(u)
                inner_d = h.digest()
                h2 = outer_base.copy()
                h2.update(inner_d)
                u = h2.digest()
                for j in range(digest_size):
                    t[j] ^= u[j]
            res.extend(t)
        return bytes(res[:dklen])

    hashlib.pbkdf2_hmac = _pbkdf2_hmac

# Ensure Cloudflare Worker runtime environment variables are set for Django
os.environ["DJANGO_SETTINGS_MODULE"] = "SRCEM_CMS.settings"
os.environ["DB_ENGINE"] = "d1"
os.environ["CLOUDFLARE_BINDING"] = "DB"
os.environ["DEBUG"] = "False"

from workers import WorkerEntrypoint, Response
from django_cf import DjangoCF
from SRCEM_CMS.wsgi import application
import django.utils.crypto
django.utils.crypto.pbkdf2 = lambda password, salt, iterations, dklen=0, digest=None: _pbkdf2_hmac(
    digest().name if digest else "sha256", password, salt, iterations, dklen
)

# Cloudflare Worker Django-CF entrypoint
class Default(DjangoCF, WorkerEntrypoint):
    def get_app(self):
        return application

    async def fetch(self, request):
        try:
            return await super().fetch(request)
        except Exception as e:
            tb = traceback.format_exc()
            error_html = f"""<!DOCTYPE html>
<html>
<head><title>SRCEM CMS - Runtime Error</title></head>
<body style="font-family: Consolas, monospace; background: #0f172a; color: #f87171; padding: 30px; line-height: 1.6;">
    <h2 style="color: #ef4444; border-bottom: 2px solid #334155; padding-bottom: 10px;">Django Cloudflare Worker Runtime Exception</h2>
    <p style="color: #94a3b8;">The Worker caught an exception during request execution:</p>
    <pre style="background: #1e293b; color: #f1f5f9; padding: 20px; border-radius: 8px; overflow-x: auto; font-size: 14px; border: 1px solid #475569;">{tb}</pre>
</body>
</html>"""
            return Response(error_html, status=500, headers={"content-type": "text/html; charset=utf-8"})




