# gfoffline

Background tasks and offline processing for the Give Food project (no public URL - internal processes only)

## Overview

This app manages background tasks and offline processing for the Give Food project. It handles scheduled jobs, data maintenance, and automated updates that run independently of user interactions.

## Features

### Views (Internal URLs)

The following views are triggered by scheduled jobs or internal processes:

- **precacher** (`/precacher/`) - Pre-caches food bank and location data in memory
- **discrepancy_check** (`/discrepancy_check/`) - Monitors food bank websites for changes in phone numbers, postcodes, and availability
- **foodbank_need_check** (`/foodbank_need_check/<slug>/`) - Checks and updates what a specific food bank needs
- **need_categorisation** (`/need_categorisation/`) - Categorizes food bank needs using AI
- **pluscodes** (`/pluscodes/`) - Generates Google Plus Codes for food bank locations
- **place_ids** (`/place_ids/`) - Fetches Google Place IDs for food banks and locations
- **load_mps** (`/load_mps/`) - Imports MP data from CSV and downloads their photos
- **refresh_mps** (`/refresh_mps/`) - Updates MP information from Parliament API
- **render_proxy** (`/render_proxy/`) - Renders a URL to Markdown via Cloudflare Browser Rendering, used by the need check

### Management Commands

Run these commands using `python manage.py <command>`:

#### needcheck
Queues a need check for every open food bank onto the `needcheck` queue, recording the batch as a
`CrawlSet`. The checks themselves are performed by the `db_worker` task worker, not by this command —
it returns as soon as everything is enqueued.
```bash
python manage.py needcheck
```
Scheduled: 45 7,11,15,19 * * * (4 times daily at 7:45, 11:45, 15:45, 19:45)

#### getarticles
Fetches and processes news articles from food bank RSS feeds.
```bash
python manage.py getarticles
```
Scheduled: 20 8-22/2 * * * (Every 2 hours from 8:20-22:20)

#### charityinfo
Updates charity registration information for food banks from:
- England & Wales: Charity Commission API
- Scotland: OSCR API
- Northern Ireland: Charity Commission NI

```bash
python manage.py charityinfo
```
Scheduled: 30 5 * * * (Daily at 5:30 AM)

#### resaver
Resaves all instances of a model to trigger save() methods and update dependent data.
```bash
python manage.py resaver <ModelName>
# Example: python manage.py resaver Foodbank
```

#### cleanup_subs
Cleans up food bank subscriber data.
```bash
python manage.py cleanup_subs
```

#### days_between_needs
Calculates statistics on the frequency of needs updates.
```bash
python manage.py days_between_needs
```

#### regenerate_need_ids
Regenerates unique IDs for food bank needs.
```bash
python manage.py regenerate_need_ids
```

#### set_foodbank_bounds
Sets the map bounds (`bounds_north`, `bounds_south`, `bounds_east`, `bounds_west`) for all food banks
from their locations and donation points.
```bash
python manage.py set_foodbank_bounds
```

#### place_populations
Populates the `population` field on each Place using AI (Gemini), in batches.
```bash
python manage.py place_populations
```

#### import_places
Replaces all Place rows with the contents of `places.csv`.
```bash
python manage.py import_places
```

#### import_postcodes
Imports postcodes from a CSV file, skipping any not marked "In Use".
```bash
python manage.py import_postcodes
```

#### newlang
Translates `latest_need` for all food banks into a specified language — used when adding a new locale.
```bash
python manage.py newlang <language_code>
```

## Templates

The app includes AI prompt templates for:
- `foodbank_need_prompt.txt` - Extracting needs from food bank websites
- `foodbank_detail_prompt.txt` - Extracting contact details from websites
- `categorisation_prompt.txt` - Categorizing food items
- `need_check.html` - Display template for need check results

## Key Functions

### Automated Data Maintenance
- **Web Scraping**: Monitors food bank websites for changes using the GiveFoodBot user agent. Pages
  are rendered to Markdown via Cloudflare Browser Rendering, so JS-heavy sites (the Trussell/IFAN
  `*.foodbank.org.uk` platforms) resolve correctly
- **AI Integration**: Needs are extracted with DeepSeek via OpenRouter; Google GenAI (Gemini) handles
  contact-detail extraction, item categorisation and place populations
- **Geocoding**: Maintains location data with Google Plus Codes and Place IDs
- **Charity Data**: Syncs with official charity registries across UK nations

### Discrepancy Detection
The discrepancy check system identifies when food bank websites show:
- Changed phone numbers
- Changed postcodes
- Website unavailability or errors

### Caching
Maintains in-memory caches of frequently accessed data to improve API and website performance.

## Related Documentation

- [Cron schedule](../docs/crons.md) - Details of scheduled task timings
- [Main README](../README.md) - Project overview and structure
