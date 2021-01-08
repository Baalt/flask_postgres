DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
        CREATE TYPE user_status AS
        (
            username varchar,
            pswd varchar,
            referral_key varchar,
            parent_status smallint,
            inheritor_status smallint
        );
    END IF;
END$$;