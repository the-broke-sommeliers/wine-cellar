# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.6.1 (2026-04-14)

### fix

- Revert "refactor: move Caddyfile into docker compose to avoid file dependency"
    
    revert the below commit as it won't work with podman.
    
    This reverts commit a188e18d27b0e71afde671837617986ce06f799c.



## 0.6.0 (2026-04-14)

### BREAKING CHANGE

- Move the caddyfile into docker-compose.prod.yml to
    avoid the file dependency. If you've made modifications to the Caddyfile, apply
    them to the config in `docker-compose.prod.yml` instead.


### feat

- add option to scan barcode within add/edit form

- **security**: add content security policy
- **wine**: add option to use ai to extract data from wine label    
    You can now use ai to extract data about a new wine by uploading
    a picture of the front and/or back label. This should make adding
    a new wine much easier. To use this feature you need an api key
    for an api compatible with litellm. Currently gogole also offers
    free api keys with a limited quota for e.g. gemini-2.5-flash.

- **stock**: add edit view for items in stock

### fix

- **csp**: add missing csp for barcode scanner
- **deps**: update dependency barcode-detector to v3.1.2
- adjust csp for maps and image previews

- include purecss locally

- **ai**: dynamically construct values for wine type and category    
    - make ai value parsing a bit more robust

- image upload not working as intended
    
    Uploading images should now work again. Additionally,
    thumbnails will now be properly cleaned up on image
    deletion/replacement.

- only enforce email validation when signup is enabled

- **registration**: require email verification on signup
- **deps**: update babel monorepo to v7.29.2
- **deps**: update dependency barcode-detector to v3.1.1
- **docker**: fix permission issue with selinux
- only import debug toolbar if installed

- **deps**: update dependency barcode-detector to v3.1.0
- **deps**: update dependency tom-select to v2.5.2

### refactor

- **forms**: improve view structure for adding a new wine    
    - fix some small ui quirks

- move Caddyfile into docker compose to avoid file dependency
    
    BREAKING CHANGE: Move the caddyfile into docker-compose.prod.yml to
    avoid the file dependency. If you've made modifications to the Caddyfile, apply
    them to the config in `docker-compose.prod.yml` instead.



## 0.5.0 (2026-02-19)

### BREAKING CHANGE

- django-celery beat has been removed. If you setup custom celery beat schedules via the
    django admin they will no longer work.


### feat

- **language**: enable french    
    thanks @philmassart

- **lang**: add french translation    
    django.po file

- **lang**: add french translation    
    djangojs.po file

- **wine**: add field for region and appellation
- **wine**: add location field to wine    
    The location field allows to set a marker for the origin of the wine
    (e.g. region, vineyard, site) on the map. This location will then be
    used on the global map instead of just showing the marker on the
    country.

- **docker-dev**: add make command to add sample data for development    
    You can run `make docker-fixtures` after starting the containers to
    populate the db with some sample data for development.


### fix

- **deps**: update dependency tom-select to v2.5.1
- **deps**: update font awesome to v7.2.0
- **translations**: auto remove fuzzy translations
- **translations**: ignore static files dir and add extensions for js translations
- **deps**: update dependency @turf/turf to v7.3.4
- **deps**: update dependency tom-select to v2.4.6
- **deps**: update dependency tom-select to v2.4.5
- **deps**: update dependency tom-select to v2.4.4
- **wine form**: fix error in handling region and appellation
- **wine form**: fix image step no longer accessible
- **deps**: update dependency @turf/turf to v7.3.3
- **docker**: fix broken Dockerfile for prod after node update
- **deps**: update react monorepo
- **map**: fix incorrect call to get_map_attributes
- **storage**: don't include deleted bottles in used slots count
- **form**: use NumberInput widget for abv and price    
    This will show the number input on mobile instead of the full keyboard

- **docker-dev**: hot reload of js/css not working
- **filter**: when sorting by price show wines without price last
- **docker-dev**: only run migrations in web container
- **deps**: update babel monorepo to v7.28.6

### refactor

- **celery**: remove django-celery-beat as it's not really maintained and overkill.    
    BREAKING CHANGE: django-celery beat has been removed. If you setup custom celery beat schedules via the
    django admin they will no longer work.

- **ci**: add better name for docs workflow
- format map_choose_point_widget.html



## 0.4.0 (2026-01-15)

### feat

- **stats**: if a stock item has no price, use the price of the wine

### fix

- **docker**: fix DJANGO_ENABLE_SIGNUPS variable not working as intended    
    When `DJANGO_ENABLE_SIGNUPS` is set to "False" it still allowed signups.
    If you didn't want to allow signups please check if any users registered
    in the django-admin under `/admin`.

- **templates**: fix allauth templates not showing errors
- **docker dev**: fix hot reload not working, add missing services for full dev setup
- **docker-dev**: don't flush database on start
- **deps**: update dependency react-barcode-scanner to v4.0.1
- **wine details**: order stock items by storage, row, column

### refactor

- **templates**: remove redundant login template


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

