# Registry and API

SourceScan data can be read two ways: from the public HTTP API at `https://api.sourcescan.dev`, or straight from the registry contracts through any NEAR RPC endpoint. Everything on this page is read-only and needs no key.

## HTTP API

The [API reference](https://api.sourcescan.dev/) lists these endpoints. No authentication is declared.

| Request | Returns |
| --- | --- |
| `GET /api/contracts/by-code-hash/{codeHash}?networkId=testnet` | `{networkId, codeHash, contracts}`, where `contracts` is a list of `[accountId, record]` pairs with that code hash |
| `GET /api/contracts/count?networkId=testnet` | `{networkId, count}`, the number of records |
| `GET /api/ipfs/structure?cid={cid}&path={path}` | `{cid, structure}`, the files and folders at `path` in an archived snapshot. Omit `path` for the root |
| `GET /ipfs/{cid}/{filePath}` | The bytes of one archived file |
| `POST /api/verify/rust` | Runs a whole verification with `networkId`, `accountId` and an optional `blockId`, answers when it finishes, and can publish a record. Use it through [NearBlocks](quickstart.md#request-verification-in-nearblocks) |

Leave out `networkId` and you get mainnet. Any value other than `mainnet` returns testnet data, and the response echoes the value you sent, not the network that was read, so a typo such as `networkId=mainet` returns testnet data labelled `mainet`. Send exactly `mainnet` or `testnet`. [Contracts controller](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/src/controllers/contracts/contracts.controller.ts#L21-L65)

NearBlocks sends verification requests to `https://api-v2.sourcescan.dev`, which publishes the same API description. Whether the two hosts are one deployment is not published.

In `structure`, `Type` 1 is a folder and `Type` 2 is a file. A `path` that does not exist returns an empty list, not an error. The API has no endpoint to list or search all records; use the registry for that.

## Registry contract

| Network | Registry account |
| --- | --- |
| Mainnet | `v2-verifier.sourcescan.near` |
| Testnet | `v2-verifier.sourcescan.testnet` |

Call these view methods with an RPC `call_function` query, as in [the lookup guide](lookup.md#3-read-the-registry-record). Arguments are JSON, base64-encoded.

| Method | Arguments | Returns |
| --- | --- | --- |
| `get_contract` | `{"account_id": "..."}` | The account's record, or `null` |
| `get_contracts_by_code_hash` | `{"code_hash": "..."}` | A list of `[account_id, record]` pairs |
| `get_contracts` | `{"from_index": 0, "limit": 40}` | `[pairs, pages]`, one page of all records |
| `search` | `{"key": "...", "from_index": 0, "limit": 40}` | `[pairs, pages]` for account IDs containing `key`, ignoring `.near` and `.testnet` |
| `get_contracts_count` | `{}` | The number of records |

[Registry source](https://github.com/SourceScan/verifier-contract/blob/18aea3e8c579555ccedd4c585347699affd07f84/src/lib.rs#L111-L170)

### Record fields

| Field | Meaning |
| --- | --- |
| `code_hash` | Base58 SHA-256 of the WASM that matched when the record was written. Compare it with the account's current code hash |
| `block_height` | Block height stored with the record |
| `cid` | IPFS CID of the archived source snapshot |
| `lang` | Source language. Every record on both networks was `rust` on 23 November 2026 |
| `votes`, `comments` | Public feedback on the record. Not part of verification |

The code hash is base58, as NEAR RPC reports it. `sha256sum` prints the same digest in hex, so convert before comparing.

## Worked example

This example follows the testnet code hash of `buildguide.testnet`, the contract deployed in the original guide. Responses were captured on 23 November 2026 and are shortened where marked.

### 1. Find every record for a code hash

```bash
curl -s 'https://api.sourcescan.dev/api/contracts/by-code-hash/HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E?networkId=testnet' | jq
```

```json
{
  "networkId": "testnet",
  "codeHash": "HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E",
  "contracts": [
    ["buildguide.testnet", {
      "cid": "QmVLksjJXS45Sc7aGbsRQRz2t62PsWrWBrFP8eL7CfcbM2",
      "lang": "rust",
      "code_hash": "HedR5aofxXmWDhKctUKcFmoe1phwhEsXLSD7D7CfCs7E",
      "block_height": 175346644,
      "votes": [],
      "comments": []
    }],
    ["hjbjhbjhb.testnet", { "block_height": 175946450, "...": "same cid and code_hash" }],
    ["democontract.testnet", { "block_height": 178303048, "...": "same cid and code_hash" }]
  ]
}
```

Three accounts have their own record for identical bytes. A by-hash result shows that the code was verified somewhere. To learn about one account, compare that account's current code hash, as in [the lookup guide](lookup.md#1-get-the-deployed-code-hash).

### 2. List the archived source

```bash
curl -s 'https://api.sourcescan.dev/api/ipfs/structure?cid=QmVLksjJXS45Sc7aGbsRQRz2t62PsWrWBrFP8eL7CfcbM2' | jq -r '.structure[] | "\(.Type) \(.Name)"'
```

```text
2 Cargo.lock
2 Cargo.toml
2 README.md
2 rust-toolchain.toml
1 src
1 tests
```

Add `&path=src` to list a folder.

### 3. Read a file

```bash
curl -s https://api.sourcescan.dev/ipfs/QmVLksjJXS45Sc7aGbsRQRz2t62PsWrWBrFP8eL7CfcbM2/Cargo.toml
```

The response is the archived `Cargo.toml`, served as plain text. The same CID always returns the same content.

### 4. Count records

```bash
curl -s 'https://api.sourcescan.dev/api/contracts/count?networkId=mainnet'
```

```json
{"networkId":"mainnet","count":115}
```
