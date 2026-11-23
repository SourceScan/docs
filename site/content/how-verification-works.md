# How verification works

Verification has three parts: build metadata compiled into the contract, a hosted service that rebuilds and compares, and a registry contract that stores the result for explorers to read. This page follows one request through each part, as implemented in the public source on 23 November 2026.

## From API to registry to NearBlocks

1. **The contract describes its own build.** A contract built with cargo-near exposes `contract_source_metadata` ([NEP-330](https://github.com/near/NEPs/blob/095fe98218d2272a0a285008f72bdb3e8957e613/neps/nep-0330.md)). Its `build_info` names the Git source snapshot, the builder image by digest, the build command and the contract path. Version 1.2.0 of the standard added `build_info`, and NEAR's verifier library requires it. [near-verify-rs validation](https://github.com/near/near-verify-rs/blob/2dc29f6408c72a96ac17becef3384c5152d09867/src/types/contract_source_metadata/validate.rs#L9-L33)
2. **A request starts the rebuild.** NearBlocks sends the account ID and network to `POST /api/verify/rust` on `api-v2.sourcescan.dev`. The service reads the metadata, checks that the [source snapshot](#source-snapshots) is a public Git commit it can fetch, then runs `near contract verify deployed-at ACCOUNT_ID network-config NETWORK now`. NEAR CLI rebuilds in the pinned image and compares the result with the code deployed in the latest final block. The API also accepts an optional `blockId`, which changes the block the metadata is read from, but the comparison always uses the latest final block. The request returns only after the rebuild, so it can take minutes. [Verify controller](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/controllers/verify/verify.controller.ts#L98-L137) and [CLI call](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/services/compiler/compiler.service.ts#L33-L41)
3. **A match is archived and recorded.** When NEAR CLI reports identical code, the service pins the repository snapshot to IPFS and writes a record to the registry with the code hash, block height, language `rust` and the IPFS CID. It then answers `Contract verified successfully`. If the account already has a record with the same hash, it answers `Code hash didn't change` and writes nothing. [Record write](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/controllers/verify/verify.controller.ts#L184-L268)
4. **Explorers compare when you look.** NearBlocks and the SourceScan explorer read the registry and compare the recorded hash with the code deployed now. Nothing updates a record when the account is redeployed. See [after a redeploy](results.md#after-a-redeploy).

The registries are `v2-verifier.sourcescan.near` on mainnet and `v2-verifier.sourcescan.testnet` on testnet. Their read methods are listed in the [registry reference](api.md#registry-contract).

## NearBlocks integration

NearBlocks reads SourceScan data on its **Contract Code** page.

- **Status.** NearBlocks calls the contract's `contract_source_metadata` and the registry's `get_contracts_by_code_hash`, takes the first record returned, and shows **Contract Source Code Verified** when that record's hash equals the deployed hash. Otherwise it shows its **Verify and Publish** prompt, including when the registry call fails. It shows neither when it gets no NEP-330 metadata, which also happens when the metadata call fails or takes longer than 5 seconds. [Code page](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/app/%5Blang%5D/address/%5Baddress%5D/contract/code/page.tsx)
- **Source files.** NearBlocks lists the record's CID through `https://api.sourcescan.dev/api/ipfs/structure`, keeps `.rs`, `.toml` and `.lock` files under `contract_path`, skips the `.git`, `.github`, `.cargo`, `.vscode`, `node_modules` and `target` folders, and loads each file by its own IPFS hash. If loading fails, it shows **Failed to load source files** or **No Rust source files found**. [Source viewer](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/ipfs.tsx#L56-L198)
- **Verify page.** `/verify-contract?account=ACCOUNT_ID` shows the registry, standard, language and build environment, and its **Verify Contract** button sends `accountId` and `networkId` to SourceScan. The button is disabled when the metadata lacks NEP-330, `build_environment` or `source_code_snapshot`. The language is fixed to Rust. [Verify form](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/address/contract/verifier.tsx#L66-L78)

## SourceScan explorer

The [SourceScan explorer](https://app.sourcescan.dev/) lists registry records by network. Its contract page reads the account's own record with `get_contract`, compares it with the hash that `view_code` returns for the account, and links to the Git snapshot and to a code viewer for the IPFS copy. Older `sourcescan.dev` links forward to the same path on `app.sourcescan.dev`. See [labels and their meaning](lookup.md#in-the-sourcescan-explorer).

## Source snapshots

A record points to source in two ways.

- **IPFS archive.** At verification time, SourceScan pins the source snapshot to its IPFS node and stores the CID in the record. A CID is derived from the content, so the same CID always identifies the same files. Reads go through `api.sourcescan.dev`. How long SourceScan keeps content pinned is not published.
- **Git snapshot.** `source_code_snapshot` in the metadata is a repository URL with a commit, for example `git+https://github.com/OWNER/REPO?rev=COMMIT`. It is the input the verifier rebuilt from. The repository owner controls whether it stays available.

The hosted verifier accepts a snapshot only in this form. [Snapshot checks](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/services/github/github.service.ts)

- It starts with `git+`.
- The repository URL uses HTTPS or SSH, including the `git@host:owner/repo` form, and contains no user name or password in an HTTPS URL.
- It pins a full 40-character commit SHA, as `?rev=SHA` or `#SHA`.

NEP-330 also allows other references, such as `ipfs://` snapshots. The hosted verifier rejects them.

If the IPFS gateway is unavailable, the Git snapshot is still a usable copy as long as it exists, and the reverse is also true.

## Who can write records

Only the registry's owner account can add, replace or remove verification records, so a record is an attestation by SourceScan's service. The registry also has public methods for votes and comments on records. They are separate from verification and do not change a record's code hash or CID. [Registry source](https://github.com/SourceScan/verifier-contract/blob/18aea3e8c579555ccedd4c585347699affd07f84/src/lib.rs#L46-L110)

To check a result without relying on SourceScan, [rebuild it yourself](results.md#what-a-match-proves).
