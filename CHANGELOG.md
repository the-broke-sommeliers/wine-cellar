# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.3.0 (2026-01-04)

### feat

- **wine**: add sorting by average price and total value statistic    
    - the wine list can now be sorted by the average price of a wine
    - the homepage shows the total value of all bottles in stock

- **stock**: add option to add the bottle price to a stock item    
    - show average price across all bottles of a wine in wine detail view


### fix

- **stock**: make adding a bottle to a previously occupied slot work.
- **deps**: update react monorepo to v19.2.3


## 0.2.0 (2025-12-13)

### feat

- **wine**: allow uploading multiple images of a wine    
    This allows uploading images for front, back, label front, label back.
    Additionally, previews are now shown in the form and images can be
    deleted.

- **auth**: use django-allauth for authentication    
    For now this will allow login via openid_connect. Other providers can be
    added on request. Also adds proper email and password change views.
    
    It also introduces a new setting `ENABLE_SIGNUP` which defaults to `False`.
    To enable signups add/change it in `.env-prod`.


### fix

- **wine_card**: wrap image in a fixed-size container
- **deps**: update react monorepo to v19.2.1
- **wine detail**: fix image carousel buttons not working    
    - use consistent button icons
    - fix template structure and js element querying

- **wine list**: fix filtering getting lost on page change
- **docker**: fix pip not installing optional dependencies
- **deps**: update dependency @babel/runtime to v7.28.4
- **wine_card**: add missing maring-top and make detail container use available space
- **deps**: update dependency barcode-detector to v3.0.8


## 0.1.0 (2025-11-12)

### feat

- **storage**: add a stock history page which lists removed stock items    
    mark stock items as deleted instead of actually deleting them from the db

- **wine**: add orange wine to model with migration

### fix

- **filters**: don't show wines with only deleted stock items
- **deps**: update dependency barcode-detector to v3.0.7
- **stats**: don't count removed bottles
- **storage**: add more validation and tests for the stock add view
- **storage**: fix broken stock adding
- **map**: change boolean value for the popup close button fixes #467

