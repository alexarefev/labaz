CREATE FUNCTION public.dbdeletion_test_pass() RETURNS integer 
    LANGUAGE plpgsql
    AS $$
DECLARE
    database_name varchar;
    user_name varchar;
    host integer;
    backup boolean;
    db_type varchar;
    pass varchar;

    result varchar;
    result_chk integer;
    res integer;
BEGIN
    RAISE NOTICE 'Initialization';
    SELECT 'unit_test_db1', 'unit_test_user1', 'test_type1', 'true', 'qazwsx', 0 INTO database_name, user_name, db_type, backup, pass, res;
    TRUNCATE databases RESTART IDENTITY CASCADE;
    TRUNCATE hosts RESTART IDENTITY CASCADE;
    RAISE NOTICE 'INSERT INTO hosts: %, %', host, db_type;
    INSERT INTO hosts (host_name, host_type) VALUES ('unit_test_host', db_type);
    SELECT host_id INTO host FROM hosts WHERE host_name='unit_test_host';
    INSERT INTO databases(db_name, host_id, db_user, db_secret, db_state) VALUES (database_name, host, user_name, crypt(pass, gen_salt('md5')), 1);
    PERFORM * FROM pgq.create_queue(db_type);

    RAISE NOTICE 'TEST: wrong pass, with backup';
    SELECT '1234' INTO pass;
    RAISE NOTICE 'VALUES: %, %, %, %', database_name, backup, pass, db_type;
    SELECT * FROM dbdeletion(database_name, backup, pass, db_type) INTO result;
    RAISE NOTICE 'DBDELETION RESULT: %', result;
    SELECT regexp_replace(result, '(.),.+', '\1') INTO result_chk;
    IF result_chk <> '2' THEN
        RAISE NOTICE 'Wrong result, %', result_chk;
        res = 1;
    END IF;

    SELECT 'unit_test_db2', 'unit_test_user2', 'test_type1', 'false', 'qazwsx', 0 INTO database_name, user_name, db_type, backup, pass, res;
    INSERT INTO databases(db_name, host_id, db_user, db_secret, db_state) VALUES (database_name, host, user_name, crypt(pass, gen_salt('md5')), 1);
    RAISE NOTICE 'TEST: wrong pass, without backup';
    SELECT '1234' INTO pass;
    RAISE NOTICE 'VALUES: %, %, %, %', database_name, backup, pass, db_type;
    SELECT * FROM dbdeletion(database_name, backup, pass, db_type) INTO result;
    RAISE NOTICE 'DBDELETION RESULT: %', result;
    SELECT regexp_replace(result, '(.),.+', '\1') INTO result_chk;
    IF result_chk <> '2' THEN
        RAISE NOTICE 'Wrong result, %', result_chk;
        res = res + 1;
    END IF;

    TRUNCATE databases RESTART IDENTITY CASCADE;
    TRUNCATE hosts RESTART IDENTITY CASCADE;
    PERFORM * FROM pgq.drop_queue('test_type1', 'true');
    RETURN res;
END;
$$;
