from django.contrib.auth.hashers import PBKDF2PasswordHasher

class CloudflarePBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """
    PBKDF2PasswordHasher with 10,000 iterations tailored for Cloudflare Workers / WebAssembly.
    Ensures password verification executes in ~15-20ms, safely below Cloudflare's 50ms CPU limit.
    """
    iterations = 10000
