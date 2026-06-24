CREATE SCHEMA IF NOT EXISTS nsi;


-- =====================================
-- Добавляем криптографические функции для генерации хешей
-- =====================================


CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =====================================
-- RAW LAYER
-- =====================================


CREATE TABLE IF NOT EXISTS nsi.raw_medical_organizations
(
    raw_hash_key varchar(64) primary key,
    org_id varchar not null,

    full_name text,
    short_name text,
    ogrn varchar,
    inn varchar,
    address text,
    ved_affiliation_id varchar,
    inclusion_date date,

    raw_payload jsonb,

    source_version varchar not null,

    loaded_at timestamptz default now()
);


-- =====================================
-- LOAD CONTROL
-- для восстановления после падения
-- =====================================


CREATE TABLE IF NOT EXISTS nsi.load_control
(
    load_id uuid primary key,
    source_version varchar not null,
    page_number integer not null,
    status varchar not null,
    started_at timestamptz default now(),
    finished_at timestamptz
);


-- =====================================
-- HUB
-- =====================================


CREATE TABLE IF NOT EXISTS nsi.hub_organization
(
    hub_org_hash_key varchar(64) primary key,
    org_id varchar unique not null,
    load_date timestamptz,
    record_source varchar
);


-- =====================================
-- SAT ATTRIBUTES
-- =====================================


CREATE TABLE IF NOT EXISTS nsi.sat_organization_attrs
(
    hub_org_hash_key varchar(64),
    hashdiff varchar(64),
    load_date timestamptz,
    full_name text,
    short_name text,
    ogrn varchar,
    inn varchar,
    address text,
    ved_affiliation_id varchar,
    inclusion_date date,
    record_source varchar,

    primary key
    (
        hub_org_hash_key,
        hashdiff
    )
);


-- =====================================
-- TRACKING SAT
-- =====================================


CREATE TABLE IF NOT EXISTS nsi.sat_organization_changes
(
    change_id serial primary key,
    hub_org_hash_key varchar(64),
    attribute_name varchar,
    attribute_value text,
    valid_from date,
    valid_to date,
    loaded_at timestamptz default now()
);


CREATE INDEX IF NOT EXISTS idx_tracking_current

ON nsi.sat_organization_changes
(
hub_org_hash_key,
attribute_name
)

WHERE valid_to IS NULL;
