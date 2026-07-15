import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).parent / "portal_data.json"

st.set_page_config(page_title="Investicioni portal", layout="wide")


@st.cache_data
def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


records = load_data()

st.title("Investicioni portal")
st.caption("Pronađite lokacije koje odgovaraju vašim investicionim kriterijumima")

opstine = sorted({r["opstina"] for r in records if r["opstina"]})
sve_vrste = sorted({v for r in records for v in r["vrste_zemljista"]})

VLASNISTVO_LABELS = {
    "Sve": "Sve",
    "privatna": "Privatna",
    "drzavna_javna": "Državna / javna",
    "mesovita": "Mešovita",
}


def dostupne_kulture(opstina: str, vrste: list[str]) -> list[str]:
    """Kulture koje se STVARNO pojavljuju za trenutno izabranu opštinu
    i vrstu/e zemljišta (gleda po delu parcele, ne po celoj parceli,
    jer jedna parcela može imati delove različitih vrsta zemljišta)."""
    kulture = set()

    for record in records:
        if opstina != "Sve" and record["opstina"] != opstina:
            continue

        for deo in record["delovi"]:
            if vrste and deo["vrsta_zemljista"] not in vrste:
                continue
            if deo["kultura"]:
                kulture.add(deo["kultura"])

    return sorted(kulture)


with st.sidebar:
    st.header("Filteri")

    izabrana_opstina = st.selectbox("Opština", ["Sve"] + opstine)

    min_povrsina = st.number_input(
        "Minimalna površina (m²)",
        min_value=0,
        value=0,
        step=50,
    )

    izabrane_vrste = st.multiselect("Vrsta zemljišta", sve_vrste)

    izabrane_kulture = st.multiselect(
        "Kultura",
        dostupne_kulture(izabrana_opstina, izabrane_vrste),
        help="Lista se sužava na osnovu izabrane vrste zemljišta.",
    )

    bez_tereta = st.checkbox("Prikaži samo parcele bez tereta")
    jedan_vlasnik = st.checkbox("Prikaži samo parcele sa jednim imaocem prava")

    vlasnistvo_kljucevi = list(VLASNISTVO_LABELS.keys())
    izabrano_vlasnistvo = st.selectbox(
        "Vlasnička struktura",
        vlasnistvo_kljucevi,
        format_func=lambda key: VLASNISTVO_LABELS[key],
    )


def prolazi_filtere(record: dict) -> bool:
    if izabrana_opstina != "Sve" and record["opstina"] != izabrana_opstina:
        return False

    povrsina = record.get("povrsina_prikaz_m2")
    if isinstance(povrsina, (int, float)):
        if povrsina < min_povrsina:
            return False
    elif min_povrsina > 0:
        return False

    if izabrane_vrste and not (set(izabrane_vrste) & set(record["vrste_zemljista"])):
        return False

    if izabrane_kulture and not (set(izabrane_kulture) & set(record["kulture"])):
        return False

    if bez_tereta and record["ima_tereta"]:
        return False

    if jedan_vlasnik and record["broj_imaoca_prava"] != 1:
        return False

    if izabrano_vlasnistvo != "Sve" and record["vlasnicka_struktura"] != izabrano_vlasnistvo:
        return False

    return True


# Kolone koje mogu imati više vrednosti spojenih zarezom (npr. parcela
# sa 3 dela može imati 3 različite kulture) — za njih prikazujemo pun
# tekst kao tooltip na hover, jer ne staju uvek u širinu ćelije.
TOOLTIP_KOLONE = {"Vrsta zemljišta", "Kultura"}

TABLE_CSS = """
<style>
.rgz-table-wrap {
    max-height: 640px;
    overflow-y: auto;
    border: 1px solid #e6e6e6;
    border-radius: 4px;
}
.rgz-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.rgz-table th, .rgz-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #eee;
    text-align: left;
    white-space: nowrap;
}
.rgz-table th {
    position: sticky;
    top: 0;
    background: #fafafa;
    z-index: 1;
}
.rgz-table td.truncate {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: help;
}
</style>
"""


def render_table(df: pd.DataFrame) -> None:
    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)

    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            text = html.escape(str(row[col]))
            if col in TOOLTIP_KOLONE:
                cells.append(f'<td class="truncate" title="{text}">{text}</td>')
            else:
                cells.append(f"<td>{text}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = (
        TABLE_CSS
        + '<div class="rgz-table-wrap"><table class="rgz-table">'
        + f"<thead><tr>{headers}</tr></thead>"
        + f"<tbody>{''.join(rows)}</tbody>"
        + "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


filtrirano = [r for r in records if prolazi_filtere(r)]

prikaz = pd.DataFrame(
    [
        {
            "Opština": r["opstina"],
            "Broj parcele": r["broj_parcele_prikaz"],
            "Površina m²": r["povrsina_prikaz_m2"],
            "Vrsta zemljišta": ", ".join(r["vrste_zemljista"]),
            "Kultura": ", ".join(r["kulture"]),
            "Broj delova": r["broj_delova"],
            "Broj imalaca prava": r["broj_imaoca_prava"],
            "Vlasnička struktura": VLASNISTVO_LABELS.get(
                r["vlasnicka_struktura"], r["vlasnicka_struktura"]
            ),
            "Ima tereta": "Da" if r["ima_tereta"] else "Ne",
            "Ima napomena": "Da" if r["ima_napomena"] else "Ne",
        }
        for r in filtrirano
    ]
)

render_table(prikaz)
