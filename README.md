<!-- Allow this file to not have a first line heading -->
<!-- markdownlint-disable-file MD041 -->

<!-- inline html -->
<!-- markdownlint-disable-file MD033 -->

<div align="center">

# `🔦 pdm-plugin-torch `

A utility tool for selecting torch backend and version.

[![Embark](https://img.shields.io/badge/embark-open%20source-blueviolet.svg)](https://embark.dev)
[![Embark](https://img.shields.io/badge/discord-ark-%237289da.svg?logo=discord)](https://discord.gg/dAuKfZS)
[![Build status](https://badge.buildkite.com/968ac3c0bb075fb878f9f973ed91406c8b257b0f050c197542.svg?theme=github&branch=main)](https://buildkite.com/embark-studios/pdm-plugin-torch)
[![Docs status](https://img.shields.io/badge/Docs-latest-brightgreen)](https://embarkstudios.github.io/pdm-plugin-torch/)
[![pdm-managed](https://img.shields.io/badge/PDM-v2.3.0-blueviolet)](https://pdm.fming.dev)

</div>


## What it does

Due to torch being published in many different variants with local versions to signify the underlying API, it is hard to integrate into a lockfile-based workflow. This is due to the local versions - `+cu111`, `+cpu`, and so on - being considered the "same" package, so you can't resolve two at the same time.

This tool generate multiple lockfiles *only for torch* and allows you to use a pdm subcommand (`pdm torch`) to select the one you want.

### Configuration

These are the supported options:

```toml
[tool.pdm.plugins.torch]
dependencies = [
   "torch==1.10.2"
]
lockfile = "torch.lock"
enable-cpu = true

enable-rocm = true
rocm-versions = ["4.2"]

enable-cuda = true
cuda-versions = ["cu111", "cu113"]
```

## Installation

Currently PDM does not support specifying plugin-dependencies in your pyproject.toml. Thus, we suggest using a setup like the following:

``` toml
[tool.pdm.scripts]
post_install = "pdm plugin add pdm-plugin-torch==$VERSION"
```

## Contribution

[![Contributor Covenant](https://img.shields.io/badge/contributor%20covenant-v1.4-ff69b4.svg)](../main/CODE_OF_CONDUCT.md)

We welcome community contributions to this project.

Please read our [Contributor Guide](CONTRIBUTING.md) for more information on how to get started.
Please also read our [Contributor Terms](CONTRIBUTING.md#contributor-terms) before you make any contributions.

Any contribution intentionally submitted for inclusion in an Embark Studios project, shall comply with the Rust standard licensing model (MIT OR Apache 2.0) and therefore be dual licensed as described below, without any additional terms or conditions:

### License

This contribution is dual licensed under EITHER OF

* Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or <http://www.apache.org/licenses/LICENSE-2.0>)
* MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.

For clarity, "your" refers to Embark or any other licensee/user of the contribution.
