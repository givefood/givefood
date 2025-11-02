# gfwrite - Write to Your MP

Tool allowing constituents to contact their MPs about food banks at https://www.givefood.org.uk/write/

## Overview

gfwrite enables UK constituents to easily contact their Members of Parliament about food bank issues in their constituency. The app provides a streamlined workflow for finding MPs, viewing local food bank data, and composing personalized emails about food insecurity.

**Live URL**: https://www.givefood.org.uk/write/

## Purpose

The tool helps constituents:
- Raise awareness about food bank usage with their MP
- Share concerns about local food insecurity
- Encourage MPs to support policies addressing food poverty
- Build relationships between food banks and representatives

## Key Features

### Postcode Lookup
- **Find Your MP**: Enter postcode to identify your parliamentary constituency
- **Automatic Redirect**: Automatically routes to the correct constituency page
- **Validation**: Uses official postcode data to ensure accuracy

### Constituency Information
- **MP Details**: Shows MP name, party, and contact information
- **Local Food Banks**: Lists all food banks operating in the constituency
- **Interactive Map**: Visual representation of constituency boundaries and food bank locations
- **Context**: Provides relevant local data for the email

### Email Workflow
- **Template Email**: Pre-populated email template about food banks
- **Customization**: Users can edit subject and body before sending
- **Personal Details**: Users provide name, address, and email
- **Preview**: Review email before sending
- **Send**: Delivers email directly to MP with copy to sender

### Subscription System
- **Optional Opt-In**: Users can subscribe to constituency-level updates
- **Food Bank News**: Receive occasional emails about local food banks
- **Privacy Respected**: Clear opt-in with no spam

## URL Structure

### Main Pages
- `/write/` - Homepage with postcode entry form
- `/write/to/<slug>/` - Constituency page showing MP and food banks
- `/write/to/<slug>/email/` - Email composition page
- `/write/to/<slug>/email/send/` - Email sending endpoint (POST)
- `/write/to/<slug>/email/done/` - Confirmation page after sending

## User Journey

### Step 1: Enter Postcode
User visits `/write/` and enters their postcode:
- Form accepts UK postcodes
- Validates and looks up parliamentary constituency
- Redirects to constituency page with postcode in URL

### Step 2: View Constituency
User sees `/write/to/<constituency-slug>/?postcode=SW1A1AA`:
- MP information (name, party, photo)
- List of local food banks
- Interactive map showing constituency and food banks
- Form to enter personal details

### Step 3: Enter Details
User completes form with:
- Full name
- Complete address (including postcode)
- Email address
- Optional: Checkbox to receive updates

### Step 4: Compose Email
User sees pre-filled email at `/write/to/<constituency-slug>/email/`:
- To: MP's name and email
- From: User's name and email
- Subject: Pre-filled with constituency context
- Body: Template email mentioning local food banks
- All fields editable

### Step 5: Send
User reviews and clicks send:
- Email delivered to MP's official email address
- CC sent to user's email address
- BCC sent to Give Food for monitoring
- Reply-to set to user's email for MP's response

### Step 6: Confirmation
User sees confirmation at `/write/to/<constituency-slug>/email/done/`:
- Confirmation that email was sent
- User's email displayed
- Next steps guidance

## Email Template

### Default Content
The template email includes:
- Sender's name and address
- Reference to local food banks by name
- Expression of concern about food insecurity
- Request for MP's support
- Professional, respectful tone

### Email Headers
Emails are configured with:
- **To**: MP's official parliamentary email
- **From**: User's provided email (via Give Food's mail server)
- **Reply-To**: User's email for direct MP responses
- **CC**: User's email for their records
- **BCC**: `write-bcc@givefood.org.uk` for Give Food monitoring
- **Subject**: "Food Banks in [Constituency Name]"

## Forms

### ConstituentDetailsForm
Fields:
- `name` - User's full name (max 100 chars)
- `address` - Full postal address (textarea)
- `email` - Email address for communication
- `subscribe` - Optional checkbox for updates (default checked)

### EmailForm
Fields:
- `to_field` - MP email (read-only)
- `from_field` - User email (read-only)
- `from_name` - Hidden field
- `from_email` - Hidden field
- `subject` - Email subject (editable)
- `body` - Email content (editable textarea)

## Technical Details

### Postcode to Constituency
Uses `admin_regions_from_postcode()` from `givefood.func` to:
- Validate UK postcodes
- Look up parliamentary constituency
- Get constituency slug for routing

### Constituency Data
Uses `ParliamentaryConstituency` model including:
- Constituency name and slug
- MP name, party, and email
- Geographic boundaries for maps
- Associated food banks

### Subscription Management
Uses `ConstituencySubscriber` model to store:
- Subscriber name and email
- Linked parliamentary constituency
- Opt-in timestamp

### Email Delivery
Uses `send_email()` helper from `givefood.func` to:
- Format emails properly
- Set headers (To, From, CC, BCC, Reply-To)
- Add sender details header
- Handle delivery via mail server

### Map Integration
Constituency pages include interactive maps:
- GeoJSON boundary data from `/needs/in/constituency/<slug>/geo.json`
- Food bank location markers
- Constituency outline
- Maximum zoom level of 14

## Templates

Located in `templates/write/`:
- `index.html` - Postcode entry homepage
- `constituency.html` - Constituency information and form
- `email.html` - Email composition interface
- `done.html` - Confirmation page
- `email.txt` - Email body template
- `email_header.txt` - Email header with sender details

## Security & Privacy

### Data Protection
- Minimal data collection (name, address, email)
- No storage of email content
- User controls email content before sending
- Clear privacy notices

### Spam Prevention
- No automated emails from Give Food
- Subscription is optional
- User controls all email content to MP
- BCC monitoring prevents abuse

### Authentication
- No authentication required (public tool)
- One email per form submission
- Rate limiting via server configuration

## Integration with Other Apps

### gfwfbn Integration
- Links to constituency pages at `/needs/in/constituency/<slug>/`
- Uses GeoJSON endpoints for maps
- Shares food bank location data

### givefood Core
- Uses `ParliamentaryConstituency` model
- Uses `ConstituencySubscriber` model
- Uses `admin_regions_from_postcode()` function
- Uses `send_email()` helper

## Use Cases

### Constituents
- Contact MP about local food bank issues
- Raise awareness of food insecurity
- Request policy support
- Build constituency pressure

### MPs
- Hear directly from constituents
- Understand local food bank landscape
- Receive actionable information
- Respond directly to constituents

### Give Food
- Amplify food bank advocacy
- Connect MPs with local issues
- Track engagement (via BCC)
- Build constituency relationships

## Development Notes

### Postcode Handling
- Preserves postcode through workflow via URL parameters
- Used for context but not for email content
- Validates using Give Food's postcode utilities

### Form Validation
- Django forms handle validation
- Invalid submissions redisplay form with errors
- POST-only for email submission
- GET returns 404 for email endpoint

### Email Headers
- Special header added with sender details for MP context
- Header includes: name, email, "with_header" flag
- Helps MPs identify constituent origin

## Related Apps

- **gfwfbn** - Food bank discovery tool
- **givefood** - Core models and utilities
- **gfadmin** - Admin interface for reviewing emails (via BCC)

## Future Enhancements

Potential future features:
- Email templates for different occasions
- Additional recipients (local councillors)
- Social media sharing
- Campaign organization tools
- Impact tracking

## Contact

For questions or issues with the Write to Your MP tool:
- Email: mail@givefood.org.uk
- Include constituency name or postcode for faster assistance
