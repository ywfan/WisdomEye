class ExternalError(Exception):
    """Represents external-call failures with a short code and optional detail."""
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail

def classify_http(status: int) -> str:
    """Map HTTP status code to coarse error category."""
    if status >= 500:
        return "server_error"
    if status == 429:
        return "rate_limited"
    if status == 401 or status == 403:
        return "unauthorized"
    if status >= 400:
        return "bad_request"
    return "ok"
"""Lightweight error types and HTTP status classification."""
