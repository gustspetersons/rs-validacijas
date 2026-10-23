# Izveido RS_validacijas_2026-06.duckdb no data.gov.lv lejupielādētajiem failiem:
# ValidacijuDati06_2026/*.txt (e-taloni, viens fails dienā) un *.csv (lietotnes)
import duckdb

with duckdb.connect("RS_validacijas_2026-06.duckdb") as con:
    con.sql(
        "CREATE OR REPLACE TABLE etaloni AS "
        "SELECT * FROM read_csv('ValidacijuDati06_2026/*.txt')"
    )
    con.sql(
        "CREATE OR REPLACE TABLE lietotnes AS "
        "SELECT * FROM read_csv('ValidacijuDati06_2026/*.csv')"
    )
    for tabula in ["etaloni", "lietotnes"]:
        rindas = con.sql(f"SELECT count(*) FROM {tabula}").fetchone()[0]
        print(f"{tabula}: {rindas:,} rindas".replace(",", " "))
