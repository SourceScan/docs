# Read a verification result

A verification result compares two code hashes: the hash of the WASM deployed on an account now, and the hash stored in a SourceScan record. Read it as a statement about bytes at a point in time, not about whether the contract is safe.

## Outcomes

This guide uses five neutral terms. The tools label them differently, as the second column shows.

| Outcome | How it appears | What it means | What to do |
| --- | --- | --- | --- |
| **Match** | The deployed hash equals the record's hash. NearBlocks shows **Contract Source Code Verified**; the explorer shows **Code Hash Matches**. | The deployed bytes equal the bytes SourceScan rebuilt from the recorded source and builder. | Read the archived source. Check [what a match does not prove](#what-a-match-does-not-prove). |
| **Mismatch** | The account has a record, but its hash differs from the deployed hash. The explorer shows **Code Hash Mismatches** with no error message; NearBlocks shows its **Verify and Publish** prompt. | The account was redeployed after verification. The archived source describes earlier code. | Do not rely on the archived source for current behaviour. The owner can request verification of the new code. |
| **Not verified** | No record for the account and none for its code hash. NearBlocks shows its **Verify and Publish** prompt. | SourceScan has not verified this code. That says nothing either way about safety. | Read the [build metadata](lookup.md#2-read-the-build-metadata). Ask the owner to publish reproducible metadata and request verification. |
| **Not deployed** | `view_code` returns `NO_CONTRACT_CODE`. A `view_account` hash of `11111111111111111111111111111111` is not enough on its own, because accounts that use a global contract show it too. | The account runs no contract. Any record describes code that was removed. | Nothing to verify. |
| **Unavailable** | An RPC error, timeout, HTTP 429 or 5xx response, or an explorer error message. | No answer, neither a match nor a mismatch. | Retry later or [ask an RPC provider directly](lookup.md#check-it-yourself-with-rpc). |

NearBlocks has no separate mismatch or unavailable state: a record lookup that fails or finds a different hash shows the same prompt as a contract that was never verified. The SourceScan explorer shows **Code Hash Mismatches** for a real mismatch, for a failed code lookup and for an account that no longer runs a contract, with an error message underneath in the last two cases. When the label matters, confirm with [RPC](lookup.md#check-it-yourself-with-rpc). [NearBlocks source](https://github.com/Nearblocks/nearblocks/blob/27be10332a241a01b55467687c56f0dd5ff7761f/apps/frontend/src/components/address/contract/code/index.tsx) and [explorer source](https://github.com/SourceScan/verifier-front/blob/5fe0f22fb79604e24ef11a62830e2e5c242cc5d5/pages/contract/%5Bslug%5D.tsx#L326-L348)

## What a match proves

A matching hash is evidence that the rebuilt WASM and the deployed WASM are the same bytes. It applies to the recorded build inputs and to the code deployed when the comparison ran.

The SourceScan registry is an attestation: only the registry's owner account can write verification records. [Registry source](https://github.com/SourceScan/verifier-contract/blob/18aea3e8c579555ccedd4c585347699affd07f84/src/lib.rs#L61-L72)

For evidence that does not rely on SourceScan, rebuild it yourself. NEAR CLI reads the metadata and deployed code, rebuilds in the pinned image with Docker and compares the bytes. It sends no transaction.

```bash
near contract verify deployed-at buildguide.testnet network-config testnet now
```

Docker must be able to run `linux/amd64` images. Metadata that names the GHCR builder needs NEAR CLI 0.31.0 or later; see [builder images](builders.md#which-tools-accept-which-image).

## What a match does not prove

A match does not show that the code is secure, correct, audited or free of backdoors. It does not identify the author or owner, and it does not vouch for dependencies.

Identical code on two accounts can behave differently because of state, initialization, access keys and upgrade control. An account holder with a full-access key can deploy different code at any time. Check the account's access keys in NearBlocks before relying on code staying the same.

An account can also run a [global contract](https://docs.near.org/smart-contracts/global-contracts). If its `view_account` response includes `global_contract_account_id`, the account that published that code can change what this account runs without touching this account. A `global_contract_hash` reference stays on the same bytes.

An archived CID identifies the source, but gateway availability and long-term retention are separate from the match.

## Same code on several accounts

Each record belongs to one account, but lookup by code hash returns every record with that hash. On testnet, `buildguide.testnet`, `hjbjhbjhb.testnet` and `democontract.testnet` have separate records with code hash `HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E`, verified at different block heights. The [worked example](api.md#worked-example) shows the response.

NearBlocks uses the first record returned for the deployed hash, so an account can show **Contract Source Code Verified** because identical bytes were verified elsewhere. The page does not name the account the record came from. Because the bytes are identical, the source matches the code. The other account's verification is not a statement about this account's keys, state or owner.

## After a redeploy

A redeploy does not revoke or update a record. The registry keeps the old record until a new verification for that account replaces it, and explorers compare hashes when you view the page, so a match becomes a mismatch. No automatic re-verification is confirmed; see [support status](support.md#features).

This is common. On 23 November 2026, a read-only comparison of every mainnet record with the code each account runs, using `view_code`, found 77 matches, 26 mismatches, 3 accounts that run no contract and 9 accounts that no longer exist. On testnet, 134 of 161 records matched. Twelve of the mainnet matches are accounts that run a global contract; a check based on `view_account` would have reported them as having no contract.

To restore a match, deploy reproducible WASM and [request verification again](quickstart.md#request-verification-in-nearblocks). If the code hash did not change, the hosted verifier answers `Code hash didn't change`.
