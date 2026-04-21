--
-- PostgreSQL database dump
--

\restrict z2FBfvhg9ANB2WSoZwyz4IkXY5FRiRj5aSuKuy8DYb79TANDOvqCDwJsHKlwIS2

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

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

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: cliente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cliente (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    nombre character varying NOT NULL,
    rfc character varying(13),
    razon_social character varying,
    contacto character varying,
    email character varying,
    telefono character varying,
    direccion character varying,
    ciudad character varying,
    cp character varying(5),
    activo boolean NOT NULL,
    notas character varying
);


ALTER TABLE public.cliente OWNER TO postgres;

--
-- Name: cliente_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cliente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cliente_id_seq OWNER TO postgres;

--
-- Name: cliente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cliente_id_seq OWNED BY public.cliente.id;


--
-- Name: concepto_orden_trabajo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.concepto_orden_trabajo (
    id integer NOT NULL,
    orden_id integer NOT NULL,
    concepto_cotizacion_id integer NOT NULL,
    descripcion character varying NOT NULL,
    cantidad numeric(10,2) NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    importe numeric(10,2) NOT NULL,
    unidad character varying NOT NULL,
    estado character varying DEFAULT 'pendiente'::character varying NOT NULL,
    fecha_completado timestamp without time zone,
    completado_por character varying,
    creado_por character varying DEFAULT ''::character varying NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT now() NOT NULL,
    descuento_porcentaje numeric DEFAULT '0'::numeric NOT NULL
);


ALTER TABLE public.concepto_orden_trabajo OWNER TO postgres;

--
-- Name: concepto_orden_trabajo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.concepto_orden_trabajo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.concepto_orden_trabajo_id_seq OWNER TO postgres;

--
-- Name: concepto_orden_trabajo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.concepto_orden_trabajo_id_seq OWNED BY public.concepto_orden_trabajo.id;


--
-- Name: conceptocotizacion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conceptocotizacion (
    cantidad numeric NOT NULL,
    precio_unitario numeric NOT NULL,
    descuento_porcentaje numeric NOT NULL,
    importe numeric NOT NULL,
    id integer NOT NULL,
    cotizacion_id integer NOT NULL,
    servicio_id integer,
    codigo_sat character varying NOT NULL,
    descripcion character varying NOT NULL,
    unidad character varying NOT NULL,
    codigo_unidad character varying NOT NULL
);


ALTER TABLE public.conceptocotizacion OWNER TO postgres;

--
-- Name: conceptocotizacion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conceptocotizacion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conceptocotizacion_id_seq OWNER TO postgres;

--
-- Name: conceptocotizacion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conceptocotizacion_id_seq OWNED BY public.conceptocotizacion.id;


--
-- Name: cotizaciones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cotizaciones (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    subtotal numeric NOT NULL,
    descuento_global numeric NOT NULL,
    iva numeric NOT NULL,
    total numeric NOT NULL,
    fecha_emision date NOT NULL,
    estado character varying NOT NULL,
    metodo_pago character varying NOT NULL,
    forma_pago character varying NOT NULL,
    notas character varying,
    notas_privadas character varying,
    folio character varying NOT NULL,
    id integer NOT NULL,
    numero character varying NOT NULL,
    numero_version character varying NOT NULL,
    version_letra character varying,
    cotizacion_original_id integer,
    cliente_id integer NOT NULL,
    fecha_vigencia date,
    cliente_nombre character varying,
    cliente_rfc character varying(13),
    cliente_direccion character varying,
    cliente_ciudad character varying,
    cliente_cp character varying(5),
    cliente_telefono character varying,
    cliente_email character varying
);


ALTER TABLE public.cotizaciones OWNER TO postgres;

--
-- Name: cotizaciones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cotizaciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cotizaciones_id_seq OWNER TO postgres;

--
-- Name: cotizaciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cotizaciones_id_seq OWNED BY public.cotizaciones.id;


--
-- Name: detalle_orden_compra; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.detalle_orden_compra (
    cantidad numeric NOT NULL,
    precio_unitario numeric NOT NULL,
    descuento_porcentaje numeric NOT NULL,
    importe numeric NOT NULL,
    id integer NOT NULL,
    orden_id integer NOT NULL,
    servicio_proveedor_id integer,
    codigo_sku character varying NOT NULL,
    descripcion character varying NOT NULL,
    unidad character varying NOT NULL,
    cantidad_recibida numeric NOT NULL
);


ALTER TABLE public.detalle_orden_compra OWNER TO postgres;

--
-- Name: detalle_orden_compra_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.detalle_orden_compra_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detalle_orden_compra_id_seq OWNER TO postgres;

--
-- Name: detalle_orden_compra_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.detalle_orden_compra_id_seq OWNED BY public.detalle_orden_compra.id;


--
-- Name: orden_compra; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orden_compra (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    subtotal numeric NOT NULL,
    descuento_global numeric NOT NULL,
    iva numeric NOT NULL,
    total numeric NOT NULL,
    id integer NOT NULL,
    proveedor_id integer NOT NULL,
    fecha_emision date NOT NULL,
    fecha_entrega_estimada date,
    folio character varying NOT NULL,
    estado character varying NOT NULL,
    notas character varying,
    metodo_pago character varying(20) DEFAULT 'POR_DEFINIR'::character varying,
    forma_pago character varying(2) DEFAULT '99'::character varying,
    notas_privadas text,
    proveedor_nombre character varying,
    proveedor_rfc character varying(13),
    proveedor_direccion character varying,
    proveedor_ciudad character varying,
    proveedor_cp character varying(5),
    proveedor_telefono character varying,
    proveedor_email character varying
);


ALTER TABLE public.orden_compra OWNER TO postgres;

--
-- Name: orden_compra_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.orden_compra_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orden_compra_id_seq OWNER TO postgres;

--
-- Name: orden_compra_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.orden_compra_id_seq OWNED BY public.orden_compra.id;


--
-- Name: ordentrabajo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ordentrabajo (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    numero_ot character varying NOT NULL,
    cotizacion_id integer NOT NULL,
    cliente_nombre character varying NOT NULL,
    domicilio character varying NOT NULL,
    contacto character varying NOT NULL,
    fecha_programada date NOT NULL,
    hora_programada character varying NOT NULL,
    duracion integer NOT NULL,
    estado character varying NOT NULL,
    notas_publicas character varying,
    notas_privadas character varying,
    tecnico_id integer,
    tecnico_nombre character varying
);


