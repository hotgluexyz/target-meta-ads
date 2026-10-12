# Copyright (c) 2026 Hotglue
"""Authentication helpers for MetaAds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from hotglue_singer_sdk.target_sdk.auth import OAuthAuthenticator

if TYPE_CHECKING:
    from hotglue_singer_sdk.plugin_base import PluginBase

# Absolute Unix expiry timestamps are well above this; relative TTLs are not.
_ABSOLUTE_EXPIRY_THRESHOLD = 1_000_000_000


class MetaAdsAuthenticator(OAuthAuthenticator):
    """OAuth 2.0 authenticator for Meta Ads (Graph API)."""

    def __init__(
        self,
        target: PluginBase,
        state: dict[str, Any],
        auth_endpoint: str | None = None,
    ) -> None:
        """Initialize the authenticator.

        Args:
            target: The Singer target instance.
            state: Authentication state.
            auth_endpoint: Token endpoint URL (from ``target.access_token_support``).
        """
        super().__init__(target, state, auth_endpoint=auth_endpoint)
        # Seed validity from config so a provided access_token can be used without
        # an immediate refresh (SDK treats last_refreshed=None as expired).
        if self._config.get("access_token"):
            now = datetime.now(tz=timezone.utc)
            self.last_refreshed = now
            expires_in = self._config.get("expires_in")
            if expires_in is not None:
                expires_in = int(expires_in)
                if expires_in < _ABSOLUTE_EXPIRY_THRESHOLD:
                    self.expires_in = int(now.timestamp()) + expires_in
                else:
                    self.expires_in = expires_in

    @property
    def oauth_request_body(self) -> dict:
        """OAuth request body for Meta's fb_exchange_token grant."""
        return {
            "grant_type": "fb_exchange_token",
            "client_id": self._config["client_id"],
            "client_secret": self._config["client_secret"],
            "fb_exchange_token": self._config.get("access_token"),
        }
