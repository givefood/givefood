<img width="217" alt="Give Food" src="https://user-images.githubusercontent.com/763913/120896619-51472b00-c61a-11eb-950d-fd3a0411c928.png">

The source of https://www.givefood.org.uk. A Google App Engine app written in Python, using Django and [Djangae](https://github.com/potatolondon/djangae).

## Structure 
| App Name  | Description                         | URL                                    |
|-----------|-------------------------------------|----------------------------------------|
| gfadmin   | Admin tool                          | https://www.givefood.org.uk/admin/     |
| gfapi1    | Deprecated first version of our API | https://www.givefood.org.uk/api/1/     |
| gfap2     | Current API                         | https://www.givefood.org.uk/api/       |
| gfdash    | Data dashboards                     | https://www.givefood.org.uk/dashboard/ |
| gfoffline | Offline tasks                       |                                        |
| gfwfbn    | What food banks need tool           | https://www.givefood.org.uk/needs/     |
| givefood  | Public app                          | https://www.givefood.org.uk            |

## About Us

We maintain the the largest publically available database of food banks and what they are requesting to have donated in the UK. We currently cover over 2400 locations.

The data is used by supermarkets, food bank networks, governments, media partners, mobile apps and voice devices.

Give Food is a registered charity in England & Wales [1188192](https://register-of-charities.charitycommission.gov.uk/charity-details/?regid=1188192&subid=0)

## Data

* We have an API at https://www.givefood.org.uk/api/
* Our data is versioned here https://github.com/givefood/data

## Contact us

* Email mail@givefood.org.uk
* Twitter https://twitter.com/GiveFood_org_uk
* Facebook https://www.facebook.com/GiveFoodOrgUK

# Local development

To set up for local development, run the following:

 - `virtualenv --python=python2.7 .venv`
 - `source .venv/bin/activate`
 - `./install_deps`
 - `./manage.py runserver`
