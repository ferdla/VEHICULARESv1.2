Use MavacVehiculos;
show tables;

-- 1. Empresas (Rimac, Pacífico, Mapfre, Positiva)
CREATE TABLE empresa (
    id_empresa          INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nombre_empresa      VARCHAR(100) NOT NULL UNIQUE,
    activo              TINYINT(1) DEFAULT 1,
    fecha_creacion      DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO empresa (nombre_empresa) 
VALUES 
    ('RIMAC'),
    ('PACIFICO'),
    ('MAPFRE'),
    ('LA POSITIVA');

SELECT * FROM EMPRESA;

-- 2. Tipos de Riesgo (Alto Riesgo, Bajo riesgo, etc.)
CREATE TABLE tipo_riesgo (
    id_tipo_riesgo      INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nombre_riesgo       VARCHAR(100) NOT NULL UNIQUE,
    codigo_interno      VARCHAR(30) UNIQUE,                  -- ej: BR, BR1, CH-PK, PU
    fecha_creacion      DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tipo_riesgo (nombre_riesgo, codigo_interno)
VALUES
	('Bajo Riesgo', 'BR'),
    ('Bajo Riesgo 1', 'BR1'),
    ('Bajo Riesgo 2', 'BR2'),
    ('Bajo Riesgo 2.', 'BR2.'),
    ('Mediano Riesgo', 'MR'),
    ('Alto Riesgo', 'AR'),
    ('Alto Riesgo 1', 'AR1'),
    ('Alto Riesgo 2', 'AR2'),
    ('Chino-Hindu', 'CH-H'),
    ('Chino-Hindu-pk', 'CH-H-PK'),
    ('Pickup', 'PK');

select * from tipo_riesgo;


CREATE TABLE empresa_tipo_riesgo (
    id_empresa          INT NOT NULL,
    id_tipo_riesgo      INT NOT NULL,
    activo              TINYINT(1) DEFAULT 1,
    fecha_asignacion    DATE DEFAULT (CURRENT_DATE),
    PRIMARY KEY (id_empresa, id_tipo_riesgo),
    FOREIGN KEY (id_empresa)    REFERENCES empresa(id_empresa)    ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_riesgo) REFERENCES tipo_riesgo(id_tipo_riesgo) ON DELETE RESTRICT
);

INSERT INTO empresa_tipo_riesgo (id_empresa, id_tipo_riesgo)
VALUES
	-- Bajo Riesgo
	(3, 1),
	(4, 1),
	-- Bajo Riesgo 1
	(1, 2),
	(2, 2),
	-- Bajo Riesgo 2
	(1, 3),
	(2, 3),
	-- Bajo Riesgo 2.
	(1, 4),
	-- Mediano Riesgo
	(2, 5),
	(3, 5),
	(4, 5),
	-- Alto Riesgo
	(2, 6),
	(3, 6),
	(4, 6),
	-- Alto Riesgo 1
	(1, 7),
	-- Alto Riesgo 2
	(1, 8),
	-- Chino-Hindu
	(1, 9),
	(2, 9),
	(3, 9),
	(4, 9),
	-- Chino-Hindu-pk
	(1, 10),
	(2, 10),
	(3, 10),
	(4, 10),
	-- Pickup
	(1, 11),
	(2, 11),
	(3, 11),
	(4, 11);

SELECT 
    e.nombre_empresa,
    tr.nombre_riesgo,
    tr.codigo_interno
FROM empresa_tipo_riesgo etr
JOIN empresa e ON etr.id_empresa = e.id_empresa
JOIN tipo_riesgo tr ON etr.id_tipo_riesgo = tr.id_tipo_riesgo
ORDER BY e.nombre_empresa;

CREATE TABLE  marca (
	id_marca INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nombre_marca VARCHAR(50) NOT NULL UNIQUE
);

insert into marca (nombre_marca) values 
	('Alfa Romeo'),
    ('Audi'),
	('BAIC'),
	('BMW'),
	('Brilliance'),
	('BYD'),
	('Changan'),
	('Chery'),
	('Chevrolet'),
	('Chrysler'),
	('Citroën'),
	('Cupra'),
	('Daihatsu'),
	('DFSK'),
	('Dodge'),
	('Dongfeng'),
	('FAW'),
	('Fiat'),
	('Ford'),
	('Foton'),
	('GAC'),
	('Geely'),
	('Great Wall'),
	('Hafei'),
	('Haima'),
	('Haval'),
	('Honda'),
	('Hummer'),
	('Hyundai'),
	('JAC'),
	('Jaguar'),
	('Jeep'),
	('JMC'),
	('Jonway'),
	('Kia'),
	('Land Rover'),
	('Lexus'),
	('Lifan'),
	('Mahindra'),
	('Maxus'),
	('Mazda'),
	('Mercedes-Benz'),
	('MG'),
	('MINI'),
	('Mitsubishi'),
	('Nissan'),
	('Peugeot'),
	('Porsche'),
	('RAM'),
	('Renault'),
	('Seat'),
	('Skoda'),
	('SMA'),
	('SsangYong'),
	('Subaru'),
	('Suzuki'),
	('Toyota'),
	('Volkswagen'),
	('Volvo'),
	('ZNA'),
	('Zotye'),
	('ZXAuto');
    
select * from marca;

CREATE TABLE modelo (
    id_modelo INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_marca INT NOT NULL,
    nombre_modelo VARCHAR(150) NOT NULL,
    comentario TEXT DEFAULT NULL,
    FOREIGN KEY (id_marca) REFERENCES marca(id_marca),
    UNIQUE(id_marca, nombre_modelo)
);

select * from modelo where id_marca= 9 ;

UPDATE modelo
SET id_modelo = id_modelo - 1
WHERE id_modelo >= 1992
ORDER BY id_modelo ASC;


CREATE TABLE regla_clasificacion (
    id_regla_clasificacion INT AUTO_INCREMENT PRIMARY KEY,
    id_empresa INT NOT NULL,
    id_tipo_riesgo INT NOT NULL, -- Riesgo por defecto para esta regla
    id_marca INT NOT NULL,
    id_modelo INT DEFAULT NULL, -- NULL = aplica a TODA la marca
    anio_inicio INT DEFAULT NULL,
    anio_fin INT DEFAULT NULL,
    suma_min DECIMAL(15,2) DEFAULT NULL,
    suma_max DECIMAL(15,2) DEFAULT NULL,
    nota_regla TEXT DEFAULT NULL,               -- Descripción de la regla
    activo TINYINT(1) DEFAULT 1,
    
    FOREIGN KEY (id_empresa, id_tipo_riesgo) 
        REFERENCES empresa_tipo_riesgo(id_empresa, id_tipo_riesgo),
    FOREIGN KEY (id_marca) REFERENCES marca(id_marca),
    FOREIGN KEY (id_modelo) REFERENCES modelo(id_modelo)
);

select * from regla_clasificacion;


CREATE TABLE excepcion_confirmada (
    id_excepcion INT AUTO_INCREMENT PRIMARY KEY,
    id_regla_clasificacion INT NOT NULL,
    id_modelo INT NOT NULL,
    tipo_excepcion ENUM('EXCLUIR', 'INCLUIR_SOLO') NOT NULL DEFAULT 'EXCLUIR',
    id_tipo_riesgo_alternativo INT NULL,
    nota_excepcion VARCHAR(255) DEFAULT NULL,
    
    FOREIGN KEY (id_regla_clasificacion) REFERENCES regla_clasificacion(id_regla_clasificacion) ON DELETE CASCADE,
    FOREIGN KEY (id_modelo) REFERENCES modelo(id_modelo) ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_riesgo_alternativo) REFERENCES tipo_riesgo(id_tipo_riesgo),
    UNIQUE KEY uk_regla_modelo (id_regla_clasificacion, id_modelo)
);

