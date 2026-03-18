"""
Create backend registration OTPs (and optionally run full user creation flow).

Default flow:
1) Log in as admin (/api/token)
2) Generate OTP (/api/otp)

Optional full flow:
3) Register user with OTP (/api/register)
4) Optionally verify new user login (/api/token)

Edit the CONFIG section below, then run:
    python3 app/services/create_user_with_otp.py
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


# =========================
# CONFIG (EDIT THESE)
# =========================
API_BASE = "https://apivisits.paradigmops.com"

ADMIN_USERNAME = "eliezer"
ADMIN_PASSWORD = "Anchor2025"

# Choose:
# - "otp_only" (recommended): only generate OTP, user self-registers in frontend
# - "full_flow": script also registers the new user
MODE = "otp_only"

# Only used when MODE == "full_flow"
NEW_USERNAME = ""
NEW_PASSWORD = ""
VERIFY_NEW_USER_LOGIN = True
# =========================


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url=url, data=data, method="POST", headers=req_headers)
    return _send(req)


def _post_form(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    req = urllib.request.Request(url=url, data=data, method="POST", headers=req_headers)
    return _send(req)


def _send(req: urllib.request.Request) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8") if resp else ""
            parsed = json.loads(body) if body else {}
            return resp.getcode(), parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc else ""
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"detail": body or str(exc)}
        return exc.code, parsed
    except Exception as exc:  # noqa: BLE001
        return 0, {"detail": str(exc)}


def main() -> None:
    token_url = f"{API_BASE}/api/token"
    otp_url = f"{API_BASE}/api/otp"
    register_url = f"{API_BASE}/api/register"

    print("1) Logging in as admin...")
    status, token_resp = _post_form(
        token_url,
        {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    if status != 200 or "access_token" not in token_resp:
        raise SystemExit(f"Admin login failed ({status}): {token_resp}")

    admin_access_token = token_resp["access_token"]
    print("   Admin login OK.")

    print("2) Generating OTP...")
    status, otp_resp = _post_json(
        otp_url,
        payload={},
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    if status != 200 or "otp" not in otp_resp:
        raise SystemExit(f"OTP generation failed ({status}): {otp_resp}")

    otp = otp_resp["otp"]
    print(f"   OTP created: {otp}")
    print(f"   OTP expires_at: {otp_resp.get('expires_at')}")

    if MODE == "otp_only":
        print("\nDone. Share this OTP with the user so they can self-register:")
        print(f"OTP: {otp}")
        return

    if MODE != "full_flow":
        raise SystemExit(f"Invalid MODE '{MODE}'. Use 'otp_only' or 'full_flow'.")

    if not NEW_USERNAME or not NEW_PASSWORD:
        raise SystemExit(
            "In full_flow mode, set NEW_USERNAME and NEW_PASSWORD in the config section."
        )

    print("3) Registering new user with OTP...")
    status, register_resp = _post_json(
        register_url,
        {
            "otp": otp,
            "username": NEW_USERNAME,
            "password": NEW_PASSWORD,
        },
    )
    if status != 200:
        raise SystemExit(f"Registration failed ({status}): {register_resp}")

    print("   Registration OK.")
    print(f"   Created user: {register_resp}")

    if VERIFY_NEW_USER_LOGIN:
        print("4) Verifying new user login...")
        status, verify_resp = _post_form(
            token_url,
            {"username": NEW_USERNAME, "password": NEW_PASSWORD},
        )
        if status != 200 or "access_token" not in verify_resp:
            raise SystemExit(f"New user login verification failed ({status}): {verify_resp}")
        print("   New user login verified.")

    print("\nDone.")


if __name__ == "__main__":
    main()
