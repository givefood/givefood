# SQL

Useful SQL statements for managing the Give Food database.

## Indexes

These indexes are defined on the Django models and should be present in the database. Run these if they are missing.

```sql
-- FoodbankHit: speeds up the 28-day hit annotation on the /admin/foodbanks/ list
-- Index name follows Django's convention: <app>_<model>_<fields>_<hash>
-- Verify the exact name Django expects by running:
--   python manage.py sqlmigrate  (or inspecting Meta.indexes in givefood/models.py)
CREATE INDEX givefood_foodbankhit_foodbank_id_day_e16a5960
    ON givefood_foodbankhit (foodbank_id, day);
```