select * from excepcion_confirmada;


CREATE TABLE excepcion_pendiente (
    id_excepcion_pendiente  INT AUTO_INCREMENT PRIMARY KEY,
    id_regla_clasificacion      INT NOT NULL,
    nombre_modelo_pendiente VARCHAR(150) NOT NULL,       -- nombre escrito por el usuario
    tipo_excepcion          ENUM('EXCLUIR','INCLUIR_SOLO') NOT NULL DEFAULT 'EXCLUIR',
    id_tipo_riesgo_alt      INT NULL,                    -- NULL = No Asegurable
    nota_excepcion          VARCHAR(255) DEFAULT NULL,
    resuelta                TINYINT(1) DEFAULT 0,        -- 0=pendiente, 1=resuelta
    fecha_creacion          DATETIME DEFAULT CURRENT_TIMESTAMP,
 
    FOREIGN KEY (id_regla_clasificacion)
        REFERENCES regla_clasificacion(id_regla_clasificacion) ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_riesgo_alt)
        REFERENCES tipo_riesgo(id_tipo_riesgo) ON DELETE SET NULL
);


CREATE TABLE regla_pendiente (
    id_regla_pendiente      INT AUTO_INCREMENT PRIMARY KEY,
    id_empresa              INT NOT NULL,
    id_tipo_riesgo          INT NOT NULL,
    nombre_marca_pendiente  VARCHAR(50) NOT NULL,        -- nombre de marca escrito por el usuario
    nombre_modelo_pendiente VARCHAR(150) NULL,           -- NULL = aplica a toda la marca
    anio_inicio             INT NULL,
    anio_fin                INT NULL,
    suma_min                DECIMAL(15,2) NULL,
    suma_max                DECIMAL(15,2) NULL,
    nota_regla              TEXT NULL,
    resuelta                TINYINT(1) DEFAULT 0,        -- 0=pendiente, 1=resuelta
    fecha_creacion          DATETIME DEFAULT CURRENT_TIMESTAMP,
 
    FOREIGN KEY (id_empresa, id_tipo_riesgo)
        REFERENCES empresa_tipo_riesgo(id_empresa, id_tipo_riesgo)
);

