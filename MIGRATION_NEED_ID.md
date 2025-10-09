# Need ID Migration to UUID

## Overview

This migration replaces the SHA256-based hash generation for `FoodbankChange.need_id` with UUID-based generation.

## Changes Made

1. **Model Update**: The `FoodbankChange.save()` method now generates `need_id` using `uuid.uuid4().hex[:8]` instead of `hashlib.sha256(str_to_hash).hexdigest()[:8]`

2. **Management Command**: A new management command `regenerate_need_ids` has been created to update all existing records with UUID-based IDs.

## Running the Migration

To regenerate all existing need_ids:

```bash
python manage.py regenerate_need_ids
```

**Important**: 
- This command updates the `need_id` field without triggering the `modified` field update, preserving the original modification timestamps.
- **Breaking Change**: All existing URLs containing old need_ids will no longer work after running this command. This is expected behavior as all needs receive completely new IDs.

## Technical Details

- The new UUID-based need_ids are still 8 hexadecimal characters
- All existing URL patterns (`\b[0-9a-f]{8}\b`) continue to work without changes
- The API responses remain compatible with existing clients
- New records automatically receive UUID-based need_ids

## Why This Change?

UUID generation provides:
- Better uniqueness guarantees
- No dependency on timestamp or URI (which could be unavailable)
- Simpler code without encoding and hashing steps
