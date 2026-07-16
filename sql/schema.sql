CREATE TABLE IF NOT EXISTS users (
    chat_id BIGINT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL,
    send_time VARCHAR(5) NOT NULL,
    status TEXT NOT NULL DEFAULT 'onboarding'
        CHECK (status IN ('onboarding', 'active', 'paused', 'stopped')),
    mode TEXT NOT NULL DEFAULT 'global',
    mode_position INTEGER NOT NULL DEFAULT 0,
    next_send_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    local_date DATE NOT NULL,
    reference_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('sending', 'sent')),
    sent_at TIMESTAMPTZ,
    UNIQUE(chat_id, local_date, kind)
);

CREATE TABLE IF NOT EXISTS favorites (
    chat_id BIGINT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
    reference_key TEXT NOT NULL,
    saved_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(chat_id, reference_key)
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_input_state (
    chat_id BIGINT PRIMARY KEY REFERENCES users(chat_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    origin TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_updates (
    update_id BIGINT PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_locks (
    name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS users_due_idx ON users(status, next_send_at);
