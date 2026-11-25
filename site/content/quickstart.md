# Verify a Rust contract

Build reproducible WASM from a public commit, deploy it, then ask SourceScan to verify it through NearBlocks. Try it on testnet first. Mainnet works the same way with a mainnet account and NearBlocks mainnet.

If the contract is already deployed with reproducible build metadata, skip building and deploying: [check its metadata](lookup.md#2-read-the-build-metadata) and go to [request verification in NearBlocks](#request-verification-in-nearblocks). That needs no account, key or Docker.

To build and deploy, you need:

- a public Git repository you can push to
- a NEAR account you control, with its usual signer
- Docker that can run `linux/amd64` images, which ARM hosts such as Apple silicon run through emulation

## Set up the tools

Install [Rust](https://www.rust-lang.org/learn/get-started), Git, [Docker Engine](https://docs.docker.com/engine/install), [cargo-near](https://github.com/near/cargo-near) and [NEAR CLI](https://github.com/near/near-cli-rs). On Linux, see [Docker's post-install steps](https://docs.docker.com/engine/install/linux-postinstall) if your user cannot reach the daemon. Check that `docker info`, `cargo near --version` and `near --version` all work.

To create a testnet account, use the account creation flow in NEAR CLI and make sure the account holds enough testnet NEAR for deployment and storage.

For a new contract, run `cargo near new` and keep the reproducible build settings it generates. For an existing deployment, start from the commit, lockfile and builder recorded in its metadata. Updating dependencies first changes the code you are trying to verify.

## Pin the source and build

Point `package.repository` at your public repository's HTTPS URL. cargo-near records it with the pushed commit as `git+https://…?rev=COMMIT`, the [snapshot form](how-verification-works.md#source-snapshots) the verifier can rebuild from. The example below is from the [cargo-near 0.23.0 project template](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/cargo-near/src/commands/new/new-project-template/Cargo.template.toml#L18-L37), the latest release on 23 November 2026. To choose a different image, read [choose a builder image](builders.md) first.

```toml
[package]
# Keep your existing name, version, edition and other package fields.
repository = "https://github.com/YOUR-ORG/YOUR-CONTRACT"

[package.metadata.near.reproducible_build]
image = "sourcescan/cargo-near:0.22.0-rust-1.99.1"
image_digest = "sha256:c9655eaf7436b90c87ea8b25739f91063032c5c30ba24cfeafe72c142943b5bb"
passed_env = []
container_build_command = ["cargo", "near", "build", "non-reproducible-wasm", "--locked"]
```

Commit `Cargo.toml`, `Cargo.lock`, your source and every other build input, then push that exact commit. Build locally to check it works and to find the WASM.

```bash
git status --short
cargo near build reproducible-wasm
```

The reproducible build runs against the committed source in the pinned container and ignores uncommitted changes. It needs `Cargo.lock` committed for its `--locked` build. [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L131-L136)

For a contract in a workspace, select the crate with `--manifest-path path/to/Cargo.toml`.

Reproducible builds have no `--features` flag. Put Cargo features in `container_build_command`, or define a named variant. The metadata records the command that was used, so the verifier rebuilds with the same features. This example assumes your crate defines a `testnet` feature in `[features]`. [cargo-near variants](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L170-L206)

```toml
[package.metadata.near.reproducible_build.variant.testnet]
container_build_command = ["cargo", "near", "build", "non-reproducible-wasm", "--locked", "--features", "testnet"]
```

Build a variant by name, then deploy it with the same `--variant`, as shown in the next section.

```bash
cargo near build reproducible-wasm --variant testnet
```

![The cargo-near terminal showing the reproducible build and generated WASM path](images/cargo-near-build.png)

## Deploy the reproducible WASM

Run one of these in your own terminal, matching the build you checked. For the default build:

```bash
cargo near deploy build-reproducible-wasm
```

Or, for a named variant:

```bash
cargo near deploy build-reproducible-wasm --variant testnet
```

Select the account, the initialization option your contract needs and the network, then review and sign with your usual signer.

Deployment requires a clean working tree, with no modified tracked files, staged changes or untracked content, and a commit already pushed to `package.repository`. [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L263-L268)

You can also deploy the exact WASM from `cargo near build reproducible-wasm` with NEAR CLI. Save the account ID, deployment transaction and block height.

## Request verification in NearBlocks

1. Open `https://testnet.nearblocks.io/address/ACCOUNT_ID/contract/code`.
2. Select **Verify and Publish** to open `/verify-contract?account=ACCOUNT_ID`. If NearBlocks already shows **Contract Source Code Verified**, it found a record for the deployed hash and you do not need to submit again. If no banner appears, the contract may not expose NEP-330 metadata, or the metadata call may have failed. [Read the metadata with RPC](lookup.md#2-read-the-build-metadata) and see [troubleshooting](troubleshooting.md#no-source-metadata-or-build-info).
3. Check the network, account, standard and build environment, then select **Verify Contract**. The button stays disabled if the metadata lacks `build_environment` or `source_code_snapshot`. NearBlocks sends the account ID and network to SourceScan. Nothing is signed and no key is requested.
4. Wait for the answer. SourceScan rebuilds the contract before it replies, which can take several minutes. A match returns **Contract verified successfully**; any other message explains what failed. NearBlocks shows **Verification submitted successfully** only if SourceScan sends no message.
5. Reload **Contract Code**. A match shows **Contract Source Code Verified** with the archived source files. Then [read the result](results.md).

SourceScan reads the metadata and deployed code at the latest final block, rebuilds the code the metadata names, compares the two, archives the source on IPFS and writes a record to the registry. See [how verification works](how-verification-works.md#from-api-to-registry-to-nearblocks).

The verify page reads only the `account` parameter. Older links using `accountId` and `selectedVerifier` open a page that asks for an account in the address.

Labels were checked on [NearBlocks testnet](https://testnet.nearblocks.io/verify-contract?account=buildguide.testnet) and in [NearBlocks source](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/locales/en/address.ts#L397-L437) on 23 November 2026. This guide did not submit a new verification request.
