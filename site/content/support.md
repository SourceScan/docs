# Support status

This page separates what is known to work from what does not, including features the old GitBook docs described. Rows were checked on 23 November 2026 against public source code and read-only responses from the live services. Rows on hosted GHCR builds, source snapshot forms and block selection were updated on 25 November 2026.

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
| `sourcescan/cargo-near` with hosted verification | **Verified** | Accepted by the NEAR CLI allowlist. The deployed metadata for all 77 matching Mainnet accounts examined on 23 November 2026 named this image. |
| `ghcr.io/near/cargo-near` with `near contract verify` 0.31.0 or later | **Verified** | [NEAR CLI 0.31.0 release](https://github.com/near/near-cli-rs/releases/tag/v0.31.0) and [allowlist](https://github.com/near/near-cli-rs/blob/5cdedc38e09b23b84ae9d69f6abbb26568dda579/src/commands/contract/verify/mod.rs#L224-L236). |
| `ghcr.io/near/cargo-near` with hosted verification | **Unconfirmed** | Production ran NEAR CLI 0.31.1 on 25 November 2026. That version allows GHCR, but hosted verification has not been confirmed end to end. Registry records do not store the builder image. |
| Any other image, including `docker.io/sourcescan/cargo-near` | **Unsupported** | The NEAR CLI allowlist compares names exactly. Some older testnet records name an image outside today's allowlist; re-verifying those contracts now would fail. |
| Build parameters through `passed_env` | **Unsupported** | The [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L157-L160) says SourceScan and NearBlocks do not yet verify them. |

See [choose a builder image](builders.md) for how to pin either image.

## Features

| Feature | Status | Evidence |
| --- | --- | --- |
| Mainnet and testnet | **Verified** | Separate registries and API data for each network. |
| Public repositories outside GitHub | **Unconfirmed** | The verifier and NEAR CLI accept any public HTTPS Git URL, but all 134 testnet and 77 mainnet records that match deployed code point to `github.com`. The SourceScan explorer links only GitHub snapshots. |
| Source snapshots that are not Git commits, such as `ipfs://` | **Unsupported** | The hosted verifier [requires a `git+` URL pinned to a full commit SHA](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/services/github/github.service.ts), although NEP-330 allows other forms. |
| Snapshots pinned only by `#SHA`, or in `git@host:owner/repo` form | **Unsupported** | The hosted precheck can accept these forms, but the NEAR CLI rebuild takes the commit only from `?rev=` and cannot parse the shorthand. See [source snapshots](how-verification-works.md#source-snapshots). |
| Private repositories | **Unsupported** | The verifier [refuses repositories that are not public](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/controllers/verify/verify.controller.ts#L150-L171). |
| Verification at a chosen block | **Verified** | A positive `blockId` in a direct API request selects the block for the metadata, code and rebuild, if the verifier's RPC nodes still serve it. NearBlocks does not send one. A successful verification can update the record to describe code from that block even if the account now runs other code. [Verify controller](https://github.com/SourceScan/verifier-back/blob/0d986c041a65a010d834c0ffc095f3aea7203012/nest/src/controllers/verify/verify.controller.ts#L96-L143) |
| Status shown as mismatch after a redeploy | **Verified** | Explorers compare hashes at view time; the SourceScan explorer when you open a contract page. NearBlocks shows its verify prompt instead of a mismatch label. |
| Records revoked automatically after a redeploy | **Unsupported** | A redeploy leaves the record in place. A new verification can update its verification details. |
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
