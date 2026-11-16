#!/usr/bin/env python3
"""Atualiza data/acoes.csv com os dados dos tickers listados em tickers.txt.

Colunas geradas (separador ; e vírgula decimal, para o Google Sheets em português):
ticker, dy_12m, lpa, dpa, payout, n_papeis, lucro_projetivo, atualizado_em
"""
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

RAIZ = Path(__file__).parent
SAIDA = RAIZ / "data" / "acoes.csv"
CAMPOS = ["ticker", "dy_12m", "lpa", "dpa", "payout",
          "n_papeis", "lucro_projetivo", "atualizado_em"]


def br(valor, casas):
    """Formata número com vírgula decimal (vazio se não houver valor)."""
    if valor is None or pd.isna(valor):
        return ""
    return f"{valor:.{casas}f}".replace(".", ",")


def coletar(ticker):
    t = yf.Ticker(f"{ticker}.SA")
    info = t.info or {}
    preco = info.get("currentPrice") or info.get("regularMarketPrice")
    lpa = info.get("trailingEps")            # lucro por ação dos últimos 12 meses
    papeis = info.get("sharesOutstanding")   # número de ações

    # DPA = soma dos proventos pagos nos últimos 12 meses
    dpa = 0.0
    divs = t.dividends
    if divs is not None and len(divs):
        corte = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
        dpa = float(divs[divs.index >= corte].sum())

    dy = dpa / preco if preco else None
    payout = dpa / lpa if lpa and lpa > 0 else 0.0
    lucro = lpa * papeis if lpa is not None and papeis else None

    return {
        "ticker": ticker,
        "dy_12m": br(dy, 4),
        "lpa": br(lpa, 2),
        "dpa": br(dpa, 2),
        "payout": br(payout, 4),
        "n_papeis": br(papeis, 0),
        "lucro_projetivo": br(lucro, 0),
        "atualizado_em": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def ler_antigo():
    if not SAIDA.exists():
        return {}
    with open(SAIDA, encoding="utf-8", newline="") as f:
        return {l["ticker"]: l for l in csv.DictReader(f, delimiter=";")}


def main():
    tickers = [l.strip().upper() for l in
               (RAIZ / "tickers.txt").read_text().splitlines() if l.strip()]
    antigo = ler_antigo()
    linhas, falhas = [], 0
    for tk in tickers:
        try:
            linhas.append(coletar(tk))
            print(f"ok    {tk}")
        except Exception as e:  # mantém a linha antiga se der erro
            falhas += 1
            print(f"ERRO  {tk}: {e}", file=sys.stderr)
            linhas.append(antigo.get(tk, {"ticker": tk}))
        time.sleep(1)

    if falhas == len(tickers):
        sys.exit("Nenhum ticker atualizado; arquivo mantido.")

    SAIDA.parent.mkdir(exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", restval="")
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
