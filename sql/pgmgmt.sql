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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'standard public schema';

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


-----------------------------------------------------------
-- Add after this line
-----------------------------------------------------------


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
        UPDATE databases SET db_state='1' WHERE db_name=database_name AND host_id=host;
        RETURN '0, Database status has been updated';
    WHEN 'delete' THEN      
        DELETE FROM databases WHERE db_name=database_name AND host_id=host;
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
    SELECT count(t1.db_id) INTO db_chk FROM databases t1, hosts t2 WHERE t1.db_name=database_name AND t2.host_id=t1.host_id AND t2.host_type=db_type;
    IF db_chk = 0 THEN
        SELECT host_type INTO type_name FROM hosts WHERE host_name=host;
        IF type_name <> db_type THEN
            RETURN '2, Invalid type';
        END IF;
        IF host = '' THEN
            SELECT host_id, host_name INTO id, srv_name FROM hosts WHERE host_type=db_type AND host_id IN (SELECT host_id FROM hosts WHERE host_type=db_type ORDER BY RANDOM() LIMIT 1);
        ELSE
            SELECT host_id, host_name INTO id, srv_name FROM hosts WHERE host_name=host;
	    IF COALESCE(id,0) = 0 THEN
		RETURN '3, Invalid server';
	    END IF;
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
        UPDATE databases SET db_state='-1' WHERE db_name=database_name AND host_id=host;
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
        UPDATE databases SET db_state='-1' WHERE db_name=database_name and host_id=host;
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
-- Data for Name: databases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.databases (db_id, host_id, db_name, db_user, db_secret, db_state) FROM stdin;
\.


--
-- Data for Name: hosts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.hosts (host_id, host_name, host_type) FROM stdin;
\.


--
-- Name: databases_db_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.databases_db_id_seq', 1, false);


--
-- Name: hosts_host_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.hosts_host_id_seq', 1, false);


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
-- Name: databases databases_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.databases
    ADD CONSTRAINT databases_host_id_fkey FOREIGN KEY (host_id) REFERENCES public.hosts(host_id);


--
-- Name: FUNCTION dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dbcreation(database_name character varying, user_name character varying, host character varying, db_type character varying) TO pgmgmt;


--
-- Name: FUNCTION dbdeletion(database_name character varying, backup boolean, user_pass character varying, db_type character varying); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dbdeletion(database_name character varying, backup boolean, user_pass character varying, db_type character varying) TO pgmgmt;


--
-- Name: FUNCTION dblist(db_type character varying); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.dblist(db_type character varying) TO pgmgmt;


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
