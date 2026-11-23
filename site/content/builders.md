# Choose a builder image

The builder image is part of what gets verified. cargo-near records it in the contract's NEP-330 metadata as `build_environment`, in the form `image:tag@sha256:digest`, and a verifier rebuilds inside exactly that digest. Choose it before your first reproducible deployment and keep it with the commit.

Write the image name exactly as `sourcescan/cargo-near` or `ghcr.io/near/cargo-near`. NEAR CLI compares the name literally, so a registry prefix such as `docker.io/sourcescan/cargo-near`, the form in the NEP-330 example, is rejected.

## Docker Hub or GHCR

Two image families are accepted for verification. Both are published for `linux/amd64`.

| | Docker Hub | GitHub Container Registry (GHCR) |
| --- | --- | --- |
| Image | `sourcescan/cargo-near` | `ghcr.io/near/cargo-near` |
| Published by | SourceScan, from [cargo-near-image](https://github.com/SourceScan/cargo-near-image/blob/a50f8c15442ce73866c7a28763831aff6c958075/.github/workflows/on-release-publish.yml) | NEAR, from [cargo-near](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/.github/workflows/publish-image.yml) |
| Tags | [Docker Hub tag list](https://hub.docker.com/r/sourcescan/cargo-near/tags) | [GHCR package](https://github.com/near/cargo-near/pkgs/container/cargo-near) |
| Used by `cargo near new` in cargo-near 0.23.0 | Yes | No |

Use Docker Hub `sourcescan/cargo-near` if you want hosted verification through NearBlocks today. Every NEAR CLI release that can verify accepts it, and all 77 mainnet records that still matched deployed code on 23 November 2026 name this image. No record on either network names a GHCR image, and the NEAR CLI version inside the deployed hosted verifier is not published, so hosted acceptance of GHCR is unconfirmed.

Use GHCR `ghcr.io/near/cargo-near` when you want NEAR's own builder and can verify locally with NEAR CLI 0.31.0 or later. Do not count on hosted verification of a GHCR-built contract until it is confirmed in [support status](support.md#builder-images).

## Which tools accept which image

| Tool | `sourcescan/cargo-near` | `ghcr.io/near/cargo-near` |
| --- | --- | --- |
| `near contract verify` in NEAR CLI 0.31.0 and later | **Verified** | **Verified** |
| `near contract verify` in NEAR CLI 0.21.0 to 0.30.x | **Verified** | **Unsupported** |
| Hosted SourceScan verifier as deployed on 23 November 2026, used by NearBlocks | **Verified** | **Unconfirmed** |
| Any other image | **Unsupported** | **Unsupported** |

NEAR CLI checks the image name against an exact-match allowlist before building. The `verify` command has had one since it first shipped in NEAR CLI 0.21.0, naming only `sourcescan/cargo-near`; [NEAR CLI 0.31.0](https://github.com/near/near-cli-rs/releases/tag/v0.31.0) added the GHCR image ([allowlist in 0.31.1](https://github.com/near/near-cli-rs/blob/5cdedc38e09b23b84ae9d69f6abbb26568dda579/src/commands/contract/verify/mod.rs#L224-L236), [exact match](https://github.com/near/near-verify-rs/blob/2dc29f6408c72a96ac17becef3384c5152d09867/src/types/contract_source_metadata/validate.rs#L59-L72)). The `--no-image-whitelist` flag skips the check for a local rebuild only, and the hosted verifier does not use it.

So hosted GHCR support depends on the NEAR CLI version inside the deployed verifier: 0.31.0 or later accepts GHCR images, earlier versions reject them. The public source of the deployed verifier installs NEAR CLI without a fixed version, and the version actually running is not published. [Backend Dockerfile](https://github.com/SourceScan/verifier-back/blob/d518da7236a5b337da118dc668794cebde82a20b/nest/Dockerfile#L49-L50) A verifier release can move this row to either **Verified** or **Unsupported**, so check the date on [support status](support.md#builder-images) before relying on it.

## Pin the image

Keep these fields together in `[package.metadata.near.reproducible_build]`.

- **`image`** names the repository and tag, written exactly as `sourcescan/cargo-near:TAG` or `ghcr.io/near/cargo-near:TAG`. The tag describes the version; it does not identify the bytes.
- **`image_digest`** identifies the exact image. Verification requires it.
- **`container_build_command`** depends on the image version, as shown below.
- **`passed_env`** passes build-time environment variables. Leave it empty: the cargo-near README says SourceScan and NearBlocks do not yet verify contracts whose metadata includes these parameters. [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L157-L160)

| Image version | `container_build_command` |
| --- | --- |
| `0.13.0-rust-1.83.0` and later | `["cargo", "near", "build", "non-reproducible-wasm", "--locked"]` |
| Before `0.13.0-rust-1.83.0` | `["cargo", "near", "build"]` |

The outer `cargo near build reproducible-wasm` command starts the pinned container, and the container command runs inside it. [cargo-near README](https://github.com/near/cargo-near/blob/c8facb827d10feb4aeef571a0d6a4ec044097d0c/README.md#L147-L152)

### Same tag, different digest

The same tag name can exist on both registries with different digests. Copy the digest from the registry you build with, never from the other one.

| Image and tag | Digest |
| --- | --- |
| `sourcescan/cargo-near:0.22.0-rust-1.99.1` | `sha256:c9655eaf7436b90c87ea8b25739f91063032c5c30ba24cfeafe72c142943b5bb` |
| `ghcr.io/near/cargo-near:0.22.0-rust-1.99.1` | `sha256:9076a6fd276c874830316917a2a27a63b81acfe89f635d03493c0f67429f43d2` |

Digests were read from both registries on 23 November 2026. To read a tag's digest yourself:

```bash
docker buildx imagetools inspect ghcr.io/near/cargo-near:0.22.0-rust-1.99.1
```

Use the `Digest:` line from the output. The cargo-near issue [tracking the GHCR move](https://github.com/near/cargo-near/issues/461) describes the same difference.

### On an ARM host

The images are `linux/amd64` only. On Apple silicon and other ARM hosts, Docker runs them through emulation, which is slower. Enable amd64 emulation in Docker if a build fails to start.

## Existing deployments

The metadata is compiled into the WASM, so changing any of these fields changes the bytes and needs a new deployment. [near-sdk metadata macro](https://github.com/near/near-sdk-rs/blob/a2d4aa4a8f5d99db28af3ff4628e04e2552c7ca2/near-sdk-macros/src/core_impl/contract_metadata/mod.rs#L95-L97) To reproduce or verify code that is already deployed, use the image, digest and command from its metadata, even if a newer image exists. Do not swap a Docker Hub image for the GHCR one, or the reverse.

## Updating for a new release

Pick the new tag, copy its digest from the same registry, update `container_build_command` if the version range requires it, then commit, build, deploy and request verification again. On 23 November 2026, cargo-near 0.23.0 is the latest release, and its template still names Docker Hub. Proposals to move the template to GHCR were still open in the cargo-near repository.
