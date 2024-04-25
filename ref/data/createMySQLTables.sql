CREATE TABLE DigAcc (  -- Digger Hub access account
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  email VARCHAR(256) NOT NULL UNIQUE,
  phash VARCHAR(256) NOT NULL,
  hubdat LONGTEXT,
  status VARCHAR(256),
  actsends LONGTEXT,
  actcode VARCHAR(256),
  firstname VARCHAR(256) NOT NULL,
  digname VARCHAR(256) UNIQUE,
  kwdefs LONGTEXT,
  igfolds LONGTEXT,
  settings LONGTEXT,
  musfs LONGTEXT,
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
  smti VARCHAR(256),
  smar VARCHAR(256),
  smab VARCHAR(256),
  el INT,
  al INT,
  kws VARCHAR(256),
  rv INT,
  fq VARCHAR(256),
  nt LONGTEXT,
  lp VARCHAR(256),
  pd VARCHAR(256),
  pc INT,
  srcid BIGINT,
  srcrat VARCHAR(256),
  spid VARCHAR(256),
  PRIMARY KEY (dsId)
);
ALTER TABLE Song AUTO_INCREMENT = 2020;

CREATE TABLE SKeyMap (  -- Song Title/Artist/Album key mappings
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  skey VARCHAR(256) NOT NULL UNIQUE,
  spid VARCHAR(256),
  notes LONGTEXT,
  PRIMARY KEY (dsId)
);
ALTER TABLE SKeyMap AUTO_INCREMENT = 2020;

CREATE TABLE DigMsg (  -- Music communications between DigAccs
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  sndr BIGINT NOT NULL,
  rcvr BIGINT NOT NULL,
  msgtype VARCHAR(256) NOT NULL,
  status VARCHAR(256) NOT NULL,
  srcmsg BIGINT,
  songid BIGINT,
  ti VARCHAR(256) NOT NULL,
  ar VARCHAR(256),
  ab VARCHAR(256),
  nt LONGTEXT,
  PRIMARY KEY (dsId)
);
ALTER TABLE DigMsg AUTO_INCREMENT = 2020;

CREATE TABLE SASum (  -- Song activity summary, e.g. weekly top20
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  aid BIGINT NOT NULL,
  digname VARCHAR(256),
  sumtype VARCHAR(256) NOT NULL,
  songs LONGTEXT,
  easiest LONGTEXT,
  hardest LONGTEXT,
  chillest LONGTEXT,
  ampest LONGTEXT,
  start VARCHAR(256),
  end VARCHAR(256),
  ttlsongs INT,
  PRIMARY KEY (dsId)
);
ALTER TABLE SASum AUTO_INCREMENT = 2020;

CREATE TABLE AppService (  -- Processing service access
  dsId BIGINT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  created VARCHAR(256) NOT NULL,
  modified VARCHAR(256) NOT NULL,
  batchconv VARCHAR(256),
  name VARCHAR(256) NOT NULL UNIQUE,
  ckey VARCHAR(256),
  csec VARCHAR(256),
  data LONGTEXT,
  PRIMARY KEY (dsId)
);
ALTER TABLE AppService AUTO_INCREMENT = 2020;

