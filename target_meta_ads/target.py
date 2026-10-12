"""MetaAds target class."""


from __future__ import annotations

from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.target_sdk.target import TargetHotglue
from target_meta_ads.auth import MetaAdsAuthenticator
from target_meta_ads.sinks import (
    AudiencesSink,
    AudienceMembersSink,
    RemoveAudienceMembersSink,
)


class TargetMetaAds(TargetHotglue):
    """Target for MetaAds."""

    name = "target-meta-ads"
    SINK_TYPES = [AudiencesSink, AudienceMembersSink, RemoveAudienceMembersSink]

    config_jsonschema = th.PropertiesList(
        th.Property(
            "client_id",
            th.StringType(),
            required=True,
            description="Client identifier for the token endpoint",
        ),
        th.Property(
            "client_secret",
            th.StringType(),
            required=True,
            description="Client secret for the token endpoint",
        ),
        th.Property(
            "refresh_token",
            th.StringType,
            required=True,
            description="Refresh token used to obtain new access tokens",
        ),
        th.Property(
            "access_token",
            th.StringType,
            required=False,
            description="Current access token (usually populated after refresh)",
        ),
        th.Property(
            "expires_in",
            th.IntegerType,
            required=False,
            description="Epoch seconds when the access token expires (updated on refresh)",
        ),
        th.Property(
            "account_id",
            th.StringType(),
            required=True,
            description="Meta Ads ad account ID (with or without the act_ prefix)",
        ),
    ).to_dict()

    @classmethod
    def access_token_support(cls, connector=None):
        return (
            MetaAdsAuthenticator,
            "https://graph.facebook.com/v26.0/oauth/access_token",
        )

if __name__ == "__main__":
    TargetMetaAds.cli()
