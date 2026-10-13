# Copyright (c) 2026 Hotglue
"""HTTP client and sink base classes for MetaAds."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from hotglue_singer_sdk.target_sdk.client import HotglueBaseSink, HotglueBatchSink, HotglueSink

if TYPE_CHECKING:
    from hotglue_singer_sdk.plugin_base import PluginBase


class MetaAdsSink(HotglueBaseSink):
    """MetaAds Base target sink class for sinks."""

    base_url = "https://graph.facebook.com/v26.0"

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: dict,
        key_properties: list[str] | None,
    ) -> None:
        """Initialize the sink and a single authenticator for its lifetime."""
        super().__init__(target, stream_name, schema, key_properties)
        authenticator_class, auth_endpoint = self._target.access_token_support(self._target)
        self.authenticator = authenticator_class(self._target, {}, auth_endpoint)

    @property
    def account_id(self) -> str:
        """Ad account ID with the ``act_`` prefix required by the Graph API."""
        account_id = str(self.config["account_id"])
        if account_id.startswith("act_"):
            return account_id
        return f"act_{account_id}"


class MetaAdsRecordSink(MetaAdsSink, HotglueSink):
    """MetaAds Record target sink class for record sinks."""

    name = "MetaAdsRecordSink"

    def preprocess_record(self, record: dict, _context: dict) -> dict:
        # TODO: preprocess each record if needed (SDK calls this for every record).
        return record

    def upsert_record(self, record: dict, _context: dict) -> None:
        # Called for each record on all sinks unless overridden.
        state_updates = {}
        pk_field = self.key_properties[0] if self.key_properties else "id"
        pk = record.get(pk_field)
        method = "POST"
        endpoint = self.endpoint

        if pk:
            method = "PATCH"
            endpoint = f"{endpoint}{pk}"
            state_updates["updated"] = True

        response = self.request_api(method, endpoint, request_data=record)
        record_id = pk or response.json().get("id")
        return record_id, True, state_updates


class MetaAdsBatchSink(MetaAdsSink, HotglueBatchSink):
    """MetaAds Batch target sink class for batch sinks."""

    name = "MetaAdsBatchSink"

    def process_batch_record(self, record: dict, _index: int) -> dict:
        return record

    @abstractmethod
    def make_batch_request(self, records: list[dict]) -> Any:
        # TODO: build the batch API request (SDK calls this per batch).
        return self.request_api("POST", self.endpoint, request_data=records)

    def handle_batch_response(self, _response: Any) -> dict:
        """Return per-record state updates from the batch response.

        ``state_updates`` has one entry per input record, with ``success`` and
        any available ``id``, ``externalId``, ``error``, or ``is_updated``.
        """
        return {"state_updates": []}
