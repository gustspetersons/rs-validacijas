# Sagatavo Power BI modeļa datus: no RS_validacijas_2026-06.duckdb izveido piecus
# Parquet failus mapē powerbi/dati/. Palaid repozitorija mapē tāpat kā
# izveidot_datubazi.py: python sagatavot_powerbi_datus.py
#
# Zvaigznes shēma: divas faktu tabulas, katra savā detalizācijā (etaloni: viena
# rinda = viena validācija; lietotnes: datums × stunda × maršruts), un trīs kopīgas
# dimensijas (maršruti, datumi, stundas). Maršrutu nosaukumus, dienu tipus, komentārus
# un analīzes periodu nosaka definicijas.py, tāpat kā analīzē.
from pathlib import Path

import duckdb
from duckdb.sqltypes import BIGINT, DATE, VARCHAR

from definicijas import (
    DIENU_NOSAUKUMI,
    JANU_IETEKMES_SAKUMS,
    dienas_tips,
    komentars,
    stundas_intervals,
    tirit,
)

DB_PATH = "RS_validacijas_2026-06.duckdb"
OUT_DIR = Path("powerbi") / "dati"
REQUIRED_COLUMNS = {
    "etaloni": {
        "Laiks",
        "TranspVeids",
        "TMarsruts",
        "MarsrNos",
        "Parks",
        "GarNr",
        "Virziens",
        "ValidTalonaId",
    },
    "lietotnes": {"Datums", "Stunda", "Transports", "Marsruts", "Skaits"},
}

# pirmdiena … svētdiena, weekday() secībā
DIENAS = list(DIENU_NOSAUKUMI.values())
MENESI = [
    "janvāris",
    "februāris",
    "marts",
    "aprīlis",
    "maijs",
    "jūnijs",
    "jūlijs",
    "augusts",
    "septembris",
    "oktobris",
    "novembris",
    "decembris",
]


# nosaukumi pēc indeksa, nevis strftime("%A"), kas atkarīgs no datora valodas
def nedelas_diena(datums):
    return DIENAS[datums.weekday()]


def menesis(datums):
    return MENESI[datums.month - 1]


# piem., „1.–19. jūnijs”
def perioda_nosaukums(sakums, beigas):
    return f"{sakums.day}.–{beigas.day}. {menesis(beigas)}"


# Python funkcijas, ko SQL vaicājumi izsauc ar to pašu nosaukumu
SQL_FUNCTIONS = [
    (tirit, [VARCHAR]),
    (dienas_tips, [DATE]),
    (komentars, [DATE]),
    (stundas_intervals, [BIGINT]),
    (nedelas_diena, [DATE]),
    (menesis, [DATE]),
    (perioda_nosaukums, [DATE, DATE]),
]

# maršruta atslēga = transportlīdzekļa veids + numurs, kā analīzē; nosaukums ir
# agrākais, ko maršruts jūnijā „nēsāja”, pēc tīrīšanas ar tirit()
MARSRUTI_SQL = r"""
CREATE TABLE marsruti AS
WITH et AS (
    SELECT
        TranspVeids AS transports,
        string_split(trim(TMarsruts), ' ')[-1] AS numurs,
        TMarsruts AS kods,
        arg_min(MarsrNos, Laiks) AS nosaukums
    FROM rs.etaloni
    GROUP BY ALL
),
liet AS (
    SELECT DISTINCT Transports AS transports, CAST(Marsruts AS VARCHAR) AS numurs
    FROM rs.lietotnes
)
SELECT
    row_number() OVER (
        ORDER BY
            transports,
            numurs LIKE 'N%',
            try_cast(regexp_extract(numurs, '\d+') AS INTEGER),
            numurs
    ) AS id,
    transports,
    numurs,
    kods,
    tirit(nosaukums) AS nosaukums
FROM et
FULL JOIN liet USING (transports, numurs)
"""

ETALONI_SQL = """
SELECT
    CAST(e.Laiks AS DATE) AS "Datums",
    CAST(hour(e.Laiks) AS INTEGER) AS "Stunda",
    m.id AS "Maršruta ID",
    e.Parks AS "Parks",
    e.GarNr AS "Transportlīdzekļa identifikators",
    CASE e.Virziens
        WHEN 'Forth' THEN 'turp'
        WHEN 'Back' THEN 'atpakaļ'
        ELSE e.Virziens
    END AS "Virziens",
    e.ValidTalonaId AS "E-talona identifikators"
FROM rs.etaloni AS e
JOIN marsruti AS m
    ON m.transports = e.TranspVeids
    AND m.kods = e.TMarsruts
"""

LIETOTNES_SQL = """
SELECT
    CAST(l.Datums AS DATE) AS "Datums",
    CAST(left(l.Stunda, 2) AS INTEGER) AS "Stunda",
    m.id AS "Maršruta ID",
    l.Skaits AS "Validāciju skaits"
FROM rs.lietotnes AS l
JOIN marsruti AS m
    ON m.transports = l.Transports
    AND m.numurs = CAST(l.Marsruts AS VARCHAR)
"""

