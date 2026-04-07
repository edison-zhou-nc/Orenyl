-- Orenyl Governed Memory Schema
-- 5 tables. That's it.

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,              -- "event:<type>:<uuid>"
    type TEXT NOT NULL,               -- e.g. "med_started", "role_assigned", "diet_preference"
    payload TEXT NOT NULL,            -- JSON blob
    content_hash TEXT,
    sensitivity TEXT NOT NULL DEFAULT 'medium',
    consent_source TEXT NOT NULL DEFAULT 'implicit',
    expires_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    retention_tier TEXT NOT NULL DEFAULT 'hot',
    archived_at TEXT,
    agent_id TEXT,
    session_id TEXT,
    source TEXT DEFAULT 'user',       -- who/what created this
    tenant_id TEXT NOT NULL DEFAULT 'default',
    ts TEXT NOT NULL,                 -- ISO 8601 timestamp of when the event occurred
    valid_from TEXT,                  -- optional: when this event becomes relevant
    valid_to TEXT,                    -- optional: when this event stops being relevant
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    deleted_at TEXT                   -- soft delete (NULL = active)
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,              -- "fact:<key>:v<version>"
    key TEXT NOT NULL,                -- e.g. "active_medications", "current_role", "diet_preference"
    value TEXT NOT NULL,              -- JSON blob
    transform_config TEXT NOT NULL DEFAULT '{}',
    stale INTEGER NOT NULL DEFAULT 0,
    importance REAL NOT NULL DEFAULT 0.5,
    version INTEGER NOT NULL DEFAULT 1,
    rule_id TEXT NOT NULL,            -- which derivation rule produced this
    rule_version TEXT NOT NULL DEFAULT 'v1',
    confidence REAL NOT NULL DEFAULT 1.0,
    model_id TEXT NOT NULL DEFAULT 'deterministic',
    tenant_id TEXT NOT NULL DEFAULT 'default',
    valid_from TEXT NOT NULL,
    valid_to TEXT,                    -- NULL = currently valid
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    invalidated_at TEXT,             -- set when downstream delete propagation hits this
    invalidation_reason TEXT          -- why it was invalidated
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    parent_id TEXT NOT NULL,          -- upstream item (event or fact)
    parent_type TEXT NOT NULL,        -- "event" or "fact"
    child_id TEXT NOT NULL,           -- downstream item (fact)
    child_type TEXT NOT NULL DEFAULT 'fact',
    relation TEXT NOT NULL DEFAULT 'derived_from',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tombstones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    target_id TEXT NOT NULL,          -- what was deleted
    target_type TEXT NOT NULL,        -- "event" or "fact"
    reason TEXT,                      -- why it was deleted
    deleted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    cascade_invalidated TEXT          -- JSON array of downstream fact IDs that were invalidated
);

CREATE TABLE IF NOT EXISTS retrieval_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    query TEXT,                       -- what was asked
    context_pack TEXT NOT NULL,       -- JSON: the full context pack returned
    trace TEXT NOT NULL,              -- JSON: why each item was included
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS event_domains (
    event_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, domain)
);

CREATE TABLE IF NOT EXISTS domain_registry (
    domain TEXT PRIMARY KEY,
    display_name TEXT,
    is_core INTEGER NOT NULL DEFAULT 0,
    aliases TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    event_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_registry (
    rule_family TEXT NOT NULL,
    version TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (rule_family, version)
);

CREATE TABLE IF NOT EXISTS tenant_registry (
    tenant_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',
    key_version TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS agent_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    action TEXT NOT NULL,
    effect TEXT NOT NULL DEFAULT 'allow',
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS delegation_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    grantor_agent_id TEXT NOT NULL,
    grantee_agent_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    fact_id TEXT,
    action TEXT NOT NULL DEFAULT 'read',
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sync_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    direction TEXT NOT NULL,          -- outbound|inbound
    envelope_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS event_embeddings (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    model_id TEXT NOT NULL,
    vector TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fact_embeddings (
    fact_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    model_id TEXT NOT NULL,
    vector TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS consent_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    subject_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL,             -- granted|withdrawn|expired
    legal_basis TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'user',
    effective_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS subject_requests (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    subject_id TEXT NOT NULL,
    request_type TEXT NOT NULL,       -- erasure|portability|access|rectification
    status TEXT NOT NULL DEFAULT 'open',
    opened_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    closed_at TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS dr_snapshots (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    wal_lsn TEXT NOT NULL DEFAULT '',
    checksum TEXT NOT NULL DEFAULT '',
    storage_uri TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    verified_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_deleted ON events(deleted_at);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
CREATE INDEX IF NOT EXISTS idx_facts_valid ON facts(invalidated_at);
CREATE INDEX IF NOT EXISTS idx_edges_parent ON edges(parent_id);
CREATE INDEX IF NOT EXISTS idx_edges_child ON edges(child_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_unique_relation
ON edges(parent_id, parent_type, child_id, child_type, relation);
CREATE INDEX IF NOT EXISTS idx_events_content_hash ON events(content_hash);
CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_tenant_id ON events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_domains_domain ON event_domains(domain);
CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_key_version_unique ON facts(tenant_id, key, version);
CREATE INDEX IF NOT EXISTS idx_facts_tenant_id ON facts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_edges_tenant_id ON edges(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tombstones_tenant_id ON tombstones(tenant_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_logs_tenant_ts ON retrieval_logs(tenant_id, ts);
CREATE INDEX IF NOT EXISTS idx_event_embeddings_tenant_id ON event_embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_fact_embeddings_tenant_id ON fact_embeddings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_embeddings_model_id ON event_embeddings(model_id);
CREATE INDEX IF NOT EXISTS idx_fact_embeddings_model_id ON fact_embeddings(model_id);
CREATE INDEX IF NOT EXISTS idx_rule_registry_active ON rule_registry(rule_family, active);
CREATE INDEX IF NOT EXISTS idx_agent_permissions_lookup
ON agent_permissions(tenant_id, agent_id, domain, action, effect);
CREATE INDEX IF NOT EXISTS idx_delegation_grants_lookup
ON delegation_grants(tenant_id, grantee_agent_id, domain, action, expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_journal_idempotency
ON sync_journal(tenant_id, direction, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_sync_journal_applied_item
ON sync_journal(tenant_id, direction, status, json_extract(payload, '$.item_id'), id);
CREATE INDEX IF NOT EXISTS idx_consent_lookup
ON consent_records(tenant_id, subject_id, purpose, effective_at);
CREATE INDEX IF NOT EXISTS idx_subject_requests_lookup
ON subject_requests(tenant_id, subject_id, request_type, status);
CREATE INDEX IF NOT EXISTS idx_dr_snapshots_tenant
ON dr_snapshots(tenant_id, created_at);
