-- See: https://docs.voltdb.com/UsingVoltDB/ChapDesignSchema.php
CREATE TABLE Hero (
    HeroID INTEGER UNIQUE NOT NULL,
    Name VARCHAR(15),
    PRIMARY KEY(HeroID)
);

-- See: https://docs.voltdb.com/UsingVoltDB/DesignCodeFreeProcs.php
CREATE PROCEDURE LookUpHero AS
    SELECT HeroID, Name FROM Hero WHERE HeroID = ?;
