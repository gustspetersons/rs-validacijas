# Definīcijas, kas kopīgas analīzei (Rigas_satiksmes_validacijas_2026-06.ipynb)
# un datu sagatavošanai Power BI modelim (sagatavot_powerbi_datus.py)
import re

DIENU_NOSAUKUMI = {
    "Monday": "Pirmdiena",
    "Tuesday": "Otrdiena",
    "Wednesday": "Trešdiena",
    "Thursday": "Ceturtdiena",
    "Friday": "Piektdiena",
    "Saturday": "Sestdiena",
    "Sunday": "Svētdiena",
}


# vietu nosaukumi, kas avotā uzrakstīti kļūdaini, un to pareizā rakstība
VIETU_LABOJUMI = {
    "Ziepnniekkalns": "Ziepniekkalns",
    "Jaunmarupe": "Jaunmārupe",
    "TEC2": "TEC 2",
    "Centr": "Centrs",
    "Pētersalas": "Pētersala",
}


# sadala maršruta nosaukumu vietās pie defisēm un domuzīmēm, izmetot liekās
# atstarpes: „Imanta  - Jugla” → [„Imanta”, „Jugla”]
def vietu_saraksts(marsruta_nosaukums):
    return [" ".join(v.split()) for v in re.split(r"\s*[-–]+\s*", marsruta_nosaukums)]


# izlabo vietu rakstību un savieno vietas ar domuzīmi bez atstarpēm („Imanta–Jugla”)
# vai ar atstarpēm, ja vietu ir vairāk nekā divas vai kādā vietā ir vairāki vārdi
def tirit(marsruta_nosaukums):
    vietas = [VIETU_LABOJUMI.get(v, v) for v in vietu_saraksts(marsruta_nosaukums)]
    ar_atstarpem = len(vietas) > 2 or any(" " in v for v in vietas)
    atdalitajs = " – " if ar_atstarpem else "–"
    return atdalitajs.join(vietas)


KOMENTARI = {
    "2026-06-06": (
        "1. gadatirgus diena: atsevišķs maršruts A 71; "
        "pastiprināti Tr 31, A 28, A 29; četrsekciju Tm 1"
    ),
    "2026-06-07": "2. gadatirgus diena + pirmā saulainā vasaras nedēļas nogales diena",
    "2026-06-11": "LVĢMC oranžais brīdinājums par negaisu",
    "2026-06-20": "sestdiena pirms Jāņiem",
    "2026-06-22": "pirmdiena kā pārceltā brīvdiena",
    "2026-06-23": (
        "Līgo — svētku diena, Rīgas satiksmes sabiedriskais transports bez maksas"
    ),
    "2026-06-24": (
        "Jāņi — svētku diena, Rīgas satiksmes sabiedriskais transports bez maksas"
    ),
    "2026-06-26": "kruīza kuģis pie Krievu salas; vienreizējs maršruts A 95",
    "2026-06-27": "sestdiena kā pārceltā darbdiena (saīsināta)",
    "2026-06-29": (
        "pirmā darbdiena pēc Jāņu svētku nedēļas, "
        "validācijas ~16 % zem pirmssvētku darbdienu līmeņa"
    ),
    "2026-06-30": (
        "otrā darbdiena pēc Jāņu svētku nedēļas, "
        "validācijas ~16 % zem pirmssvētku darbdienu līmeņa"
    ),
}
DIENU_TIPI = {
    "2026-06-22": "brīvdiena",
    "2026-06-23": "svētku diena",
    "2026-06-24": "svētku diena",
    "2026-06-27": "darbdiena",
}


# dienas tips: izņēmums no DIENU_TIPI vai, ja tāda nav, pēc nedēļas dienas
# (weekday(): pirmdiena 0, …, sestdiena 5, svētdiena 6)
def dienas_tips(datums):
    pec_nedelas_dienas = "nogales diena" if datums.weekday() >= 5 else "darbdiena"
    return DIENU_TIPI.get(datums.strftime("%Y-%m-%d"), pec_nedelas_dienas)


# kalendāra komentārs; tukša virkne, ja datumam komentāra nav
def komentars(datums):
    return KOMENTARI.get(datums.strftime("%Y-%m-%d"), "")


# analīzes periods: 1.–19. jūnijs
JANU_IETEKMES_SAKUMS = "2026-06-20"


# vizualizācijās izmantotās stundas atspoguļošana tās patiesajā saturā 17 → 17:00–17:59
def stundas_intervals(h):
    return f"{h}:00–{h}:59"
