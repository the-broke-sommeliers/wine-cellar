# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.0-rc.1 (2025-12-06)

### Fix

- **docker**: fix pip not installing optional dependencies

## 0.2.0-rc.0 (2025-12-06)

### Feat

- **wine**: allow uploading multiple images of a wine
- **auth**: use django-allauth for authentication

### Fix

- **deps**: update dependency @babel/runtime to v7.28.4
- **wine_card**: add missing maring-top and make detail container use available space
- **deps**: update dependency barcode-detector to v3.0.8

## 0.1.0 (2025-11-12)

### Fix

- **filters**: don't show wines with only deleted stock items
- **deps**: update dependency barcode-detector to v3.0.7
- **stats**: don't count removed bottles

## 0.1.0-rc.0 (2025-11-04)

### Feat

- **storage**: add a stock history page which lists removed stock items
- **wine**: add orange wine to model with migration

### Fix

- **storage**: add more validation and tests for the stock add view
- **storage**: fix broken stock adding
- **map**: change boolean value for the popup close button fixes #467

## v0.0.12

### Fixed
- storage creation failing when no rows or columns specified

## v0.0.11

### Important 
There was a mistake in the docker-compose file which could potentially have
caused some issues with the django migrations in v0.0.10. It is recommended to
backup the postgresql database before updating to this release. This can for
example be done with:

`docker-compose -f docker-compose.prod.yml exec db /usr/bin/pg_dump -U django django > postgres-backup-2025-10-15.sql`

When running v.0.0.11 for the first time, check the logs and see if the
migrations are applied without error.


### Added
- **add generic attributes to be able to add tags like natural, organic** 
- **add a storage system to allow tracking bottles**
- add sentry/bugsink as an error reporting system
- add attribute model to admin 
- add fixtures for grapes, wines and stock 
- add focus style to secondary button 
- add some initial ai generated docs for wine and storage 
- utility: add styling for visually hidden 
- more storage tests 

## Changed
- refactor wine card 
- improve text styling 
- Separate post_clean code into mixin 
- Winecard text 
- auto-format django templates 
- refactor tests a bit and add some initial tests for the storage model 
- replace favicon and cleanup assets 
- update docs 

### Fixed
- Fix docker setup running migrate concurrently 
- fix broken translate tag 
- fix map center of spain 
- fix renovate.json again 
- fix some issues with numbers not shown in correct language format 
- fix some issues with the new wine card 
- fix typo in stock form queryset 
- fix wine name search not finding partial matches 
- wine_cards: fix stock no longer showing 
- wine_detail: fix text align 
- don't expose caddy port to the outside

### Removed
- **removed the docker-compose.prod.full.yml as it doesn't really provide
anything useful**
- remove old stock field 

## v0.0.10

### Added

- add 'Drink By' field to save a date until a wine should be drunk
- add an email reminder to drink wines which will expire in 14 days.
  - Requires a smtp server to be configured in your .env.prod
- add pound sterlin as currency
- add price field to wine
- show wine sources in detail view
- map with overview of the origin of all wines (country only for now)

### Fixed

- use gettext_lazy to fix some translations not being picked up
- fix missing user from wine model unique constraint
- fix bug in react map showing the wrong item popup data
- fix sizing issue on small screens for the comment form field

### Changed

- make wine picture in detail view have rounded corners

## v0.0.9

### Fixed

- models: fix some incorrect unique constraints preventing multiple users adding
  the same grape

### Changed

- update dependencies

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
