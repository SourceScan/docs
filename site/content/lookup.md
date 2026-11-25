# Look up a deployed contract

Check what code a NEAR account runs and whether SourceScan has a matching verification record. Every step on this page is a read: you need no wallet, account, key or signature.

Before you start, note the exact account ID and network. A record on testnet says nothing about mainnet, and an account with a similar name is a different account.

## In NearBlocks

1. Open NearBlocks for the network, [mainnet](https://nearblocks.io/) or [testnet](https://testnet.nearblocks.io/), and search for the account.
2. Select **Contract**, then **Contract Code**. The direct address is `/address/ACCOUNT_ID/contract/code`, for example [buildguide.testnet's contract code](https://testnet.nearblocks.io/address/buildguide.testnet/contract/code). The **Contract** tab appears only when a contract is deployed.
3. Read the banner at the top of **Contract Code**.

| Banner | What NearBlocks found |
| --- | --- |
| **Contract Source Code Verified** | A SourceScan record whose code hash equals the deployed code hash. The contract's own version, its NEP-330 standard, the source snapshot commit, IPFS CID, build environment, build command and archived source files follow. |
| **Are you the contract owner? Verify and Publish your contract source code today!** | No matching record, or the record lookup failed. NearBlocks shows the same prompt in both cases. |
| No banner | NearBlocks got no NEP-330 metadata. Either the contract declares none, or the metadata call failed or took longer than 5 seconds. [Read the metadata with RPC](#2-read-the-build-metadata) to tell which. |

NearBlocks looks records up by code hash. A contract can show as verified because identical code was verified on another account, and the page does not say which account that was. See [same code on several accounts](results.md#same-code-on-several-accounts).

The NearBlocks file browser lists only `.rs`, `.toml` and `.lock` files, only those under `contract_path` when the metadata sets one, and skips the `.git`, `.github`, `.cargo`, `.vscode`, `node_modules` and `target` folders. A `.cargo/config.toml` can change a build but is not shown there. Use the [API](api.md#worked-example) to list every archived file.

Older links of the form `/address/ACCOUNT_ID?tab=contract` now open the account's transactions. Labels and routes were checked in Chrome and against [NearBlocks source](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/app/%5Blang%5D/address/%5Baddress%5D/contract/code/page.tsx) on 23 November 2026.

## In the SourceScan explorer

The [SourceScan explorer](https://app.sourcescan.dev/) reads the SourceScan registry directly. Its home page lists the records on one network, each with the block it was verified at, and checks no deployed code. Search for the account and open it. The contract page is at `/contract/ACCOUNT_ID`, for example [buildguide.testnet in the explorer](https://app.sourcescan.dev/contract/buildguide.testnet). Accounts ending in `.near` or `.testnet` open on their own network; for other accounts, add `?network=mainnet` or `?network=testnet`, or choose the network first. Older `sourcescan.dev` links forward to the same path on `app.sourcescan.dev`.

Opening the page reads the account's own record, then the hash of the code the account runs at the latest finalized block, with `view_code`. The verdict shows the recorded hash, the deployed hash when available, and the block checked when reported by the RPC.

| Verdict | Meaning |
| --- | --- |
| **Checking the deployed code…** | The code read is still running. |
| **Deployed code matches the verified source** | The record describes the code deployed now. |
| **Deployed code does not match the verified source** | The account runs different code from the record: it was redeployed after verification, or the record was verified at an earlier block. |
| **No code is deployed on this account** | `view_code` found no contract, or the account does not exist on this network. |
| **Deployed code status unknown** | The RPC read failed or returned no usable hash. Select **Retry**, or check with RPC below. |

If the account has no record on that network, the page shows **No verified record on Mainnet** or **No verified record on Testnet** instead. **Couldn’t load the verification record** means the registry read failed; select **Try again**.

Below the verdict are three tabs.

- **Verified source** lists the files archived under the record's IPFS CID.
- **Evidence** explains the verdict: both hashes, the block the record was verified at, the final block checked, the CID, the Git repository for GitHub snapshots, the registry contract and a NearBlocks link.
- **Build** shows the NEP-330 metadata the contract exposes now.

A mismatch means the deployed code differs from this account's record. NearBlocks may still find a match by hash on another account. Use the recorded CID for the archived source. The **Build** tab and, when derived from live metadata, the **Repository** link may describe a different build. If the source viewer is empty because the live contract path changed, [list the archived CID directly](api.md#2-list-the-archived-source). [Explorer source](https://github.com/SourceScan/verifier-front/blob/559775d5d1d4f8a46b4923f7dfab2a701b99b02c/pages/contract/%5Bslug%5D.tsx#L50-L82) and [verdicts](https://github.com/SourceScan/verifier-front/blob/559775d5d1d4f8a46b4923f7dfab2a701b99b02c/components/Contracts/Verdict.tsx#L7-L37)

## Check it yourself with RPC

For an answer that does not depend on either explorer, ask a NEAR RPC endpoint. The examples use FastNEAR's public testnet endpoint from [NEAR's list of RPC providers](https://docs.near.org/api/rpc/providers). For mainnet, use `https://rpc.mainnet.fastnear.com` and the `v2-verifier.sourcescan.near` registry. NEAR [deprecated the free `rpc.testnet.near.org` and `rpc.mainnet.near.org` endpoints](https://near.org/blog/deprecation-of-near-org-and-pagoda-co-rpc-endpoints) from June 2025, and they answered with HTTP 429 when checked on 23 November 2026. Public endpoints are rate limited, so use your own provider for repeated checks. You need `curl` and `jq`.

### 1. Get the deployed code hash

```bash
curl -s https://rpc.testnet.fastnear.com -H 'Content-Type: application/json' -d '{
  "jsonrpc": "2.0", "id": "docs", "method": "query",
  "params": {"request_type": "view_code", "finality": "final",
    "account_id": "buildguide.testnet"}
}' | jq -r .result.hash
```

```text
HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E
```

`view_code` returns the hash of the code the account runs, whether that is the account's own contract or a [global contract](https://docs.near.org/smart-contracts/global-contracts) it uses. Explorers and NEAR CLI compare this hash. The response also carries the whole WASM as base64, so it can be large.

| Response | Meaning |
| --- | --- |
| A `hash` | The code the account runs now. Compare it in step 4. |
| `NO_CONTRACT_CODE` error | The account runs no contract, local or global. |
| `UNKNOWN_ACCOUNT` error | The account does not exist on this network. |

Do not compare against the `code_hash` from a `view_account` query. That field is the hash of the account's own local contract only, and it is `11111111111111111111111111111111` both when the account has no contract and when it uses a global contract. A global contract shows up there as `global_contract_hash` or `global_contract_account_id`. [nearcore account view](https://github.com/near/nearcore/blob/c060644ef702d73048b91cd1adca8d56d5809dee/core/primitives/src/views.rs#L128-L141) and [code view](https://github.com/near/nearcore/blob/c060644ef702d73048b91cd1adca8d56d5809dee/runtime/runtime/src/state_viewer/mod.rs#L176-L212)

### 2. Read the build metadata

```bash
curl -s https://rpc.testnet.fastnear.com -H 'Content-Type: application/json' -d '{
  "jsonrpc": "2.0", "id": "docs", "method": "query",
  "params": {"request_type": "call_function", "finality": "final",
    "account_id": "buildguide.testnet", "method_name": "contract_source_metadata",
    "args_base64": "e30="}
}' | jq '.result.result | implode | fromjson'
```

`e30=` is `{}` encoded as base64. The response is the contract's NEP-330 metadata. `build_info` names the source snapshot, builder image and command that a verifier must use.

```json
{
  "version": "0.1.0",
  "standards": [{ "standard": "nep330", "version": "1.2.0" }],
  "build_info": {
    "build_environment": "sourcescan/cargo-near:0.8.2-rust-1.81.0@sha256:3b5e6efa1d0cef710009f9cc20c845d316187cc170455edc5ba7fdf471c19655",
    "build_command": ["cargo", "near", "build"],
    "contract_path": "",
    "source_code_snapshot": "git+https://github.com/Canvinus/cargo-near-new-example?rev=45fbb14f90e24dc9105cb8daf32fa2ba624250b0"
  }
}
```

The output above omits the `link` field. If `jq` reports `implode input must be an array`, rerun without the `jq` filter and read `result.error`. `MethodNotFound` there means the contract has no `contract_source_metadata` method and cannot be verified as deployed.

### 3. Read the registry record

```bash
ARGS=$(printf '{"account_id":"buildguide.testnet"}' | base64)
curl -s https://rpc.testnet.fastnear.com -H 'Content-Type: application/json' -d '{
  "jsonrpc": "2.0", "id": "docs", "method": "query",
  "params": {"request_type": "call_function", "finality": "final",
    "account_id": "v2-verifier.sourcescan.testnet", "method_name": "get_contract",
    "args_base64": "'"$ARGS"'"}
}' | jq '.result.result | implode | fromjson'
```

```json
{
  "cid": "QmVLksjJXS45Sc7aGbsRQRz2t62PsWrWBrFP8eL7CfcbM2",
  "lang": "rust",
  "code_hash": "HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E",
  "block_height": 175346644,
  "votes": [],
  "comments": []
}
```

`null` means this account has no record on this network. The [registry reference](api.md#registry-contract) describes every field.

### 4. Compare the hashes

The record describes the current code only when its `code_hash` equals the hash from step 1. Then [read the result](results.md). Responses above were captured on 23 November 2026; the account's code can change after a redeploy.

## Open the archived source

A verified contract has two copies of its source.

- **Registry copy.** The record's `cid` points to the source archived on IPFS when the contract was verified. A CID identifies exact content, so the same CID always means the same files. Browse it in NearBlocks, in the explorer's **Verified source** tab, or through the [API](api.md#worked-example).
- **Git snapshot.** `source_code_snapshot` in the deployed metadata names the repository and commit for that build. After a mismatch, it is not a reliable link to the recorded source. The repository owner can delete or move it, so it may not stay available.

## What to note down

When you report or rely on a check, record the network, account ID, time or block height, deployed code hash, the record's code hash and CID, and the source commit. A later redeploy changes the answer, and that record lets someone else repeat your check.
