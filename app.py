"""VirtuTrade public market snapshot and optional DNSE feed worker."""

import argparse
import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, url_for

from database import init_database, read_market

ROOT = Path(__file__).resolve().parent
VIETNAM = timezone(timedelta(hours=7))


def parse_timestamp(value):
    # Python 3.10 accepts only microseconds; storage keeps all 9 digits for ordering.
    text = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    result = datetime.fromisoformat(text)
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result


def present_quotes(quotes):
    now = datetime.now(timezone.utc)
    for quote in quotes:
        try:
            timestamp = parse_timestamp(quote["quoted_at"])
            age = (now - timestamp).total_seconds()
            quote["stale"] = age > 900 or age < -300
        except (ValueError, TypeError, AttributeError):
            timestamp = None
            quote["stale"] = True
        if quote["source"] == "dnse":
            try:
                reference_at = parse_timestamp(quote["reference_at"])
                if timestamp is None or (
                    reference_at.astimezone(VIETNAM).date()
                    != timestamp.astimezone(VIETNAM).date()
                ):
                    quote["previous_close_vnd"] = None
            except (ValueError, TypeError, AttributeError):
                quote["previous_close_vnd"] = None
        reference = quote["previous_close_vnd"]
        quote["change"] = None
        if reference:
            change = Decimal(quote["price_vnd"] - reference) / Decimal(reference) * 100
            quote["change"] = format(
                change.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f"
            )
    return quotes


def create_app(config=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__)
    database_path = Path(os.environ.get("DATABASE_PATH", "instance/virtutrade.db"))
    if not database_path.is_absolute():
        database_path = ROOT / database_path
    app.config.update(DATABASE=str(database_path))
    if config:
        app.config.update(config)

    @app.template_filter("vnd")
    def vnd(value):
        return f"{value:,}"

    @app.get("/")
    def home():
        return redirect(url_for("market"))

    @app.get("/market")
    def market():
        try:
            quotes = present_quotes(read_market(app.config["DATABASE"]))
        except sqlite3.Error:
            app.logger.exception("Could not read market database")
            return render_template("market.html", quotes=[], error=True), 503
        return render_template("market.html", quotes=quotes, error=False)

    @app.get("/api/market/quotes")
    def market_quotes():
        try:
            response = jsonify(
                quotes=present_quotes(read_market(app.config["DATABASE"]))
            )
        except sqlite3.Error:
            app.logger.exception("Could not read market database")
            response = jsonify(
                error={
                    "code": "MARKET_UNAVAILABLE",
                    "message": "Market data is temporarily unavailable.",
                }
            )
            response.status_code = 503
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VirtuTrade M2 walking skeleton")
    parser.add_argument(
        "command", nargs="?", choices=["run", "init-db", "stream"], default="run"
    )
    args = parser.parse_args()
    application = create_app()
    if args.command == "init-db":
        count = init_database(application.config["DATABASE"])
        print(f"Database ready: {count} price_quote rows (12 on a fresh database).")
    elif args.command == "stream":
        from dnse import FeedError, Settings, run_feed

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
        )
        try:
            settings = Settings.from_environment(application.config["DATABASE"])
            asyncio.run(run_feed(settings, application.config["DATABASE"]))
        except FeedError as exc:
            parser.exit(1, f"{exc}\n")
        except sqlite3.Error:
            parser.exit(
                1,
                "Database unavailable or outdated. Run app.py init-db and check DATABASE_PATH.\n",
            )
        except KeyboardInterrupt:
            print("DNSE worker stopped; saved quotes are unchanged.")
    else:
        application.run(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=False,
        )