ALTER TABLE public.ordentrabajo OWNER TO postgres;

--
-- Name: ordentrabajo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ordentrabajo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ordentrabajo_id_seq OWNER TO postgres;

--
-- Name: ordentrabajo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ordentrabajo_id_seq OWNED BY public.ordentrabajo.id;


--
-- Name: proveedor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proveedor (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    nombre character varying NOT NULL,
    rfc character varying(13),
    razon_social character varying,
    contacto character varying,
    email character varying,
    telefono character varying,
    direccion character varying,
    ciudad character varying,
    cp character varying(5),
    categoria character varying,
    activo boolean NOT NULL,
    notas character varying
);


ALTER TABLE public.proveedor OWNER TO postgres;

--
-- Name: proveedor_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proveedor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.proveedor_id_seq OWNER TO postgres;

--
-- Name: proveedor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proveedor_id_seq OWNED BY public.proveedor.id;


--
-- Name: servicio; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.servicio (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    codigo_sat character varying NOT NULL,
    clave character varying NOT NULL,
    descripcion character varying,
    area character varying NOT NULL,
    precio_base numeric NOT NULL,
    unidad character varying NOT NULL,
    codigo_unidad character varying NOT NULL,
    activo boolean NOT NULL,
    notas character varying
);


ALTER TABLE public.servicio OWNER TO postgres;

--
-- Name: servicio_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.servicio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.servicio_id_seq OWNER TO postgres;

--
-- Name: servicio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.servicio_id_seq OWNED BY public.servicio.id;


--
-- Name: servicio_proveedor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.servicio_proveedor (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    proveedor_id integer NOT NULL,
    codigo_sku character varying NOT NULL,
    descripcion character varying NOT NULL,
    descripcion_detallada character varying,
    costo_unitario numeric NOT NULL,
    moneda character varying(3) NOT NULL,
    unidad character varying NOT NULL,
    activo boolean NOT NULL
);


ALTER TABLE public.servicio_proveedor OWNER TO postgres;

--
-- Name: servicio_proveedor_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.servicio_proveedor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.servicio_proveedor_id_seq OWNER TO postgres;

--
-- Name: servicio_proveedor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.servicio_proveedor_id_seq OWNED BY public.servicio_proveedor.id;


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuario (
    fecha_creacion timestamp with time zone DEFAULT date_trunc('second'::text, now()) NOT NULL,
    fecha_modificacion timestamp with time zone,
    creado_por character varying NOT NULL,
    modificado_por character varying,
    id integer NOT NULL,
    usuario character varying NOT NULL,
    "contraseña" character varying,
    nombres character varying NOT NULL,
    rol character varying NOT NULL,
    correo character varying NOT NULL,
    area character varying,
    permisos_ver json,
    permisos_crear json,
    permisos_editar json,
    permisos_eliminar json
);


ALTER TABLE public.usuario OWNER TO postgres;

--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuario_id_seq OWNER TO postgres;

--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: cliente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cliente ALTER COLUMN id SET DEFAULT nextval('public.cliente_id_seq'::regclass);


--
-- Name: concepto_orden_trabajo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepto_orden_trabajo ALTER COLUMN id SET DEFAULT nextval('public.concepto_orden_trabajo_id_seq'::regclass);


--
-- Name: conceptocotizacion id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conceptocotizacion ALTER COLUMN id SET DEFAULT nextval('public.conceptocotizacion_id_seq'::regclass);


--
-- Name: cotizaciones id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotizaciones ALTER COLUMN id SET DEFAULT nextval('public.cotizaciones_id_seq'::regclass);


--
-- Name: detalle_orden_compra id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.detalle_orden_compra ALTER COLUMN id SET DEFAULT nextval('public.detalle_orden_compra_id_seq'::regclass);


--
-- Name: orden_compra id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orden_compra ALTER COLUMN id SET DEFAULT nextval('public.orden_compra_id_seq'::regclass);


--
-- Name: ordentrabajo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ordentrabajo ALTER COLUMN id SET DEFAULT nextval('public.ordentrabajo_id_seq'::regclass);


--
-- Name: proveedor id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proveedor ALTER COLUMN id SET DEFAULT nextval('public.proveedor_id_seq'::regclass);


--
-- Name: servicio id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.servicio ALTER COLUMN id SET DEFAULT nextval('public.servicio_id_seq'::regclass);


