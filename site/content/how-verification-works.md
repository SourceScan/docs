# How verification works

Verification has three parts: build metadata compiled into the contract, a hosted service that rebuilds and compares, and a registry contract that stores the result for explorers to read. This page follows one request through each part, as implemented in the public source on 25 November 2026.

## From API to registry to NearBlocks

1. **The contract describes its own build.** A contract built with cargo-near exposes `contract_source_metadata` ([NEP-330](https://github.com/near/NEPs/blob/095fe98218d2272a0a285008f72bdb3e8957e613/neps/nep-0330.md)). Its `build_info` names the Git source snapshot, the builder image by digest, the build command and the contract path. Version 1.2.0 of the standard added `build_info`, and NEAR's verifier library requires it. [near-verify-rs validation](https://github.com/near/near-verify-rs/blob/2dc29f6408c72a96ac17becef3384c5152d09867/src/types/contract_source_metadata/validate.rs#L9-L33)
2. **A request starts the rebuild at one block.** NearBlocks sends the account ID and network to `POST /api/verify/rust` on `api-v2.sourcescan.dev`. The service reads the metadata and pins the code comparison to the block hash returned with it. It reads the deployed code hash there, checks that the [source snapshot](#source-snapshots) is a public Git commit it can fetch, then runs `near contract verify deployed-at ACCOUNT_ID network-config NETWORK at-block-hash BLOCK_HASH`. NEAR CLI reads the same metadata and code, rebuilds in the pinned image and compares. Without a `blockId`, or with `blockId` 0, the metadata read starts from the latest finalized block; NearBlocks sends none. A positive `blockId` in a direct API request selects a height the verifier's RPC nodes must still serve. A rebuild can take several minutes. [Verify controller](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/controllers/verify/verify.controller.ts#L96-L143) and [CLI call](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/services/compiler/compiler.service.ts#L34-L43)
3. **A match is archived and recorded.** When NEAR CLI reports identical code and its hash equals the deployed hash at that block, the service pins the repository snapshot to IPFS and records the code hash, block height, language `rust` and IPFS CID. It then answers `Contract verified successfully`. If the account's record already has the same hash, it answers `Code hash didn't change` and writes nothing. Each account has one record. A successful verification updates those four fields on an existing record and keeps its votes and comments. The registry accepts writes at any block height, so a request for an earlier block, or a slower request that finishes later, can update the record to describe code the account no longer runs. [Record write](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/controllers/verify/verify.controller.ts#L240-L305) and [registry](https://github.com/SourceScan/verifier-contract/blob/18aea3e8c579555ccedd4c585347699affd07f84/src/lib.rs#L61-L97)
4. **Explorers compare when you look.** NearBlocks looks records up by the deployed code hash. The SourceScan explorer reads the account's own record and checks the deployed code when you open its contract page. Nothing updates a record when the account is redeployed. See [after a redeploy](results.md#after-a-redeploy).

The registries are `v2-verifier.sourcescan.near` on mainnet and `v2-verifier.sourcescan.testnet` on testnet. Their read methods are listed in the [registry reference](api.md#registry-contract).

## NearBlocks integration

NearBlocks reads SourceScan data on its **Contract Code** page.

- **Status.** NearBlocks calls the contract's `contract_source_metadata` and the registry's `get_contracts_by_code_hash`, takes the first record returned, and shows **Contract Source Code Verified** when that record's hash equals the deployed hash. Otherwise it shows its **Verify and Publish** prompt, including when the registry call fails. It shows neither when it gets no NEP-330 metadata, which also happens when the metadata call fails or takes longer than 5 seconds. [Code page](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/app/%5Blang%5D/address/%5Baddress%5D/contract/code/page.tsx)
- **Source files.** NearBlocks lists the record's CID through `https://api.sourcescan.dev/api/ipfs/structure`, keeps `.rs`, `.toml` and `.lock` files under `contract_path`, skips the `.git`, `.github`, `.cargo`, `.vscode`, `node_modules` and `target` folders, and loads each file by its own IPFS hash. If loading fails, it shows **Failed to load source files** or **No Rust source files found**. [Source viewer](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/ipfs.tsx#L56-L198)
- **Verify page.** `/verify-contract?account=ACCOUNT_ID` shows the registry, standard, language and build environment, and its **Verify Contract** button sends `accountId` and `networkId` to SourceScan. The button is disabled when the deployed code is already verified or the metadata lacks NEP-330, `build_environment` or `source_code_snapshot`. The language is fixed to Rust. [Submission](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/address/contract/verifier.tsx#L67-L96) and [button state](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/address/contract/verifier.tsx#L294-L308)

## SourceScan explorer

The [SourceScan explorer](https://app.sourcescan.dev/) lists registry records by network without checking deployed code. When you open a record, your browser reads the current finalized code hash through a public RPC endpoint and compares it with the recorded hash. The **Verified source** tab reads from the recorded IPFS CID. The **Build** tab reads live metadata, which can also determine the **Repository** link. After a redeploy, that metadata may refer to a different build than the archived source. Older `sourcescan.dev` links forward to the same path on `app.sourcescan.dev`. See [labels and their meaning](lookup.md#in-the-sourcescan-explorer). [Explorer source](https://github.com/SourceScan/verifier-front/blob/559775d5d1d4f8a46b4923f7dfab2a701b99b02c/pages/contract/%5Bslug%5D.tsx#L50-L82)

## Source snapshots

The registry record identifies the archived source. The contract's metadata identifies the Git snapshot for its deployed build.

- **IPFS archive.** At verification time, SourceScan pins the source snapshot to its IPFS node and stores the CID in the record. A CID is derived from the content, so the same CID always identifies the same files. Reads go through `api.sourcescan.dev`. How long SourceScan keeps content pinned is not published.
- **Git snapshot.** `source_code_snapshot` in the metadata is a repository URL with a commit. cargo-near writes it from `package.repository` and the pushed commit, as `git+https://github.com/OWNER/REPO?rev=COMMIT`. It is the input the verifier rebuilt from. The repository owner controls whether it stays available.

Use that form: a public repository over HTTPS, then `?rev=` and the full 40-character commit SHA. The verifier's checks before the rebuild are looser than the rebuild itself.

- **Precheck.** The snapshot must start with `git+`, use HTTPS or SSH with no user name or password in an HTTPS URL, and pin a full commit as `?rev=SHA` or `#SHA`. The `git@host:owner/repo` shorthand also passes. [Snapshot checks](https://github.com/SourceScan/verifier-back/blob/0fad9fde2ccdba7e15bf8aef88bd770fdd9f14bd/nest/src/services/github/github.service.ts)
- **Rebuild.** NEAR CLI takes the commit only from `?rev=` and cannot parse the `git@host:owner/repo` shorthand. A fragment-only pin or shorthand URL can pass the precheck's format rules, but it cannot work for this rebuild. [NEAR CLI 0.31.1](https://github.com/near/near-cli-rs/blob/5cdedc38e09b23b84ae9d69f6abbb26568dda579/src/commands/contract/verify/mod.rs#L239-L254) and [snapshot parser](https://github.com/near/near-verify-rs/blob/2dc29f6408c72a96ac17becef3384c5152d09867/src/types/source_id/mod.rs#L88-L172)

NEP-330 also allows other references, such as `ipfs://` snapshots. The hosted verifier rejects them.

If the IPFS gateway is unavailable, the Git snapshot is still a usable copy as long as it exists, and the reverse is also true.

## Who can write records

Only the registry's owner account can add or remove records or update their verification details, so a record is an attestation by SourceScan's service. The registry also has public methods for votes and comments on records. They are separate from verification and do not change a record's code hash or CID. [Registry source](https://github.com/SourceScan/verifier-contract/blob/18aea3e8c579555ccedd4c585347699affd07f84/src/lib.rs#L46-L110)

To check a result without relying on SourceScan, [rebuild it yourself](results.md#what-a-match-proves).
