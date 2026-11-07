"""Candle history for charts, without HTTP or SQL.

DNSE quotes use stored provider bars. One-minute bars make 15-minute candles;
hourly bars make 1H and 4H candles, with the latest hours rebuilt from minutes;
daily bars make daily, weekly and monthly candles, with today's daily candle
built from minutes until the provider's daily bar arrives. Simulation quotes use the candles recorded by
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

# Requested resolution -> (stored resolution, candle size, lookback seconds).
# Sizes are seconds, or "week"/"month" for calendar candles in Vietnam time.
RESOLUTIONS = {
    "15": ("1", 900, 30 * 86400),
    "1H": ("1H", 3600, 120 * 86400),
    "4H": ("1H", 4 * 3600, 400 * 86400),
    "1D": ("1D", 86400, 700 * 86400),
    "1W": ("1D", "week", 1830 * 86400),
    "1M": ("1D", "month", 1830 * 86400),
}
MAX_CANDLES = 500
# Enough candles for a 200-period moving average to show; monthly history stops
# at ten years, since the Vietnamese exchange only opened in 2000.
ILLUSTRATIVE_COUNT = 400
ILLUSTRATIVE_MONTHS = 120
# Continuous-matching sessions in minutes after midnight, Vietnam time.
SESSIONS = ((9 * 60, 11 * 60 + 30), (13 * 60, 14 * 60 + 45))
VOLATILITY = {"15": 0.004, "1H": 0.007, "4H": 0.012, "1D": 0.018, "1W": 0.04, "1M": 0.08}
VOLUME_SHARE = {"15": 1 / 18, "1H": 1 / 5, "4H": 1 / 2, "1D": 1, "1W": 5, "1M": 21}


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
    recent = int(now.timestamp()) - 3 * 86400
    if stored == "1D":
        daily = with_today(reader.fetch_bars(symbol, "1D", since),
                           reader.fetch_bars(symbol, "1", recent))
        return daily if size == 86400 else calendar(daily, size)
    if stored == "1H":
        hourly = with_recent(reader.fetch_bars(symbol, "1H", since),
                             aggregate(reader.fetch_bars(symbol, "1", recent), 3600))
        return aggregate(hourly, size)
    return aggregate(reader.fetch_bars(symbol, "1", since), size)


def backfill(quote, first, resolution):
    """Illustrative candles that end at the first recorded candle's open."""
    start = datetime.fromtimestamp(first.time - 1, timezone.utc)
    anchor = replace(quote, price_vnd=first.open, previous_close_vnd=first.open,
                     quoted_at=start.isoformat().replace("+00:00", "Z"))
    return [candle for candle in illustrative_candles(anchor, resolution)
            if candle.time < first.time]


def merge_into(result, start, candle):
    """Add an ordered candle to the bucket opening at `start`."""
    if result and result[-1].time == start:
        last = result[-1]
        result[-1] = Candle(start, last.open, max(last.high, candle.high),
                            min(last.low, candle.low), candle.close, last.volume + candle.volume)
    else:
        result.append(Candle(start, candle.open, candle.high, candle.low,
                             candle.close, candle.volume))


def aggregate(candles, size):
    """Group ordered candles into buckets of `size` seconds.

    Vietnam is UTC+7, so hour buckets line up with local hours, and 4-hour
    buckets open at 07:00 and 11:00 local time: one morning and one afternoon
    candle per session.
    """
    if size == 60:
        return list(candles)
    result = []
    for candle in candles:
        merge_into(result, candle.time - candle.time % size, candle)
    return result


def vietnam_date(stamp):
    return datetime.fromtimestamp(stamp, VIETNAM).date()


def vietnam_midnight(day):
    return int(datetime(day.year, day.month, day.day, tzinfo=VIETNAM).timestamp())


def period_start(day, unit):
    """First day of the week (Monday) or month containing `day`."""
    return day - timedelta(days=day.weekday()) if unit == "week" else day.replace(day=1)


def calendar(daily, unit):
    """Group daily candles into weeks or months, in Vietnam time."""
    result = []
    for candle in daily:
        merge_into(result, vietnam_midnight(period_start(vietnam_date(candle.time), unit)), candle)
    return result


def with_recent(stored, rebuilt):
    """Let candles rebuilt from minutes replace the latest stored ones and extend them."""
    if stored:
        rebuilt = [candle for candle in rebuilt if candle.time >= stored[-1].time]
    if not rebuilt:
        return list(stored)
    return [candle for candle in stored if candle.time < rebuilt[0].time] + rebuilt


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
            extra[day] = Candle(vietnam_midnight(day), candle.open, candle.high, candle.low,
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
    size = RESOLUTIONS[resolution][1]
    if resolution == "1D":
        day = local.date()
        while len(times) < count:
            if day.weekday() < 5:
                times.append(vietnam_midnight(day))
            day -= timedelta(days=1)
        return times[::-1]
    if size in ("week", "month"):
        first = period_start(local.date(), size)
        while len(times) < count:
            times.append(vietnam_midnight(first))
            first = period_start(first - timedelta(days=1), size)
        return times[::-1]
    cursor = int(local.timestamp()) - int(local.timestamp()) % size
    while len(times) < count:
        moment = datetime.fromtimestamp(cursor, VIETNAM)
        minute = moment.hour * 60 + moment.minute
        # Keep candles that overlap a session (a 4H candle opens at 07:00 or 11:00).
        if moment.weekday() < 5 and any(minute < stop and minute + size // 60 > start
                                        for start, stop in SESSIONS):
            times.append(cursor)
        cursor -= size
    return times[::-1]


def illustrative_candles(quote, resolution, *, now=None, count=None):
    """A repeatable random walk ending at the stored quote; for demo charts only.

    History is anchored to the stored previous close, so earlier candles stay
    put when a simulated price changes; only the final candle moves to it.
    """
    try:
        end = parse_timestamp(quote.quoted_at)
    except (ValueError, TypeError, AttributeError):
        end = now or datetime.now(timezone.utc)
    count = count or (ILLUSTRATIVE_MONTHS if resolution == "1M" else ILLUSTRATIVE_COUNT)
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
