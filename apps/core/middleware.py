import base64
import random
import string
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class HTMLObfuscationMiddleware(MiddlewareMixin):
    """
    Middleware to encrypt HTML response content on-the-fly.
    It generates a dynamic key for each request, encrypts the HTML using XOR,
    and returns a bootstrap wrapper that decrypts it client-side.
    """
    def process_response(self, request, response):
        # Only obfuscate successful HTML responses
        # Skip Django admin pages to avoid breaking admin functionalities
        # Also skip if ?raw=1 parameter is present (for developer debugging)
        if (response.has_header('Content-Type') and 
                response['Content-Type'].startswith('text/html') and 
                not request.path.startswith('/admin/') and
                response.status_code == 200):
            
            # Developer back-door to view raw HTML source during debugging
            if settings.DEBUG and request.GET.get('raw') == '1':
                return response
                
            try:
                original_bytes = response.content
                
                # Generate a random 16-character key
                key = "".join(random.choices(string.ascii_letters + string.digits, k=16))
                key_codes = [ord(char) for char in key]
                
                # Encrypt response content byte-by-byte
                encrypted_bytes = bytearray(b ^ ord(key[i % 16]) for i, b in enumerate(original_bytes))
                ciphertext_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
                
                # Client-side decryption bootstrap
                bootstrap_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script>
        (function() {{
            try {{
                var ciphertext = "{ciphertext_b64}";
                var keyCodes = {key_codes};
                var key = keyCodes.map(function(c) {{ return String.fromCharCode(c); }}).join('');
                var decoded = atob(ciphertext);
                var decrypted = "";
                for (var i = 0; i < decoded.length; i++) {{
                    var charCode = decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length);
                    decrypted += String.fromCharCode(charCode);
                }}
                var utf8String = decodeURIComponent(escape(decrypted));
                document.open();
                document.write(utf8String);
                document.close();
            }} catch (e) {{
                console.error("HTML decryption error:", e);
            }}
        }})();
    </script>
</head>
<body>
</body>
</html>"""
                
                response.content = bootstrap_html.encode('utf-8')
                response['Content-Length'] = str(len(response.content))
            except Exception:
                # Fallback to normal rendering if any error occurs
                pass
                
        return response

