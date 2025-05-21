# Changelog

All notable changes to this project will be documented in this file.

Since version v0.0.1 the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.0.8

### Added

- Add settings page to be able to change the language and currency
- Add german translation
- Extend barcode scanning with more advanced options
- Add filter to only show wines in stock
- Add user field to user created content in the django-admin
- homepage.html: add links to cards and format

### Fixed

- fix some issues with the dev docker file
- webpack: fix missing node polyfill after barcode-detector update

### Changed

- **BREAKING CHANGE** Migrate repo to new organisation. This requires you to
  update the link to the new docker package (see the docker-compose.prod.yml)
- update links to new repo
- migrate renovate config
- update link for coverage
- update docker links
- update dependencies

## v0.0.7

### Fixed

- fix barcode scanner wasm not being loaded

## v0.0.6

### Added

- add clear and finish btn to wine create form
- add sorting options to wine list
- add stock buttons to wine detail view and other small improvements
- ci: add coveralls gh action
- add models to django admin
- add some more tests
- add more tests for wine form, scan views, change stock views
- add whitenoise to production
- Add webpack prod and some more docker fixes, add translations

### Fixed

- css: add overflow-wrap on card title
- css style unifying
- make all strings translatable and add form error messages to login
- Dockerfile: fix caps on RUN command

### Changed

- add tests for fields and remove some redundant code
- update/refactor docs
- more docs refactoring, add more barcodes
- renovate: only merge minor and patch versions
- update dependency pytest-django to v4.10.0
- update dependency djlint to v1.36.4
- update dependency flake8 to v7.1.2
- update dependency postcss to v8.5.3
- update dependency mkdocs-material to v9.6.5
- update dependency black to v25
- update dependency django-filter to v25
- update dependency isort to v6
- update dependency pytest-cov to v6
- update dependency faker to v36
- update dependency django-debug-toolbar to v5
- update dependency eslint to v9.21.0
- update dependency prettier to v3.5.2
- update dependency psycopg to v3.2.5
- update dependency sass to v1.85.1
- update dependency stylelint-declaration-strict-value to v1.10.8
- update dependency react-barcode-scanner to v3.2.0
- update dependency react-barcode-scanner to v3.2.1
- update dependency eslint-config-prettier to v10.0.2
- update dependency isort to v6.0.1
- update dependency stylelint-declaration-strict-value to v1.10.10
- update dependency babel-loader to v10
- update dependency copy-webpack-plugin to v13
- update dependency stylelint to v16.15.0
- update dependency typescript to v5.8.2
- update dependency mkdocs-material to v9.6.6
- update dependency pytest to v8.3.5
- update dependency mkdocs-material to v9.6.7
- update dependency prettier to v3.5.3
- update dependency faker to v36.2.2
- update dependency django to v5.1.7
- update dependency eslint-config-prettier to v10.1.0
- update dependency eslint-config-prettier to v10.1.1
- update dependency faker to v36.2.3
- update dependency eslint to v9.22.0
- update dependency autoprefixer to v10.4.21
- update dependency stylelint-declaration-strict-value to v1.10.11
- update babel monorepo to v7.26.10
- update dependency python to 3.13
- update dependency lint-staged to v15.5.0
- update dependency faker to v37

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
