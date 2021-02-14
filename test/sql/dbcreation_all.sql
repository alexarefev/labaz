CREATE FUNCTION public.dbcreation_test_correct() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    database_name varchar;
    user_name varchar;
    host varchar;
    db_type varchar;

    database_name_chk varchar;
    user_name_chk varchar;
    host_chk varchar;
    db_type_chk varchar;
    db_st_chk integer;
    res integer;
BEGIN
    RAISE NOTICE 'Initialization';
    SELECT 'unit_test_db', 'unit_test_user', 'unit_test_host', 'test_type1', 0 INTO database_name, user_name, host, db_type, res;
    TRUNCATE databases RESTART IDENTITY CASCADE;
    TRUNCATE hosts RESTART IDENTITY CASCADE;
    RAISE NOTICE 'INSERT INTO hosts: %, %', host, db_type;
    INSERT INTO hosts (host_name, host_type) VALUES (host, db_type);
    RAISE NOTICE 'INSERT INTO hosts: %, test_type2', host;
    INSERT INTO hosts (host_name, host_type) VALUES (host, 'test_type2');
    PERFORM * FROM pgq.create_queue(db_type);
    PERFORM * FROM pgq.create_queue('test_type2');

    RAISE NOTICE 'TEST: All parameters are correct';
    RAISE NOTICE 'VALUES: %, %, %, %', database_name, user_name, host, db_type;
    PERFORM * FROM dbcreation(database_name, user_name, host, db_type);
    SELECT t1.db_state INTO db_st_chk
           FROM databases t1, hosts t2 WHERE
           t1.host_id = t2.host_id AND t2.host_name = host AND
           t2.host_type = db_type AND t1.db_name = database_name;
    IF db_st_chk <> -1 THEN
        RAISE NOTICE 'Wrong state, %', db_st_chk;
        res = 'Wrong state, %', db_st_chk;
    END IF;
    TRUNCATE databases RESTART IDENTITY CASCADE;
    TRUNCATE hosts RESTART IDENTITY CASCADE;
    PERFORM * FROM pgq.drop_queue('test_type1', 'true');
    PERFORM * FROM pgq.drop_queue('test_type2', 'true');
    RETURN res;
END;
$$;

