# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [23.3.0] - 2023-11-14

- Add support for PDM 2.9 and 2.10
- On all versions where applicable, enforces `static-url`.
- Removes support for PDM 2.8 as it has a show-stopper bug
- Fixed a bug with `CPU` target that would sometimes include non-CPU-specific wheels.

## [23.2.0] - 2023-09-14

- Drops support for PDM 2.3 and 2.4, adds support for PDM 2.6-2.8

## [23.1.1] - 2023-06-15

- Fix a bug where 2.5.0 would crash with an assertion.

## [23.1.0] - 2023-04-19

- Adds support for PDM 2.5.0

## [23.0.0] - 2023-03-01

This is the initial release

[Unreleased]: https://github.com/EmbarkStudios/pdm-plugin-torch/compare/23.3.0...HEAD
[23.3.0]: https://github.com/EmbarkStudios/pdm-plugin-torch/compare/23.2.0...23.3.0
[23.2.0]: https://github.com/EmbarkStudios/pdm-plugin-torch/compare/23.1.0...23.2.0
[23.1.1]: https://github.com/EmbarkStudios/pdm-plugin-torch/compare/23.1.0...23.1.1
[23.1.0]: https://github.com/EmbarkStudios/pdm-plugin-torch/compare/23.0.0...23.1.0
[23.0.0]: https://github.com/EmbarkStudios/pdm-plugin-torch/releases/tag/23.0.0
