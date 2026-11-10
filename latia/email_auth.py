import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID

from flask import current_app


class EmailAuthError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def otp_available():
    url = urlsplit(current_app.config["SUPABASE_URL"])
    secure = url.scheme == "https" or (
        url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
    )
    return bool(secure and url.hostname and current_app.config["SUPABASE_PUBLISHABLE_KEY"])


def auth_request(path, payload):
    if not otp_available():
        raise EmailAuthError("El envío de códigos aún no está configurado.", 503)
    url = current_app.config["SUPABASE_URL"].rstrip("/")
    request = Request(
        f"{url}/auth/v1/{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "apikey": current_app.config["SUPABASE_PUBLISHABLE_KEY"]},
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 429:
            raise EmailAuthError("Demasiados intentos. Espera un momento antes de volver a intentar.", 429) from None
        if path == "verify" and error.code in {400, 403, 422}:
            raise EmailAuthError("El código no es válido o venció. Puedes solicitar uno nuevo.", 422) from None
    except (URLError, TimeoutError, ValueError):
        pass
    raise EmailAuthError("El servicio de correo no está disponible en este momento.", 503)


def send_code(email):
    auth_request("otp", {"email": email, "create_user": True})


def verify_code(email, code):
    result = auth_request("verify", {"email": email, "token": code, "type": "email"})
    try:
        return UUID(result["user"]["id"])
    except (KeyError, ValueError, TypeError):
        raise EmailAuthError("El servicio no devolvió una identidad válida.", 503) from None
