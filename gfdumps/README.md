# gfdumps - Data Dumps Management

Manages data dumps for the Give Food project at https://www.givefood.org.uk/dumps/

## Overview

gfdumps provides public access to daily CSV exports of Give Food's food bank database. These dumps allow researchers, developers, and organizations to access historical snapshots of food bank data for analysis, backup, or integration purposes.

**Live URL**: https://www.givefood.org.uk/dumps/

## Purpose

Data dumps serve multiple purposes:
- **Research**: Academic and policy research on food insecurity
- **Integration**: Third-party systems can import bulk data
- **Backup**: Historical snapshots of database state
- **Transparency**: Open access to Give Food's public data
- **Offline Analysis**: Download data for local processing

## Features

### Web Interface
- **Browse Dumps**: View available dump types and formats
- **Download Latest**: Quick access to most recent data
- **Historical Access**: Download dumps from specific dates
- **Format Selection**: Choose CSV format

### Daily Generation
- **Automated Creation**: New dumps created daily via management command
- **Retention Policy**: Keeps dumps for 28 days, plus 1st of each month
- **Multiple Types**: Different dump types for different use cases

### CSV Export
- **Standard Format**: CSV files compatible with Excel, databases, etc.
- **Headers**: Column names included in first row
- **UTF-8 Encoding**: Proper handling of international characters
- **Consistent Schema**: Stable column structure across dumps

## Dump Types

### 1. Food Banks Dump
**Type**: `foodbanks`  
**Content**: All food banks and their locations

**Columns Include**:
- Food bank name and slug
- Contact information (phone, email, website)
- Address and postcode
- Geographic coordinates
- Charity registration details
- Parliamentary constituency
- Network affiliation
- Current needs
- Locations (distribution points)

### 2. Items Dump
**Type**: `items`  
**Content**: All food bank need items

**Columns Include**:
- Food bank name and slug
- Item name
- Item category and type
- Timestamp of need
- Need ID
- Quantity indicators (if available)
- Item classification

## URL Structure

### Browse Interface
- `/dumps/` - Index showing available dump types
- `/dumps/<type>/` - List formats for a dump type (e.g., `/dumps/foodbanks/`)
- `/dumps/<type>/<format>/` - List available dumps (e.g., `/dumps/foodbanks/csv/`)
- `/dumps/<type>/<format>/latest/` - Download latest dump
- `/dumps/<type>/<format>/YYYY-MM-DD/` - Download specific date's dump

### Examples
```
/dumps/foodbanks/csv/latest/           # Latest food banks CSV
/dumps/foodbanks/csv/2024-11-01/       # Food banks from Nov 1, 2024
/dumps/items/csv/latest/               # Latest items CSV
/dumps/items/csv/2024-11-01/           # Items from Nov 1, 2024
```

## Management Command

### Generate Dumps
The `dump` management command creates new data exports:

```bash
python manage.py dump
```

**What it does**:
1. Generates CSV dump for food banks
2. Generates CSV dump for items
3. Saves files with date-stamped filenames
4. Deletes old dumps (>28 days, except monthly archives)
5. Logs dump creation

**Scheduling**: Should be run daily via cron or task scheduler

### Retention Policy
- **Recent dumps**: Kept for 28 days
- **Monthly archives**: 1st of each month kept indefinitely
- **Automatic cleanup**: Old files deleted during each run

### File Naming
Dumps are saved with consistent naming:
- Format: `<type>_<YYYY-MM-DD>.csv`
- Example: `foodbanks_2024-11-02.csv`
- Example: `items_2024-11-02.csv`

## File Structure

### Food Banks CSV Schema
Typical columns:
```
name,slug,url,phone,email,address,postcode,lat_lng,
charity_number,network,mp,constituency,needs,locations,...
```

### Items CSV Schema
Typical columns:
```
foodbank_name,foodbank_slug,item,category,type,
need_id,timestamp,quantity,...
```

## Technical Details

### Storage
- Dumps stored in filesystem (location configured in settings)
- Public read access via Django views
- Served with appropriate content-type headers

### Generation Process
1. Query database for all relevant records
2. Format data as CSV rows
3. Write to file with date-stamped name
4. Set proper file permissions
5. Clean up old dumps
6. Log completion

### Performance
- Generation happens offline (not during user requests)
- Pre-generated files served quickly
- No database load during downloads

### Caching
Views are cached for performance:
- Index and listing pages cached
- Direct file downloads not cached
- Cache invalidation on new dump generation

## Use Cases

### Academic Research
Researchers studying food insecurity can:
- Download historical data for trend analysis
- Compare needs across regions
- Track food bank growth
- Analyze item patterns

### Integration Projects
Developers can:
- Import data into their systems
- Build visualizations
- Create custom tools
- Aggregate with other datasets

### Media & Journalism
Journalists can:
- Analyze food bank coverage
- Identify stories in specific areas
- Track changes over time
- Create data visualizations

### Policy Analysis
Policy makers can:
- Understand food insecurity patterns
- Evaluate program effectiveness
- Plan resource allocation
- Support evidence-based decisions

## Data Licensing

Give Food's data is public domain. See the main project [LICENSE](../../LICENSE) file for details.

When using dumps:
- **Credit**: Link to www.givefood.org.uk
- **Update**: Refresh data regularly (it changes multiple times daily)
- **Link**: Include links to food banks when displaying their data
- **Respect**: Don't bulk contact food banks using the data

## Integration with API

For real-time data access, use the [API](../gfapi2/) instead of dumps:
- **API**: Current data, more fields, filtered queries
- **Dumps**: Historical snapshots, bulk download, offline analysis

Choose dumps when you need:
- Complete dataset downloads
- Historical point-in-time data
- Offline processing
- Reduced API calls

Choose API when you need:
- Current/live data
- Specific filtered queries
- Geographic search
- Integration with web apps

## Templates

Located in `templates/dumps/`:
- `index.html` - Main dumps index page
- `type.html` - Format selection for a dump type
- `list.html` - List of available dumps for type/format

## Monitoring

### Health Checks
Monitor dump generation:
- Check daily dump creation
- Verify file sizes are reasonable
- Ensure cleanup happens correctly
- Alert on generation failures

### Usage Tracking
Track dump downloads to understand:
- Most popular dump types
- Download frequency
- Peak usage times
- File size trends

## Related Apps

- **gfapi2** - API for real-time data access
- **givefood** - Core models being dumped
- **gfadmin** - Admin interface for data management
- **gfdash** - Visualizations of the same data

## Development Notes

### Adding New Dump Types
To add a new dump type:
1. Add generation logic to `management/commands/dump.py`
2. Define CSV schema/columns
3. Update templates to list new type
4. Update this documentation

### Customizing Retention
Adjust retention policy in `dump.py`:
- Change 28-day threshold
- Modify monthly archive logic
- Add custom retention rules

### Performance Optimization
For large dumps:
- Use streaming CSV writing
- Add progress indicators
- Implement compression
- Consider splitting into multiple files

## Contact

For questions about data dumps:
- Email: mail@givefood.org.uk
- Include dump type and date if reporting issues
