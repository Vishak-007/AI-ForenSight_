"""Create the UFDR forensic database schema."""

from .connection import get_connection


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cases (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_name TEXT NOT NULL,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    imei TEXT,
    extraction_date TIMESTAMPTZ,
    CONSTRAINT devices_case_device_id_key UNIQUE (case_id, device_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    contact_id TEXT NOT NULL,
    name TEXT,
    phone TEXT,
    CONSTRAINT contacts_case_contact_id_key UNIQUE (case_id, contact_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL,
    sender TEXT,
    receiver TEXT,
    timestamp TIMESTAMPTZ,
    text TEXT,
    CONSTRAINT messages_case_message_id_key UNIQUE (case_id, message_id)
);

CREATE TABLE IF NOT EXISTS calls (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    call_id TEXT NOT NULL,
    caller TEXT,
    callee TEXT,
    timestamp TIMESTAMPTZ,
    duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    type TEXT,
    CONSTRAINT calls_case_call_id_key UNIQUE (case_id, call_id)
);

CREATE TABLE IF NOT EXISTS media (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    media_id TEXT NOT NULL,
    type TEXT,
    timestamp TIMESTAMPTZ,
    filename TEXT,
    storage_path TEXT NOT NULL,
    sha256 CHAR(64),
    file_size_bytes BIGINT CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    associated_message_id TEXT,
    associated_call_id TEXT,
    status TEXT,
    CONSTRAINT media_case_media_id_key UNIQUE (case_id, media_id),
    CONSTRAINT media_message_reference_fk
        FOREIGN KEY (case_id, associated_message_id)
        REFERENCES messages(case_id, message_id),
    CONSTRAINT media_call_reference_fk
        FOREIGN KEY (case_id, associated_call_id)
        REFERENCES calls(case_id, call_id)
);

CREATE TABLE IF NOT EXISTS ocr_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    media_id BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    translated_text TEXT
);

-- Backfills the column on a database that already had ocr_results before
-- translate.py existed; a no-op on a fresh database (column is already
-- part of the CREATE TABLE above).
ALTER TABLE ocr_results ADD COLUMN IF NOT EXISTS translated_text TEXT;

CREATE TABLE IF NOT EXISTS transcriptions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    media_id BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    language TEXT
);

CREATE TABLE IF NOT EXISTS image_analysis (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    media_id BIGINT NOT NULL UNIQUE REFERENCES media(id) ON DELETE CASCADE,
    width INTEGER CHECK (width IS NULL OR width >= 0),
    height INTEGER CHECK (height IS NULL OR height >= 0),
    format TEXT,
    context TEXT,
    face_count INTEGER CHECK (face_count IS NULL OR face_count >= 0)
);

CREATE TABLE IF NOT EXISTS image_tags (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    media_id BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT image_tags_media_tag_key UNIQUE (media_id, tag)
);

CREATE INDEX IF NOT EXISTS devices_case_id_idx ON devices(case_id);
CREATE INDEX IF NOT EXISTS contacts_case_id_idx ON contacts(case_id);
CREATE INDEX IF NOT EXISTS messages_case_id_idx ON messages(case_id);
CREATE INDEX IF NOT EXISTS messages_timestamp_idx ON messages(timestamp);
CREATE INDEX IF NOT EXISTS calls_case_id_idx ON calls(case_id);
CREATE INDEX IF NOT EXISTS calls_timestamp_idx ON calls(timestamp);
CREATE INDEX IF NOT EXISTS media_case_id_idx ON media(case_id);
CREATE INDEX IF NOT EXISTS media_timestamp_idx ON media(timestamp);
CREATE INDEX IF NOT EXISTS media_message_reference_idx
    ON media(case_id, associated_message_id);
CREATE INDEX IF NOT EXISTS media_call_reference_idx
    ON media(case_id, associated_call_id);
CREATE INDEX IF NOT EXISTS ocr_results_media_id_idx ON ocr_results(media_id);
CREATE INDEX IF NOT EXISTS transcriptions_media_id_idx ON transcriptions(media_id);
CREATE INDEX IF NOT EXISTS image_tags_media_id_idx ON image_tags(media_id);
"""


def initialize_schema() -> None:
    """Create all UFDR tables and indexes when they are absent."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_SQL)


def main() -> None:
    try:
        initialize_schema()
    except RuntimeError as error:
        print(f"Database schema initialization failed: {error}")
        raise SystemExit(1) from error
    print("UFDR database schema initialized successfully.")


if __name__ == "__main__":
    main()