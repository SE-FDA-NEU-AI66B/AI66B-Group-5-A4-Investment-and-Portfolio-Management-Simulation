"""Candle history for charts, without HTTP or SQL.

DNSE quotes use stored provider bars: one-minute bars are grouped into 5/15/60
minute candles, and today's daily candle is built from today's minute bars until
the provider's daily bar arrives. Simulation quotes use the candles recorded by
the practice simulator, preceded by an illustrative backfill. Demo seed quotes
have no history, so they get a deterministic illustrative series. Generated
candles are always labelled as such and never feed an order.
"""

import math
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from virtutrade.market.models import Candle
from virtutrade.market.service import VIETNAM, parse_timestamp

# Requested resolution -> (stored resolution, candle seconds, lookback seconds).
RESOLUTIONS = {
    "1": ("1", 60, 7 * 86400),
    "5": ("1", 300, 14 * 86400),
    "15": ("1", 900, 30 * 86400),
    "1H": ("1", 3600, 30 * 86400),
    "1D": ("1D", 86400, 700 * 86400),
}
MAX_CANDLES = 500
# Enough candles for a 200-period moving average to show.
ILLUSTRATIVE_COUNT = 400
# Continuous-matching sessions in minutes after midnight, Vietnam time.
SESSIONS = ((9 * 60, 11 * 60 + 30), (13 * 60, 14 * 60 + 45))
VOLATILITY = {"1": 0.0012, "5": 0.0025, "15": 0.004, "1H": 0.007, "1D": 0.018}
VOLUME_SHARE = {"1": 1 / 270, "5": 1 / 54, "15": 1 / 18, "1H": 1 / 5, "1D": 1}


def price_history(reader, quote, resolution, *, now=None):
    """Return (source, candles) oldest first.

    source is 'dnse' (provider bars), 'simulation' (simulator bars after an
    illustrative backfill) or 'illustrative' (generated only).
    """
    if resolution not in RESOLUTIONS:
        raise ValueError("Unsupported resolution")
    if quote.source not in ("dnse", "simulation"):
        return "illustrative", illustrative_candles(quote, resolution, now=now)
    candles = stored_candles(reader, quote.symbol, resolution,
                             now or datetime.now(timezone.utc))
    if quote.source == "dnse":
        return "dnse", candles[-MAX_CANDLES:]
    if not candles:
        return "illustrative", illustrative_candles(quote, resolution, now=now)
    return "simulation", (backfill(quote, candles[0], resolution) + candles)[-MAX_CANDLES:]


def stored_candles(reader, symbol, resolution, now):
    stored, size, lookback = RESOLUTIONS[resolution]
    since = int(now.timestamp()) - lookback
    if stored == "1D":
        daily = reader.fetch_bars(symbol, "1D", since)
        minutes = reader.fetch_bars(symbol, "1", int(now.timestamp()) - 3 * 86400)
        return with_today(daily, minutes)
    return aggregate(reader.fetch_bars(symbol, "1", since), size)


def backfill(quote, first, resolution):
    """Illustrative candles that end at the first recorded candle's open."""
    start = datetime.fromtimestamp(first.time - 1, timezone.utc)
    anchor = replace(quote, price_vnd=first.open, previous_close_vnd=first.open,
                     quoted_at=start.isoformat().replace("+00:00", "Z"))
    return [candle for candle in illustrative_candles(anchor, resolution)
            if candle.time < first.time]


def aggregate(candles, size):
    """Group ordered candles into buckets of `size` seconds (UTC+7 is whole hours)."""
    if size == 60:
        return list(candles)
    result = []
    for candle in candles:
        start = candle.time - candle.time % size
        if result and result[-1].time == start:
            last = result[-1]
            result[-1] = Candle(start, last.open, max(last.high, candle.high),
                                min(last.low, candle.low), candle.close,
                                last.volume + candle.volume)
        else:
            result.append(Candle(start, candle.open, candle.high, candle.low,
                                 candle.close, candle.volume))
    return result


def vietnam_date(stamp):
    return datetime.fromtimestamp(stamp, VIETNAM).date()


