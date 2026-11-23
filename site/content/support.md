# Support status

This page separates what is known to work from what does not, including features the old GitBook docs described. Each row was checked on 23 November 2026 against public source code and read-only responses from the live services.

| Label | Meaning |
| --- | --- |
| **Verified** | Confirmed in public source code or a live read-only response. |
| **Unsupported** | Public source rejects it, never implemented it, or removed it. |
| **Unconfirmed** | Could not be confirmed either way from public evidence. Do not rely on it. |
| **Historical** | Described in old docs or code, and no longer part of the product. |

No verification request was submitted for this review. A row marked **Verified** is not a promise of uptime.

## Languages

| Language or toolchain | Status | Evidence |
| --- | --- | --- |
| Rust built with cargo-near, with NEP-330 `build_info` | **Verified** | The only verify route is `/api/verify/rust`. All 161 testnet and 115 mainnet records have language `rust`. |
| JavaScript or TypeScript with near-sdk-js | **Unsupported** | No verify route exists. TypeScript build code in the backend was never connected to a route and was [removed in December 2025](https://github.com/SourceScan/verifier-back/commit/8d3ae215640dc79c686d658d446ee15dc6db43af). NearBlocks shows JavaScript as a disabled option. near-sdk-js source has no NEP-330 `build_info` support. |
| Other languages compiled to WASM | **Unsupported** | No verify route or builder image exists for them. |
| Rust without reproducible build metadata | **Unsupported** | Verification needs `build_info` in the deployed contract. Rebuild with cargo-near and redeploy. |

## Builder images

| Builder | Status | Evidence |
| --- | --- | --- |
| `sourcescan/cargo-near` with hosted verification | **Verified** | Accepted by every NEAR CLI allowlist. All 77 mainnet records that matched deployed code on 23 November 2026 name this image. |
| `ghcr.io/near/cargo-near` with `near contract verify` 0.31.0 or later | **Verified** | [NEAR CLI 0.31.0 release](https://github.com/near/near-cli-rs/releases/tag/v0.31.0) and [allowlist](https://github.com/near/near-cli-rs/blob/5cdedc38e09b23b84ae9d69f6abbb26568dda579/src/commands/contract/verify/mod.rs#L224-L236). |
| `ghcr.io/near/cargo-near` with hosted verification, as deployed on 23 November 2026 | **Unconfirmed** | Depends on the NEAR CLI version inside the deployed verifier: 0.31.0 and later accept GHCR. The deployed verifier's public source does not fix that version, the running version is not published, and no record names a GHCR image. A verifier release can change this row. |
| Any other image, including `docker.io/sourcescan/cargo-near` | **Unsupported** | The NEAR CLI allowlist compares names exactly. Some older testnet records name an image outside today's allowlist; re-verifying those contracts now would fail. |
| Build parameters through `passed_env` | **Unsupported** | The [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L157-L160) says SourceScan and NearBlocks do not yet verify them. |

See [choose a builder image](builders.md) for how to pin either image.

## Features

| Feature | Status | Evidence |
| --- | --- | --- |
| Mainnet and testnet | **Verified** | Separate registries and API data for each network. |
| Public repositories outside GitHub | **Unconfirmed** | The verifier accepts any public HTTPS or SSH Git URL, but all 134 testnet and 77 mainnet records that match deployed code point to `github.com`. |
| Source snapshots that are not Git commits, such as `ipfs://` | **Unsupported** | The hosted verifier [requires a `git+` URL pinned to a full commit SHA](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/services/github/github.service.ts), although NEP-330 allows other forms. |
| Private repositories | **Unsupported** | The verifier [refuses repositories that are not public](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/controllers/verify/verify.controller.ts#L120-L137). |
| Verification against a chosen historical block | **Unsupported** | The hosted verifier compares with the latest final block. |
| Status shown as mismatch after a redeploy | **Verified** | Explorers compare hashes at view time. NearBlocks shows its verify prompt instead of a mismatch label. |
| Records revoked automatically after a redeploy | **Unsupported** | Records stay until a new verification replaces them. |
| Automatic re-verification of new deployments | **Unconfirmed** | No public service, schedule or source for it is published. Request verification again after each deployment. |
| Source lookup by code hash | **Verified** | API `by-code-hash` and registry `get_contracts_by_code_hash`. |
| Lookup for accounts that run a global contract | **Verified** | Both explorers and NEAR CLI compare the hash from `view_code`, which returns the global code. Twelve such mainnet accounts matched their records on 23 November 2026. |
| Listing or searching all records over HTTP | **Unsupported** | Use the registry's `get_contracts` or `search` view methods. |
| Verification through the BOS widget or a full-access key | **Unsupported** | See [legacy paths](legacy.md#bos-and-full-access-keys). |

## Old GitBook pages

The previous docs at `docs.sourcescan.dev` described plans and features from 2023 and 2024. Each old address forwards to the closest page on this site.

| Old page and claim | Status | Current position |
| --- | --- | --- |
| Supported languages: Rust, with TypeScript "coming soon" | **Unsupported** | Rust only. See [languages](#languages). |
| Automated verification, "coming soon" | **Unconfirmed** | See [features](#features). |
| Continuous monitoring: badges removed when code changes | **Historical** | Explorers compare at view time. See [after a redeploy](results.md#after-a-redeploy). |
| Technical overview: NEAR contract-builder image and JWT-protected temporary folders | **Historical** | Rebuilds now run through NEAR CLI in a pinned cargo-near image. |
| Contract lookup through a BOS widget with an entry point field | **Historical** | Use [NearBlocks, the explorer or RPC](lookup.md). |
| Roadmap for 2023 and 2024 | **Historical** | No current roadmap is published. |
