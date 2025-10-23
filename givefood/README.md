# givefood - Public Application & Core Framework

The main public-facing Django application and core framework for Give Food at https://www.givefood.org.uk

## Overview

The `givefood` app serves as both the public-facing website and the foundational framework for the entire Give Food charity platform. It provides the homepage, donation pages, annual reports, food bank registration, and other public-facing features, while also containing the core data models, shared utilities, middleware, and configuration used by all other apps in the project.

This app acts as the foundation upon which specialized apps (gfadmin, gfapi2, gfwfbn, etc.) are built, providing shared models like `Foodbank`, `FoodbankChange`, `Order`, and `ParliamentaryConstituency` that power the entire system.

## Key Features

### Public Pages
- **Homepage** - Main landing page with statistics, recently updated food banks, most viewed locations, and interactive map
- **About Us** - Information about Give Food charity
- **Donate** - Donation information and managed donation campaigns
- **Annual Reports** - Yearly impact reports (2019-2024)
- **Food Bank Registration** - Public form for new food banks to register with Give Food
- **Bot Information** - Documentation about GiveFoodBot web crawler
- **Privacy & Legal** - Privacy policy, colophon, security information
- **Flag Content** - Allow users to report issues with content

### Managed Donations
- Track bulk food donations to multiple food banks via `OrderGroup`
- Display delivery statistics (items, weight, calories, cost)
- Interactive maps showing distribution of donated items
- GeoJSON endpoints for visualization

### UUID Redirects
- Universal identifier system for food banks, locations, and donation points
- Automatic redirection from UUID to correct object page
- Future-proof linking system for external integrations

### Sitemaps & SEO
- XML sitemaps for search engines
- robots.txt configuration
- Multi-language sitemap support
- External sitemap for non-translated pages

### Internationalization
- Full i18n support via Django's translation framework
- Language switcher in context processors
- Translated URLs for major pages
- Support for multiple languages (English, Welsh, Spanish, Polish)

## URL Structure

### Main Pages
- `/` - Homepage with map and statistics
- `/about-us/` - About Give Food charity
- `/colophon/` - Technical details about the website
- `/bot/` - GiveFoodBot information
- `/privacy/` - Privacy policy
- `/human/` - Human verification endpoint
- `/flag/` - Flag problematic content

### Registration & Donation
- `/register-foodbank/` - Food bank registration form
- `/donate/` - Donation information
- `/donate/managed/<slug>-<key>/` - Managed donation campaign page
- `/donate/managed/<slug>-<key>/geo.json` - Donation campaign GeoJSON

### Annual Reports
- `/annual-reports/` - Annual reports index
- `/<year>/` - Specific year report (2019-2024)

### Utility Endpoints
- `/<uuid:pk>/` - UUID redirect to appropriate object
- `/robots.txt` - Robots file for search engines
- `/sitemap.xml` - Main sitemap
- `/sitemap_external.xml` - External sitemap
- `/frag/<slug>/` - Fragment caching endpoint

### Other Apps (included in URLs)
The `givefood` app's URL configuration includes routes for:
- `/needs/` - gfwfbn (What Food Banks Need)
- `/api/` - gfapi2 (Current API)
- `/admin/` - gfadmin (Admin interface)
- `/dashboard/` - gfdash (Data dashboards)
- `/write/` - gfwrite (Contact MPs tool)
- `/offline/` - gfoffline (Background tasks)
- `/auth/` - gfauth (Authentication)

## Core Components

### Data Models (`models.py`)

The app contains all core data models used across the entire platform:

#### Food Bank Models
- **Foodbank** - Main food bank organizations with address, charity info, political data, contact details
- **FoodbankLocation** - Distribution points operated by food banks
- **FoodbankDonationPoint** - Third-party donation collection points (supermarkets, etc.)
- **FoodbankChange** - Historical record of food bank needs updates
- **FoodbankChangeLine** - Individual items in a needs update
- **FoodbankChangeTranslation** - Multilingual translations of needs
- **FoodbankGroup** - Networks/groupings of food banks
- **FoodbankDiscrepancy** - Data quality issues flagged for review
- **FoodbankArticle** - News articles mentioning food banks
- **FoodbankHit** - Analytics tracking for food bank pages
- **FoodbankSubscriber** - Email subscription management

#### Order & Delivery Models
- **Order** - Food deliveries from Give Food to food banks
- **OrderLine** - Individual line items in orders (deprecated)
- **OrderItem** - Items in orders
- **OrderGroup** - Bulk donation campaigns spanning multiple orders

#### Political Models
- **ParliamentaryConstituency** - UK parliamentary constituency data with boundaries, MPs, and political information
- **ConstituencySubscriber** - Constituency-level email subscriptions

#### Supporting Models
- **GfCredential** - Secure storage for API keys and credentials
- **Place** - Google Places data cache
- **PlacePhoto** - Google Places photo metadata
- **Changelog** - System changelog entries

### Utility Functions (`func.py`)

Extensive collection of 1300+ lines of helper functions including:

#### Data Access
- `get_all_foodbanks()` - Cached food bank retrieval
- `get_all_open_foodbanks()` - Active food banks only
- `get_all_locations()` - All distribution locations
- `find_foodbanks()` - Search food banks by various criteria
- `find_parlcons()` - Find parliamentary constituencies

#### Geographic Functions
- `geocode()` - Convert addresses to coordinates via Google Maps
- `latt_long_from_postcode()` - Postcode to coordinates
- `admin_regions_from_postcode()` - Get administrative regions
- `validate_postcode()` - Postcode validation
- `pluscode()` - Generate Plus Codes
- `distance()` - Calculate distances between points

