# Need ID Migration to UUID

## Overview

This migration replaces the SHA256-based hash generation for `FoodbankChange.need_id` with full UUID generation.

## Changes Made

1. **Model Update**: The `FoodbankChange.need_id` field is now a `UUIDField` with automatic UUID generation via `default=uuid.uuid4`

2. **Management Command**: A new management command `regenerate_need_ids` has been created to update all existing records with full UUIDs.

## Running the Migration

To regenerate all existing need_ids:

```bash
python manage.py regenerate_need_ids
```

**Important**: 
- This command updates the `need_id` field without triggering the `modified` field update, preserving the original modification timestamps.
- **Breaking Change**: All existing URLs containing old need_ids will no longer work after running this command. This is expected behavior as all needs receive completely new UUIDs.

## Technical Details

- The new need_ids are full UUIDs (36 characters with dashes, e.g., `992af24a-e590-40c9-8f35-1c6d3e68a023`)
- URL patterns have been updated to accept the full UUID format
- The API responses now return full UUIDs in the `id` and `need_id` fields
- New records automatically receive UUID-based need_ids via the field default

## Why This Change?

UUID generation provides:
- Better uniqueness guarantees with standard UUID format
- No dependency on timestamp or URI
- Simpler code with automatic generation by Django
- Industry-standard identifier format
