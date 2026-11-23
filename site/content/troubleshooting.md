# Troubleshoot verification

Find the symptom, then work through the checks in order. Most failures come from metadata that does not describe the deployed build exactly.

## No source metadata or build info

Confirm the account and network, and that the deployment completed. [Read the deployed metadata](lookup.md#2-read-the-build-metadata) and check that it lists NEP-330 and includes `build_info`.

NearBlocks shows no verification banner when it gets no NEP-330 metadata. That happens when the contract declares none, and also when NearBlocks' metadata call fails or takes longer than 5 seconds, so reload the page or check with RPC before concluding anything. If the metadata lists NEP-330 but has no `build_info`, NearBlocks still shows its **Verify and Publish** prompt, but **Verify Contract** stays disabled.

If the deployed WASM lacks these fields, it cannot be verified as it stands: rebuild with the [reproducible build steps](quickstart.md#pin-the-source-and-build) and deploy again.

## Repository or commit cannot be fetched

Check the repository and exact commit in `source_code_snapshot`. Open both from a signed-out browser session. Make sure all build inputs are committed and every dependency can be fetched publicly. Keep credentials out of commits and build inputs.

The hosted verifier accepts only `git+` snapshots over HTTPS or SSH, pinned to a full 40-character commit; see [source snapshots](how-verification-works.md#source-snapshots). Its answers tell you which rule failed.

| Message | Cause |
| --- | --- |
| `Source snapshot must use git+ URL format` | The snapshot is not a `git+` URL, for example an `ipfs://` reference. |
| `Source snapshot must pin a full 40-character commit SHA` | No commit, or a short or symbolic one such as a branch name. |
| `Repository URL must use HTTPS or SSH` | Another scheme, such as `http://` or `file://`. |
| `Repository URL must not contain secrets` | A user name or password in the URL. |
| `Repository is not publicly accessible` | The repository is private or does not exist. |
| `Pre-verification checks failed: ...` with HTTP 500 | Another fetch failure, including a commit that is not in the public repository. |

[Snapshot checks](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/services/github/github.service.ts) and [pre-verification](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/controllers/verify/verify.controller.ts#L120-L169)

## Image cannot be pulled or build fails

Compare the registry, repository, tag, digest and platform in `build_environment` with what the registry offers. The name must be exactly `sourcescan/cargo-near` or `ghcr.io/near/cargo-near`; `docker.io/sourcescan/cargo-near` fails the allowlist. A tag can have a different digest on Docker Hub and GHCR. Check the toolchain, lockfile and `container_build_command` for that image version. A local pull does not show that the hosted verifier accepts the image. Builds whose metadata includes `passed_env` parameters are not verified by SourceScan or NearBlocks. [Pin the image](builders.md#pin-the-image) and [cargo-near build options](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L145-L160)

## Rebuilt and deployed hashes differ

Check the account, network and current finalized hash. Replay the exact published commit, image digest, contract path, features and build command. Compare the WASM before any stripping, optimization or other post-processing. Compare the same hash encoding: NEAR reports code hashes in base58, while `sha256sum` prints hex. A deployment made while the request runs also changes the code being compared.

To reproduce the comparison locally, with Docker running:

```bash
near contract verify deployed-at buildguide.testnet network-config testnet now
```

## NEAR CLI reports HTTP 429

Older NEAR CLI configurations point at `rpc.testnet.near.org` or `rpc.mainnet.near.org`. NEAR [deprecated those endpoints](https://near.org/blog/deprecation-of-near-org-and-pagoda-co-rpc-endpoints) from June 2025, and they answered with HTTP 429 when checked on 23 November 2026. Point the connection at a current provider from [NEAR's RPC list](https://docs.near.org/api/rpc/providers), for example:

```bash
near config edit-connection testnet --key rpc_url --value https://archival-rpc.testnet.fastnear.com/
```

## Already verified, or source is missing

If the verifier answers `Code hash didn't change`, the account already has a record for this code. Use [lookup](lookup.md) to see it. After a deployment, wait for finality and reload the explorer.

If a record exists but the source browser is empty, list the CID through the [API](api.md#2-list-the-archived-source). NearBlocks shows only `.rs`, `.toml` and `.lock` files and hides folders such as `.cargo`, so other files, including `.cargo/config.toml`, appear only through the API. If the IPFS gateway is unavailable, use the Git snapshot named in the metadata.

A service error or timeout leaves the outcome unknown. [Check the current hash and record](lookup.md#check-it-yourself-with-rpc) before submitting again.

## Status looks wrong

NearBlocks shows its **Verify and Publish** prompt when a record exists for older code, when no record exists, and when its registry call fails. The SourceScan explorer shows **Code Hash Mismatches** when the code lookup fails or the account runs no contract.

If your own check says the account has no contract while an explorer shows a match, you probably compared the `code_hash` from `view_account`. Accounts that run a global contract show `11111111111111111111111111111111` there. Use [`view_code`](lookup.md#1-get-the-deployed-code-hash) instead. [Read the result](results.md#outcomes) for how to tell these apart.

## Get help

Open an issue in the relevant [SourceScan repository on GitHub](https://github.com/SourceScan). A useful report includes the network, public account ID, deployment transaction or block, code hash, public source commit, image reference and a redacted error. Keep keys, seed phrases, credentials, signed payloads and local configuration out of reports.
