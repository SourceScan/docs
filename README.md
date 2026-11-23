# SourceScan documentation

[docs.sourcescan.dev](https://docs.sourcescan.dev/) is the documentation for SourceScan. Use it to check whether a NEAR account's deployed code matches a verified build, find the source behind a NearBlocks result, or verify a contract of your own.

## Guides

| I want to... | Start here |
| --- | --- |
| Find the source for a deployed contract | [Look up a contract](https://docs.sourcescan.dev/lookup/) |
| Understand a match, mismatch, or missing record | [Read a verification result](https://docs.sourcescan.dev/results/) |
| Verify my own Rust contract | [Rust quickstart](https://docs.sourcescan.dev/quickstart/) and [builder images](https://docs.sourcescan.dev/builders/) |
| Query verification records from another application | [Registry and API reference](https://docs.sourcescan.dev/api/) |

See [how verification works](https://docs.sourcescan.dev/how-verification-works/) for the build and source archive process, or [troubleshooting](https://docs.sourcescan.dev/troubleshooting/) for a failed lookup or verification.

## Contributing

Edit the [Markdown articles](site/content/). The [maintainer guide](site/README.md) explains how to build the site, check its links, and test the legacy routes.

<a name="verifying-smart-contracts-on-near-step-by-step-guide"></a>

## Original walkthrough

The [illustrated testnet walkthrough](guides/original-verification-walkthrough.md) is preserved for readers following older links. For current commands, use the [Rust quickstart](https://docs.sourcescan.dev/quickstart/).

<details>
<summary>Steps from the original guide</summary>

- <a name="step-1-install-required-tools"></a>[Step 1: Install Required Tools](guides/original-verification-walkthrough.md#step-1-install-required-tools)
- <a name="step-2-create-or-update-contract-with-nep-330-support"></a>[Step 2: Create or Update Contract with NEP-330 Support](guides/original-verification-walkthrough.md#step-2-create-or-update-contract-with-nep-330-support)
- <a name="if-you-want-to-update-your-existing-contract"></a>[If you want to update your existing contract](guides/original-verification-walkthrough.md#if-you-want-to-update-your-existing-contract)
- <a name="necessary-fields"></a>[Necessary Fields](guides/original-verification-walkthrough.md#necessary-fields)
- <a name="step-3-create-or-import-a-near-account"></a>[Step 3: Create or Import a NEAR Account](guides/original-verification-walkthrough.md#step-3-create-or-import-a-near-account)
- <a name="step-4-prepare-git-repository"></a>[Step 4: Prepare Git Repository](guides/original-verification-walkthrough.md#step-4-prepare-git-repository)
- <a name="step-5-compile-and-deploy"></a>[Step 5: Compile and Deploy](guides/original-verification-walkthrough.md#step-5-compile-and-deploy)
- <a name="deploy-using-near-cli-rs-optional"></a>[Deploy using near-cli-rs (optional)](guides/original-verification-walkthrough.md#deploy-using-near-cli-rs-optional)
- <a name="step-6-trigger-contract-verification-using-nearblocks"></a>[Step 6: Trigger Contract Verification Using Nearblocks](guides/original-verification-walkthrough.md#step-6-trigger-contract-verification-using-nearblocks)

</details>
