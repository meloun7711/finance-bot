"""
Command-line entry point.

Usage:
    python -m finance_bot.cli universe            # show the universe
    python -m finance_bot.cli download            # Step 1: all tickers
    python -m finance_bot.cli download --sample   # Step 1: quick 8-ticker test
    python -m finance_bot.cli download --force     # ignore the freshness cache
"""

from __future__ import annotations

import argparse
import sys


def _cmd_universe(args: argparse.Namespace) -> int:
    from finance_bot.universe import THEMES, all_tickers
    tickers = all_tickers()
    print(f"{len(tickers)} unique tickers across {len(THEMES)} themes\n")
    for theme, ticks in THEMES.items():
        print(f"  {theme:20} {len(ticks):3d}  {', '.join(ticks[:8])}"
              f"{' …' if len(ticks) > 8 else ''}")
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from finance_bot.ingest.prices import download_universe, download_batch
    from finance_bot.universe import all_tickers
    if args.sample:
        tickers = ["PLTR", "NVDA", "LMT", "IONQ", "XOM", "TSM", "AAPL", "COIN"]
    else:
        tickers = all_tickers()
    if args.source == "alpaca":
        from finance_bot.ingest.alpaca import download_alpaca
        print(f"Alpaca download: {len(tickers)} tickers (~2y daily, IEX feed) …\n")
        n = download_alpaca(tickers)
        print(f"\nWrote {n}/{len(tickers)} tickers.")
        return 0 if n > len(tickers) * 0.6 else 1
    if args.fast:
        period = args.period or "2y"
        print(f"Fast batch download: {len(tickers)} tickers (period={period}) …\n")
        n = download_batch(tickers, period=period)
        print(f"\nWrote {n}/{len(tickers)} tickers.")
        return 0 if n >= 100 else 1   # accept partial: 100+ names is plenty to pick top-20
    print(f"Downloading {len(tickers)} tickers "
          f"(period={args.period or 'default'}, force={args.force}) …\n")
    status = download_universe(tickers, period=args.period, force=args.force)
    failed = [t for t, s in status.items() if s == "failed"]
    if failed:
        print("Failed:", ", ".join(failed))
    return 0 if not failed else 1


