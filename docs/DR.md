# Disaster Recovery

## Scope

Orenyl currently supports database-wide disaster recovery for single-tenant SQLite deployments through:

- snapshot creation
- snapshot verification
- snapshot restore

## Operational targets

Treat these as starting guidance, not guarantees:

- Suggested RPO: up to the age of the most recent verified snapshot
- Suggested RTO: minutes, depending on database size, storage throughput, and post-restore validation

If you need tighter objectives, run snapshots more frequently and rehearse restore on production-sized data.

## Snapshot flow

1. Call `create_snapshot`.
2. Record the returned `snapshot_id` and checksum.
3. Verify the snapshot with `verify_snapshot`.
4. Store the verified artifact in your backup retention workflow.

`create_snapshot` does not return `storage_uri` in the API response. Orenyl keeps snapshot file paths in internal DR metadata instead.

## Verification flow

Run `verify_snapshot` routinely, not only during incidents.

Recommended cadence:

- after every snapshot
- after moving backup artifacts
- on a scheduled restore-readiness drill

Verification fails closed when:

- the snapshot record is missing
- the stored path escapes the configured snapshot directory
- the snapshot file is missing
- the checksum does not match

## Restore flow

1. Stop live traffic.
2. Run `verify_snapshot` for the target snapshot.
3. Call `restore_snapshot`.
4. Restart Orenyl.
5. Run smoke tests against the restored database.
6. Confirm expected event counts, retrieval behavior, and audit access still work.

Orenyl creates a `.pre_restore.bak` file beside the active database before restoring when the target database already exists.

## Restore rehearsal checklist

- Snapshot can be created successfully.
- Verification passes before restore.
- Restore completes successfully inside a database transaction.
- Pre-restore backup file is present when expected.
- Expected historical events are present after restore.
- Events created after the snapshot do not appear after restore.

## Configuration

Key environment variables:

- `ORENYL_DB_PATH`: active SQLite database path
- `ORENYL_DR_SNAPSHOT_DIR`: directory used for snapshot artifacts
- `ORENYL_ENABLE_MULTI_TENANT=0`: required for create/restore snapshot operations

Verification remains available in multi-tenant mode because it checks an existing artifact and does not materialize a database-wide backup.

## Recommended practice

- Keep snapshot storage on a different volume or backup target than the live database.
- Test restore on a separate host or temp workspace before relying on the process in production.
- Pair DR drills with application smoke tests, not checksum validation alone.
