# Copyright (c) 2026 Hotglue
"""MetaAds target sink class, which handles writing streams."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from target_meta_ads.client import MetaAdsBatchSink, MetaAdsRecordSink

DEFAULT_SUBTYPE = "CUSTOM"
DEFAULT_CUSTOMER_FILE_SOURCE = "USER_PROVIDED_ONLY"
MAX_MEMBERS_PER_REQUEST = 10000
_HEX_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def _is_hashed(value: str) -> bool:
    return bool(_HEX_SHA256.match(value))


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_and_hash_email(email: str) -> str:
    """Normalize email (trim + lowercase) and SHA-256 hex-encode it."""
    if _is_hashed(email):
        return email.lower()
    return _sha256_hex(email.strip().lower())


def normalize_and_hash_phone(phone: str) -> str:
    """Normalize phone to digits (no leading zeros) and SHA-256 hex-encode it."""
    if _is_hashed(phone):
        return phone.lower()
    digits = re.sub(r"\D", "", phone.strip()).lstrip("0")
    return _sha256_hex(digits)


class AudiencesSink(MetaAdsRecordSink):
    """Create or update Custom Audiences in Meta Ads."""

    name = "Audiences"

    @property
    def endpoint(self) -> str:
        return f"/{self.account_id}/customaudiences"

    def preprocess_record(self, record: dict, _context: dict) -> dict:
        name = record.get("name")
        if not name:
            message = "Audiences records require name"
            raise ValueError(message)

        payload = {
            "id": record.get("id"),
            "name": name,
            "description": record.get("description"),
            "subtype": record.get("subtype", DEFAULT_SUBTYPE),
            "customer_file_source": record.get(
                "customer_file_source", DEFAULT_CUSTOMER_FILE_SOURCE
            ),
        }
        return self.clean_payload(payload)

    def upsert_record(self, record: dict, _context: dict) -> tuple:
        state_updates = {}
        pk = record.pop("id", None)
        # Graph API uses POST for both create and update.
        if pk:
            endpoint = f"/{pk}"
            state_updates["is_updated"] = True
            # subtype / customer_file_source are create-only fields
            record.pop("subtype", None)
            record.pop("customer_file_source", None)
        else:
            endpoint = self.endpoint

        response = self.request_api("POST", endpoint, request_data=record)
        record_id = pk or response.json().get("id")
        return record_id, True, state_updates


class AudienceUsersSink(MetaAdsBatchSink):
    """Upload hashed emails and phones to a Custom Audience users endpoint."""

    max_size = MAX_MEMBERS_PER_REQUEST
    http_method = "POST"
    relation_fields = [
        {
            "field": "productDestinationId",
            "objectName": "Audiences",
        },
        {
            "field": "audienceId",
            "objectName": "Audiences",
        },
    ]

    def process_batch_record(self, record: dict, _index: int) -> dict:
        audience_id = (
            record.get("audienceId")
            or record.get("productDestinationId")
            or record.get("customAudienceId")
        )
        if not audience_id:
            message = (
                f"{self.name} records require audienceId "
                "(or productDestinationId / customAudienceId)"
            )
            raise ValueError(message)

        email = record.get("email")
        phone = record.get("phone") or record.get("phoneNumber")
        if not email and not phone:
            message = f"{self.name} records require email and/or phone/phoneNumber"
            raise ValueError(message)

        external_id = record.get("externalId") or record.get("id")
        return {
            "_externalId": str(external_id) if external_id is not None else None,
            "_audienceId": str(audience_id),
            "_email": normalize_and_hash_email(str(email)) if email else None,
            "_phone": normalize_and_hash_phone(str(phone)) if phone else None,
        }

    def make_batch_request(self, records: list[dict]) -> list[dict[str, Any]]:
        """Send one users request per audienceId group."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for record in records:
            groups[record["_audienceId"]].append(record)

        results: list[dict[str, Any]] = []
        for audience_id, group in groups.items():
            payload = self._build_payload(group)
            response = self.request_api(
                self.http_method,
                f"/{audience_id}/users",
                request_data={"payload": payload},
            )
            results.append({"records": group, "response": response})
        return results

    def handle_batch_response(self, response: list[dict[str, Any]]) -> dict:
        state_updates = []
        for result in response:
            api_response = result["response"]
            body = api_response.json() if api_response.content else {}
            audience_id = body.get("audience_id")
            invalid_samples = body.get("invalid_entry_samples") or {}
            warning = None
            if body.get("num_invalid_entries"):
                warning = (
                    f"num_invalid_entries={body['num_invalid_entries']}; samples={invalid_samples}"
                )

            for item in result["records"]:
                state = {
                    "externalId": item.get("_externalId"),
                    "success": api_response.ok,
                    "id": audience_id,
                }
                if warning:
                    state["warning"] = warning
                if not api_response.ok:
                    state["error"] = body or api_response.text
                state_updates.append(state)
        return {"state_updates": state_updates}

    def _build_payload(self, records: list[dict]) -> dict:
        has_email = any(item.get("_email") for item in records)
        has_phone = any(item.get("_phone") for item in records)

        if has_email and has_phone:
            return {
                "schema": ["EMAIL", "PHONE"],
                "data": [[item.get("_email") or "", item.get("_phone") or ""] for item in records],
            }
        if has_phone:
            return {
                "schema": "PHONE_SHA256",
                "data": [item["_phone"] for item in records],
            }
        return {
            "schema": "EMAIL_SHA256",
            "data": [item["_email"] for item in records],
        }


class AudienceMembersSink(AudienceUsersSink):
    """Add hashed emails and phones to a Meta Custom Audience."""

    name = "AudienceMembers"


class RemoveAudienceMembersSink(AudienceUsersSink):
    """Remove hashed emails and phones from a Meta Custom Audience."""

    name = "RemoveAudienceMembers"
    http_method = "DELETE"
