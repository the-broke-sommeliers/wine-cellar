# Changelog

All notable changes to this project will be documented in this file.

Since version v0.0.1 the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.0.5

### Added

- add github actions ci
- docker image for a standalone setup (without needing a reverse proxy or manua
tls setup)

### Changed

- replace nginx with caddy in docker images
- make menu responsible
- improve wine cards responsiveness
- requirements: refactor python deps
- add static folder to default settings
- update dependency django to v5.1.6
- update babel monorepo to v7.26.9
- update dependency eslint to v9.20.1
- update dependency factory-boy to v3.3.3
- update dependency prettier to v3.5.1
- update dependency tom-select to v2.4.3
- update dependency webpack to v5.98.0
- update python docker tag to v3.13.2
- update dependency pytest to v8.3.4
- update dependency psycopg to v3.2.4
- update dependency sass-loader to v16.0.5
- update dependency sass to v1.85.0

### Fixed

- fix footer not being sticky at bottom of the page
- fix barcode scan forward not working
- fix missing md module for mkdocs

**Full Changelog**: https://github.com/goapunk/wine-cellar/compare/v0.0.4...v0.0.5

## v0.0.4

### Added

- add option to add and remove bottles via barcode

### Changed

- update lint rules and fix errors
- update dependency css-loader to v7
- update dependency eslint-plugin-promise to v7
- update dependency lint-staged to v15.4.3
- update dependency mini-css-extract-plugin to v2.9.2
- update dependency neostandard to v0.12.1
- update dependency postcss to v8.5.2
- update dependency prettier to v3.5.0
- update dependency react-barcode-scanner to v3.1.0
- update dependency sass to v1.84.0
- update dependency sass-loader to v16
- update dependency stylelint to v16.14.1
- update dependency stylelint-config-standard-scss to v14
- update dependency tom-select to v2.4.2
- update dependency typescript to v5.7.3
- update dependency webpack to v5.97.1
- update dependency webpack-cli to v6
- update dependency webpack-merge to v6

## v0.0.3

### Added

- added initial docker support

### Removed

- removed the background removal feature for now as it is broken on python 3.13

## v0.0.2

### Changed

- use LoginRequiredMiddleware instead of LoginRequiredMixin

### Fixed

- removed MaxValue validator from vintage field as it will cause a migration
  every year, the form already validates against a future vintage year input.
- optimise WineBaseForm code
- fix OpenMultipleChoiceField not adding the creating user
- prevent wine filters from leaking info about other users wines
- only show statistics on landing page about wines

## v0.0.1

- initial release
