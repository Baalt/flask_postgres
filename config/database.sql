CREATE TABLE IF NOT EXISTS registration
(
  	user_id integer GENERATED ALWAYS AS IDENTITY NOT NULL PRIMARY KEY,  
  	username varchar(255) NOT NULL,
	pswd varchar(255) NOT NULL,
	email varchar(255) UNIQUE NOT NULL,
 	reg_repair_key varchar(255) NOT NULL,
	referral_key varchar(255) NOT NULL,
  	ip_address varchar(64),
  	is_active smallint DEFAULT 0,
	created_at timestamp DEFAULT date_trunc('second', now()),  
  
  	CONSTRAINT chk_is_active CHECK (is_active = 0 OR is_active = 1)
);


CREATE TABLE IF NOT EXISTS referral
(
	referral_id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
	fk_parent_id integer NOT NULL,
	fk_inheritor_id integer UNIQUE NOT NULL,
	ref_active integer DEFAULT 0,
	
	CONSTRAINT fk_parent_registration FOREIGN KEY (fk_parent_id) REFERENCES registration (user_id),
	CONSTRAINT fk_inheritor_registration FOREIGN KEY (fk_inheritor_id ) REFERENCES registration (user_id),
	CONSTRAINT chk_ref_active CHECK (ref_active = 0 OR ref_active = 1)
);