--
-- Name: servicio_proveedor id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.servicio_proveedor ALTER COLUMN id SET DEFAULT nextval('public.servicio_proveedor_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
da5b731a1ea2
\.


--
-- Data for Name: cliente; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cliente (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, nombre, rfc, razon_social, contacto, email, telefono, direccion, ciudad, cp, activo, notas) FROM stdin;
2026-02-24 01:45:22+00	\N	ulises.moreno	ulises.moreno	336	MARIO ANDRÉS RUIZ SALINAS	RUSM840127DV3	MARIO ANDRÉS RUIZ SALINAS	MARIO RUIZ SALINAS	mars_gi@hotmail.com	\N	\N	\N	\N	t	COMPLETAR DATOS
2026-02-24 21:46:57+00	2026-03-05 01:12:33+00	ulises.moreno	mjimenez	337	DORA CASAS ROMERO	CARD690703N3A	DORA CASAS ROMERO	JUAN MANUEL ROMERO	desisol.maquinados10@gmail.com	+52 55 5507 3890	ESTUDIOS STHAL, NO. 35, COL. JARDINES TECMA, IZTACALCO, CDMX.	CDMX	08920	t	None
2026-02-27 23:10:35+00	2026-03-05 01:14:06+00	ulises.moreno	mjimenez	338	BADER DE MEXICO S. EN C. POR A. DE C.V.	BME950626IJ9	BADER DE MEXICO S. EN C. POR A. DE C.V.	LIZETH RAMÍREZ	Lizeth.Ramirez@bader-leather.com	+524771343786	Tabachines, 201, Col. Unidad Obrera, Leon, Guanajuato.	LÉON	37179	t	ATENCIÓN ING. NÉSTOR FRÍAS HERAS
2026-03-06 20:41:44+00	2026-03-06 20:44:38+00	ulises.moreno	ulises.moreno	339	FELIPE GARFIAS TORRES	GATF730729P49	FELIPE GARGIAS TORRES	ING. FELIPE GARFIAS TORRES / DRA. BERENICE SALINAS	saludehigiene@3-s.com.mx	5535667288	LAGO DE CHAPULTEPEC, 141 2G L51 COL. PASEOS DE CHAVARRÍA, MINERAL DE REFORMA, HIDALGO	MINERAL DE LA REFORMA, HIDALGO	42186	t	\N
2026-03-06 20:52:51+00	\N	ulises.moreno	ulises.moreno	340	DISTRIBUIDORA DE TEXTILES AVANTE	DTA93062436A	DISTRIBUIDORA DE TEXTILES AVANTE, S.A. DE C.V.	WILLIAM CRUZ GONZALEZ	william.cruz@avantetextil.com	722 279 0900	AV. INDUSTRIA AUTOMOTRIZ, NO. 128, EL COECILLO, TOLUCA, ESTADO DE MÉXICO	TOLUCA	50246	t	\N
2026-03-20 15:16:26+00	2026-03-20 15:18:09+00	ulises.moreno	ulises.moreno	341	BERNARDO MORALES SERAFÍN	MOSB6902212U8	BERNARDO MORALES SERAFÍN	ING. BERNARDO MORALES SERAFÍN	bemose@gmail.com	+523331066872	\N	GUADALAJARA, JALISCO	\N	t	\N
2026-03-26 18:08:37+00	2026-03-26 19:09:27+00	ulises.moreno	ulises.moreno	342	TEKNOPELLETS SA DE CV	TEK0902203G1	TEKNOPELLETS SA DE CV	Ing. Aarón García	seguridadindustrialn24@teknopellets.com	7221181019	Jaime Blades, 11 Torre D Pent House, Col. Polanco I Sección	LERMA	11510	t	UBICACIÓN PLANTAS PRODUCTIVAS: Boulevard Miguel Alemán, KM 5.5 S/N, Parque Industrial Lerma, \nLerma de Villada, Estado de México CP: 52000
2026-02-21 03:42:49+00	2026-02-21 04:16:33+00	mjimenez	mjimenez	2	Marco Alvaro Jimenez Ferra	JIFM961103	Marco Alvaro Jimenez Ferra	Michael Joseph	marcoljimenezcp@gmail.com	112233445566	Mzna 4 Gpo 24 	CDMX	01170	t	Sin notas
\.


--
-- Data for Name: concepto_orden_trabajo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.concepto_orden_trabajo (id, orden_id, concepto_cotizacion_id, descripcion, cantidad, precio_unitario, importe, unidad, estado, fecha_completado, completado_por, creado_por, fecha_creacion, descuento_porcentaje) FROM stdin;
1	1	6	ANÁLISIS DE LODOS Y BIOSOLIDOS NOM-004-SEMARNAT	1.00	10500.00	10500.00	ANÁLISIS	completado	2026-03-04 22:02:46.311666	ulises.moreno	ulises.moreno	2026-02-28 02:18:11.327886	0
2	1	7	ANÁLISIS CRETI NOM-052-SEMARNAT-2005	1.00	16500.00	16500.00	ANÁLISIS	completado	2026-03-04 22:02:58.77217	ulises.moreno	ulises.moreno	2026-02-28 02:18:11.328198	0
3	2	18	EVALUACIÓN Y DICTAMEN DE RECIPIENTES SUJETOS A PRESIÓN NOM-020-STPS-2011	1.00	13500.00	13500.00	SERVICIO	pendiente	\N	\N	ulises.moreno	2026-03-05 20:31:52.966338	0
4	3	17	ESTUDIO DE RUIDO AL EXTERIOR NOM-081-SEMARNAT-1994	2.00	4500.00	9000.00	SERVICIO	pendiente	\N	\N	ulises.moreno	2026-03-25 01:13:22.392956	0
5	4	9	MUESTRA Y ANÁLISIS DE AGENTES QUÍMICOS NOM-010-STPS-2015	4.00	1700.00	6800.00	SERVICIO	pendiente	\N	\N	ulises.moreno	2026-03-25 01:15:18.48109	0
6	5	28	ILUMINACIÓN NOM-025-STPS-2008	770.00	125.00	96250.00	SERVICIO	pendiente	\N	\N	ulises.moreno	2026-03-31 20:59:31.886287	0.00
\.


--
-- Data for Name: conceptocotizacion; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.conceptocotizacion (cantidad, precio_unitario, descuento_porcentaje, importe, id, cotizacion_id, servicio_id, codigo_sat, descripcion, unidad, codigo_unidad) FROM stdin;
1	10500	0	10500	6	2	71	77102000	ANÁLISIS DE LODOS Y BIOSOLIDOS NOM-004-SEMARNAT	ANÁLISIS	H87
1	16500	0	16500	7	2	72	77102000	ANÁLISIS CRETI NOM-052-SEMARNAT-2005	ANÁLISIS	H87
4	1700	0	6800	9	4	75	93141808	MUESTRA Y ANÁLISIS DE AGENTES QUÍMICOS NOM-010-STPS-2015	SERVICIO	H87
4	1700	0	6800	10	5	75	93141808	MUESTRA Y ANÁLISIS DE AGENTES QUÍMICOS NOM-010-STPS-2015	SERVICIO	H87
30	200	0	6000	11	1	66	93141808	ILUMINACIÓN NOM-025-STPS-2008.	SERVICIO	H87
10	600	0	6000	12	1	67	93141808	NIVEL DE EXPOSICIÓN A RUIDO Y ESPECTRO ACÚSTICO NOM-011-STPS-2001	SERVICIO	H87
1	650	0	650	13	1	68	93141808	TIERRAS FÍSICAS NOM-022-STPS-2015	SERVICIO	H87
5	1550	0	7750	14	1	69	93141808	TEMPERATURAS ELEVADAS NOM-015-STPS-2001	SERVICIO	H87
1	800	0	800	15	1	70	77101700	VIÁTICOS	SERVICIO	H87
2	4500	0	9000	17	3	74	77131603	ESTUDIO DE RUIDO AL EXTERIOR NOM-081-SEMARNAT-1994	SERVICIO	H87
1	13500	0	13500	18	6	73	93141808	EVALUACIÓN Y DICTAMEN DE RECIPIENTES SUJETOS A PRESIÓN NOM-020-STPS-2011	SERVICIO	H87
1	4500	0	4500	19	6	74	77131603	ESTUDIO DE RUIDO AL EXTERIOR NOM-081-SEMARNAT-1994	SERVICIO	H87
1	130000	0	130000	20	7	76	93141808	RECONOCIMIENTO INICIAL PARA NOM-010-STPS-2015   500 SUSTANCIAS	SERVICIO	H87
1	10500	0	10500	24	8	77	77131603	PARTICULAS SUSPENDIDAS TOTALES, DIÓXIDO DE AZUFRE, ÓXIDOS DE NITRÓGENO Y MONÓXIDO DE CARBONO NOM-043-SEMARNAT-1993 CALDERA 600 CC COMBUSTOLEO 2025 EMA Y PROFEPA.	SERVICIO	H87
1	10000	0	10000	25	8	77	77131603	PARTICULAS SUSPENDIDAS TOTALES, DIÓXIDO DE AZUFRE, ÓXIDOS DE NITRÓGENO Y MONÓXIDO DE CARBONO NOM-043-SEMARNAT-1993 2025 CALDERA 600 CC COMBUSTOLEO EMA	SERVICIO	H87
1	8500	0	8500	26	8	77	77131603	PARTICULAS SUSPENDIDAS TOTALES, DIÓXIDO DE AZUFRE, ÓXIDOS DE NITRÓGENO Y MONÓXIDO DE CARBONO NOM-043-SEMARNAT-1993 2026 CALDERA 600 CC COMBUSTOLEO EMA	SERVICIO	H87
13	750	0	9750	27	9	68	93141808	TIERRAS FÍSICAS NOM-022-STPS-2015	SERVICIO	H87
770	125	0	96250	28	10	66	93141808	ILUMINACIÓN NOM-025-STPS-2008	SERVICIO	H87
1	11350	10	10215.0	29	11	68	93141808	TIERRAS FÍSICAS NOM-022-STPS-2015 CAMPECHE	SERVICIO	H87
\.


--
-- Data for Name: cotizaciones; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cotizaciones (fecha_creacion, fecha_modificacion, creado_por, modificado_por, subtotal, descuento_global, iva, total, fecha_emision, estado, metodo_pago, forma_pago, notas, notas_privadas, folio, id, numero, numero_version, version_letra, cotizacion_original_id, cliente_id, fecha_vigencia, cliente_nombre, cliente_rfc, cliente_direccion, cliente_ciudad, cliente_cp, cliente_telefono, cliente_email) FROM stdin;
2026-02-24 02:32:10+00	2026-03-05 00:16:38+00	ulises.moreno	mjimenez	21200.00	0.00	3392.0000	24592.0000	2026-02-24	borrador	PPD	99	Pendiente definir cantidad de mediciones de Tierras Físicas\n\nTrabajos a realizar en Tizayuca, Hidalgo.\nConfirmar domicilio	\N	COT-260224-1	1	COT-260224-1	COT-260224-1	\N	\N	336	2026-03-26	MARIO ANDRÉS RUIZ SALINAS	RUSM840127DV3	\N	\N	\N	\N	mars_gi@hotmail.com
2026-02-24 22:51:07+00	2026-03-04 22:02:58+00	ulises.moreno	ulises.moreno	27000	0.00	4320.00	31320.00	2026-02-24	finalizada	PUE	99		\N	COT-260224-2	2	COT-260224-2	COT-260224-2	\N	\N	337	2026-03-26	DORA CASAS ROMERO	CARD690703N3A	ESTUDIOS STHAL, NO. 35, COL. JARDINES TECMA, IZTACALCO, CDMX	CDMX	08920	+52 55 5507 3890	desisol.maquinados10@gmail.com
2026-03-04 20:03:13+00	2026-03-05 01:38:06.956293+00	ulises.moreno	ulises.moreno	6800	0.00	1088.00	7888.00	2026-03-04	borrador	PPD	99	Sustancias a evaluar: Sulfuro de Hidrógeno, Dióxido de Azufre, Cloro y Óxidos de Nitrógeno. TRABAJOS A REALIZAR EN PLANTA SPLIT. CONFIRMAR DOMICILIO.	500 NFH	COT-260304-5	5	COT-260304-5	COT-260304-5	\N	\N	338	2026-04-03	BADER DE MEXICO S. EN C. POR A. DE C.V.	BME950626IJ9	Tabachines, 201, Col. Unidad Obrera,Leon, Guanajuato	LÉON	37179	+524771343786	Lizeth.Ramirez@bader-leather.com
2026-03-31 19:18:46+00	2026-03-31 19:18:46+00	ulises.moreno	ulises.moreno	10215.0	0.00	1634.400	11849.400	2026-03-31	borrador	PPD	99	TRABAJOS A REALIZAR EN PLANTA HECELCHAKÁN, CAMPECHE.	\N	COT-260331-11	11	COT-260331-11	COT-260331-11	\N	\N	340	2026-04-30	DISTRIBUIDORA DE TEXTILES AVANTE	DTA93062436A	AV. INDUSTRIA AUTOMOTRIZ, NO. 128, EL COECILLO, TOLUCA, ESTADO DE MÉXICO	TOLUCA	50246	722 279 0900	william.cruz@avantetextil.com
2026-03-20 15:23:27+00	2026-03-22 23:05:34+00	ulises.moreno	mjimenez	29000	0.00	4640.00	33640.00	2026-03-20	borrador	PPD	99	Precios Unitarios por Cada Concepto	\N	COT-260320-8	8	COT-260320-8	COT-260320-8	\N	\N	341	2026-04-19	BERNARDO MORALES SERAFÍN	MOSB6902212U8	\N	GUADALAJARA, JALISCO	\N	+523331066872	bemose@gmail.com
2026-03-30 23:48:31+00	2026-03-31 20:59:31+00	ulises.moreno	ulises.moreno	96250	0.00	15400.00	111650.00	2026-03-30	programada	PPD	99	TRABAJOS A REALIZAR EN PROSEDE, CUAUTITLÁN, EDO. MÉX. 	\N	COT-260330-10	10	COT-260330-10	COT-260330-10	\N	\N	339	2026-04-29	FELIPE GARFIAS TORRES	GATF730729P49	LAGO DE CHAPULTEPEC, 141 2G L51 COL. PASEOS DE CHAVARRÍA, MINERAL DE REFORMA, HIDALGO	MINERAL DE LA REFORMA, HIDALGO	42186	5535667288	saludehigiene@3-s.com.mx
2026-02-27 23:15:03+00	2026-03-25 01:13:22+00	ulises.moreno	ulises.moreno	9000	0.00	1440.00	10440.00	2026-02-27	programada	PPD	99	SE CONSIDERAN 2 PUNTOS, POR SER 2 TURNOS, DIURNO Y NOCTURNO	1000 NFH	COT-260227-3	3	COT-260227-3	COT-260227-3	\N	\N	338	2026-03-29	BADER DE MEXICO S. EN C. POR A. DE C.V.	BME950626IJ9	Tabachines, 201, Col. Unidad Obrera, Leon, Guanajuato.	LÉON	37179	+524771343786	Lizeth.Ramirez@bader-leather.com
2026-03-05 20:29:19+00	2026-03-06 20:19:00+00	ulises.moreno	ulises.moreno	18000	0.00	2880.00	20880.00	2026-03-05	cancelada	PPD	04	Test	\N	COT-260305-6	6	COT-260305-6	COT-260305-6	\N	\N	2	2026-04-04	Marco Alvaro Jimenez Ferra	JIFM961103	Mzna 4 Gpo 24 	CDMX	01170	112233445566	marcoljimenezcp@gmail.com
2026-03-06 20:55:00+00	2026-03-06 20:55:00+00	ulises.moreno	ulises.moreno	130000	0.00	20800.00	150800.00	2026-03-06	borrador	PPD	99	TRABAJOS A REALIZAR EN SAN JUAN DEL RÍO, CONFIRMAR DOMICILIO	\N	COT-260306-7	7	COT-260306-7	COT-260306-7	\N	\N	339	2026-04-05	FELIPE GARFIAS TORRES	GATF730729P49	LAGO DE CHAPULTEPEC, 141 2G L51 COL. PASEOS DE CHAVARRÍA, MINERAL DE REFORMA, HIDALGO	MINERAL DE LA REFORMA, HIDALGO	42186	5535667288	saludehigiene@3-s.com.mx
2026-03-02 00:56:42+00	2026-03-25 01:15:18+00	ulises.moreno	ulises.moreno	6800	0.00	1088.00	7888.00	2026-03-02	programada	PPD	99	SUSTANCIAS A EVALUAR: DIÓXIDO DE SILICIO, INCLUYE BLANCOS DE CAMPO PARA CADA MUESTRA	500 NFH	COT-260302-4	4	COT-260302-4	COT-260302-4	\N	\N	338	2026-04-01	BADER DE MEXICO S. EN C. POR A. DE C.V.	BME950626IJ9	Tabachines, 201, Col. Unidad Obrera,Leon, Guanajuato	LÉON	37179	+524771343786	Lizeth.Ramirez@bader-leather.com
2026-03-26 19:13:53+00	2026-03-26 19:13:53+00	ulises.moreno	ulises.moreno	9750	0.00	1560.00	11310.00	2026-03-26	borrador	PPD	99	TRABAJOS A REALIZAR EN: Boulevard Miguel Alemán, KM 5.5 S/N, Parque Industrial Lerma, \nLerma de Villada, Estado de México	\N	COT-260326-9	9	COT-260326-9	COT-260326-9	\N	\N	342	2026-04-25	TEKNOPELLETS SA DE CV	TEK0902203G1	Jaime Blades, 11 Torre D Pent House, Col. Polanco I Sección	LERMA	11510	7221181019	seguridadindustrialn24@teknopellets.com
\.


--
-- Data for Name: detalle_orden_compra; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.detalle_orden_compra (cantidad, precio_unitario, descuento_porcentaje, importe, id, orden_id, servicio_proveedor_id, codigo_sku, descripcion, unidad, cantidad_recibida) FROM stdin;
\.


--
-- Data for Name: orden_compra; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.orden_compra (fecha_creacion, fecha_modificacion, creado_por, modificado_por, subtotal, descuento_global, iva, total, id, proveedor_id, fecha_emision, fecha_entrega_estimada, folio, estado, notas, metodo_pago, forma_pago, notas_privadas, proveedor_nombre, proveedor_rfc, proveedor_direccion, proveedor_ciudad, proveedor_cp, proveedor_telefono, proveedor_email) FROM stdin;
\.


--
-- Data for Name: ordentrabajo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ordentrabajo (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, numero_ot, cotizacion_id, cliente_nombre, domicilio, contacto, fecha_programada, hora_programada, duracion, estado, notas_publicas, notas_privadas, tecnico_id, tecnico_nombre) FROM stdin;
2026-02-28 02:18:11+00	2026-03-04 22:02:58+00	ulises.moreno	ulises.moreno	1	OT-260228-1	2	DORA CASAS ROMERO	ESTUDIOS STHAL, NO. 35, COL. JARDINES TECMA, IZTACALCO, CDMX	JUAN MANUEL ROMERO	2026-03-02	15:15	3	finalizada	\N	\N	65	Prueba Tecnico
2026-03-05 20:31:52+00	2026-03-06 20:18:08+00	ulises.moreno	ulises.moreno	2	OT-260305-2	6	Marco Alvaro Jimenez Ferra	Mzna 4 Gpo 24 	Michael Joseph	2026-03-10	16:20	2	cancelada	\N	\N	65	Prueba Tecnico
2026-03-25 01:13:22+00	2026-03-25 01:13:22+00	ulises.moreno	ulises.moreno	3	OT-260325-3	3	BADER DE MEXICO S. EN C. POR A. DE C.V.	Tabachines, 201, Col. Unidad Obrera, Leon, Guanajuato.	LIZETH RAMÍREZ	2026-03-26	10:00	4	programada	\N	\N	65	Prueba Tecnico
2026-03-25 01:15:18+00	2026-03-25 01:17:11+00	ulises.moreno	ulises.moreno	4	OT-260325-4	4	BADER DE MEXICO S. EN C. POR A. DE C.V.	Tabachines, 201, Col. Unidad Obrera, Leon, Guanajuato.	LIZETH RAMÍREZ	2026-03-26	11:00	4	programada	\N	\N	2	Ulises Moreno
2026-03-31 20:59:31+00	2026-03-31 20:59:31+00	ulises.moreno	ulises.moreno	5	OT-260331-5	10	FELIPE GARFIAS TORRES	LAGO DE CHAPULTEPEC, 141 2G L51 COL. PASEOS DE CHAVARRÍA, MINERAL DE REFORMA, HIDALGO	ING. FELIPE GARFIAS TORRES / DRA. BERENICE SALINAS	2026-04-27	10:30	24	programada	\N	\N	65	Prueba Tecnico
\.


--
-- Data for Name: proveedor; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.proveedor (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, nombre, rfc, razon_social, contacto, email, telefono, direccion, ciudad, cp, categoria, activo, notas) FROM stdin;
2026-02-22 05:11:30+00	2026-03-27 04:28:18+00	mjimenez	mjimenez	1	Marco Alvaro Jimenez Ferra	JIFM961103EQ2	Marco Alvaro Jimenez Ferra	Michael	marcoljimenezcp@gmail.com	5536561789	Unidad Santa Fe Mazna 4 Gpo 24	CDMX	01170	Tecnología de la Información	t	Sistema web, pagina web, correos electronicos y computadoras.
\.


--
-- Data for Name: servicio; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.servicio (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, codigo_sat, clave, descripcion, area, precio_base, unidad, codigo_unidad, activo, notas) FROM stdin;
2026-02-21 03:45:15+00	\N	mjimenez	mjimenez	1	77131701-ECO	E-LPTAR-004	ANÁLISIS DE LODOS PTAR	ECO	8000	MUESTRA	E48-SERV	t	Muestra de lodos.
2026-02-21 03:46:17+00	\N	mjimenez	mjimenez	2	93141808-HI	HI-RSP-020	PRUEBA Y DICTAMEN DE RECIPIENTES SUJETOS A PRESIÓN NOM-020-STPS-2011	HI	13000	SERVICIO	E48-SERV	t	
2026-02-24 01:32:05+00	\N	ulises.moreno	ulises.moreno	66	93141808	HI-025	ILUMINACIÓN NOM-025-STPS-2008	HI	200	SERVICIO	E48	t	PUNTO DE ESTUDIO DE ILUMINACIÓN PARA NOM-025-STPS-2008
2026-02-24 01:34:20+00	\N	ulises.moreno	ulises.moreno	67	93141808	HI-011	NIVEL DE EXPOSICIÓN A RUIDO Y ESPECTRO ACÚSTICO NOM-011-STPS-2001	HI	600	SERVICIO	E48	t	MEDICIÓN DEL NIVEL DE EXPOSICIÓN A RUIDO Y ESPECTRO ACÚSTICO PARA NOM-011-STPS-2001
2026-02-24 01:36:00+00	\N	ulises.moreno	ulises.moreno	68	93141808	HI-022	TIERRAS FÍSICAS NOM-022-STPS-2015	HI	650	SERVICIO	E48	t	MEDICIÓN DE RESISTENCIA A TIERRA A SISTEMAS DE PUESTA A TIERRA Y/O PARARRAYOS PARA NOM-022-STPS-2015
2026-02-24 01:40:37+00	2026-02-24 01:46:05+00	ulises.moreno	ulises.moreno	69	93141808	HI-015-EL	TEMPERATURAS ELEVADAS NOM-015-STPS-2001	HI	1550	SERVICIO	E48	t	MEDICIÓN DE ESTRÉS TÉRMICO POR TEMPERATURAS ELEVADAS PARA NOM-015-STPS-2001
2026-02-24 21:40:45+00	\N	ulises.moreno	ulises.moreno	71	77102000	ECO-04	ANÁLISIS DE LODOS Y BIOSOLIDOS NOM-004-SEMARNAT	ECO	10500	ANÁLISIS	E48	t	ANÁLISIS DE LODOS Y BIOSOLIDOS DE PLANTA DE TRATAMIENTO DE AGUAS RESIDUALES PARA NOM-004-SEMARNAT
2026-02-24 21:42:46+00	\N	ulises.moreno	ulises.moreno	72	77102000	ECO-52	ANÁLISIS CRETI NOM-052-SEMARNAT-2005	ECO	16500	ANÁLISIS	E48	t	ANÁLISIS CRETI PARA NOM-052-SEMARNAT-2005
2026-02-26 21:00:02+00	\N	ulises.moreno	ulises.moreno	73	93141808	HI-020	EVALUACIÓN Y DICTAMEN DE RECIPIENTES SUJETOS A PRESIÓN NOM-020-STPS-2011	HI	13500	SERVICIO	E48	t	PRUEBAS NO DESTRUCTIVAS PARA DICTAMINAR RECIPIENTES SUJETOS A PRESIÓN PARA NOM-STPS-2011
2026-02-27 18:41:45+00	\N	ulises.moreno	ulises.moreno	74	77131603	ECO-081	ESTUDIO DE RUIDO AL EXTERIOR NOM-081-SEMARNAT-1994	ECO	4500	SERVICIO	E48	t	MEDICIÓN DE NIVEL DE RUIDO HACIA EL EXTERIOR PARA NOM-081-SEMARNAT-1994
2026-02-27 20:09:52+00	\N	ulises.moreno	ulises.moreno	75	93141808	HI-010	MUESTRA Y ANÁLISIS DE AGENTES QUÍMICOS NOM-010-STPS-2015	HI	1700	SERVICIO	E48	t	MUESTRA Y ANÁLISIS DE DIVERSOS AGENTES QUÍMICOS PARA NOM-010-STPS-2015
2026-03-06 20:36:33+00	\N	ulises.moreno	ulises.moreno	76	93141808	HI-010-RI	RECONOCIMIENTO INICIAL PARA NOM-010-STPS-2015	HI	20000	SERVICIO	E48	t	RECONOCIMIENTO INICIAL PARA AGENTES QUÍMICOS DE NOM-101-STPS-2015
2026-02-24 02:29:10+00	2026-03-07 02:31:36+00	ulises.moreno	ulises.moreno	70	77101700	VIAT	VIÁTICOS	HI	0	SERVICIO	E48	t	\N
2026-03-19 22:47:27+00	\N	ulises.moreno	ulises.moreno	77	77131603	ECO-043-NX	PARTICULAS SUSPENDIDAS TOTALES, DIÓXIDO DE AZUFRE, ÓXIDOS DE NITRÓGENO Y MONÓXIDO DE CARBONO NOM-043-SEMARNAT-1993	ECO	8500	SERVICIO	E48	t	\N
\.


--
-- Data for Name: servicio_proveedor; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.servicio_proveedor (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, proveedor_id, codigo_sku, descripcion, descripcion_detallada, costo_unitario, moneda, unidad, activo) FROM stdin;
\.


--
-- Data for Name: usuario; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuario (fecha_creacion, fecha_modificacion, creado_por, modificado_por, id, usuario, "contraseña", nombres, rol, correo, area, permisos_ver, permisos_crear, permisos_editar, permisos_eliminar) FROM stdin;
2026-02-22 05:08:54+00	2026-03-19 04:07:38+00	mjimenez	mjimenez	65	prueba.tecnico	$2b$12$/rAMFo7Ff/FAGXg88JmD8esjHfj8h1ExussbUVrbUZ1.S8mRCK.Ge	Prueba Tecnico	tecnico	tecnico@teamsa.com.mx	ECO	["ordenes"]	[]	["ordenes"]	[]
2026-03-31 20:48:48+00	2026-03-31 21:02:26+00	ulises.moreno	ulises.moreno	133	ulises.reyes	$2b$12$iKWZ2N7ulcN9scVZVRRutOmz8yQfnQSP9t2UTAXStVuh1c8YtPH0y	ULISES MORENO REYES	funcionario	direccion@teamsa.com.mx	Dirección	["usuarios", "clientes", "cotizaciones", "ordenes"]	["cotizaciones"]	[]	[]
2026-02-10 10:12:25+00	2026-03-25 01:16:42+00	mjimenez	ulises.moreno	36	Prueba2	$2b$12$as3l.Q0WUrfBrtAL8ZovPegeowr6yNyfEsUBJDtHP4SA.fKCbumiu	Prueba Funcionario2	tecnico	prueba2@gmail.com	ECO	["ordenes"]	[]	["ordenes"]	[]
2026-02-05 02:19:20+00	2026-03-29 22:45:18+00	SYSTEM	mjimenez	1	mjimenez	$2b$12$MNmgg6UTZbNeed2ojcBoR./YkLhafBjKf0e4/J7VSZAILUT9BLfSu	Marco Jimenez	admin	mjimenez@teamsa.com.mx	TI	["usuarios", "clientes", "proveedores", "servicios", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "cotizaciones", "ordenes", "ordenes_compra"]
2026-02-05 02:19:20+00	2026-03-31 20:47:41+00	SYSTEM	ulises.moreno	2	ulises.moreno	$2b$12$dyTitT0MPASdC8ScyzaCFubq5olVLVi6ql1TzmHfkNvfue.XcpuM.	Ulises Moreno	admin	ulises.moreno@teamsa.com.mx	Dirección	["usuarios", "clientes", "proveedores", "servicios", "servicios_proveedores", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "servicios_proveedores", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "servicios_proveedores", "cotizaciones", "ordenes", "ordenes_compra"]	["usuarios", "clientes", "proveedores", "servicios", "servicios_proveedores", "cotizaciones", "ordenes", "ordenes_compra"]
\.


--
-- Name: cliente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cliente_id_seq', 343, true);


--
-- Name: concepto_orden_trabajo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.concepto_orden_trabajo_id_seq', 6, true);


--
-- Name: conceptocotizacion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.conceptocotizacion_id_seq', 29, true);


--
-- Name: cotizaciones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cotizaciones_id_seq', 11, true);


--
-- Name: detalle_orden_compra_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.detalle_orden_compra_id_seq', 9, true);


--
-- Name: orden_compra_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.orden_compra_id_seq', 9, true);


--
-- Name: ordentrabajo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ordentrabajo_id_seq', 5, true);


--
-- Name: proveedor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.proveedor_id_seq', 82, true);


--
-- Name: servicio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.servicio_id_seq', 77, true);


--
-- Name: servicio_proveedor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.servicio_proveedor_id_seq', 36, true);


--
-- Name: usuario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usuario_id_seq', 133, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: cliente cliente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cliente
    ADD CONSTRAINT cliente_pkey PRIMARY KEY (id);


--
-- Name: concepto_orden_trabajo concepto_orden_trabajo_concepto_cotizacion_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepto_orden_trabajo
    ADD CONSTRAINT concepto_orden_trabajo_concepto_cotizacion_id_key UNIQUE (concepto_cotizacion_id);


--
-- Name: concepto_orden_trabajo concepto_orden_trabajo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepto_orden_trabajo
    ADD CONSTRAINT concepto_orden_trabajo_pkey PRIMARY KEY (id);


--
-- Name: conceptocotizacion conceptocotizacion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conceptocotizacion
    ADD CONSTRAINT conceptocotizacion_pkey PRIMARY KEY (id);


--
-- Name: cotizaciones cotizaciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotizaciones
    ADD CONSTRAINT cotizaciones_pkey PRIMARY KEY (id);


--
-- Name: detalle_orden_compra detalle_orden_compra_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.detalle_orden_compra
    ADD CONSTRAINT detalle_orden_compra_pkey PRIMARY KEY (id);


--
-- Name: orden_compra orden_compra_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orden_compra
    ADD CONSTRAINT orden_compra_pkey PRIMARY KEY (id);


--
-- Name: ordentrabajo ordentrabajo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ordentrabajo
    ADD CONSTRAINT ordentrabajo_pkey PRIMARY KEY (id);


--
-- Name: proveedor proveedor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proveedor
    ADD CONSTRAINT proveedor_pkey PRIMARY KEY (id);


--
-- Name: servicio servicio_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.servicio
    ADD CONSTRAINT servicio_pkey PRIMARY KEY (id);


--
-- Name: servicio_proveedor servicio_proveedor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.servicio_proveedor
    ADD CONSTRAINT servicio_proveedor_pkey PRIMARY KEY (id);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: ix_cliente_nombre; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cliente_nombre ON public.cliente USING btree (nombre);


--
-- Name: ix_concepto_ot_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_concepto_ot_estado ON public.concepto_orden_trabajo USING btree (estado);


--
-- Name: ix_concepto_ot_orden_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_concepto_ot_orden_id ON public.concepto_orden_trabajo USING btree (orden_id);


--
-- Name: ix_conceptocotizacion_cotizacion_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_conceptocotizacion_cotizacion_id ON public.conceptocotizacion USING btree (cotizacion_id);


--
-- Name: ix_conceptocotizacion_servicio_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_conceptocotizacion_servicio_id ON public.conceptocotizacion USING btree (servicio_id);


--
-- Name: ix_cotizaciones_cliente_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cotizaciones_cliente_id ON public.cotizaciones USING btree (cliente_id);


--
-- Name: ix_cotizaciones_cotizacion_original_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cotizaciones_cotizacion_original_id ON public.cotizaciones USING btree (cotizacion_original_id);


--
-- Name: ix_cotizaciones_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cotizaciones_estado ON public.cotizaciones USING btree (estado);


--
-- Name: ix_cotizaciones_folio; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_cotizaciones_folio ON public.cotizaciones USING btree (folio);


--
-- Name: ix_cotizaciones_numero; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_cotizaciones_numero ON public.cotizaciones USING btree (numero);


--
-- Name: ix_cotizaciones_numero_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_cotizaciones_numero_version ON public.cotizaciones USING btree (numero_version);


--
-- Name: ix_detalle_orden_compra_orden_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_detalle_orden_compra_orden_id ON public.detalle_orden_compra USING btree (orden_id);


--
-- Name: ix_detalle_orden_compra_servicio_proveedor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_detalle_orden_compra_servicio_proveedor_id ON public.detalle_orden_compra USING btree (servicio_proveedor_id);


--
-- Name: ix_orden_compra_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_orden_compra_estado ON public.orden_compra USING btree (estado);


--
-- Name: ix_orden_compra_folio; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_orden_compra_folio ON public.orden_compra USING btree (folio);


--
-- Name: ix_orden_compra_proveedor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_orden_compra_proveedor_id ON public.orden_compra USING btree (proveedor_id);


--
-- Name: ix_ordentrabajo_cotizacion_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ordentrabajo_cotizacion_id ON public.ordentrabajo USING btree (cotizacion_id);


--
-- Name: ix_ordentrabajo_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ordentrabajo_estado ON public.ordentrabajo USING btree (estado);


--
-- Name: ix_ordentrabajo_numero_ot; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_ordentrabajo_numero_ot ON public.ordentrabajo USING btree (numero_ot);


--
-- Name: ix_ordentrabajo_tecnico_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ordentrabajo_tecnico_id ON public.ordentrabajo USING btree (tecnico_id);


--
-- Name: ix_proveedor_nombre; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_proveedor_nombre ON public.proveedor USING btree (nombre);


--
-- Name: ix_servicio_clave; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_servicio_clave ON public.servicio USING btree (clave);


--
-- Name: ix_servicio_codigo_sat; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_servicio_codigo_sat ON public.servicio USING btree (codigo_sat);


--
-- Name: ix_servicio_codigo_unidad; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_servicio_codigo_unidad ON public.servicio USING btree (codigo_unidad);


--
-- Name: ix_servicio_proveedor_codigo_sku; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_servicio_proveedor_codigo_sku ON public.servicio_proveedor USING btree (codigo_sku);


--
-- Name: ix_servicio_proveedor_proveedor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_servicio_proveedor_proveedor_id ON public.servicio_proveedor USING btree (proveedor_id);


--
-- Name: ix_usuario_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_usuario_usuario ON public.usuario USING btree (usuario);


--
-- Name: concepto_orden_trabajo concepto_orden_trabajo_concepto_cotizacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepto_orden_trabajo
    ADD CONSTRAINT concepto_orden_trabajo_concepto_cotizacion_id_fkey FOREIGN KEY (concepto_cotizacion_id) REFERENCES public.conceptocotizacion(id);


--
-- Name: concepto_orden_trabajo concepto_orden_trabajo_orden_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.concepto_orden_trabajo
    ADD CONSTRAINT concepto_orden_trabajo_orden_id_fkey FOREIGN KEY (orden_id) REFERENCES public.ordentrabajo(id) ON DELETE CASCADE;


--
-- Name: conceptocotizacion conceptocotizacion_cotizacion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conceptocotizacion
    ADD CONSTRAINT conceptocotizacion_cotizacion_id_fkey FOREIGN KEY (cotizacion_id) REFERENCES public.cotizaciones(id);


--
-- Name: conceptocotizacion conceptocotizacion_servicio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conceptocotizacion
    ADD CONSTRAINT conceptocotizacion_servicio_id_fkey FOREIGN KEY (servicio_id) REFERENCES public.servicio(id);


--
-- Name: cotizaciones cotizaciones_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotizaciones
    ADD CONSTRAINT cotizaciones_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.cliente(id);


--
-- Name: cotizaciones cotizaciones_cotizacion_original_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cotizaciones
    ADD CONSTRAINT cotizaciones_cotizacion_original_id_fkey FOREIGN KEY (cotizacion_original_id) REFERENCES public.cotizaciones(id);


--
-- Name: detalle_orden_compra detalle_orden_compra_orden_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.detalle_orden_compra
    ADD CONSTRAINT detalle_orden_compra_orden_id_fkey FOREIGN KEY (orden_id) REFERENCES public.orden_compra(id);


--
-- Name: detalle_orden_compra detalle_orden_compra_servicio_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.detalle_orden_compra
    ADD CONSTRAINT detalle_orden_compra_servicio_proveedor_id_fkey FOREIGN KEY (servicio_proveedor_id) REFERENCES public.servicio_proveedor(id);


--
-- Name: orden_compra orden_compra_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orden_compra
    ADD CONSTRAINT orden_compra_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedor(id);


--
-- Name: ordentrabajo ordentrabajo_tecnico_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ordentrabajo
    ADD CONSTRAINT ordentrabajo_tecnico_id_fkey FOREIGN KEY (tecnico_id) REFERENCES public.usuario(id) ON DELETE SET NULL;


--
-- Name: servicio_proveedor servicio_proveedor_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.servicio_proveedor
    ADD CONSTRAINT servicio_proveedor_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedor(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict z2FBfvhg9ANB2WSoZwyz4IkXY5FRiRj5aSuKuy8DYb79TANDOvqCDwJsHKlwIS2