select * from regla_pendiente;

CREATE TABLE tasa (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_empresa INT NOT NULL,
    id_tipo_riesgo INT NOT NULL,
    anio_inicio INT NOT NULL,
    anio_fin INT NOT NULL,
    es_0km TINYINT(1) NOT NULL DEFAULT 0,
    tasa DECIMAL(20,14) NOT NULL,
    FOREIGN KEY (id_empresa, id_tipo_riesgo)
        REFERENCES empresa_tipo_riesgo(id_empresa, id_tipo_riesgo)
);

select * from tasa;

select  e.nombre_empresa, tp.nombre_riesgo, t.anio_inicio, t.anio_fin, t.es_0km, t.tasa from tasa t
join empresa e ON t.id_empresa = e.id_empresa
join tipo_riesgo tp ON t.id_tipo_riesgo = tp.id_tipo_riesgo
where e.id_empresa = 2 order by tp.id_tipo_riesgo asc;

SELECT DISTINCT anio_inicio, anio_fin, es_0km
        FROM tasa
        ORDER BY anio_inicio DESC, es_0km DESC;


CREATE TABLE valor_vehiculo (
    id_valor INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_modelo INT NOT NULL,
    anio INT DEFAULT NULL, -- NULL si es VRN
    valor DECIMAL(12,2) NOT NULL,
    tipo_valor ENUM('VRN','HISTORICO') NOT NULL DEFAULT 'VRN',
    FOREIGN KEY (id_modelo) REFERENCES modelo(id_modelo)
);

select * from regla_clasificacion ORDER BY ID_REGLA_CLASIFICACION DESC;

ALTER TABLE regla_clasificacion AUTO_INCREMENT = 3;

CREATE TABLE cobertura_empresa (
    id_cobertura        INT AUTO_INCREMENT PRIMARY KEY,
    id_empresa          INT NOT NULL UNIQUE,
    rc_terceros         VARCHAR(100) DEFAULT NULL,
    rc_ocupantes        VARCHAR(100) DEFAULT NULL,
    acc_muerte          VARCHAR(100) DEFAULT NULL,
    acc_invalidez       VARCHAR(100) DEFAULT NULL,
    acc_curacion        VARCHAR(100) DEFAULT NULL,
    acc_sepelio         VARCHAR(100) DEFAULT NULL,
    acc_estetica        VARCHAR(100) DEFAULT NULL,
    gps                 VARCHAR(50)  DEFAULT NULL,
    defensa_juridica    VARCHAR(100) DEFAULT NULL,
    auxilio_mecanico    VARCHAR(150) DEFAULT NULL,
    veh_reemplazo       VARCHAR(150) DEFAULT NULL,
    chofer_reemplazo    VARCHAR(100) DEFAULT NULL,
    alcoholemia         VARCHAR(100) DEFAULT NULL,
    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,
 
    FOREIGN KEY (id_empresa) REFERENCES empresa(id_empresa) ON DELETE CASCADE
);

SELECT * FROM COBERTURA_EMPRESA;

CREATE TABLE cobertura_deducibles (
    id_deducible        INT AUTO_INCREMENT PRIMARY KEY,
    id_empresa          INT NOT NULL,
    id_tipo_riesgo      INT NOT NULL,
    deducible_evento    TEXT DEFAULT NULL,
    deducible_taller    TEXT DEFAULT NULL,
    deducible_robo      TEXT DEFAULT NULL,
    deducible_musicales TEXT DEFAULT NULL,
    deducible_veh_reemplazo TEXT DEFAULT NULL,
    deducible_lunas     TEXT DEFAULT NULL,
    deducible_conductores TEXT DEFAULT NULL,
    
    UNIQUE KEY uk_empresa_riesgo (id_empresa, id_tipo_riesgo),
    FOREIGN KEY (id_empresa)     REFERENCES empresa(id_empresa),
    FOREIGN KEY (id_tipo_riesgo) REFERENCES tipo_riesgo(id_tipo_riesgo)
);
 
-- Datos Rimac (id_empresa=1)
-- id_tipo_riesgo: 2=BR1, 3=BR2, 4=BR2., 7=AR1, 8=AR2, 9=CH-H, 10=CH-H-PK, 11=PK
INSERT INTO cobertura_deducibles
    (id_empresa, id_tipo_riesgo, deducible_evento, deducible_taller, deducible_robo)
