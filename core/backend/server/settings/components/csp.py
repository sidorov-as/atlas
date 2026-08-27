from csp.constants import SELF

# The SPA and Django APIs are same-site in production; Vite is explicitly
# allowed only by the development environment below.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF],
        "img-src": [SELF, "data:"],
        "connect-src": [SELF],
    },
}
