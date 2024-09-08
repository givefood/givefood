<img width="200" alt="Give Food" src="https://github.com/givefood/givefood/assets/763913/0b5033f6-a5be-467a-87e4-79b5c33810af"><br>


The source of https://www.givefood.org.uk. A Google App Engine app, fronted by CloudFlare, written in Python, using Django and [Djangae](https://gitlab.com/potato-oss/djangae/djangae).

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

[/givefood/static/img/photos/](https://github.com/givefood/givefood/tree/main/givefood/static/img/photos) is deployed to https://photos.givefood.org.uk

## About Us

We are a UK charity that uses data to highlight local and structural food insecurity then provides tools to help alleviate it.

We maintain the largest publicly available database of food banks and what they are requesting to have donated in the UK. We currently cover around 2800 locations.

Our data is used by governments, councils, universities, supermarkets, political parties, the NHS, food manufacturers, hundreds of national & local news websites, apps & the Trussell Trust.

Give Food is a registered charity in England & Wales [1188192](https://register-of-charities.charitycommission.gov.uk/charity-details/?regid=1188192&subid=0)

## Data

* We have an API at https://www.givefood.org.uk/api/
* Our data is versioned here https://github.com/givefood/data

## Contact us

* Email mail@givefood.org.uk
* Twitter https://twitter.com/GiveFoodCharity
* Facebook https://www.facebook.com/GiveFoodOrgUK

# Local development

To set up for local development, run the following:

 - `virtualenv --python=python2.7 .venv`
 - `source .venv/bin/activate`
 - `./install_deps`
 - `./manage.py runserver`
