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


CREATE TYPE user_status AS (username varchar, pswd varchar, referral_key varchar, parent_status smallint, inheritor_status smallint);



CREATE FUNCTION chk_new_user_for_duplication_and_ip_attack_then_add(username varchar, 
																	pswd varchar, 
																	client_email varchar, 
																	reg_repair_key varchar, 
																	referral_key varchar, 
																	client_ip_address varchar) 
RETURNS varchar AS $$
DECLARE
	func_count smallint;
BEGIN
	DELETE FROM registration
	WHERE (date_trunc('second', now()) - created_at) > time '01:00:00' AND is_active = 0;

	SELECT COUNT(ip_address) INTO func_count 
	FROM registration
	WHERE ip_address = client_ip_address 
	AND (date_trunc('second', now()) - created_at) < time '00:02:00';
	
	IF func_count > 0 THEN RETURN 'ip_attack';
	END IF;

	SELECT COUNT(email) INTO func_count
	FROM registration 
	WHERE email = client_email;
	
	IF func_count = 0 THEN INSERT INTO registration (username, pswd, email, reg_repair_key, referral_key, ip_address)
						   VALUES (username, pswd, client_email, reg_repair_key, referral_key, client_ip_address);
						   RETURN 'registration';
						   
	ELSEIF func_count = 1 THEN SELECT COUNT(email) 
						   INTO func_count 
						   FROM registration 
						   WHERE email = client_email AND is_active = 1;
		
	END IF;
	
	IF func_count = 1 THEN 
		RETURN 'registered';
	
	ELSEIF func_count = 0 THEN SELECT COUNT(email) 
						   INTO func_count
						   FROM registration 
						   WHERE email = client_email AND is_active = 0;
	
	END IF;
	
	IF func_count = 1 THEN RETURN 'check email';
	
	ELSE
		RETURN 'unknown';
	END IF;
		
END;
$$ LANGUAGE plpgsql;



CREATE FUNCTION insert_into_referral_parent_inheritor_id(parent_referral_key varchar, client_email varchar) 
RETURNS void AS $$
DECLARE
	parent_id integer;
	inheritor_id integer;
BEGIN
	SELECT user_id
	INTO parent_id
	FROM registration
	WHERE referral_key = parent_referral_key;
	
	IF FOUND THEN SELECT user_id
				  INTO inheritor_id
				  FROM registration 
				  WHERE email = client_email;
				  
				  IF parent_id <> inheritor_id THEN INSERT INTO referral (fk_parent_id, fk_inheritor_id)
				  									VALUES (parent_id, inheritor_id);
				  END IF;
	END IF;	
END;
$$ LANGUAGE plpgsql;



CREATE FUNCTION chk_url_change_reg_status(url_reg_repair_key varchar, new_reg_repair_key varchar) 
RETURNS varchar AS $$
DECLARE
	inheritor_id smallint;
	chk_count smallint;
BEGIN
	SELECT user_id 
	INTO inheritor_id
	FROM registration 
	WHERE reg_repair_key = url_reg_repair_key AND is_active = 0;
	
	IF FOUND THEN UPDATE registration
				  SET is_active = 1, reg_repair_key = new_reg_repair_key
			      WHERE reg_repair_key = url_reg_repair_key;				   
				  
				  UPDATE referral
				  SET ref_active = 1
	 			  WHERE fk_inheritor_id = inheritor_id;
				  RETURN 'updated';
					   
	ELSE
		SELECT user_id 
		INTO chk_count
		FROM registration 
		WHERE reg_repair_key = url_reg_repair_key AND is_active = 1;
		
		IF FOUND THEN RETURN 'registered';
		END IF;	
		
		RETURN 'unknown';
	END IF;		
END;
$$ LANGUAGE plpgsql;


CREATE FUNCTION chk_email_return_username_pswd_referral_parent_inheritor(client_email varchar) RETURNS user_status AS $$
DECLARE
	result_record user_status;
BEGIN

	SELECT username, pswd, referral_key
	INTO result_record.username, result_record.pswd, result_record.referral_key
	FROM registration
	WHERE email = client_email AND is_active = 1;
			 
	IF FOUND THEN SELECT COUNT(fk_parent_id)
						 INTO result_record.parent_status
						 FROM referral
						 INNER JOIN registration ON registration.user_id = referral.fk_parent_id
						 WHERE registration.email = client_email AND ref_active = 1;

						 SELECT COUNT(fk_inheritor_id)
						 INTO result_record.inheritor_status
						 FROM referral
						 INNER JOIN registration ON registration.user_id = referral.fk_inheritor_id
						 WHERE registration.email = client_email AND ref_active = 1;
	END IF;	
	RETURN result_record;
END;
$$ LANGUAGE plpgsql;

