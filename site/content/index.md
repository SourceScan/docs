# SourceScan documentation

<span id="value-proposition"></span>
<span id="benefits-of-smart-contract-source-code-visibility"></span>

SourceScan checks whether the WebAssembly (WASM) deployed to a NEAR account can be rebuilt byte for byte from public Rust source. When it can, a verification record ties that code hash to an archived copy of the source, and NearBlocks shows the source next to the contract.

[Look up a contract](lookup.md){: .button .primary }
[Verify your Rust contract](quickstart.md){: .button }
{: .actions }

## Check a contract

You need no wallet, account or signature for any of these.

<div class="cards" markdown>

### [Look up a contract](lookup.md)

Find an account's deployed code hash, its verification record and the archived source.

### [Read a result](results.md)

What match, mismatch, not verified, not deployed and unavailable mean, and what a match does not prove.

### [Registry and API](api.md)

Query records and source snapshots directly, with a worked testnet example.

</div>

## Verify your contract

<div class="cards" markdown>

### [Verify a Rust contract](quickstart.md)

Pin the source and builder, deploy reproducible WASM, then request verification in NearBlocks.

### [Choose a builder image](builders.md)

Docker Hub or the official NEAR image on GHCR, and how to pin the tag, digest and command.

### [Troubleshooting](troubleshooting.md)

Missing metadata, failed builds, hash differences and missing source.

</div>

## Know the limits

- [Support status](support.md) separates what was verified to work from what is unsupported or unconfirmed, including languages and features described in the old GitBook docs.
- [How verification works](how-verification-works.md) follows a request from build metadata to the registry and NearBlocks.
- [Legacy paths](legacy.md) covers the retired BOS widget and full-access-key flows.

## Official links

- [SourceScan explorer](https://app.sourcescan.dev/) and the [public API reference](https://api.sourcescan.dev/)
- NearBlocks on [mainnet](https://nearblocks.io/) and [testnet](https://testnet.nearblocks.io/)
- [SourceScan on GitHub](https://github.com/SourceScan) and the [original verification guide](https://github.com/SourceScan/docs/blob/main/guides/original-verification-walkthrough.md)
