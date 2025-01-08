# Changelog

All notable changes to this project will be documented in this file.

Since version v0.0.1 the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- use LoginRequiredMiddleware instead of LoginRequiredMixin

### Fixed

- removed MaxValue validator from vintage field as it will cause a migration
every year, the form already validates against a future vintage year input.
- optimise WineBaseForm code
- fix OpenMultipleChoiceField not adding the creating user 
- prevent wine filters from leaking info about other users wines

## v0.0.1
- initial release
