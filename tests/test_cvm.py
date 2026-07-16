"""Audited Brazil — CVM DFP bulk. The load-bearing rules, each pinned:
ÚLTIMO-only, MIL scaling, consolidated-over-individual, cost negation,
FCA trading-code resolve, multi-year accumulation into ONE raw frame."""

from __future__ import annotations

import io
import zipfile

import duckdb
import pandas as pd

from crible.providers.cvm import parse_dfp, resolve_cvm

CNPJ_BB = "00.000.000/0001-91"
CNPJ_IND = "11.111.111/0001-11"

DFP_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)


def _dfp_line(cnpj, ordem, period, code, value, escala="MIL") -> str:
    return (
        f"{cnpj};{period};1;X;001;DF;REAL;{escala};{ordem};"
        f"{period[:4]}-01-01;{period};{code};D;{value};S"
    )


def _zip(members: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        for name, body in members.items():
            bundle.writestr(name, body.encode("latin-1"))
    buf.seek(0)
    return buf


def _dfp_zip(year=2024) -> io.BytesIO:
    dre_con = "\n".join([
        DFP_HEADER,
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "3.01", "1000"),
        _dfp_line(CNPJ_BB, "PENÚLTIMO", f"{year - 1}-12-31", "3.01", "999999"),  # dropped
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "3.02", "-400"),  # negated cost
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "3.11", "50"),
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "3.11.01", "45"),  # outranks 3.11
    ])
    dre_ind = "\n".join([
        DFP_HEADER,
        # BB files consolidated too → this line must lose
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "3.01", "7"),
        # IND-only filer → kept
        _dfp_line(CNPJ_IND, "ÚLTIMO", f"{year}-12-31", "3.01", "111"),
    ])
    bpa_con = "\n".join([
        DFP_HEADER,
        _dfp_line(CNPJ_BB, "ÚLTIMO", f"{year}-12-31", "1", "9000", escala="UNIDADE"),
    ])
    return _zip({
        f"dfp_cia_aberta_DRE_con_{year}.csv": dre_con,
        f"dfp_cia_aberta_DRE_ind_{year}.csv": dre_ind,
        f"dfp_cia_aberta_BPA_con_{year}.csv": bpa_con,
        f"dfp_cia_aberta_{year}.csv": "meta;file",  # non-statement member ignored
    })


FCA_HEADER = (
    "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;"
    "Valor_Mobiliario;Sigla_Classe_Acao_Preferencial;Classe_Acao_Preferencial;"
    "Codigo_Negociacao;Composicao_BDR_Unit;Mercado;Sigla_Entidade_Administradora;"
    "Entidade_Administradora;Data_Inicio_Negociacao;Data_Fim_Negociacao;Segmento;"
    "Data_Inicio_Listagem;Data_Fim_Listagem"
)


def _fca_zip() -> io.BytesIO:
    rows = "\n".join([
        FCA_HEADER,
        f"{CNPJ_BB};2025-01-01;1;1;BB;Ações;;;BBAS3;;Bolsa;B3;B3;2006-05-31;;NM;1977-07-20;",
        f"{CNPJ_IND};2025-01-01;1;2;IND;Ações;;;INDL4;;Bolsa;B3;B3;2010-01-01;;NM;2010-01-01;",
        # delisted line (Data_Fim_Negociacao set) never matches
        f"{CNPJ_IND};2025-01-01;1;3;IND;Ações;;;DEAD3;;Bolsa;B3;B3;2010-01-01;2020-01-01;NM;;",
    ])
    return _zip({"fca_cia_aberta_valor_mobiliario_2025.csv": rows})


