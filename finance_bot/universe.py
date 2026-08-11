"""
The investable universe: ~250 tickers grouped by theme.

Grouping matters downstream: the "modular mind" (Step 2) uses these theme
buckets as a prior for which stocks *should* be correlated, before it ever
looks at price data. War/defense, AI, quantum, and semiconductors are broken
out explicitly per the project brief.

Edit THEMES to change the universe. Everything else derives from it.
"""

from __future__ import annotations

# theme -> list of tickers. A ticker may appear in several themes; that is
# intentional (PLTR is both defense and AI). `all_tickers()` de-dupes.
THEMES: dict[str, list[str]] = {
    # --- War / defense / military hardware -------------------------------
    "defense": [
        "LMT", "RTX", "NOC", "GD", "BA", "LHX", "HII", "LDOS", "KTOS",
        "AVAV", "HWM", "TDG", "AXON", "BAH", "TXT", "CW", "HEI", "RKLB",
        "OSK", "DRS", "BWXT", "GE", "CACI", "SAIC", "MRCY", "VSEC",
        "TDY", "AIR", "HXL", "CAE", "ESLT", "SPR",
    ],
    # --- Artificial intelligence -----------------------------------------
    "ai": [
        "NVDA", "PLTR", "MSFT", "GOOGL", "META", "AMZN", "AI", "PATH",
        "SNOW", "AMD", "SOUN", "BBAI", "SMCI", "DELL", "ARM", "TSM",
        "NOW", "CRM", "ADBE", "ORCL", "IBM", "APP", "TSLA",
        "RBLX", "U", "CRWV", "NBIS", "DUOL", "TWLO",
    ],
    # --- Quantum computing -----------------------------------------------
    "quantum": [
        "IONQ", "RGTI", "QBTS", "QUBT", "IBM", "GOOGL", "HON", "MSFT",
        "NVDA", "QMCO", "LAES",
    ],
    # --- Semiconductors / chips ------------------------------------------
    "semis": [
        "NVDA", "AMD", "INTC", "TSM", "ASML", "AVGO", "QCOM", "MU", "TXN",
        "ADI", "MRVL", "AMAT", "LRCX", "KLAC", "ON", "NXPI", "MCHP", "STM",
        "TER", "ENTG", "ARM", "SMCI", "WOLF", "GFS", "SWKS", "QRVO",
        "MPWR", "CRUS", "LSCC", "AMKR", "ACLS", "COHR",
        "SLAB", "POWI", "DIOD", "FORM", "ONTO", "CAMT", "NVMI", "AEHR",
        "INDI", "SITM", "UCTT",
    ],
    # --- Big tech / software / platforms ---------------------------------
    "tech": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "ADBE", "CRM",
        "ORCL", "CSCO", "IBM", "NOW", "INTU", "UBER", "SHOP", "SPOT",
        "ABNB", "SNOW", "DDOG", "MDB", "TEAM", "WDAY", "PANW", "ANET",
        "ESTC", "CFLT", "GTLB", "HUBS", "ZM", "DOCU", "RBLX",
    ],
    # --- Cybersecurity ---------------------------------------------------
    "cyber": [
        "CRWD", "PANW", "ZS", "FTNT", "S", "OKTA", "NET", "CYBR", "TENB",
        "QLYS", "RPD", "VRNS",
    ],
    # --- Energy / oil (geopolitics & war supply shocks) ------------------
    "energy": [
        "XOM", "CVX", "COP", "SLB", "OXY", "HAL", "EOG", "PSX", "VLO",
        "MPC", "WMB", "KMI", "LNG", "HES", "DVN", "FANG", "BKR", "CTRA",
        "TRGP", "OKE", "ET", "EPD", "MPLX",
    ],
    # --- Rare earths / materials / supply chain --------------------------
    "materials": [
        "MP", "ALB", "FCX", "NUE", "STLD", "LIN", "APD", "SHW", "CTVA",
    ],
    # --- Financials ------------------------------------------------------
    "financials": [
        "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V",
        "MA", "PYPL", "SPGI", "BX", "KKR", "COF",
        "MET", "PRU", "ICE", "CME", "NDAQ", "TROW",
    ],
    # --- Healthcare / pharma ---------------------------------------------
    "healthcare": [
        "LLY", "UNH", "JNJ", "MRK", "PFE", "ABBV", "TMO", "ABT", "DHR",
        "AMGN", "ISRG", "MRNA", "REGN", "VRTX", "GILD",
        "BSX", "MDT", "SYK", "ZTS", "BMY", "CI",
    ],
    # --- Space / next-gen ------------------------------------------------
    "space": [
        "RKLB", "LUNR", "ASTS", "PL", "ACHR", "JOBY",
    ],
    # --- Crypto-exposed equities -----------------------------------------
    "crypto": [
        "COIN", "MSTR", "MARA", "RIOT", "HOOD", "CLSK",
    ],
    # --- Industrial / consumer bellwethers (macro anchors) ---------------
    "industrial_consumer": [
        "CAT", "DE", "HON", "MMM", "UPS", "WMT", "COST", "HD", "PG", "KO",
        "PEP", "MCD", "NKE", "DIS", "F", "GM", "BA",
        "SBUX", "TGT", "LOW", "BKNG", "TJX",
    ],
    # --- Broad-market / macro reference (benchmarks, not necessarily
    #     traded — used by the mind to detect market-wide moves) ----------
    "benchmarks": [
        "SPY", "QQQ", "IWM", "DIA", "VIXY", "TLT", "GLD", "USO", "XLE",
        "XLK", "XLF", "SMH", "ITA", "HACK",
    ],
}


def all_tickers(include_benchmarks: bool = True) -> list[str]:
    """De-duplicated, sorted list of every ticker in the universe."""
    seen: set[str] = set()
    for theme, tickers in THEMES.items():
        if theme == "benchmarks" and not include_benchmarks:
            continue
        seen.update(tickers)
    return sorted(seen)


def theme_of(ticker: str) -> list[str]:
    """Which themes a ticker belongs to (a stock can be in several)."""
    return [t for t, ticks in THEMES.items() if ticker in ticks]


def themes_map() -> dict[str, list[str]]:
    """ticker -> [themes], for the graph builder."""
    out: dict[str, list[str]] = {}
    for theme, tickers in THEMES.items():
        for tk in tickers:
            out.setdefault(tk, []).append(theme)
    return out


if __name__ == "__main__":
    tickers = all_tickers()
    print(f"{len(tickers)} unique tickers "
          f"({len(all_tickers(include_benchmarks=False))} excl. benchmarks)")
    for theme, ticks in THEMES.items():
        print(f"  {theme:20} {len(ticks):3d}")