#### Text Processing
- `clean_foodbank_need_text()` - Parse and clean food bank needs
- `diff_html()` - Generate HTML diffs between versions
- `validate_turnstile()` - Cloudflare Turnstile validation
- `translate_need_async()` - Asynchronous need translation

#### Data Integration
- `get_calories()` - Calculate caloric content of items
- `get_cred()` - Retrieve stored credentials
- `send_email()` - Email sending wrapper
- `gemini()` - Google GenAI integration
- `geojson_dict()` - Generate GeoJSON from querysets

#### Caching
- `decache_async()` - Asynchronous cache invalidation

### Middleware (`middleware.py`)

Custom middleware components:

- **RenderTime** - Injects page render time into responses
- **OfflineKeyCheck** - Validates API keys for offline/background apps
- **LoginRequiredAccess** - Enforces authentication for admin areas (gfadmin)
- **RedirectToWWW** - Redirects origin.givefood.org.uk to www

### Context Processors (`context_processors.py`)

Provides global template context:
- Language information (code, name, direction)
- Canonical URLs and paths
- Instance ID and version numbers
- Facebook locale mapping
- Language switcher URLs
- Flag reporting paths
- Speculation rules for prerendering/prefetching
- App name detection

### Forms (`forms.py`)

Django forms for data entry:

- **FoodbankRegistrationForm** - Public food bank registration
- **FlagForm** - Content flagging form
- **FoodbankForm** - Food bank editing (admin)
- **FoodbankLocationForm** - Location management
- **FoodbankDonationPointForm** - Donation point management
- **OrderForm** - Delivery order creation
- **OrderGroupForm** - Bulk donation campaigns
- **NeedForm** - Food bank needs editing
- **NeedLineForm** - Individual need items
- **ParliamentaryConstituencyForm** - Constituency data
- **GfCredentialForm** - Credential management
- **ChangelogForm** - System changelog

### Constants (`const/`)

Organized constant definitions:
- `cache_times.py` - Cache duration constants
- `general.py` - General configuration, choices, schemas
- `item_types.py` - Food item categorization
- `item_classes.py` - Item classification system
- `parlcon_mp.py` - Parliamentary constituency to MP mapping
- `parlcon_party.py` - Constituency party data
- `topplaces.py` - Popular location searches

### Settings (`settings.py`)

Main Django configuration including:
- Database setup (PostgreSQL)
- Installed apps
- Middleware configuration
- Template engines
- Static file handling
- Internationalization
- Cache backends
- Email configuration
- Third-party integrations (Sentry, Google Maps, etc.)

## Templates

Located in `templates/public/`:

- `index.html` - Homepage
- `about_us.html` - About page
- `colophon.html` - Technical information
- `donate.html` - Donation information
- `managed_donation.html` - Donation campaign display
- `register_foodbank.html` - Registration form
- `bot.html` - Bot documentation
- `ar/` - Annual report templates (2019-2024)
- `includes/` - Reusable template fragments
- Email templates for registration and flagging
- Error pages (403, 500)

## Static Files

Located in `static/`:

### Images (`img/`)
- GiveFoodBot logo
- Annual report images and charts
- Web app manifest screenshots
- Icons and UI elements

### Root Files (`root/`)
- `humans.txt` - Team information
- `security.txt` - Security contact information

## Caching Strategy

Uses Django's `@cache_page` decorator with varied cache times:

- **1 week** (`SECONDS_IN_WEEK`): Static content, annual reports, about us, sitemap
- **1 day** (`SECONDS_IN_DAY`): Flag form
- **1 hour** (`SECONDS_IN_HOUR`): Homepage, managed donations
- **2 minutes** (`SECONDS_IN_TWO_MINUTES`): Fragment endpoints

## Security Features

- Cloudflare Turnstile for bot protection on forms
- CSRF protection via session-csrf
- Email validation on submissions
- Authentication required for admin apps (via middleware)
- Secure credential storage in database
- Content flagging system for moderation

## Technical Requirements

### Dependencies
- Django 5.2.7
- PostgreSQL with django-earthdistance
- Python 3.12
- Bulma CSS framework via django-bulma
- Google GenAI for AI features
- Requests for HTTP operations
- BeautifulSoup for HTML parsing
- feedparser for RSS processing

### External Services
- **Google Maps API** - Geocoding, Places, Static Maps
- **Google GenAI** - AI-powered features
- **Cloudflare Turnstile** - Bot protection
- **Sentry** - Error tracking
- **Cloudflare R2** - Photo storage

## Development Notes

### Model Conventions
- Most models include UUID fields for stable external references
- Geographic models use lat/lng string storage with separate float fields
- Postcode validation uses regex from `const.general`
- Models auto-save edit timestamps
- Extensive use of choices for consistent data entry

### Function Organization
- Geographic functions handle UK postcodes and coordinates
- Text processing functions handle food bank needs parsing
- Cache helper functions maintain performance
- Async functions use django-tasks for background processing

### Template Features
- Multi-language support via `{% trans %}` tags
- Bulma CSS components via custom template tags
- Dynamic map configuration via JSON context
- Speculation rules for performance optimization

### URL Patterns
- Translated URLs use `i18n_patterns()`
- Legacy redirects maintained for old food bank slugs
- Namespace separation for different apps
- Untranslated API and admin routes

## Related Apps

The givefood app is used by all other apps in the project:

- **gfadmin** - Uses models for data management
- **gfapi2** - Exposes models via REST API
- **gfwfbn** - Displays food bank needs to public
- **gfdash** - Visualizes data from models
- **gfoffline** - Background tasks updating models
- **gfwrite** - MP contact tool using constituency data
- **gfauth** - Authentication for admin access

## Contact

- **Email**: mail@givefood.org.uk
- **Website**: https://www.givefood.org.uk
- **Charity Number**: England & Wales 1188192
