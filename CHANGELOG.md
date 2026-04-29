# Changelog

## [0.2.1](https://github.com/invacuation/calamari/compare/v0.2.0...v0.2.1) (2026-04-29)


### Bug Fixes

* refresh Tado access token per-cycle and auto-retry 401s ([#15](https://github.com/invacuation/calamari/issues/15)) ([1f44b47](https://github.com/invacuation/calamari/commit/1f44b47ae19edc2e02f7e16053604a01eed1116a))

## [0.2.0](https://github.com/invacuation/calamari/compare/v0.1.2...v0.2.0) (2026-04-29)


### Features

* submit readings every 3 hours with update logic ([#14](https://github.com/invacuation/calamari/issues/14)) ([7969ce4](https://github.com/invacuation/calamari/commit/7969ce4c240e394ad73b07769146ac60d2779c6a))


### Bug Fixes

* handle duplicate Tado readings by updating existing ([#12](https://github.com/invacuation/calamari/issues/12)) ([41fb42a](https://github.com/invacuation/calamari/commit/41fb42a2606c0f2805de194798dddddc4c3cb205))

## [0.1.2](https://github.com/invacuation/calamari/compare/v0.1.1...v0.1.2) (2026-04-29)


### Bug Fixes

* build multi-arch Docker images for amd64 and arm64 ([#9](https://github.com/invacuation/calamari/issues/9)) ([95f5971](https://github.com/invacuation/calamari/commit/95f5971fa7c1b37baa4e793f4dae5c409ac86846))

## [0.1.1](https://github.com/invacuation/calamari/compare/v0.1.0...v0.1.1) (2026-04-29)


### Bug Fixes

* use clean semver tags for Docker images ([#6](https://github.com/invacuation/calamari/issues/6)) ([95a8480](https://github.com/invacuation/calamari/commit/95a8480d95ae1eab6aea74280dd361523088aa3e))

## 0.1.0 (2026-04-29)


### Features

* Octopus Energy to Tado Energy IQ integration ([#1](https://github.com/invacuation/calamari/issues/1)) ([d5390af](https://github.com/invacuation/calamari/commit/d5390af8d2522ad55b1d74f2074cefee844ccdab))


### Bug Fixes

* move release-please config to repo root, use non-deprecated action ([1bf63b2](https://github.com/invacuation/calamari/commit/1bf63b25ff79dce96c006edf98af3a9484ec7fcd))
* wrap long auth URL line to satisfy ruff ([598c546](https://github.com/invacuation/calamari/commit/598c54629a3cdc7bb0c77b98d6d7c5bc8ca7ece5))
