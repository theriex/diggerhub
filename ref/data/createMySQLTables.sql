CREATE TABLE DigAcc (  -- Digger Hub access account
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  email VARCHAR(256) NOT NULL UNIQUE,
  phash VARCHAR(256) NOT NULL,
  status VARCHAR(256),
  actsends LONGTEXT,
  actcode VARCHAR(256),
  lastsync VARCHAR(256),
  firstname VARCHAR(256) NOT NULL,
  hashtag undefined UNIQUE,
  kwdefs LONGTEXT,
  igfolds LONGTEXT,
  settings LONGTEXT,
  PRIMARY KEY (dsId)
);
ALTER TABLE DigAcc AUTO_INCREMENT = 2020;

CREATE TABLE Song (  -- Rating and play information
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  aid BIGINT NOT NULL,
  path LONGTEXT,
  ti VARCHAR(256) NOT NULL,
  ar VARCHAR(256),
  ab VARCHAR(256),
  el INT,
  al INT,
  kws VARCHAR(256),
  rv INT,
  fq VARCHAR(256),
  lp VARCHAR(256),
  nt LONGTEXT,
  PRIMARY KEY (dsId)
);
ALTER TABLE Song AUTO_INCREMENT = 2020;

