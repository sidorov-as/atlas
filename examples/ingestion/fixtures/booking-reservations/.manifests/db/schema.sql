CREATE TABLE guests (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    full_name varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE hosts (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    full_name varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE listings (
    id uuid PRIMARY KEY,
    host_id uuid NOT NULL REFERENCES hosts(id),
    title varchar(255) NOT NULL,
    nightly_rate_cents integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reservations (
    id uuid PRIMARY KEY,
    guest_id uuid NOT NULL REFERENCES guests(id),
    listing_id uuid NOT NULL REFERENCES listings(id),
    status varchar(32) NOT NULL DEFAULT 'pending',
    check_in date NOT NULL,
    check_out date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reservation_events (
    id uuid PRIMARY KEY,
    reservation_id uuid NOT NULL REFERENCES reservations(id),
    event_type varchar(64) NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);
