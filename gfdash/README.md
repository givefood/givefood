# gfdash

This app provides data dashboards and analytics for the Give Food project, displaying insights about food banks, their needs, and donation patterns.

## Purpose

The gfdash app offers a collection of data visualization dashboards primarily aimed at food bank networks, researchers, and partners. These dashboards help understand trends in food bank needs, track donations, and analyze patterns in food insecurity across the UK.

**Public URL**: https://www.givefood.org.uk/dashboard/

## Features

### Food Bank Need Analytics

- **Most Requested Items** (`/dashboard/most-requested-items/`) - Shows the most frequently requested items across food banks with configurable time periods (7, 30, 60, 90, 120, or 365 days)
- **Most Excess Items** (`/dashboard/most-excess-items/`) - Displays items food banks have in excess with configurable time periods
- **Weekly Item Count** (`/dashboard/items-requested-weekly/`) - Tracks the number of items requested per week since 2020
- **Weekly Item Count by Year** (`/dashboard/items-requested-weekly/by-year/`) - Year-over-year comparison of weekly item requests
- **Item Categories** (`/dashboard/item-categories/`) - Aggregates and counts items by category
- **Item Groups** (`/dashboard/item-groups/`) - Aggregates and counts items by group
- **Bean & Pasta Index** (`/dashboard/bean-pasta-index/`) - Tracks mentions of beans and pasta in food bank needs over time

### Trussell Trust Specific

- **Old Data** (`/dashboard/trusselltrust/old-data/`) - Shows Trussell Trust food banks with oldest and newest data updates
- **Most Requested Items (TT)** (`/dashboard/trusselltrust/most-requested-items/`) - Filtered version of most requested items for Trussell Trust network only

### Partner-Specific Dashboards

- **BeautyBanks** (`/dashboard/beautybanks/`) - Tracks toiletries and personal care items requested by food banks, with geographic filtering for London
- **Excess Stock** (`/dashboard/excess/`) - Lists recent excess stock reports from food banks

### Food Bank Discovery

- **Food Banks Found** (`/dashboard/foodbanks-found/`) - Cumulative count of food banks discovered over time

### News & Articles

- **Articles** (`/dashboard/articles/`) - Recent food bank-related news articles

### Delivery Analytics

- **Deliveries** (`/dashboard/deliveries/<metric>/`) - Tracks Give Food deliveries by:
  - `count` - Number of deliveries
  - `items` - Total items delivered
  - `weight` - Total weight in kilograms
  - `calories` - Total calories delivered
- **Price per Kilogram** (`/dashboard/price-per/kg/`) - Analyzes the cost efficiency of deliveries per kg
- **Price per Calorie** (`/dashboard/price-per/calorie/`) - Analyzes the cost efficiency of deliveries per calorie

### Donation Points

- **Supermarkets** (`/dashboard/donationpoints/supermarkets/`) - Shows distribution of donation points by supermarket company

### Financial Data

- **Charity Income & Expenditure** (`/dashboard/charity-income-expenditure/`) - Aggregates income and expenditure for food bank charities over the past 5 years

## Caching Strategy

All dashboard views are cached to improve performance and reduce database load:

- **Daily Cache** (`SECONDS_IN_DAY`) - Used for most analytics dashboards that don't require real-time updates
- **Hourly Cache** (`SECONDS_IN_HOUR`) - Used for more dynamic data like articles, old data tracking, and partner dashboards

## Data Sources

The dashboards utilize data from multiple Django models:

- `Foodbank` - Food bank locations and metadata
- `FoodbankChange` - Historical records of food bank needs updates
- `FoodbankChangeLine` - Individual items from needs updates
- `FoodbankArticle` - News articles about food banks
- `FoodbankDonationPoint` - Physical donation collection points
- `Order` & `OrderLine` - Give Food delivery orders
- `CharityYear` - Annual charity financial data

## URL Structure

All dashboard URLs are prefixed with `/dashboard/` and follow RESTful patterns where applicable. Some dashboards accept query parameters:

- `?days=N` - Filter by time period (where N is one of: 7, 30, 60, 90, 120, 365)

## Technical Details

- All views are function-based views using Django's `@cache_page` decorator
- Templates are located in `gfdash/templates/dash/`
- Geographic filtering uses Django's Earthdistance extension for location-based queries
- Some dashboards use raw SQL for complex aggregations and performance optimization
