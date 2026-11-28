# Troubleshoot verification

Find the symptom, then work through the checks in order. Most failures come from metadata that does not describe the deployed build exactly.

## No source metadata or build info

Confirm the account and network, and that the deployment completed. [Read the deployed metadata](lookup.md#2-read-the-build-metadata) and check that it lists NEP-330 and includes `build_info`.

The NearBlocks **Contract Code** page shows no verification banner when it gets no NEP-330 metadata. That happens when the contract declares none, and also when NearBlocks' metadata call fails or takes longer than 5 seconds, so reload the page or check with RPC before concluding anything. If the metadata lists NEP-330 but has no `build_info`, the code page can still show **Verify and Publish**. On the verification page, **Verify Contract** stays disabled.

If the deployed WASM lacks these fields, it cannot be verified as it stands: rebuild with the [reproducible build steps](quickstart.md#pin-the-source-and-build) and deploy again.

## Repository or commit cannot be fetched

Check the repository and exact commit in `source_code_snapshot`. Open both from a signed-out browser session. Make sure all build inputs are committed and every dependency can be fetched publicly. Keep credentials out of commits and build inputs.

Use a public HTTPS repository pinned with `?rev=` to the full 40-character commit, as `git+https://github.com/OWNER/REPO?rev=COMMIT`. See [source snapshots](how-verification-works.md#source-snapshots).

## Hosted verifier responses

| Message | HTTP status | Cause and next step |
| --- | --- | --- |
| `Could not read the verifier registry for ${accountId}. Please retry later.` | 503 | The registry read failed or returned a malformed reply. The verifier stops before looking up metadata or starting a build. Wait and retry the request. |
| `No source metadata found for <account>` | 400 | The metadata read returned no metadata or no `build_info`. [Check the deployed metadata](#no-source-metadata-or-build-info). |
| `Source snapshot must use git+ URL format` | 400 | The snapshot is not a `git+` URL, for example an `ipfs://` reference. |
| `Source snapshot must pin a full 40-character commit SHA` | 400 | No commit, or a short or symbolic one such as a branch name. |
| `Source snapshot must not contain conflicting commit SHAs` | 400 | The `?rev=` query parameter and `#` fragment pin different commits. Keep only `?rev=` with the correct full SHA. |
| `Repository URL must use HTTPS or SSH` | 400 | Another scheme, such as `http://` or `file://`. |
| `Repository URL must not contain secrets` | 400 | A password in the URL or a user name in an HTTPS URL. |
| `Repository is not publicly accessible: <repository URL>. Contract verification requires public repositories.` | 400 | Git could not authenticate or find the repository. |
| `Block ${blockHeight} is older than the verified record for ${accountId} at block ${recordHeight}. Verify at block ${recordHeight} or later.` | 409 | The deployed hash differs from the recorded hash, and the pinned block is below the record's `block_height`. Choose the recorded height or a later one. Omit `blockId` to use the latest finalized block. |
| `Pre-verification checks failed: ...` | 500 | Another failure before the rebuild, such as a commit that is not in the public repository, or an RPC read that failed, including for a `blockId` the verifier's RPC nodes no longer serve. |
| `Contract verification failed` | 400 | NEAR CLI did not report a match, or the rebuilt hash differs from the deployed hash at the verification block. [Compare the hashes](#rebuilt-and-deployed-hashes-differ). |
| Any other message with HTTP 500 | 500 | Read the error for the cause. The rebuild, IPFS archive or registry write can fail. If NEAR CLI rejects a snapshot pinned only by `#SHA` or using `git@host:owner/repo`, use a public HTTPS URL pinned with `?rev=`. |

[Registry read response](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/controllers/verify/verify.controller.ts#L86-L101), [pre-verification](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/controllers/verify/verify.controller.ts#L111-L232), [snapshot parsing](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/services/github/github.service.ts#L29-L52), [commit selection and URL checks](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/services/github/github.service.ts#L82-L168) and [rebuild and record write](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/controllers/verify/verify.controller.ts#L234-L340)

## Image cannot be pulled or build fails

Compare the registry, repository, tag, digest and platform in `build_environment` with what the registry offers. The name must be exactly `sourcescan/cargo-near` or `ghcr.io/near/cargo-near`; `docker.io/sourcescan/cargo-near` fails the allowlist. A tag can have a different digest on Docker Hub and GHCR. Check the toolchain, lockfile and `container_build_command` for that image version. A local pull does not show that the hosted verifier accepts the image. Builds whose metadata includes `passed_env` parameters are not verified by SourceScan or NearBlocks. [Pin the image](builders.md#pin-the-image) and [cargo-near build options](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L145-L160)

## Rebuilt and deployed hashes differ

Check the account, network and current finalized hash. Replay the exact published commit, image digest, contract path, features and build command. Compare the WASM before any stripping, optimization or other post-processing. Compare the same hash encoding: NEAR reports code hashes in base58, while `sha256sum` prints hex. The hosted verifier compares the code deployed at the block where it read the metadata, so a deployment after that block is not part of the request; request again once the new code is final.

To reproduce the comparison locally, run this with Docker running. To check an earlier block, such as the one a record names, replace `now` with `at-block-height HEIGHT`; old blocks need an archival RPC.

```bash
near contract verify deployed-at buildguide.testnet network-config testnet now
```

## NEAR CLI reports HTTP 429

Older NEAR CLI configurations point at `rpc.testnet.near.org` or `rpc.mainnet.near.org`. NEAR [deprecated those endpoints](https://near.org/blog/deprecation-of-near-org-and-pagoda-co-rpc-endpoints) from June 2025, and they answered with HTTP 429 when checked on 23 November 2026. Point the connection at a current provider from [NEAR's RPC list](https://docs.near.org/api/rpc/providers), for example:

```bash
near config edit-connection testnet --key rpc_url --value https://archival-rpc.testnet.fastnear.com/
```

## Already verified, or source is missing

If the verifier answers HTTP 400 with `Code hash didn't change`, the account already has a record for the code at the selected block. The verifier returns this response before cloning the repository or starting a build. Use [lookup](lookup.md) to see the record. After a deployment, wait for finality and reload the explorer. [Unchanged hash check](https://github.com/SourceScan/verifier-back/blob/787aa12cc918b637e4a2ed176b0118fcdc1e96ec/nest/src/controllers/verify/verify.controller.ts#L155-L162)

If a record exists but the source browser is empty, list the CID through the [API](api.md#2-list-the-archived-source). NearBlocks shows only `.rs`, `.toml` and `.lock` files and hides folders such as `.cargo`, so other files, including `.cargo/config.toml`, appear only through the API. If the IPFS gateway is unavailable, use the Git snapshot named in the metadata.

If the request times out or the outcome is unclear, [check the current hash and record](lookup.md#check-it-yourself-with-rpc) before submitting again.

## Status looks wrong

NearBlocks shows its **Verify and Publish** prompt when a record exists for older code, when no record exists, and when its registry call fails. The SourceScan explorer separates those cases, but shows **No code is deployed on this account** also for an account that does not exist, and **Deployed code status unknown** when its RPC read fails.

If your own check says the account has no contract while an explorer shows a match, you probably compared the `code_hash` from `view_account`. Accounts that run a global contract show `11111111111111111111111111111111` there. Use [`view_code`](lookup.md#1-get-the-deployed-code-hash) instead. [Read the result](results.md#outcomes) for how to tell these apart.

## Get help

Open an issue in the relevant [SourceScan repository on GitHub](https://github.com/SourceScan). A useful report includes the network, public account ID, deployment transaction or block, code hash, public source commit, image reference and a redacted error. Keep keys, seed phrases, credentials, signed payloads and local configuration out of reports.
