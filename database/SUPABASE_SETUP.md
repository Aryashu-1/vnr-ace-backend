Use [supabase_vnr_ace_cleanup.sql](/c:/Users/Work/code/vnr-ace-backend/database/supabase_vnr_ace_cleanup.sql) only if you want to replace conflicting legacy tables completely.

Normal setup flow:
1. Open Supabase SQL Editor.
2. Run [supabase_vnr_ace_schema.sql](/c:/Users/Work/code/vnr-ace-backend/database/supabase_vnr_ace_schema.sql).
3. From your app env, run `python scripts/sync_vnr_ace_data.py`.

Clean replacement flow:
1. Back up the existing database.
2. Run [supabase_vnr_ace_cleanup.sql](/c:/Users/Work/code/vnr-ace-backend/database/supabase_vnr_ace_cleanup.sql).
3. Run [supabase_vnr_ace_schema.sql](/c:/Users/Work/code/vnr-ace-backend/database/supabase_vnr_ace_schema.sql).
4. Run `python scripts/sync_vnr_ace_data.py`.

Alembic baseline afterward:
1. Do not keep forcing `alembic upgrade head` against the legacy path.
2. After the schema exists in Supabase, stamp the DB to the latest revision:
   `poetry run alembic stamp 9f5ab90ded04`
3. Future migrations can then build forward from that baseline.

Notes:
- This Supabase SQL uses UUID primary keys consistently.
- That matches Supabase better than the mixed integer/UUID state in the current repo.
- The ingestion script and several ORM models still assume some integer IDs today, so the next cleanup pass should align app code fully to UUIDs.
