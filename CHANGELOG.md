# Changelog

All notable changes to this project will be documented in this file.

Since version v0.0.1 the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- only show statistics on landing page about wines by the current user

## v0.0.1
- initial release
