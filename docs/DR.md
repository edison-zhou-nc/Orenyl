# Disaster Recovery

## Supported workflows

Lore currently supports:

- snapshot creation,
- snapshot verification,
- snapshot restore.

## Snapshot flow

1. Call `create_snapshot`.
2. Store the returned `snapshot_id`, `storage_uri`, and checksum metadata.
3. Call `verify_snapshot` as part of routine validation.

## Restore flow

1. Verify the target snapshot first.
2. Stop live traffic before restore.
3. Call `restore_snapshot`.
4. Restart the server and run smoke tests.

## Operational notes

- Snapshot metadata is recorded in the database.
- Snapshot files are copied from the active SQLite database path.
- Missing or checksum-mismatched snapshots fail closed.

