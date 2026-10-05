# target-meta-ads

`target-meta-ads` is a Singer target for **MetaAds**, built with the [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK) (`TargetHotglue`, HTTP sinks, SDK authenticators).

This project was generated from the Hotglue target cookiecutter with:

| Option | Value |
|--------|--------|
| `auth_method` | `OAuth2` |
| `sinks` | `Audiences | record, AudienceMembers | batch` |
| `base_url` | `https://graph.facebook.com/v26.0` |

## Project layout

| Path | Role |
|------|------|
| `target_meta_ads/target.py` | `TargetMetaAds` — config schema, `SINK_TYPES`, optional `default_sink_class` and `access_token_support` |
| `target_meta_ads/client.py` | `MetaAdsSink` base class, `RecordSink` / `BatchSink` stubs, `authenticator` |
| `target_meta_ads/sinks.py` | Per-stream sink classes (`FallbackSink` or named `*Sink` classes) |
| `target_meta_ads/auth.py` | Present only when generated with **OAuth2** (removed by cookiecutter hook otherwise) |
| `.secrets/config.json` | Sample config matching your `auth_method` |

## Configuration

Settings are defined in `config_jsonschema` on `TargetMetaAds` in `target_meta_ads/target.py`.
For this project (**OAuth2**), config includes: `client_id`, `client_secret`, `refresh_token`, and optional `access_token` / `expires_in`.

Inspect the live schema:

```bash
target-meta-ads --about
target-meta-ads --about --format=markdown
```

Local secrets: edit `.secrets/config.json` (shape matches `auth_method` above).

## Authentication

| `auth_method` | Implementation |
|---------------|----------------|
| **OAuth2** | `MetaAdsAuthenticator` in `auth.py`; `TargetMetaAds.access_token_support()` returns the authenticator class and token URL (replace the TODO endpoint in `target.py`). |
| **Bearer Token** | `BearerTokenAuthenticator` in `client.py` |
| **Basic Auth** | `BasicAuthenticator` with `username` / `password` |
| **API Key** | `ApiAuthenticator` with configurable header name/prefix |

HTTP calls use `base_url` on `MetaAdsSink` (`https://graph.facebook.com/v26.0` unless you change it in `client.py`).

## Sinks

Sinks are declared at scaffold time as `StreamName | record` or `StreamName | batch`, comma-separated.

Generated with: `Audiences | record, AudienceMembers | batch`
**Named sinks:** `sinks.py` defines one class per stream; `target.py` registers them in `SINK_TYPES`. Implement `endpoint` (and request logic) per sink in `sinks.py` / overrides on `client.py` bases.

Shared HTTP behavior lives in `client.py` (`MetaAdsRecordSink` / `MetaAdsBatchSink` as generated).

## Usage

```bash
target-meta-ads --version
target-meta-ads --help
tap-smoke-test | target-meta-ads --config /path/to/config.json
```

## Developer setup

Prerequisites: Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run target-meta-ads --help
tox -e lint    # ruff check + format
```

For implementation notes and conventions, see `AGENTS.md` (or `CLAUDE.md` if that was selected at generation).

## References

- [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK)
