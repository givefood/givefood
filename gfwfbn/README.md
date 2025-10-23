# gfwfbn - What Food Banks Need

The "What Food Banks Need" tool at https://www.givefood.org.uk/needs/

This is Give Food's primary public-facing application that helps people find food banks near them and see what items they need donated.

## Features

### Food Bank Discovery
- **Location-based search**: Find food banks near an address or coordinates
- **Food bank details**: Comprehensive information about each food bank including current needs, contact information, and charity details
- **Interactive maps**: Visual representation of food banks, locations, and donation points using GeoJSON
- **Nearby search**: Find other food banks in the area

### Food Bank Pages
- **Main food bank page**: Shows current needs, contact info, and basic information
- **Locations**: Separate distribution points operated by the food bank
- **Donation points**: Third-party locations (e.g., supermarkets) where items can be dropped off
- **News**: Feed of articles mentioning the food bank
- **Charity information**: Financial data from Charity Commission
- **Social media**: Links to the food bank's social media presence

### Subscription System
- **Email notifications**: Users can subscribe to receive updates when a food bank's needs change
- **Confirmation workflow**: Double opt-in process with confirmation emails
- **Unsubscribe functionality**: Easy one-click unsubscribe via unique keys

### Parliamentary Constituencies
- **Constituency search**: Find food banks by postcode or constituency name
- **Constituency pages**: View all food banks operating within a parliamentary constituency
- **Boundary visualization**: Display constituency boundaries on maps

### Data Feeds
- **RSS feeds**: Site-wide and per-food bank RSS feeds for needs and news
- **GeoJSON endpoints**: Machine-readable geographic data for maps and integrations
- **Web app manifest**: Progressive Web App support

### Media & Images
- **Static maps**: Pre-rendered PNG maps of food banks
- **Photos**: Google Places photos of food banks and locations
- **Screenshots**: Automated screenshots of food bank websites and shopping lists

## URL Structure

### Main Pages
- `/needs/` - Homepage with location search
- `/needs/getlocation/` - Non-JS location detection using IP geolocation
- `/needs/rss.xml` - Site-wide RSS feed
- `/needs/manifest.json` - Web app manifest

### Food Bank Pages
- `/needs/at/<slug>/` - Food bank detail page
- `/needs/at/<slug>/rss.xml` - Food bank RSS feed
- `/needs/at/<slug>/locations/` - All locations for a food bank
- `/needs/at/<slug>/<locslug>/` - Individual location page
- `/needs/at/<slug>/donationpoints/` - All donation points for a food bank
- `/needs/at/<slug>/donationpoint/<dpslug>/` - Individual donation point page
- `/needs/at/<slug>/news/` - News articles mentioning the food bank
- `/needs/at/<slug>/charity/` - Charity Commission financial information
- `/needs/at/<slug>/socialmedia/` - Social media links
- `/needs/at/<slug>/nearby/` - Nearby food banks

### Subscription Pages
- `/needs/at/<slug>/subscribe/` - Subscribe to email updates
- `/needs/at/<slug>/subscribe/sample/` - Preview of notification email
- `/needs/at/<slug>/updates/subscribe/` - Process subscription (POST)
- `/needs/at/<slug>/updates/confirm/` - Confirm subscription via email link
- `/needs/at/<slug>/updates/unsubscribe/` - Unsubscribe via email link

### Constituency Pages
- `/needs/in/constituencies/` - List all constituencies
- `/needs/in/constituency/<slug>/` - Constituency detail page

### Data Endpoints
- `/needs/geo.json` - GeoJSON of all food banks, locations, and donation points
- `/needs/at/<slug>/geo.json` - GeoJSON for a specific food bank
- `/needs/in/constituency/<slug>/geo.json` - GeoJSON for a constituency

### Media Endpoints
- `/needs/at/<slug>/map.png` - Static map image (600x400 or 1080px)
- `/needs/at/<slug>/photo.jpg` - Food bank photo from Google Places
- `/needs/at/<slug>/screenshots/homepage.png` - Screenshot of food bank website
- `/needs/at/<slug>/screenshots/shoppinglist.png` - Screenshot of shopping list page
- `/needs/at/<slug>/<locslug>/map.png` - Static map of a location
- `/needs/at/<slug>/<locslug>/photo.jpg` - Location photo
- `/needs/at/<slug>/donationpoint/<dpslug>/photo.jpg` - Donation point photo
- `/needs/at/<slug>/donationpoint/<dpslug>/openinghours/` - Opening hours table

### Analytics
- `/needs/at/<slug>/hit/` - Hit counter endpoint (returns JavaScript)

## Forms

The app includes several forms for food bank data management:

- **NeedForm**: Update food bank needs and excess items
- **FoodbankLocationForm**: Edit food bank address and delivery information
- **LocationLocationForm**: Edit individual location details
- **ContactForm**: Update food bank contact information and social media

## Internationalization

The app is fully internationalized using Django's i18n framework. All user-facing strings are wrapped with translation functions and available in multiple languages including Spanish and Polish.

## Caching

Aggressive caching is used throughout the app:
- **1 hour**: Search results, location lookups
- **1 day**: Food bank detail pages, maps
- **1 week**: Static content, GeoJSON, photos, screenshots
- **Never cached**: Location detection, hit counter, subscription actions

## External Dependencies

### APIs & Services
- **Google Maps API**: 
  - Static maps for food bank locations
  - Places API for photos
  - Geocoding for address lookup
- **freeipapi.com**: IP-based geolocation for location detection
- **Cloudflare Turnstile**: Bot protection for subscription forms

### Django Apps
- Uses models from the main `givefood` app:
  - `Foodbank`, `FoodbankLocation`, `FoodbankDonationPoint`
  - `FoodbankChange` (needs tracking)
  - `FoodbankSubscriber` (email subscriptions)
  - `FoodbankHit` (analytics)
  - `FoodbankArticle` (news)
  - `ParliamentaryConstituency`
  - `CharityYear`

## Technical Notes

### GeoJSON Precision
- All items: 4 decimal places (~11m precision)
- Single food bank/constituency: 6 decimal places (~0.11m precision)

### Map Markers
- Red: Main food bank location
- Yellow: Distribution locations
- Blue: Donation points

### Security
- CSRF exempt on subscription endpoint (uses Turnstile instead)
- Email validation on subscriptions
- Unique keys for subscription management
- Duplicate prevention via database constraints
