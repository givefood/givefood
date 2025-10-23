# gfdumps

This app manages data dumps for the Give Food project.

## Features

- **Views**: Provides web interface for browsing and downloading data dumps at `/dumps/`
- **Management Command**: `dump` command generates daily CSV dumps of food bank and items data
- **Templates**: User interface for accessing dumps at different time periods

## URL Structure

- `/dumps/` - Index of available dump types
- `/dumps/<type>/` - List of available formats for a dump type
- `/dumps/<type>/<format>/` - List of available dumps for a type and format
- `/dumps/<type>/<format>/latest/` - Download the latest dump
- `/dumps/<type>/<format>/YYYY-MM-DD/` - Download a specific date's dump

## Management Command

The `dump` command creates two types of dumps:

1. **foodbanks**: CSV dump of all food banks and their locations
2. **items**: CSV dump of all food bank need items

Old dumps (older than 28 days, except for the 1st of each month) are automatically deleted.

Usage:
```bash
python manage.py dump
```