VALUES
(1, 2,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 200.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 15.00% del monto a indemnizar, mínimo US$ 150.00',
 'Robo Parcial 20% del monto a indemnizar, mínimo US$ 200.00'),
(1, 3,
 'Por evento 15.00% del monto a indemnizar, mínimo US$ 150.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 10.00% del monto a indemnizar, mínimo US$ 150.00',
 'Robo Parcial 15% del monto a indemnizar, mínimo US$ 150.00'),
(1, 4,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 200.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 15.00% del monto a indemnizar, mínimo US$ 150.00',
 NULL),
(1, 7,
 'Por evento 15.00% del monto a indemnizar, mínimo US$ 150.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 10.00% del monto a indemnizar, mínimo US$ 150.00',
 'Robo Parcial 15% del monto a indemnizar, mínimo US$ 150.00'),
(1, 8,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 200.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 15.00% del monto a indemnizar, mínimo US$ 150.00',
 'Robo Parcial 20% del monto a indemnizar, mínimo US$ 200.00'),
(1, 9,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 200.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 20.00% del monto a indemnizar, mínimo US$ 150.00',
 NULL),
(1, 10,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 200.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 20.00% del monto a indemnizar, mínimo US$ 150.00',
 NULL),
(1, 11,
 'Por evento 20.00% del monto a indemnizar, mínimo US$ 250.00, en talleres afiliados',
 'Siniestros atendidos en red de talleres afiliados multimarca 20.00% del monto a indemnizar, mínimo US$ 200.00',
 'Robo Parcial 20% del monto a indemnizar, mínimo US$ 200.00');
 
-- Talleres Mapfre, Pacífico y La Positiva: pendiente ingresar datos
 
 
-- 2. Cotizaciones guardadas
CREATE TABLE cotizacion_guardada (
    id_cotizacion_guardada INT AUTO_INCREMENT PRIMARY KEY,
    numero_cotizacion      VARCHAR(30)  NOT NULL UNIQUE,
    fecha_cotizacion       DATE         NOT NULL DEFAULT (CURRENT_DATE),
    nombre_cliente         VARCHAR(200) DEFAULT NULL,
    dni_ruc                VARCHAR(20)  DEFAULT NULL,
    placa                  VARCHAR(20)  DEFAULT NULL,
    email                  VARCHAR(150) DEFAULT NULL,
    id_modelo              INT          NOT NULL,
    anio_fabricacion       INT          NOT NULL,
    suma_asegurada         DECIMAL(12,2) NOT NULL,
    editado_manualmente    TINYINT(1)   DEFAULT 0,
    observaciones          TEXT         DEFAULT NULL,
    fecha_creacion         DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_modelo) REFERENCES modelo(id_modelo)
);
 
 
-- 3. Detalle por empresa de cada cotización
-- ── CORREGIDO: FK apunta a id_cotizacion_guardada (no a 'id') ──────────────
CREATE TABLE cotizacion_detalle (
    id_cotizacion_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_cotizacion         INT NOT NULL,
    id_empresa            INT NOT NULL,
    tipo_riesgo           VARCHAR(100)   DEFAULT NULL,
    tasa                  DECIMAL(20,14) DEFAULT NULL,
    prima_anual           DECIMAL(12,2)  DEFAULT NULL,
    prima_editada         TINYINT(1)     DEFAULT 0,
    asegurable            TINYINT(1)     DEFAULT 1,
    FOREIGN KEY (id_cotizacion)
        REFERENCES cotizacion_guardada(id_cotizacion_guardada) ON DELETE CASCADE,
    FOREIGN KEY (id_empresa)
        REFERENCES empresa(id_empresa)
);


SELECT mo.id_modelo, ma.nombre_marca, mo.nombre_modelo, mo.comentario
        FROM modelo mo
        JOIN marca ma ON mo.id_marca = ma.id_marca
        WHERE 1=1;
        
select mo.id_modelo, mo.nombre_modelo from modelo mo join marca ma ON mo.id_marca = ma.id_marca
WHERE ma.id_marca ="1";


SELECT rv.id_regla_clasificacion, e.nombre_empresa, tr.nombre_riesgo, m.nombre_marca,
               mo.nombre_modelo, rv.anio_inicio, rv.anio_fin, rv.suma_min, rv.suma_max, rv.nota_regla
        FROM regla_clasificacion rv
        JOIN empresa e ON rv.id_empresa = e.id_empresa
        JOIN tipo_riesgo tr ON rv.id_tipo_riesgo = tr.id_tipo_riesgo
        JOIN marca m ON rv.id_marca = m.id_marca
        LEFT JOIN modelo mo ON rv.id_modelo = mo.id_modelo
        WHERE 1=1