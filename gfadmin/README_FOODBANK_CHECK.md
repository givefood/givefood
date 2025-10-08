# Food Bank Check Interface

## Overview
The food bank check interface provides an automated way to verify and update food bank information by analyzing their website content using AI.

## Access
Navigate to: `/admin/foodbank/<SLUG>/check/`

Or click the "Check Data" button on any food bank's admin page.

## Features

### 1. Automatic Data Extraction
The interface automatically:
- Downloads content from the food bank's URLs:
  - Main website URL
  - Shopping list URL
  - Donation points URL
  - Locations URL
- Uses Google's Gemini AI to extract structured data
- Compares extracted data with current database values

### 2. Field Checking
The following fields are checked for discrepancies:
- Address
- Postcode
- Phone number
- Email address
- Facebook page username
- Twitter/X username

### 3. URL Discovery
If URLs for shopping lists, donation points, or locations are missing but found in the main website HTML, they will be:
- Highlighted in the interface
- Used to fetch additional data

### 4. Location and Donation Point Detection
The interface can extract:
- Multiple location information (name, address, postcode, phone, email)
- Donation point information (name, address, postcode, phone)

## Output

The check interface displays:
1. **Discrepancies Table**: Shows current vs. extracted values for each field that differs
2. **Extracted Food Bank Data**: Raw data extracted from the main URL
3. **Extracted Locations**: Locations found on the locations page with comparison to database
4. **Extracted Donation Points**: Donation points found with comparison to database
5. **Errors**: Any connection or parsing errors encountered

## Actions
From the check page, you can:
- Edit food bank details manually
- Add new locations
- Add new donation points
- Return to the main food bank page

## Notes
- The interface is read-only - it identifies discrepancies but doesn't auto-update
- Manual review and editing is required to accept changes
- AI extraction may not be 100% accurate - always verify before updating
