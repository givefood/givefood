# GitHub Copilot Instructions for Give Food

## About This Project

Give Food is a UK charity that uses data to highlight local and structural food insecurity and provides tools to help alleviate it. We maintain the largest publicly available database of food banks and their needs in the UK, covering nearly 3000 locations.

**Charity Registration:** England & Wales [1188192](https://register-of-charities.charitycommission.gov.uk/en/charity-details/5147019)

## Technology Stack

- **Framework:** Django 5.2.7
- **Python Version:** 3.12
- **Database:** PostgreSQL with django-earthdistance for geographic queries
- **Frontend:** Bulma CSS framework via django-bulma
- **Hosting:** Mythic Beasts (Shoreditch, London) using Coolify
- **CDN:** Cloudflare
- **Static Files:** WhiteNoise for serving, CloudFlare R2 for photos
- **Background Tasks:** django-tasks
- **Internationalization:** Django i18n with translations in locale/ directory
- **Error Tracking:** Sentry
- **AI Integration:** Google GenAI for certain features

## Project Structure

The project follows Django's app-based architecture with multiple specialized apps:

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

## Coding Conventions

### Django Specific

- **Settings Module:** `givefood.settings`
- **URL Patterns:** Each app has its own urls.py that's included in the main URL configuration
- **Templates:** Located in each app's `templates/` directory
- **Static Files:** Located in `givefood/static/`
- **Middleware:** Custom middleware in `givefood.middleware` includes:
  - `LoginRequiredAccess` - Access control
  - `OfflineKeyCheck` - API key validation
  - `RenderTime` - Performance monitoring
  - `RedirectToWWW` - Canonical URL enforcement

### Code Style

- Follow PEP 8 Python style guidelines
- Use Django's best practices for models, views, and templates
- Templates use Django template language with i18n support
- Use Django's built-in utilities (e.g., `humanize`, `bulma` tags)

### Internationalization

- All user-facing strings should be wrapped with `{% trans %}` or `{% blocktrans %}` in templates
- Use `gettext_lazy` for strings in Python code
- Translation files are in `locale/` directory with support for multiple languages (es, pl, etc.)
- Run `./manage.py makemessages` and `./manage.py compilemessages` when adding translatable strings

### Database

- Uses PostgreSQL with geographic extensions
- Models should follow Django ORM conventions
- Geographic queries use django-earthdistance
- Be cautious with database migrations in production

## APIs

The project provides a public API documented at https://www.givefood.org.uk/api/

- **Current API:** gfapi2 (version 2)
- **Legacy API:** gfapi1 (deprecated)
- **Future API:** gfapi3 (in development)

API responses include food bank data, needs, locations, and parliamentary constituency information.

## Data

- **Open Data:** Our data is versioned at https://github.com/givefood/data
- **Web Crawler:** GiveFoodBot extracts data from food bank websites
- **Bot User Agent:** Documented at `/bot/` endpoint
- **Data Sources:** Food bank websites, charity registration data, news feeds

## Development Workflow

### Local Setup

```bash
virtualenv --python=python3.12 .venv
source .venv/bin/activate
pip install -r requirements.txt
./manage.py runserver
```

### Environment Variables

The project uses python-dotenv to load from `.env` file:
- `SECRET_KEY` - Django secret key
- `SENTRY_DSN` - Error tracking
- `COOLIFY_FQDN` - Deployment domain

### Important Files

- `manage.py` - Django management commands
- `requirements.txt` - Python dependencies
- `abbreviations.md` - List of abbreviations used in the project
- `crons.md` - Scheduled task documentation

## Key Features

1. **Food Bank Database:** Near-realtime tracking of 3000+ food bank locations and their needs
2. **API Service:** Public API used by governments, councils, universities, supermarkets, NHS, and media
3. **Write to MP Tool:** Allows users to contact their political representatives
4. **Data Dashboards:** Analytics and visualization of food bank data
5. **Multi-language Support:** Internationalized interface
6. **Web Scraping:** Automated data collection from food bank websites

## Security & Privacy

- No CSRF middleware enabled (handled by session-csrf)
- Debug mode OFF in production
- Sentry integration for error tracking
- Environment-based configuration
- Secure headers and middleware

## Testing

- There is currently no formal test infrastructure
- Manual testing is performed
- When adding features, ensure they work across all supported languages

## Contact & Contribution

- **Email:** mail@givefood.org.uk
- **Twitter:** [@GiveFoodCharity](https://twitter.com/GiveFoodCharity)
- **Facebook:** [GiveFoodOrgUK](https://www.facebook.com/GiveFoodOrgUK)
- **Source Code:** Public domain (see LICENSE)

## When Contributing Code

1. Understand the app structure - each app has a specific purpose
2. Follow Django conventions and existing patterns
3. Consider internationalization - add translations for new strings
4. Be mindful of the production environment - this is a live charity service
5. Test across different food bank scenarios and edge cases
6. Keep the public API stable and well-documented
7. Performance matters - the site serves millions of users
8. Maintain data integrity - food bank data accuracy is critical

## Useful Abbreviations

See `abbreviations.md` for a list of common abbreviations used throughout the codebase.

## Special Considerations

- **Charity Context:** This is a real charity helping real people - data accuracy and site reliability are critical
- **Public Data:** Much of our data is open and used by major organizations
- **Scale:** Serves millions of page views with data on thousands of food banks
- **Multi-tenant:** Different tools serve different audiences (donors, food banks, politicians, researchers)
- **Legacy Support:** Some older API versions (gfapi1) must remain functional for existing users
