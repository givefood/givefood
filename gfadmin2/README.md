# gfadmin2 - Modern Admin Interface with htmx

This is a rebuilt version of the Give Food admin interface, featuring:

## Key Features

- **htmx-powered interactions** - No full page reloads for most actions
- **Bulma CSS styling** - Consistent with the rest of the Give Food site
- **Tabbed interfaces** - Dynamic content loading for food bank details
- **Live search** - Results update as you type
- **Inline actions** - Publish, delete, and manage content without navigation
- **Responsive design** - Works on all screen sizes

## Architecture

### Views (views.py)
All views support both traditional requests and htmx requests:
- Traditional requests return full pages
- htmx requests return HTML fragments for dynamic updates

Key views:
- `index()` - Dashboard with needs, discrepancies, and stats
- `foodbanks_list()` - Sortable list of food banks
- `foodbank_detail()` - Tabbed detail view
- `needs_list()` - Filterable needs list
- `search()` - Live search across entities

### Templates
- `base.html` - Base template with htmx CDN and navigation
- `index.html` - Dashboard
- `foodbanks_list.html` - Food banks with sorting
- `foodbank_detail.html` - Tabbed detail view
- `needs_list.html` - Needs with filtering
- `search.html` - Live search interface
- `includes/` - Reusable fragments for htmx responses

### htmx Patterns Used

**Sorting**: Dropdown triggers htmx request to update table
```html
<select hx-get="..." hx-target="#table" hx-trigger="change">
```

**Tabs**: Links load content into tab container
```html
<a hx-get="...?tab=needs" hx-target="#tab-content" hx-push-url="true">
```

**Live Search**: Input triggers search with delay
```html
<input hx-get="..." hx-trigger="keyup changed delay:300ms" hx-target="#results">
```

**Inline Actions**: Buttons update specific elements
```html
<button hx-post="..." hx-target="closest tr" hx-swap="outerHTML">
```

## URL Structure

All URLs are prefixed with `/admin2/`:

- `/admin2/` - Dashboard
- `/admin2/foodbanks/` - Food banks list
- `/admin2/foodbank/{slug}/` - Food bank detail
- `/admin2/needs/` - Needs list
- `/admin2/need/{id}/` - Need detail
- `/admin2/orders/` - Orders list
- `/admin2/search/` - Search

## Development

The app follows standard Django patterns:
1. Views detect htmx requests via `request.headers.get('HX-Request')`
2. Full requests return complete pages
3. htmx requests return HTML fragments
4. All state changes use POST with CSRF protection

## Future Enhancements

Potential additions:
- More admin screens (locations, donation points, settings)
- Complex workflows (need categorization, crawl management)
- Advanced htmx features (polling, SSE for real-time updates)
- Optimistic UI updates
- Better error handling