def test_parse_dfp_pins_the_ground_rules(tmp_path) -> None:
    path = tmp_path / "dfp.zip"
    path.write_bytes(_dfp_zip().getvalue())
    frames = parse_dfp(path, {CNPJ_BB, CNPJ_IND})

    income = frames[CNPJ_BB][("income", "annual")].set_index("period")
    assert income.loc["2024-12-31", "TotalRevenue"] == 1_000_000.0  # MIL ×1000, con wins
    assert "2023-12-31" not in income.index  # PENÚLTIMO dropped
    assert income.loc["2024-12-31", "CostOfRevenue"] == 400_000.0  # negated positive
    assert income.loc["2024-12-31", "NetIncome"] == 45_000.0  # 3.11.01 outranks 3.11

    balance = frames[CNPJ_BB][("balance", "annual")].set_index("period")
    assert balance.loc["2024-12-31", "TotalAssets"] == 9000.0  # UNIDADE: no scaling

    ind = frames[CNPJ_IND][("income", "annual")].set_index("period")
    assert ind.loc["2024-12-31", "TotalRevenue"] == 111_000.0  # ind fills con-less filers


def test_resolve_cvm_maps_trading_codes(tmp_path) -> None:
    path = tmp_path / "fca.zip"
    path.write_bytes(_fca_zip().getvalue())
    mapping, unmatched = resolve_cvm(["BBAS3.SA", "INDL4.SA", "DEAD3.SA", "ZZZZ9.SA"], path)
    assert mapping == {"BBAS3.SA": CNPJ_BB, "INDL4.SA": CNPJ_IND}
    assert unmatched == ["DEAD3.SA", "ZZZZ9.SA"]  # delisted line + unknown


class _MultiHttp:
    """URL-keyed fake for fetch_if_stale (the _ZipHttp pattern, several files)."""

    def __init__(self, bodies: dict[str, bytes]) -> None:
        self.bodies = bodies

    def stream(self, method, url, headers=None):
        for fragment, body in self.bodies.items():
            if fragment in url:
                return _Resp(body)
        return _Resp(b"", status=404)


class _Resp:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.status_code = status
        self._body = body
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _seed_br_universe(tmp_path, monkeypatch) -> None:
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, pd.DataFrame([
        {"symbol": "BBAS3.SA", "name": "BB", "country": "Brazil", "sector": "F",
         "industry": "B", "exchange": "SAO", "currency": "BRL",
         "market_cap": "Large Cap", "isin": None},
    ]))
    con.close()


def test_run_cvm_accumulates_years_into_one_frame(tmp_path, monkeypatch) -> None:
    """Two yearly ZIPs → ONE income frame holding both periods (per-year
    writes would shadow each other in the newest-file raw layer)."""
    from crible.ingest.enrichment import run_cvm

    _seed_br_universe(tmp_path, monkeypatch)
    http = _MultiHttp({
        "fca_cia_aberta": _fca_zip().getvalue(),
        "dfp_cia_aberta_2024": _dfp_zip(2024).getvalue(),
        "dfp_cia_aberta_2025": _dfp_zip(2025).getvalue(),
        "dfp_cia_aberta_2026": _dfp_zip(2026).getvalue(),
    })
    outcome = run_cvm(years=3, limit=10, http=http)
    assert outcome["enriched"] == 1 and outcome["skipped"] is None

    files = sorted(tmp_path.glob("raw/provider=cvm/symbol=BBAS3.SA/income-annual-*.parquet"))
    assert len(files) == 1
    income = pd.read_parquet(files[-1]).set_index("period")
    assert {"2024-12-31", "2025-12-31", "2026-12-31"} <= set(income.index)

    # steady state: identical re-run re-stamps nothing (skip_identical)
    again = run_cvm(years=3, limit=10, http=http)
    assert again["enriched"] == 1
    assert sorted(tmp_path.glob("raw/provider=cvm/symbol=BBAS3.SA/income-annual-*.parquet")) == files


def test_run_cvm_limit_zero_is_a_pure_noop(tmp_path, monkeypatch) -> None:
    from crible.ingest.enrichment import run_cvm

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    assert run_cvm(limit=0) == {"enriched": 0, "unmatched": 0, "outage": None,
                                "skipped": "limit 0"}
    assert not (tmp_path / "mirror").exists()