<img width="200" alt="Give Food" src="https://github.com/givefood/givefood/assets/763913/0b5033f6-a5be-467a-87e4-79b5c33810af"><br>


The source of https://www.givefood.org.uk - built using Django, hosted at [Mythic Beasts](https://www.mythic-beasts.com/) in Shoreditch, London using [Coolify](https://www.coolify.io/) and fronted by [Cloudflare](https://www.cloudflare.com/).

## Structure 
| App Name  | Description                         | URL                                    |
|-----------|-------------------------------------|----------------------------------------|
| gfadmin   | Admin tool                          | https://www.givefood.org.uk/admin/     |
| gfapi1    | Deprecated first version of our API | https://www.givefood.org.uk/api/1/     |
| gfapi2    | Current API                         | https://www.givefood.org.uk/api/       |
| gfapi3    | Future API                          | https://www.givefood.org.uk/api/3/     |
| gfdash    | Data dashboards                     | https://www.givefood.org.uk/dashboard/ |
| gfoffline | Offline tasks                       | N/A                                    |
| gfwfbn    | What food banks need tool           | https://www.givefood.org.uk/needs/     |
| gfwrite   | Allow users to contact their MPs    | https://www.givefood.org.uk/write/     |
| givefood  | Public app                          | https://www.givefood.org.uk            |

[/givefood/static/img/photos/](https://github.com/givefood/givefood/tree/main/givefood/static/img/photos) is deployed to https://photos.givefood.org.uk via [CloudFlare R2](https://developers.cloudflare.com/r2/)

- Useful list of [abbreviations](abbreviations.md)
- [Copilot instructions ](/.github/copilot-instructions.md)
- [Deepwiki repository summary](https://deepwiki.com/givefood/givefood)

## About Us

We are a UK charity that uses data to highlight local and structural food insecurity then provides tools to help alleviate it.

We maintain the largest publicly available database of food banks and what they are requesting to have donated in the UK. We currently cover nearly 3000 locations.

Our data is used by governments, councils, universities, supermarkets, political parties, the NHS, broadcasters, food manufacturers, hundreds of national & local news websites, and apps.

Give Food is a registered charity in England & Wales [1188192](https://register-of-charities.charitycommission.gov.uk/en/charity-search/-/charity-details/5147019)

## Data

* We have an API at https://www.givefood.org.uk/api/
* Our data is versioned here https://github.com/givefood/data

## Contact us

* Email mail@givefood.org.uk
* Twitter https://twitter.com/GiveFoodCharity
* Facebook https://www.facebook.com/GiveFoodOrgUK

# Local development

To set up for local development, run the following:

 - `virtualenv --python=python3.12 .venv`
 - `source .venv/bin/activate`
 - `./pip install -r requirements.txt`
 - `./manage.py runserver`

## Running tests

The project includes a basic test suite using pytest. To run the tests:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run tests for a specific app
pytest givefood/tests/
pytest gfapi2/tests.py

# Run with coverage report
pytest --cov=givefood --cov=gfapi2
```

The test suite includes:
- Unit tests for utility functions (text processing, geographic calculations, etc.)
- Integration tests for API endpoints
- Basic view tests for the main application

Tests use SQLite in-memory database for speed and simplicity.