def with_today(daily, minutes):
    """Append daily candles built from minute bars on dates the provider lacks."""
    latest = vietnam_date(daily[-1].time) if daily else None
    extra = {}
    for candle in minutes:
        day = vietnam_date(candle.time)
        if latest is not None and day <= latest:
            continue
        bar = extra.get(day)
        if bar is None:
            start = int(datetime(day.year, day.month, day.day, tzinfo=VIETNAM).timestamp())
            extra[day] = Candle(start, candle.open, candle.high, candle.low,
                                candle.close, candle.volume)
        else:
            extra[day] = Candle(bar.time, bar.open, max(bar.high, candle.high),
                                min(bar.low, candle.low), candle.close,
                                bar.volume + candle.volume)
    return list(daily) + [extra[day] for day in sorted(extra)]


def tick_size(price):
    """HOSE equity price steps."""
    return 10 if price < 10_000 else 50 if price < 50_000 else 100


def round_to_step(value, step, direction):
    scaled = value / step
    units = math.ceil(scaled) if direction > 0 else math.floor(scaled) if direction < 0 \
        else round(scaled)
    return max(step, int(units) * step)


def session_starts(end, resolution, count):
    """Bar open times (unix seconds) inside Vietnam sessions, oldest first."""
    local = end.astimezone(VIETNAM)
    times = []
    if resolution == "1D":
        day = local.date()
        while len(times) < count:
            if day.weekday() < 5:
                times.append(int(datetime(day.year, day.month, day.day,
                                          tzinfo=VIETNAM).timestamp()))
            day -= timedelta(days=1)
        return times[::-1]
    step = RESOLUTIONS[resolution][1]
    cursor = int(local.timestamp()) - int(local.timestamp()) % step
    while len(times) < count:
        moment = datetime.fromtimestamp(cursor, VIETNAM)
        minute = moment.hour * 60 + moment.minute
        if moment.weekday() < 5 and any(start <= minute < stop for start, stop in SESSIONS):
            times.append(cursor)
        cursor -= step
    return times[::-1]


def illustrative_candles(quote, resolution, *, now=None, count=ILLUSTRATIVE_COUNT):
    """A repeatable random walk ending at the stored quote; for demo charts only.

    History is anchored to the stored previous close, so earlier candles stay
    put when a simulated price changes; only the final candle moves to it.
    """
    try:
        end = parse_timestamp(quote.quoted_at)
    except (ValueError, TypeError, AttributeError):
        end = now or datetime.now(timezone.utc)
    rng = random.Random(f"{quote.symbol}:{resolution}")
    sigma = VOLATILITY[resolution]
    anchor = quote.previous_close_vnd or quote.price_vnd
    closes = [anchor] * count
    closes[-1] = quote.price_vnd
    for index in range(count - 2, 0, -1):
        closes[index - 1] = closes[index] / math.exp(rng.gauss(0, sigma))
    times = session_starts(end, resolution, count)
    # About 100 billion VND traded per day, in line with the simulator's volumes.
    base_volume = 100_000_000_000 / anchor * VOLUME_SHARE[resolution]
    candles = []
    previous = closes[0] * math.exp(rng.gauss(0, sigma))
    for index, (stamp, close) in enumerate(zip(times, closes)):
        step = tick_size(close)
        # The anchor and the stored price are real stored values: keep them exact.
        close_vnd = int(close) if index >= count - 2 else round_to_step(close, step, 0)
        open_vnd = int(previous) if index == count - 1 else \
            round_to_step(previous, tick_size(previous), 0)
        high = max(open_vnd, close_vnd) * (1 + abs(rng.gauss(0, sigma / 2)))
        low = min(open_vnd, close_vnd) * (1 - abs(rng.gauss(0, sigma / 2)))
        volume = int(rng.lognormvariate(math.log(max(base_volume, 100)), 0.5)) // 100 * 100
        candles.append(Candle(
            stamp, open_vnd,
            max(round_to_step(high, step, 1), open_vnd, close_vnd),
            max(min(round_to_step(low, step, -1), open_vnd, close_vnd), 1),
            close_vnd, max(volume, 100)))
        previous = close_vnd
    return candles
