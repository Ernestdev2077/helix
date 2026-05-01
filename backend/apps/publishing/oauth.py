"""X (Twitter) OAuth 2.0 PKCE helpers.

We don't pull in tweepy.OAuth2UserHandler because it relies on requests/oauthlib
and a session-bound flow that is awkward to drive from a Django view. The
underlying spec is small enough to do directly with httpx, which gives us
predictable behaviour and easy testing.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

X_AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_USER_ME_URL = "https://api.twitter.com/2/users/me"

# read-level scopes are enough to confirm the connection. tweet.write would
# additionally require Basic API tier ($200/mo) — we add it later when
# publishing actually ships.
DEFAULT_SCOPES = ["tweet.read", "users.read", "offline.access"]


@dataclass
class OAuthFlowState:
    state: str
    code_verifier: str
    code_challenge: str

    def to_session_dict(self) -> dict[str, str]:
        return {
            "state": self.state,
            "code_verifier": self.code_verifier,
            "code_challenge": self.code_challenge,
        }

    @classmethod
    def from_session_dict(cls, data: dict[str, str]) -> "OAuthFlowState":
        return cls(
            state=data["state"],
            code_verifier=data["code_verifier"],
            code_challenge=data["code_challenge"],
        )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def make_pkce() -> OAuthFlowState:
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return OAuthFlowState(state=state, code_verifier=verifier, code_challenge=challenge)


def build_x_auth_url(*, client_id: str, redirect_uri: str, flow: OAuthFlowState,
                     scopes: list[str] | None = None) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or DEFAULT_SCOPES),
        "state": flow.state,
        "code_challenge": flow.code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{X_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_x_code(
    *, client_id: str, client_secret: str, redirect_uri: str,
    code: str, code_verifier: str,
) -> dict[str, Any]:
    auth = (client_id, client_secret) if client_secret else None
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "client_id": client_id,
    }
    with httpx.Client(timeout=15.0) as client:
        r = client.post(X_TOKEN_URL, data=data, auth=auth)
        r.raise_for_status()
        return r.json()


def fetch_x_user_me(*, access_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            X_USER_ME_URL,
            headers=headers,
            params={"user.fields": "id,username,name,profile_image_url"},
        )
        r.raise_for_status()
        return r.json().get("data") or {}
