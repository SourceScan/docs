# Legacy verification paths

SourceScan once offered a BOS widget and a hosted flow that deployed contracts with a full-access key. Both are retired. This page explains what to do if you used them. For language and feature status, see [support status](support.md).

## BOS and full-access keys

The old BOS widget, gateway, builder scripts and hosted full-access-key deployment flow are unsupported. Use the [Rust quickstart](quickstart.md) to deploy with your own signer and request verification from public metadata. Never share a private key or seed phrase, and never grant SourceScan a full-access key for verification. Current verification asks for no key at all.

If you used the historical gateway, review the account's access keys with a trusted NEAR wallet or NEAR CLI. If you find an obsolete grant, follow your wallet's key-management guidance, and keep at least one trusted key that controls the account.

## Old records

The BOS widget used separate registries, `dev.sourcescan.near` and `dev.sourcescan.testnet`, which NearBlocks and the SourceScan explorer do not read. Records that earlier versions of the verifier wrote to the current registries remain, and explorers still compare them with deployed code. Some older testnet records name a builder image that current NEAR CLI no longer accepts. To verify such a contract again, rebuild it with an [accepted image](builders.md#which-tools-accept-which-image) and redeploy.
