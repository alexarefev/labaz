--
-- PostgreSQL database dump
--

-- Dumped from database version 11.10 (Debian 11.10-1.pgdg100+1)
-- Dumped by pg_dump version 11.10 (Debian 11.10-1.pgdg100+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: pgq; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS pgq WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION pgq; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgq IS 'Generic queue for PostgreSQL';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: dback(character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: pgmgmt
--

CREATE FUNCTION public.dback(database_name character varying, ack_type character varying, db_type character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    id integer;
    host integer;
    name varchar;
    user_name varchar;
    type_name varchar;
    pass_chk boolean;
BEGIN
    SELECT t1.db_id, t1.host_id, t1.db_user, t2.host_type INTO id, host, user_name, type_name FROM databases t1, hosts t2 WHERE t1.db_name=database_name and t2.host_id=t1.host_id and t2.host_type=db_type;
    IF COALESCE(id,0) = 0 THEN
        RETURN '1, Database does not exist';
    END IF;
    CASE ack_type
    WHEN 'create' THEN
        UPDATE databases SET db_state='1' WHERE db_name=database_name AND db_host=host;
        RETURN '0, Database status has been updated';
    WHEN 'delete' THEN      
 DELETE FROM databases WHERE db_name='%s' AND db_host=host;
        RETURN '0, Database status has been deleted from list';
    ELSE 
        RETURN '2, Unknown operation';
    END CASE;
END;
$$;


ALTER FUNCTION public.dback(database_name character varying, ack_type character varying, db_type character varying) OWNER TO pgmgmt;

--
-- Name: dbcreation(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    pass varchar;
    pass_hash varchar;
    db varchar;
    usr varchar;
    id integer;
    db_chk integer;
    type_name varchar;
    srv_name varchar;
BEGIN
    SELECT count(t1.db_id) INTO db_chk FROM databases t1, hosts t2 WHERE t1.db_name=db AND t2.host_id=t1.host_id AND t2.host_type=db_type;
    IF db_chk = 0 THEN
        SELECT host_type INTO type_name FROM hosts WHERE host_name=host;
        IF type_name <> db_type THEN
            RETURN '2, Invalid type';
        END IF;
        IF host = '' THEN
            SELECT host_id, host_name INTO id, srv_name FROM hosts WHERE host_type=db_type AND host_id IN (SELECT host_id FROM hosts WHERE host_type=db_type ORDER BY RANDOM() LIMIT 1);
        ELSE
            SELECT host_id, host_name INTO id, srv_name FROM hosts WHERE host_name=host;
        END IF;
        IF database_name = '' THEN
            SELECT gen_random_uuid() INTO db;
        ELSE
            SELECT database_name INTO db;
        END IF;
        IF user_name = '' THEN
            SELECT 'user_' || gen_random_uuid() INTO usr;
        ELSE
            SELECT user_name INTO usr;
        END IF;
        SELECT md5(random()::text) INTO pass;
	SELECT crypt(pass, gen_salt('md5')) INTO pass_hash;
        RAISE NOTICE 'The database catalog updating';
        INSERT INTO databases (host_id, db_name, db_user, db_secret, db_state) VALUES (id, db, usr, pass_hash, -1);
        RAISE NOTICE 'The database creation %', database_name;
        PERFORM * FROM pgq.insert_event(db_type, 'create', db, usr, pass, host, '');
        RETURN '0,' || srv_name || ',' || db || ',' || usr || ',' || pass;
    ELSE
        RETURN '1, Database exists';
    END IF;

END;
$$;


ALTER FUNCTION public.dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying) OWNER TO postgres;

--
-- Name: dbdeletion(character varying, boolean, character varying, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.dbdeletion(database_name character varying, backup boolean, user_pass character varying, db_type character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    id integer;
    host integer;
    name varchar;
    user_name varchar;
    type_name varchar;
    pass_chk boolean;
BEGIN
    SELECT t1.db_id, t1.host_id, t1.db_user, t2.host_type INTO id, host, user_name, type_name FROM databases t1, hosts t2 WHERE t1.db_name=database_name and t2.host_id=t1.host_id and t2.host_type=db_type;
    IF COALESCE(id,0) = 0 THEN
        RETURN '1, Database does not exist';
    END IF;
    SELECT (db_secret = crypt(user_pass, db_secret)) INTO pass_chk FROM databases WHERE db_id = id;
    IF pass_chk = 't' THEN
        RAISE NOTICE 'Updating database status';
        UPDATE databases SET db_state='-1' WHERE db_name=database_name;
        SELECT host_name INTO name FROM hosts WHERE host_id=host;
        IF backup = true THEN
            RAISE NOTICE 'The database backup and deletion %', database_name;
            PERFORM * FROM pgq.insert_event(type_name, 'delete', database_name, user_name, name, 'backup', '');
        ELSE
            RAISE NOTICE 'The database deletion %', database_name;
            PERFORM * FROM pgq.insert_event(type_name, 'delete', database_name, user_name, name, '', '');
        END IF;
        RETURN '0, Database has been added to deletion queue';
    ELSE
        RETURN '2, Permissions error';
    END IF;
END;
$$;


ALTER FUNCTION public.dbdeletion(database_name character varying, backup boolean, user_pass character varying, db_type character varying) OWNER TO postgres;

--
-- Name: dblist(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.dblist(db_type character varying) RETURNS TABLE(name character varying, user_name character varying, host character varying)
    LANGUAGE sql
    AS $$
    SELECT t1.db_name, t1.db_user, t2.host_name FROM databases t1, hosts t2 WHERE t2.host_type=db_type and t1.host_id=t2.host_id;
$$;


ALTER FUNCTION public.dblist(db_type character varying) OWNER TO postgres;

--
-- Name: dbrecover(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: pgmgmt
--

CREATE FUNCTION public.dbrecover(database_name character varying, backup_file character varying, user_pass character varying, db_type character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    id integer;
    host integer;
    name varchar;
    user_name varchar;
    type_name varchar;
    pass_chk boolean;
BEGIN
    SELECT t1.db_id, t1.host_id, t1.db_user, t2.host_type INTO id, host, user_name, type_name FROM databases t1, hosts t2 WHERE t1.db_name=database_name and t2.host_id=t1.host_id and t2.host_type=db_type;
    IF COALESCE(id,0) = 0 THEN
        RETURN '1, Database does not exist';
    END IF;
    SELECT (db_secret = crypt(user_pass, db_secret)) INTO pass_chk FROM databases WHERE db_id = id;
    IF pass_chk = 't' THEN
        RAISE NOTICE 'Updating database status';
        UPDATE databases SET db_state='-1' WHERE db_name=database_name;
        SELECT host_name INTO name FROM hosts WHERE host_id=host;
        RAISE NOTICE 'The database recovery %', database_name;
        PERFORM * FROM pgq.insert_event(type_name, 'recover', database_name, user_name, name, backup_file, '');
        RETURN '0, Database has been added to recovery queue';
    ELSE
        RETURN '2, Permissions error';
    END IF;
END;
$$;


ALTER FUNCTION public.dbrecover(database_name character varying, backup_file character varying, user_pass character varying, db_type character varying) OWNER TO pgmgmt;

--
-- Name: hostlist(character varying); Type: FUNCTION; Schema: public; Owner: pgmgmt
--

CREATE FUNCTION public.hostlist(db_type character varying) RETURNS TABLE(host_name character varying, active integer)
    LANGUAGE sql
    AS $$
    SELECT t1.host_name, CASE WHEN t2.co_id IS NOT NULL THEN 1 ELSE 0 END AS active FROM hosts t1 LEFT JOIN pgq.consumer t2 ON 'worker_'||t1.host_name=t2.co_name WHERE t1.host_type=db_type;
$$;


ALTER FUNCTION public.hostlist(db_type character varying) OWNER TO pgmgmt;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: event_1; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_1 (
)
INHERITS (pgq.event_template);


ALTER TABLE pgq.event_1 OWNER TO postgres;

--
-- Name: event_1_0; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_1_0 (
)
INHERITS (pgq.event_1)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_1_0 OWNER TO postgres;

--
-- Name: event_1_1; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_1_1 (
)
INHERITS (pgq.event_1)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_1_1 OWNER TO postgres;

--
-- Name: event_1_2; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_1_2 (
)
INHERITS (pgq.event_1)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_1_2 OWNER TO postgres;

--
-- Name: event_1_id_seq; Type: SEQUENCE; Schema: pgq; Owner: postgres
--

CREATE SEQUENCE pgq.event_1_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE pgq.event_1_id_seq OWNER TO postgres;

--
-- Name: event_1_tick_seq; Type: SEQUENCE; Schema: pgq; Owner: postgres
--

CREATE SEQUENCE pgq.event_1_tick_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE pgq.event_1_tick_seq OWNER TO postgres;

--
-- Name: event_2; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_2 (
)
INHERITS (pgq.event_template);


ALTER TABLE pgq.event_2 OWNER TO postgres;

--
-- Name: event_2_0; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_2_0 (
)
INHERITS (pgq.event_2)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_2_0 OWNER TO postgres;

--
-- Name: event_2_1; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_2_1 (
)
INHERITS (pgq.event_2)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_2_1 OWNER TO postgres;

--
-- Name: event_2_2; Type: TABLE; Schema: pgq; Owner: postgres
--

CREATE TABLE pgq.event_2_2 (
)
INHERITS (pgq.event_2)
WITH (fillfactor='100', autovacuum_enabled=off, toast.autovacuum_enabled=off);


ALTER TABLE pgq.event_2_2 OWNER TO postgres;

--
-- Name: event_2_id_seq; Type: SEQUENCE; Schema: pgq; Owner: postgres
--

CREATE SEQUENCE pgq.event_2_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE pgq.event_2_id_seq OWNER TO postgres;

--
-- Name: event_2_tick_seq; Type: SEQUENCE; Schema: pgq; Owner: postgres
--

CREATE SEQUENCE pgq.event_2_tick_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE pgq.event_2_tick_seq OWNER TO postgres;

--
-- Name: databases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.databases (
    db_id integer NOT NULL,
    host_id integer,
    db_name character varying(50) NOT NULL,
    db_user character varying(50) NOT NULL,
    db_secret character varying(50) NOT NULL,
    db_state integer NOT NULL
);


ALTER TABLE public.databases OWNER TO postgres;

--
-- Name: databases_db_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.databases ALTER COLUMN db_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.databases_db_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: hosts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hosts (
    host_id integer NOT NULL,
    host_name character varying(250) NOT NULL,
    host_type character varying(12) NOT NULL
);


ALTER TABLE public.hosts OWNER TO postgres;

--
-- Name: hosts_host_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.hosts ALTER COLUMN host_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.hosts_host_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: event_1 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_1_0 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_0 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_1_id_seq'::regclass);


--
-- Name: event_1_0 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_0 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_1_1 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_1 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_1_id_seq'::regclass);


--
-- Name: event_1_1 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_1 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_1_2 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_2 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_1_id_seq'::regclass);


--
-- Name: event_1_2 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_1_2 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_2 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_2_0 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_0 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_2_id_seq'::regclass);


--
-- Name: event_2_0 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_0 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_2_1 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_1 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_2_id_seq'::regclass);


--
-- Name: event_2_1 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_1 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: event_2_2 ev_id; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_2 ALTER COLUMN ev_id SET DEFAULT nextval('pgq.event_2_id_seq'::regclass);


--
-- Name: event_2_2 ev_txid; Type: DEFAULT; Schema: pgq; Owner: postgres
--

ALTER TABLE ONLY pgq.event_2_2 ALTER COLUMN ev_txid SET DEFAULT txid_current();


--
-- Name: databases databases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.databases
    ADD CONSTRAINT databases_pkey PRIMARY KEY (db_id);


--
-- Name: databases host_id_db_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.databases
    ADD CONSTRAINT host_id_db_name UNIQUE (host_id, db_name);


--
-- Name: hosts hosts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hosts
    ADD CONSTRAINT hosts_pkey PRIMARY KEY (host_id);


--
-- Name: hosts name_type_uni; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hosts
    ADD CONSTRAINT name_type_uni UNIQUE (host_name, host_type);


--
-- Name: event_1_0_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_1_0_txid_idx ON pgq.event_1_0 USING btree (ev_txid);


--
-- Name: event_1_1_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_1_1_txid_idx ON pgq.event_1_1 USING btree (ev_txid);


--
-- Name: event_1_2_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_1_2_txid_idx ON pgq.event_1_2 USING btree (ev_txid);


--
-- Name: event_2_0_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_2_0_txid_idx ON pgq.event_2_0 USING btree (ev_txid);


--
-- Name: event_2_1_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_2_1_txid_idx ON pgq.event_2_1 USING btree (ev_txid);


--
-- Name: event_2_2_txid_idx; Type: INDEX; Schema: pgq; Owner: postgres
--

CREATE INDEX event_2_2_txid_idx ON pgq.event_2_2 USING btree (ev_txid);


--
-- Name: databases databases_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.databases
    ADD CONSTRAINT databases_host_id_fkey FOREIGN KEY (host_id) REFERENCES public.hosts(host_id);


--
-- Name: FUNCTION _grant_perms_from(src_schema text, src_table text, dst_schema text, dst_table text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq._grant_perms_from(src_schema text, src_table text, dst_schema text, dst_table text) TO pgmgmt;


--
-- Name: FUNCTION batch_event_sql(x_batch_id bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.batch_event_sql(x_batch_id bigint) TO pgmgmt;


--
-- Name: FUNCTION batch_event_tables(x_batch_id bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.batch_event_tables(x_batch_id bigint) TO pgmgmt;


--
-- Name: FUNCTION batch_retry(i_batch_id bigint, i_retry_seconds integer); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.batch_retry(i_batch_id bigint, i_retry_seconds integer) TO pgmgmt;


--
-- Name: FUNCTION create_queue(i_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.create_queue(i_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION current_event_table(x_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.current_event_table(x_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION drop_queue(x_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.drop_queue(x_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION drop_queue(x_queue_name text, x_force boolean); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.drop_queue(x_queue_name text, x_force boolean) TO pgmgmt;


--
-- Name: FUNCTION event_retry(x_batch_id bigint, x_event_id bigint, x_retry_seconds integer); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.event_retry(x_batch_id bigint, x_event_id bigint, x_retry_seconds integer) TO pgmgmt;


--
-- Name: FUNCTION event_retry(x_batch_id bigint, x_event_id bigint, x_retry_time timestamp with time zone); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.event_retry(x_batch_id bigint, x_event_id bigint, x_retry_time timestamp with time zone) TO pgmgmt;


--
-- Name: FUNCTION event_retry_raw(x_queue text, x_consumer text, x_retry_after timestamp with time zone, x_ev_id bigint, x_ev_time timestamp with time zone, x_ev_retry integer, x_ev_type text, x_ev_data text, x_ev_extra1 text, x_ev_extra2 text, x_ev_extra3 text, x_ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.event_retry_raw(x_queue text, x_consumer text, x_retry_after timestamp with time zone, x_ev_id bigint, x_ev_time timestamp with time zone, x_ev_retry integer, x_ev_type text, x_ev_data text, x_ev_extra1 text, x_ev_extra2 text, x_ev_extra3 text, x_ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION find_tick_helper(i_queue_id integer, i_prev_tick_id bigint, i_prev_tick_time timestamp with time zone, i_prev_tick_seq bigint, i_min_count bigint, i_min_interval interval, OUT next_tick_id bigint, OUT next_tick_time timestamp with time zone, OUT next_tick_seq bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.find_tick_helper(i_queue_id integer, i_prev_tick_id bigint, i_prev_tick_time timestamp with time zone, i_prev_tick_seq bigint, i_min_count bigint, i_min_interval interval, OUT next_tick_id bigint, OUT next_tick_time timestamp with time zone, OUT next_tick_seq bigint) TO pgmgmt;


--
-- Name: FUNCTION finish_batch(x_batch_id bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.finish_batch(x_batch_id bigint) TO pgmgmt;


--
-- Name: FUNCTION force_tick(i_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.force_tick(i_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION get_batch_cursor(i_batch_id bigint, i_cursor_name text, i_quick_limit integer, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_batch_cursor(i_batch_id bigint, i_cursor_name text, i_quick_limit integer, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION get_batch_cursor(i_batch_id bigint, i_cursor_name text, i_quick_limit integer, i_extra_where text, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_batch_cursor(i_batch_id bigint, i_cursor_name text, i_quick_limit integer, i_extra_where text, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION get_batch_events(x_batch_id bigint, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_batch_events(x_batch_id bigint, OUT ev_id bigint, OUT ev_time timestamp with time zone, OUT ev_txid bigint, OUT ev_retry integer, OUT ev_type text, OUT ev_data text, OUT ev_extra1 text, OUT ev_extra2 text, OUT ev_extra3 text, OUT ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION get_batch_info(x_batch_id bigint, OUT queue_name text, OUT consumer_name text, OUT batch_start timestamp with time zone, OUT batch_end timestamp with time zone, OUT prev_tick_id bigint, OUT tick_id bigint, OUT lag interval, OUT seq_start bigint, OUT seq_end bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_batch_info(x_batch_id bigint, OUT queue_name text, OUT consumer_name text, OUT batch_start timestamp with time zone, OUT batch_end timestamp with time zone, OUT prev_tick_id bigint, OUT tick_id bigint, OUT lag interval, OUT seq_start bigint, OUT seq_end bigint) TO pgmgmt;


--
-- Name: FUNCTION get_consumer_info(OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_consumer_info(OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint) TO pgmgmt;


--
-- Name: FUNCTION get_consumer_info(i_queue_name text, OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_consumer_info(i_queue_name text, OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint) TO pgmgmt;


--
-- Name: FUNCTION get_consumer_info(i_queue_name text, i_consumer_name text, OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_consumer_info(i_queue_name text, i_consumer_name text, OUT queue_name text, OUT consumer_name text, OUT lag interval, OUT last_seen interval, OUT last_tick bigint, OUT current_batch bigint, OUT next_tick bigint, OUT pending_events bigint) TO pgmgmt;


--
-- Name: FUNCTION get_queue_info(OUT queue_name text, OUT queue_ntables integer, OUT queue_cur_table integer, OUT queue_rotation_period interval, OUT queue_switch_time timestamp with time zone, OUT queue_external_ticker boolean, OUT queue_ticker_paused boolean, OUT queue_ticker_max_count integer, OUT queue_ticker_max_lag interval, OUT queue_ticker_idle_period interval, OUT ticker_lag interval, OUT ev_per_sec double precision, OUT ev_new bigint, OUT last_tick_id bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_queue_info(OUT queue_name text, OUT queue_ntables integer, OUT queue_cur_table integer, OUT queue_rotation_period interval, OUT queue_switch_time timestamp with time zone, OUT queue_external_ticker boolean, OUT queue_ticker_paused boolean, OUT queue_ticker_max_count integer, OUT queue_ticker_max_lag interval, OUT queue_ticker_idle_period interval, OUT ticker_lag interval, OUT ev_per_sec double precision, OUT ev_new bigint, OUT last_tick_id bigint) TO pgmgmt;


--
-- Name: FUNCTION get_queue_info(i_queue_name text, OUT queue_name text, OUT queue_ntables integer, OUT queue_cur_table integer, OUT queue_rotation_period interval, OUT queue_switch_time timestamp with time zone, OUT queue_external_ticker boolean, OUT queue_ticker_paused boolean, OUT queue_ticker_max_count integer, OUT queue_ticker_max_lag interval, OUT queue_ticker_idle_period interval, OUT ticker_lag interval, OUT ev_per_sec double precision, OUT ev_new bigint, OUT last_tick_id bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.get_queue_info(i_queue_name text, OUT queue_name text, OUT queue_ntables integer, OUT queue_cur_table integer, OUT queue_rotation_period interval, OUT queue_switch_time timestamp with time zone, OUT queue_external_ticker boolean, OUT queue_ticker_paused boolean, OUT queue_ticker_max_count integer, OUT queue_ticker_max_lag interval, OUT queue_ticker_idle_period interval, OUT ticker_lag interval, OUT ev_per_sec double precision, OUT ev_new bigint, OUT last_tick_id bigint) TO pgmgmt;


--
-- Name: FUNCTION grant_perms(x_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.grant_perms(x_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION insert_event(queue_name text, ev_type text, ev_data text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.insert_event(queue_name text, ev_type text, ev_data text) TO pgmgmt;


--
-- Name: FUNCTION insert_event(queue_name text, ev_type text, ev_data text, ev_extra1 text, ev_extra2 text, ev_extra3 text, ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.insert_event(queue_name text, ev_type text, ev_data text, ev_extra1 text, ev_extra2 text, ev_extra3 text, ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION insert_event_raw(queue_name text, ev_id bigint, ev_time timestamp with time zone, ev_owner integer, ev_retry integer, ev_type text, ev_data text, ev_extra1 text, ev_extra2 text, ev_extra3 text, ev_extra4 text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.insert_event_raw(queue_name text, ev_id bigint, ev_time timestamp with time zone, ev_owner integer, ev_retry integer, ev_type text, ev_data text, ev_extra1 text, ev_extra2 text, ev_extra3 text, ev_extra4 text) TO pgmgmt;


--
-- Name: FUNCTION jsontriga(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.jsontriga() TO pgmgmt;


--
-- Name: FUNCTION logutriga(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.logutriga() TO pgmgmt;


--
-- Name: FUNCTION maint_operations(OUT func_name text, OUT func_arg text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.maint_operations(OUT func_name text, OUT func_arg text) TO pgmgmt;


--
-- Name: FUNCTION maint_retry_events(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.maint_retry_events() TO pgmgmt;


--
-- Name: FUNCTION maint_rotate_tables_step1(i_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.maint_rotate_tables_step1(i_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION maint_rotate_tables_step2(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.maint_rotate_tables_step2() TO pgmgmt;


--
-- Name: FUNCTION maint_tables_to_vacuum(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.maint_tables_to_vacuum() TO pgmgmt;


--
-- Name: FUNCTION next_batch(i_queue_name text, i_consumer_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.next_batch(i_queue_name text, i_consumer_name text) TO pgmgmt;


--
-- Name: FUNCTION next_batch_custom(i_queue_name text, i_consumer_name text, i_min_lag interval, i_min_count integer, i_min_interval interval, OUT batch_id bigint, OUT cur_tick_id bigint, OUT prev_tick_id bigint, OUT cur_tick_time timestamp with time zone, OUT prev_tick_time timestamp with time zone, OUT cur_tick_event_seq bigint, OUT prev_tick_event_seq bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.next_batch_custom(i_queue_name text, i_consumer_name text, i_min_lag interval, i_min_count integer, i_min_interval interval, OUT batch_id bigint, OUT cur_tick_id bigint, OUT prev_tick_id bigint, OUT cur_tick_time timestamp with time zone, OUT prev_tick_time timestamp with time zone, OUT cur_tick_event_seq bigint, OUT prev_tick_event_seq bigint) TO pgmgmt;


--
-- Name: FUNCTION next_batch_info(i_queue_name text, i_consumer_name text, OUT batch_id bigint, OUT cur_tick_id bigint, OUT prev_tick_id bigint, OUT cur_tick_time timestamp with time zone, OUT prev_tick_time timestamp with time zone, OUT cur_tick_event_seq bigint, OUT prev_tick_event_seq bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.next_batch_info(i_queue_name text, i_consumer_name text, OUT batch_id bigint, OUT cur_tick_id bigint, OUT prev_tick_id bigint, OUT cur_tick_time timestamp with time zone, OUT prev_tick_time timestamp with time zone, OUT cur_tick_event_seq bigint, OUT prev_tick_event_seq bigint) TO pgmgmt;


--
-- Name: FUNCTION quote_fqname(i_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.quote_fqname(i_name text) TO pgmgmt;


--
-- Name: FUNCTION register_consumer(x_queue_name text, x_consumer_id text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.register_consumer(x_queue_name text, x_consumer_id text) TO pgmgmt;


--
-- Name: FUNCTION register_consumer_at(x_queue_name text, x_consumer_name text, x_tick_pos bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.register_consumer_at(x_queue_name text, x_consumer_name text, x_tick_pos bigint) TO pgmgmt;


--
-- Name: FUNCTION seq_getval(i_seq_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.seq_getval(i_seq_name text) TO pgmgmt;


--
-- Name: FUNCTION seq_setval(i_seq_name text, i_new_value bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.seq_setval(i_seq_name text, i_new_value bigint) TO pgmgmt;


--
-- Name: FUNCTION set_queue_config(x_queue_name text, x_param_name text, x_param_value text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.set_queue_config(x_queue_name text, x_param_name text, x_param_value text) TO pgmgmt;


--
-- Name: FUNCTION sqltriga(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.sqltriga() TO pgmgmt;


--
-- Name: FUNCTION ticker(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.ticker() TO pgmgmt;


--
-- Name: FUNCTION ticker(i_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.ticker(i_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION ticker(i_queue_name text, i_tick_id bigint, i_orig_timestamp timestamp with time zone, i_event_seq bigint); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.ticker(i_queue_name text, i_tick_id bigint, i_orig_timestamp timestamp with time zone, i_event_seq bigint) TO pgmgmt;


--
-- Name: FUNCTION tune_storage(i_queue_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.tune_storage(i_queue_name text) TO pgmgmt;


--
-- Name: FUNCTION unregister_consumer(x_queue_name text, x_consumer_name text); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.unregister_consumer(x_queue_name text, x_consumer_name text) TO pgmgmt;


--
-- Name: FUNCTION upgrade_schema(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.upgrade_schema() TO pgmgmt;


--
-- Name: FUNCTION version(); Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON FUNCTION pgq.version() TO pgmgmt;


--
-- Name: FUNCTION armor(bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.armor(bytea) TO pgmgmt;


--
-- Name: FUNCTION armor(bytea, text[], text[]); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.armor(bytea, text[], text[]) TO pgmgmt;


--
-- Name: FUNCTION crypt(text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.crypt(text, text) TO pgmgmt;


--
-- Name: FUNCTION dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying) TO pgmgmt;


--
-- Name: FUNCTION dblist(db_type character varying); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dblist(db_type character varying) TO pgmgmt;


--
-- Name: FUNCTION dearmor(text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dearmor(text) TO pgmgmt;


--
-- Name: FUNCTION decrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.decrypt(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION decrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.decrypt_iv(bytea, bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION digest(bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.digest(bytea, text) TO pgmgmt;


--
-- Name: FUNCTION digest(text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.digest(text, text) TO pgmgmt;


--
-- Name: FUNCTION encrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.encrypt(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION encrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.encrypt_iv(bytea, bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION gen_random_bytes(integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.gen_random_bytes(integer) TO pgmgmt;


--
-- Name: FUNCTION gen_random_uuid(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.gen_random_uuid() TO pgmgmt;


--
-- Name: FUNCTION gen_salt(text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.gen_salt(text) TO pgmgmt;


--
-- Name: FUNCTION gen_salt(text, integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.gen_salt(text, integer) TO pgmgmt;


--
-- Name: FUNCTION hmac(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.hmac(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION hmac(text, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.hmac(text, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_armor_headers(text, OUT key text, OUT value text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_armor_headers(text, OUT key text, OUT value text) TO pgmgmt;


--
-- Name: FUNCTION pgp_key_id(bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_key_id(bytea) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt(text, bytea) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt(text, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea) TO pgmgmt;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt(bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt(bytea, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt_bytea(bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt_bytea(bytea, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt(text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt(text, text, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt_bytea(bytea, text) TO pgmgmt;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text, text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt_bytea(bytea, text, text) TO pgmgmt;


--
-- Name: SEQUENCE batch_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON SEQUENCE pgq.batch_id_seq TO pgmgmt;


--
-- Name: TABLE consumer; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.consumer TO pgmgmt;


--
-- Name: SEQUENCE consumer_co_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON SEQUENCE pgq.consumer_co_id_seq TO pgmgmt;


--
-- Name: TABLE event_template; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.event_template TO pgmgmt;


--
-- Name: TABLE event_1; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_1 FROM postgres;
GRANT ALL ON TABLE pgq.event_1 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_1 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_1 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_1 TO pgmgmt;


--
-- Name: TABLE event_1_0; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_1_0 FROM postgres;
GRANT ALL ON TABLE pgq.event_1_0 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_1_0 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_1_0 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_1_0 TO pgmgmt;


--
-- Name: TABLE event_1_1; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_1_1 FROM postgres;
GRANT ALL ON TABLE pgq.event_1_1 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_1_1 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_1_1 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_1_1 TO pgmgmt;


--
-- Name: TABLE event_1_2; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_1_2 FROM postgres;
GRANT ALL ON TABLE pgq.event_1_2 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_1_2 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_1_2 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_1_2 TO pgmgmt;


--
-- Name: SEQUENCE event_1_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT SELECT ON SEQUENCE pgq.event_1_id_seq TO PUBLIC;
GRANT USAGE ON SEQUENCE pgq.event_1_id_seq TO pgq_admin;
GRANT ALL ON SEQUENCE pgq.event_1_id_seq TO pgmgmt;


--
-- Name: SEQUENCE event_1_tick_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT SELECT ON SEQUENCE pgq.event_1_tick_seq TO PUBLIC;
GRANT ALL ON SEQUENCE pgq.event_1_tick_seq TO pgmgmt;


--
-- Name: TABLE event_2; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_2 FROM postgres;
GRANT ALL ON TABLE pgq.event_2 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_2 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_2 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_2 TO pgmgmt;


--
-- Name: TABLE event_2_0; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_2_0 FROM postgres;
GRANT ALL ON TABLE pgq.event_2_0 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_2_0 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_2_0 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_2_0 TO pgmgmt;


--
-- Name: TABLE event_2_1; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_2_1 FROM postgres;
GRANT ALL ON TABLE pgq.event_2_1 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_2_1 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_2_1 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_2_1 TO pgmgmt;


--
-- Name: TABLE event_2_2; Type: ACL; Schema: pgq; Owner: postgres
--

REVOKE ALL ON TABLE pgq.event_2_2 FROM postgres;
GRANT ALL ON TABLE pgq.event_2_2 TO postgres WITH GRANT OPTION;
GRANT SELECT ON TABLE pgq.event_2_2 TO pgq_reader;
GRANT SELECT,INSERT,TRUNCATE ON TABLE pgq.event_2_2 TO pgq_admin;
GRANT ALL ON TABLE pgq.event_2_2 TO pgmgmt;


--
-- Name: SEQUENCE event_2_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT SELECT ON SEQUENCE pgq.event_2_id_seq TO PUBLIC;
GRANT USAGE ON SEQUENCE pgq.event_2_id_seq TO pgq_admin;
GRANT ALL ON SEQUENCE pgq.event_2_id_seq TO pgmgmt;


--
-- Name: SEQUENCE event_2_tick_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT SELECT ON SEQUENCE pgq.event_2_tick_seq TO PUBLIC;
GRANT ALL ON SEQUENCE pgq.event_2_tick_seq TO pgmgmt;


--
-- Name: TABLE queue; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.queue TO pgmgmt;


--
-- Name: SEQUENCE queue_queue_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON SEQUENCE pgq.queue_queue_id_seq TO pgmgmt;


--
-- Name: TABLE retry_queue; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.retry_queue TO pgmgmt;


--
-- Name: TABLE subscription; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.subscription TO pgmgmt;


--
-- Name: SEQUENCE subscription_sub_id_seq; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON SEQUENCE pgq.subscription_sub_id_seq TO pgmgmt;


--
-- Name: TABLE tick; Type: ACL; Schema: pgq; Owner: postgres
--

GRANT ALL ON TABLE pgq.tick TO pgmgmt;


--
-- Name: TABLE databases; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.databases TO pgmgmt;


--
-- Name: SEQUENCE databases_db_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.databases_db_id_seq TO pgmgmt;


--
-- Name: TABLE hosts; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.hosts TO pgmgmt;


--
-- Name: SEQUENCE hosts_host_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.hosts_host_id_seq TO pgmgmt;


--
-- PostgreSQL database dump complete
--