def _cmd_graph(args: argparse.Namespace) -> int:
    from finance_bot.mind.graph import build_graph
    g = build_graph()
    m = g["meta"]
    print(f"Step 2 — mind graph: {m['n_nodes']} nodes, {m['n_edges']} edges "
          f"({m['date_start']} -> {m['date_end']})")
    kinds: dict[str, int] = {}
    for e in g["edges"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    for k, v in sorted(kinds.items()):
        print(f"  {k:10} {v}")
    return 0


def _cmd_news(args: argparse.Namespace) -> int:
    from finance_bot.ingest.news import collect
    from finance_bot.universe import all_tickers
    tickers = (["PLTR", "NVDA", "LMT", "XOM", "IONQ", "COIN"]
               if args.sample else all_tickers(include_benchmarks=False))
    collect(tickers=tickers)
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    from finance_bot.ingest.prices import load_close_matrix, load_prices
    from finance_bot.ingest.news import load_events
    from finance_bot.backtest.engine import (
        event_study, reversal_stats, Backtest, make_news_aware_signal)
    events = load_events()
    close_m = load_close_matrix()
    study = event_study(events, close_m)
    print("Step 4 — event study:", len(study), "event-ticker observations")
    print("  reversal stats (the 'don't panic' metric):", reversal_stats(study))
    tk = args.ticker
    ser = close_m[tk] if tk in close_m.columns else None
    if ser is not None:
        res = Backtest(ser, events).run(make_news_aware_signal())
        print(f"\n  {tk} news-aware long/flat backtest:")
        print(f"    strategy return : {res.total_return:+.2%}")
        print(f"    buy & hold      : {res.buy_hold_return:+.2%}")
        print(f"    sharpe          : {res.sharpe}")
        print(f"    max drawdown    : {res.max_drawdown:+.2%}")
    return 0


def _cmd_fncbot(args: argparse.Namespace) -> int:
    import json
    from finance_bot import fncbot
    if args.reset:
        fncbot.reset(args.capital)
        print(f"FNCBOT reset to ${args.capital:,.0f} (model v1 baseline).")
        if not args.run:
            return 0
    out = fncbot.run_cycle() if args.run else fncbot.status()
    print(json.dumps(out, indent=2))
    return 0


def _cmd_paper(args: argparse.Namespace) -> int:
    import json
    from finance_bot import paper
    if args.reset:
        paper.reset(args.capital)
        print(f"Paper account reset to ${args.capital:,.0f}.")
        if not args.phase:
            return 0
    if args.phase == "open":
        out = paper.phase_open()
    elif args.phase == "close":
        out = paper.phase_close()
    else:
        out = paper.status()
    print(json.dumps(out, indent=2))
    return 0


def _cmd_export_market(args: argparse.Namespace) -> int:
    from finance_bot.analyze.decide import export_market
    print(export_market())
    return 0


def _cmd_decide(args: argparse.Namespace) -> int:
    from finance_bot.analyze.decide import decide
    print(decide())
    return 0


def _cmd_account(args: argparse.Namespace) -> int:
    import json
    from finance_bot import broker_alpaca
    print(json.dumps(broker_alpaca.summary(), indent=2))
    return 0


def _cmd_trade_paper(args: argparse.Namespace) -> int:
    import json
    from finance_bot.analyze.decide import target_book
    from finance_bot import broker_alpaca
    targets, asof = target_book()
    print(f"Target book from bot predictions (as-of {asof}): {len(targets)} names @ "
          f"{list(targets.values())[0]*100:.1f}% each" if targets else "no target names")
    if not targets:
        return 0
    result = broker_alpaca.rebalance(targets)          # PAPER endpoint, hard-locked
    print(json.dumps(result, indent=2))
    return 0 if result.get("errors", 0) == 0 else 1


def _cmd_screen(args: argparse.Namespace) -> int:
    from finance_bot.analyze.screen import dip_in_uptrend
    df = dip_in_uptrend()
    if df.empty:
        print("No 'dip in uptrend' candidates right now.")
        return 0
    print(f"Dip-in-uptrend — {len(df)} names: strong long-term, currently "
          f"pulling back (not broken)\n")
    print(df.head(args.top).to_string(index=False))
    return 0


def _cmd_daily(args: argparse.Namespace) -> int:
    if args.download:
        from finance_bot.ingest.prices import download_universe
        from finance_bot.universe import all_tickers
        print("Refreshing prices before the daily update …")
        download_universe(all_tickers(), force=True)
    from finance_bot.analyze.daily import daily_update
    summ = daily_update(as_of=args.as_of, force=args.force)
    if summ.empty:
        print("No data — run download/profile first.")
        return 1
    up = int((summ["daily_delta"] > 0).sum())
    dn = int((summ["daily_delta"] < 0).sum())
    print(f"Daily update — {len(summ)} names nudged  (↑{up}  ↓{dn})\n")
    movers = summ.reindex(summ["daily_delta"].abs()
                          .sort_values(ascending=False).index)
    print("Biggest movers today (index += daily_delta):")
    print(movers.head(args.top)[
        ["ticker", "index", "daily_delta", "structural", "themes"]
    ].to_string(index=False))
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    from finance_bot.analyze.profile import build_profiles
    summ = build_profiles()
    if summ.empty:
        print("No profiles — run download first.")
        return 1
    n_up = int((summ["bucket"] == 1).sum())
    n_flat = int((summ["bucket"] == 0).sum())
    n_down = int((summ["bucket"] == -1).sum())
    print(f"Step 5 — profiled {len(summ)} names: "
          f"+1={n_up}  ~0={n_flat}  -1={n_down}\n")
    print("Top 12 long-term (+):")
    print(summ.head(12).to_string(index=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="finance_bot")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("universe", help="print the ticker universe")

    d = sub.add_parser("download", help="Step 1: download OHLCV history")
    d.add_argument("--sample", action="store_true",
                   help="download only a small representative sample")
    d.add_argument("--force", action="store_true",
                   help="re-download even if a fresh cache exists")
    d.add_argument("--period", default=None,
                   help="yfinance period (e.g. 5y, 10y, max)")
    d.add_argument("--fast", action="store_true",
                   help="batched download of recent history (default 2y) — for cloud runs")
    d.add_argument("--source", choices=["yahoo", "alpaca"], default="yahoo",
                   help="data source; 'alpaca' is datacenter-friendly (needs APCA_* env keys)")

    sub.add_parser("graph", help="Step 2: build the correlation/lead-lag mind")

    n = sub.add_parser("news", help="Step 3: collect news events")
    n.add_argument("--sample", action="store_true",
                   help="collect for a small sample of tickers")

    b = sub.add_parser("backtest", help="Step 4: event study + backtest")
    b.add_argument("--ticker", default="PLTR",
                   help="ticker to run the walk-forward backtest on")

    sub.add_parser("profile", help="Step 5: build long-term index profiles")

    sub.add_parser("export-market", help="Box: dump market/close.parquet for the routine")
    sub.add_parser("decide", help="Routine: read market data (+news tilt) -> reports/latest.md")
    sub.add_parser("trade-paper", help="Place the predicted book as Alpaca PAPER orders (no real money)")
    sub.add_parser("account", help="Show the Alpaca PAPER account holdings + P&L")

    sc = sub.add_parser("screen", help="Find strong long-term names currently dipping")
    sc.add_argument("--top", type=int, default=20, help="how many candidates to print")

    fb = sub.add_parser("fncbot", help="FNCBOT: one-call/day self-adapting PAPER trader (data in ./FNCBOT)")
    fb.add_argument("--run", action="store_true", help="run today's cycle (settle + learn + trade)")
    fb.add_argument("--reset", action="store_true", help="wipe FNCBOT and restart at v1 baseline")
    fb.add_argument("--capital", type=float, default=100_000.0, help="starting capital on reset")

    pa = sub.add_parser("paper", help="PAPER account (simulated): run open/close phase")
    pa.add_argument("--phase", choices=["open", "close"], default=None,
                    help="open = trade at today's open; close = mark & record. Omit for status.")
    pa.add_argument("--reset", action="store_true", help="wipe and restart the paper account")
    pa.add_argument("--capital", type=float, default=100_000.0, help="starting capital on reset")

    dy = sub.add_parser("daily", help="Daily driver: nudge each index from today's metrics")
    dy.add_argument("--download", action="store_true",
                    help="refresh prices from Yahoo before updating")
    dy.add_argument("--as-of", default=None,
                    help="run the update as of this date (YYYY-MM-DD); default = latest bar")
    dy.add_argument("--force", action="store_true",
                    help="re-run even if this date was already applied")
    dy.add_argument("--top", type=int, default=15,
                    help="how many of the biggest movers to print")

    args = p.parse_args(argv)
    return {
        "universe": _cmd_universe,
        "download": _cmd_download,
        "graph": _cmd_graph,
        "news": _cmd_news,
        "backtest": _cmd_backtest,
        "profile": _cmd_profile,
        "daily": _cmd_daily,
        "screen": _cmd_screen,
        "paper": _cmd_paper,
        "fncbot": _cmd_fncbot,
        "export-market": _cmd_export_market,
        "decide": _cmd_decide,
        "trade-paper": _cmd_trade_paper,
        "account": _cmd_account,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