MARSRUTU_DIMENSIJA_SQL = """
SELECT
    id AS "Maršruta ID",
    kods AS "Maršruta kods",
    transports AS "Transportlīdzekļa veids",
    numurs AS "Maršruta numurs",
    nosaukums AS "Maršruta nosaukums",
    kods || ' · ' || nosaukums AS "Maršruts",
    CASE WHEN numurs LIKE 'N%' THEN 'jā' ELSE 'nē' END AS "Nakts maršruts"
FROM marsruti
ORDER BY id
"""

# kalendārs aptver pilnus gadus (Power BI prasība datumu tabulai); dienu tipi,
# komentāri un periodi ir pārbaudīti tikai mēnesim ar datiem, ārpus tā tie ir tukši
DATUMI_SQL = f"""
WITH faktu_datumi AS (
    SELECT CAST(Laiks AS DATE) AS d FROM rs.etaloni
    UNION ALL
    SELECT CAST(Datums AS DATE) FROM rs.lietotnes
),
robezas AS (
    SELECT
        min(d) AS pirmais,
        max(d) AS pedejais,
        DATE '{JANU_IETEKMES_SAKUMS}' AS janu_sakums
    FROM faktu_datumi
),
dienas AS (
    SELECT
        CAST(
            unnest(
                generate_series(
                    make_date(year(pirmais), 1, 1),
                    make_date(year(pedejais), 12, 31),
                    INTERVAL 1 DAY
                )
            ) AS DATE
        ) AS d,
        *
    FROM robezas
)
SELECT
    d AS "Datums",
    year(d) AS "Gads",
    month(d) AS "Mēneša numurs",
    menesis(d) AS "Mēnesis",
    day(d) AS "Mēneša diena",
    isodow(d) AS "Nedēļas dienas numurs",
    nedelas_diena(d) AS "Diena",
    CAST(date_trunc('week', d) AS DATE) + 6 AS "Nedēļa līdz",
    CASE WHEN d BETWEEN pirmais AND pedejais THEN dienas_tips(d) END AS "Dienas tips",
    CASE
        WHEN d BETWEEN pirmais AND pedejais THEN nullif(komentars(d), '')
    END AS "Komentārs",
    CASE
        WHEN d NOT BETWEEN pirmais AND pedejais THEN NULL
        WHEN d < janu_sakums THEN perioda_nosaukums(pirmais, janu_sakums - 1)
        ELSE perioda_nosaukums(janu_sakums, pedejais)
    END AS "Periods"
FROM dienas
ORDER BY d
"""

STUNDAS_SQL = """
SELECT CAST(h AS INTEGER) AS "Stunda", stundas_intervals(h) AS "Stundas intervāls"
FROM range(24) AS t(h)
"""

EXPORTS = {
    "etaloni": ETALONI_SQL,
    "lietotnes": LIETOTNES_SQL,
    "marsruti": MARSRUTU_DIMENSIJA_SQL,
    "datumi": DATUMI_SQL,
    "stundas": STUNDAS_SQL,
}


def parquet_path(name):
    return f"'{(OUT_DIR / f'{name}.parquet').as_posix()}'"


with duckdb.connect() as con:
    # avots pievienots tikai lasīšanai; darba tabula marsruti paliek atmiņā
    con.execute(f"ATTACH '{DB_PATH}' AS rs (READ_ONLY)")

    for table, required in REQUIRED_COLUMNS.items():
        columns = con.execute(
            "SELECT column_name FROM duckdb_columns() "
            "WHERE database_name = 'rs' AND table_name = ?",
            [table],
        ).fetchall()
        actual = {column[0] for column in columns}
        assert actual, f"Datubāzē nav tabulas {table}"
        missing = required - actual
        message = f"{table}: trūkst kolonnu {sorted(missing)}; ir {sorted(actual)}"
        assert not missing, message

    for function, parameters in SQL_FUNCTIONS:
        con.create_function(function.__name__, function, parameters, VARCHAR)

    con.execute(MARSRUTI_SQL)

    # katrs lietotņu datu maršruts ir arī e-talonu datos, tāpēc nosaukums ir visiem
    bez_nosaukuma = con.sql(
        "SELECT count(*) FROM marsruti WHERE nosaukums IS NULL"
    ).fetchone()[0]
    assert bez_nosaukuma == 0, f"{bez_nosaukuma} maršrutiem nav nosaukuma"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, query in EXPORTS.items():
        con.execute(f"COPY ({query}) TO {parquet_path(name)} (FORMAT parquet)")

    # eksportā validācijas nav ne pazudušas, ne divkāršojušās
    kopsummas = {
        "E-talonu validācijas": (
            "SELECT count(*) FROM rs.etaloni",
            f"SELECT count(*) FROM {parquet_path('etaloni')}",
        ),
        "Lietotņu validācijas": (
            "SELECT sum(Skaits) FROM rs.lietotnes",
            f'SELECT sum("Validāciju skaits") FROM {parquet_path("lietotnes")}',
        ),
    }
    for label, (source_query, export_query) in kopsummas.items():
        source = con.sql(source_query).fetchone()[0]
        exported = con.sql(export_query).fetchone()[0]
        assert source == exported, f"{label}: avotā {source}, eksportā {exported}"
        print(f"{label}: {source:,}".replace(",", " "))

    for name in EXPORTS:
        row_count = con.sql(f"SELECT count(*) FROM {parquet_path(name)}").fetchone()[0]
        print(f"{name}.parquet: {row_count:,} rindas".replace(",", " "))
