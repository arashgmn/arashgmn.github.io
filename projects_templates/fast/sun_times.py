#!/usr/bin/env python3
"""
sun_times.py — Compute solar event times with subsecond precision.

MODES
─────
  altitude   UTC time(s) when the Sun's centre crosses a given altitude.
  events     Dawn, sunrise, solar noon, sunset, dusk for a single date.
  year       CSV report of all events for every day of a given year.

SOLAR POSITION BACKEND (priority order)
─────────────────────────────────────────
  1. ephem   (pip install ephem)    — VSOP87 full series, sub-arcsecond
  2. astropy (pip install astropy)  — high accuracy
  3. Built-in Meeus Ch. 25/27      — ~1 arcsecond, needs scipy + numpy only

RISE / SET DEFINITION
─────────────────────
  Sunrise/sunset are the moment the Sun's UPPER LIMB (not centre) crosses the
  apparent horizon, accounting for:
    • mean atmospheric refraction at the horizon  ≈ +0.5667°
    • Sun's mean semidiameter                     ≈  0.2667°
  The Sun's geometric centre altitude at apparent sunrise/sunset is therefore
  ≈ −0.8333° (the IAU / USNO standard value).

DAWN / DUSK DEFINITION
────────────────────────
  Dawn  = Sun's CENTRE rising through a user-supplied altitude (default −6°).
  Dusk  = Sun's CENTRE setting through the same altitude.
  Common choices:
    −6°  Civil twilight  (horizon still visible, outdoor work possible)
   −12°  Nautical twilight
   −18°  Astronomical twilight (sky fully dark)

ROOT-FINDING
────────────
  Altitude crossings are pinpointed with Brent's method (scipy.optimize.brentq)
  to xtol = 1 × 10⁻⁹ minutes ≈ 60 nanoseconds.
  Solar noon is found with bounded scalar minimisation (minimize_scalar).

TIMEZONE
────────
  If an IANA timezone name is supplied, all times are also shown in local time,
  fully DST-aware (uses zoneinfo on Python ≥ 3.9, else pytz).

REQUIRED
────────
  pip install numpy scipy

OPTIONAL
────────
  pip install ephem    # highest accuracy
  pip install astropy  # alternative high-accuracy backend
  pip install pytz     # timezone support on Python < 3.9

USAGE
─────
  # Altitude-crossing mode (Sun's centre):
  python sun_times.py altitude <lat> <lon> <YYYY-MM-DD> <alt_deg> [tz]

  # Events mode (single date):
  python sun_times.py events <lat> <lon> <YYYY-MM-DD> [--twilight <alt_deg>] [--tz <tz>]

  # Year CSV mode:
  python sun_times.py year <lat> <lon> <YYYY> [--twilight <alt_deg>] [--tz <tz>] [--out <file>]

EXAMPLES
────────
  python sun_times.py altitude 52.52 13.405 2024-06-21 30 Europe/Berlin
  python sun_times.py events   52.52 13.405 2024-06-21 --twilight -18 --tz Europe/Berlin
  python sun_times.py events   52.52 13.405 2024-12-21 --twilight  -6 --tz Europe/Berlin
  python sun_times.py year     52.52 13.405 2024       --twilight  -6 --tz Europe/Berlin
  python sun_times.py year    -33.87 151.21 2024       --twilight -12 --tz Australia/Sydney
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import numpy as np
from scipy.optimize import brentq, minimize_scalar


# ══════════════════════════════════════════════════════════════════════════════
#  Julian Day
# ══════════════════════════════════════════════════════════════════════════════

def _jde(dt_utc: datetime) -> float:
    """Julian Ephemeris Day for a UTC datetime."""
    y, m = dt_utc.year, dt_utc.month
    d = (dt_utc.day
         + dt_utc.hour        / 24
         + dt_utc.minute      / 1_440
         + dt_utc.second      / 86_400
         + dt_utc.microsecond / 86_400_000_000)
    if m <= 2:
        y -= 1
        m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5


# ══════════════════════════════════════════════════════════════════════════════
#  Solar-position backends
# ══════════════════════════════════════════════════════════════════════════════

# ── Backend 1: ephem (VSOP87 full series) ─────────────────────────────────────
try:
    import ephem as _ephem

    def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
        obs           = _ephem.Observer()
        obs.lat       = str(lat)
        obs.lon       = str(lon)
        obs.elevation = 0
        obs.pressure  = 0              # geometric — no atmospheric refraction
        obs.date      = _ephem.Date(dt_utc.replace(tzinfo=None))
        return float(np.degrees(float(_ephem.Sun(obs).alt)))

    def _backend_name() -> str:
        return f"ephem {_ephem.__version__} (VSOP87 full series)"

# ── Backend 2: astropy ────────────────────────────────────────────────────────
except ImportError:
    try:
        from astropy.coordinates import AltAz, EarthLocation, get_sun
        from astropy.time import Time
        import astropy.units as u

        def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
            t     = Time(dt_utc, scale="utc")
            loc   = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)
            frame = AltAz(obstime=t, location=loc, pressure=0 * u.Pa)
            return float(get_sun(t).transform_to(frame).alt.deg)

        def _backend_name() -> str:
            import astropy
            return f"astropy {astropy.__version__}"

    # ── Backend 3: Meeus Ch. 25 / 27 (built-in) ──────────────────────────────
    except ImportError:

        def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
            """
            Geometric solar centre altitude (degrees) via Meeus
            "Astronomical Algorithms" (2nd ed.) Ch. 25/27.

            Accurate to ~1 arcsecond over a century.  No atmospheric refraction
            is applied here — callers add corrections explicitly.

            Key references:
              • Equation of centre  — Meeus eq. 25.4
              • Obliquity           — Meeus eq. 22.2 / 25.8
              • GMST → GAST         — Meeus eq. 12.6 + equation of the equinoxes
            """
            JD = _jde(dt_utc)
            T  = (JD - 2451545.0) / 36525.0      # Julian centuries from J2000.0

            # Geometric mean longitude & mean anomaly of the Sun
            L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T ** 2) % 360
            M  = (357.52911 + 35999.05029 * T - 0.0001537 * T ** 2) % 360
            Mr = np.radians(M)

            # Equation of centre — full published 3-term series (Meeus eq. 25.4)
            C = ((1.914602 - 0.004817 * T - 0.000014 * T ** 2) * np.sin(Mr)
               + (0.019993 - 0.000101 * T)                      * np.sin(2 * Mr)
               +  0.000289                                       * np.sin(3 * Mr))

            sun_lon = L0 + C      # Sun's true geometric longitude

            # Apparent longitude: aberration correction + nutation in longitude
            omega   = 125.04 - 1934.136 * T      # longitude of ascending node
            omega_r = np.radians(omega)
            app_lon = sun_lon - 0.00569 - 0.00478 * np.sin(omega_r)

            # Mean & apparent obliquity of the ecliptic (Meeus eq. 22.2 / 25.8)
            eps0 = (23.0
                    + 26.0 / 60
                    + 21.448 / 3600
                    - (46.8150  / 3600) * T
                    - (0.00059  / 3600) * T ** 2
                    + (0.001813 / 3600) * T ** 3)
            eps  = eps0 + 0.00256 * np.cos(omega_r)  # apparent obliquity
            epsr = np.radians(eps)

            # Equatorial coordinates (right ascension & declination)
            app_lon_r = np.radians(app_lon)
            ra  = np.degrees(np.arctan2(np.cos(epsr) * np.sin(app_lon_r),
                                        np.cos(app_lon_r))) % 360
            dec = np.degrees(np.arcsin(np.sin(epsr) * np.sin(app_lon_r)))

            # Greenwich Mean Sidereal Time (Meeus eq. 12.6) — uses JD directly.
            # Note: an older split formula using JD0 + T0 produces errors of
            # several degrees away from J2000.0 and must NOT be used here.
            GMST = (280.46061837
                    + 360.98564736629 * (JD - 2451545.0)
                    + 0.000387933     * T ** 2
                    - T ** 3          / 38710000) % 360

            # Equation of the equinoxes: Δψ · cos(ε) converts GMST → GAST
            dpsi = (-17.20 / 3600) * np.sin(omega_r)   # nutation in longitude (°)
            GAST = (GMST + dpsi * np.cos(epsr)) % 360

            # Local Hour Angle
            LHA = (GAST - ra + lon) % 360

            # Altitude from the fundamental formula of spherical astronomy
            lat_r = np.radians(lat)
            dec_r = np.radians(dec)
            lha_r = np.radians(LHA)
            return float(np.degrees(np.arcsin(
                np.sin(lat_r) * np.sin(dec_r)
                + np.cos(lat_r) * np.cos(dec_r) * np.cos(lha_r)
            )))

        def _backend_name() -> str:
            return "Meeus 'Astronomical Algorithms' Ch. 25/27 (~1 arcsecond)"


# ══════════════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════════════

# Geometric altitude of the Sun's CENTRE at apparent sunrise/sunset (upper
# limb touching the apparent horizon).  This accounts for:
#   mean atmospheric refraction at horizon: +0.5667°
#   Sun's mean semidiameter:                +0.2667°
# so the centre is below the geometric horizon by 0.5667 + 0.2667 = 0.8333°.
# Source: Meeus Ch. 15; U.S. Naval Observatory.
HORIZON_UPPER_LIMB: float = -0.8333   # degrees

# Brent's method tolerance: 1e-9 minutes ≈ 60 nanoseconds
_BRENT_XTOL: float = 1e-9


# ══════════════════════════════════════════════════════════════════════════════
#  Core helpers
# ══════════════════════════════════════════════════════════════════════════════

def _day_start(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _make_f(lat: float, lon: float, day_start: datetime, target: float):
    """f(minutes) = solar_altitude(t) − target."""
    def f(minutes: float) -> float:
        return _solar_altitude(lat, lon, day_start + timedelta(minutes=minutes)) - target
    return f


def _scan_crossings(f) -> list[tuple[str, float]]:
    """
    Coarse 1-minute scan over [0, 1440], then Brent-refine each sign change.
    Returns list of ('rising'|'setting', root_in_minutes).
    """
    vals = [f(m) for m in range(24 * 60 + 1)]
    out  = []
    for i in range(24 * 60):
        a, b = vals[i], vals[i + 1]
        if a == 0.0:
            direction = "rising" if (i == 0 or vals[i - 1] < 0) else "setting"
            out.append((direction, float(i)))
        elif a * b < 0:
            root      = brentq(f, i, i + 1, xtol=_BRENT_XTOL, rtol=1e-15)
            direction = "rising" if a < 0 else "setting"
            out.append((direction, root))
    return out


def _find_single(lat: float, lon: float, date_str: str,
                 target: float, direction: str) -> Optional[datetime]:
    """Return the first crossing in `direction` at `target` altitude, or None."""
    start = _day_start(date_str)
    hits  = [m for d, m in _scan_crossings(_make_f(lat, lon, start, target))
             if d == direction]
    return (start + timedelta(minutes=hits[0])) if hits else None


# ══════════════════════════════════════════════════════════════════════════════
#  Public event finders
# ══════════════════════════════════════════════════════════════════════════════

def find_altitude_crossings(lat: float, lon: float, date_str: str,
                             target_alt: float) -> list[tuple[str, datetime]]:
    """
    All moments during *date_str* (UTC) when the Sun's CENTRE crosses *target_alt*.
    Returns [(label, datetime_utc)].
    """
    start = _day_start(date_str)
    out   = []
    for direction, mins in _scan_crossings(_make_f(lat, lon, start, target_alt)):
        label = ("Rising  (centre, altitude increasing)"
                 if direction == "rising" else
                 "Setting (centre, altitude decreasing)")
        out.append((label, start + timedelta(minutes=mins)))
    return out


def find_sunrise(lat: float, lon: float, date_str: str) -> Optional[datetime]:
    """UTC time of sunrise: Sun's upper limb at apparent horizon (−0.8333°)."""
    return _find_single(lat, lon, date_str, HORIZON_UPPER_LIMB, "rising")


def find_sunset(lat: float, lon: float, date_str: str) -> Optional[datetime]:
    """UTC time of sunset: Sun's upper limb at apparent horizon (−0.8333°)."""
    return _find_single(lat, lon, date_str, HORIZON_UPPER_LIMB, "setting")


def find_dawn(lat: float, lon: float, date_str: str,
              twilight_alt: float) -> Optional[datetime]:
    """UTC time of dawn: Sun's CENTRE rising through *twilight_alt*."""
    return _find_single(lat, lon, date_str, twilight_alt, "rising")


def find_dusk(lat: float, lon: float, date_str: str,
              twilight_alt: float) -> Optional[datetime]:
    """UTC time of dusk: Sun's CENTRE setting through *twilight_alt*."""
    return _find_single(lat, lon, date_str, twilight_alt, "setting")


def find_solar_noon(lat: float, lon: float,
                    date_str: str) -> tuple[datetime, float]:
    """
    UTC time and altitude (°) of solar noon (daily altitude maximum).

    Strategy: coarse 1-minute scan over the full UTC day to locate the
    maximum, then bounded scalar minimisation in a ±90-minute window around
    it — accurate to well under one millisecond.  Works for any longitude
    (including those where apparent noon falls near UTC midnight) and any
    latitude including polar regions.
    """
    start = _day_start(date_str)

    def neg_alt(minutes: float) -> float:
        return -_solar_altitude(lat, lon, start + timedelta(minutes=minutes))

    # Coarse scan: find the minute with the highest altitude
    coarse   = [neg_alt(m) for m in range(24 * 60)]
    best_min = int(np.argmin(coarse))      # argmin of neg_alt = argmax of alt

    # Refine in a ±90-minute window, clamped to [0, 1440]
    lo = max(0,    best_min - 90)
    hi = min(1440, best_min + 90)
    res      = minimize_scalar(neg_alt, bounds=(lo, hi), method="bounded",
                               options={"xatol": _BRENT_XTOL})
    noon_dt  = start + timedelta(minutes=res.x)
    noon_alt = -res.fun
    return noon_dt, noon_alt


# ══════════════════════════════════════════════════════════════════════════════
#  Timezone conversion & formatting
# ══════════════════════════════════════════════════════════════════════════════

def convert_timezone(dt_utc: datetime, tz_name: str) -> datetime:
    """DST-aware UTC → local time conversion."""
    try:
        from zoneinfo import ZoneInfo          # stdlib on Python ≥ 3.9
        return dt_utc.astimezone(ZoneInfo(tz_name))
    except ImportError:
        pass
    try:
        import pytz
        return dt_utc.astimezone(pytz.timezone(tz_name))
    except ImportError:
        raise ImportError(
            "No timezone library found. "
            "Install 'pytz'  or  upgrade to Python ≥ 3.9 (zoneinfo is in stdlib)."
        )


def _fmt(dt: Optional[datetime], tz_name: Optional[str] = None,
         full_date: bool = True) -> str:
    """Format datetime as 'YYYY-MM-DD HH:MM:SS.mmm TZ' (or time-only variant)."""
    if dt is None:
        return ""
    target = convert_timezone(dt, tz_name) if tz_name else dt
    date_s = target.strftime("%Y-%m-%d ") if full_date else ""
    time_s = target.strftime("%H:%M:%S.") + f"{target.microsecond // 1000:03d}"
    off    = target.utcoffset()
    if off is None:
        return f"{date_s}{time_s} UTC"
    total  = int(off.total_seconds())
    sign   = "+" if total >= 0 else "-"
    h, r   = divmod(abs(total), 3600)
    abbr   = target.strftime("%Z") or f"UTC{sign}{h:02d}:{r // 60:02d}"
    return f"{date_s}{time_s} {abbr}"


def _csv_ts(dt: Optional[datetime], tz_name: Optional[str]) -> str:
    """ISO-8601 timestamp for CSV cells (no timezone suffix — column header carries it)."""
    if dt is None:
        return ""
    target = convert_timezone(dt, tz_name) if tz_name else dt
    return target.strftime("%H:%M:%S.") + f"{target.microsecond // 1000:03d}"


# ══════════════════════════════════════════════════════════════════════════════
#  CLI — altitude mode
# ══════════════════════════════════════════════════════════════════════════════

def cmd_altitude(args):
    tz = args.timezone
    print()
    print(f"  Location  : {args.lat}°, {args.lon}°")
    print(f"  Date      : {args.date}")
    print(f"  Altitude  : {args.alt}°  (Sun's centre, geometric, no refraction)")
    if tz:
        print(f"  Timezone  : {tz}")
    print(f"  Backend   : {_backend_name()}")
    print()

    crossings = find_altitude_crossings(args.lat, args.lon, args.date, args.alt)
    if not crossings:
        print(f"  The Sun's centre never reaches {args.alt}° on {args.date} at this location.")
        return

    for label, dt_utc in crossings:
        print(f"  {label}:")
        print(f"    UTC   : {_fmt(dt_utc)}")
        if tz:
            print(f"    Local : {_fmt(dt_utc, tz)}")
        print()


# ══════════════════════════════════════════════════════════════════════════════
#  CLI — events mode
# ══════════════════════════════════════════════════════════════════════════════

def cmd_events(args):
    lat, lon, date_str = args.lat, args.lon, args.date
    twi_dawn = args.dawn
    twi_dusk = args.dusk
    tz  = args.tz

    dawn_dt             = find_dawn(lat, lon, date_str, twi_dawn)
    sunrise_dt          = find_sunrise(lat, lon, date_str)
    noon_dt, noon_alt   = find_solar_noon(lat, lon, date_str)
    sunset_dt           = find_sunset(lat, lon, date_str)
    dusk_dt             = find_dusk(lat, lon, date_str, twi_dusk)

    NONE_MSG = "(none — sun permanently above or below this altitude)"

    print()
    print(f"  Location     : {lat}°, {lon}°")
    print(f"  Date         : {date_str}")
    print(f"  Dawn alt : {twi_dawn}°  (dawn use Sun's centre)")
    print(f"  Dusk alt : {twi_dusk}°  (dusk use Sun's centre)")
    print(f"  Rise/set     : Sun's upper limb at apparent horizon ({HORIZON_UPPER_LIMB}°)")
    if tz:
        print(f"  Timezone     : {tz}")
    print(f"  Backend      : {_backend_name()}")
    print()

    W = 16

    def row(label: str, dt: Optional[datetime], extra: str = ""):
        utc_s   = _fmt(dt) if dt else NONE_MSG
        local_s = _fmt(dt, tz) if (dt and tz) else ""
        print(f"  {label:<{W}}: {utc_s}")
        if local_s:
            print(f"  {'':>{W}}  {local_s}")
        if extra:
            print(f"  {'':>{W}}  {extra}")

    row("Dawn",       dawn_dt)
    row("Sunrise",    sunrise_dt)
    row("Solar noon", noon_dt, f"(max altitude {noon_alt:.3f}°)")
    row("Sunset",     sunset_dt)
    row("Dusk",       dusk_dt)
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  CLI — year mode (CSV)
# ══════════════════════════════════════════════════════════════════════════════

def cmd_year(args):
    lat, lon, year = args.lat, args.lon, args.year
    twi_dawn = args.dawn
    twi_dusk = args.dusk
    tz   = args.tz
    out  = args.out or f"sun_times_{lat}_{lon}_{year}.csv"

    # All dates in the requested year
    d      = date(year, 1, 1)
    end    = date(year, 12, 31)
    dates  = []
    while d <= end:
        dates.append(d)
        d += timedelta(days=1)

    # Build column names that make the timezone explicit
    tz_suffix = f"_local[{tz}]" if tz else "_UTC"
    cols = [
        "date",
        f"dawn{tz_suffix}",
        f"sunrise{tz_suffix}",
        f"solar_noon{tz_suffix}",
        "solar_noon_altitude_deg",
        f"sunset{tz_suffix}",
        f"dusk{tz_suffix}",
        "dawn_altitude_deg",
        "dusk_altitude_deg",
        "rise_set_reference_alt_deg",
        "backend",
    ]

    print(f"\n  Computing solar events for {year} at ({lat}°, {lon}°)…")
    print(f"  Dawn twilight altitude : {twi_dawn}°  (Sun's centre)")
    print(f"  Dusk twilight altitude : {twi_dusk}°  (Sun's centre)")
    print(f"  Rise/set reference altitude : {HORIZON_UPPER_LIMB}°  (upper limb, apparent horizon)")
    if tz:
        print(f"  Local timezone              : {tz}")
    print(f"  Solar position backend      : {_backend_name()}")
    print(f"  Output file                 : {out}")
    print()

    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()

        for i, d in enumerate(dates):
            ds  = d.isoformat()

            dawn_dt           = find_dawn(lat, lon, ds, twi_dawn)
            sunrise_dt        = find_sunrise(lat, lon, ds)
            noon_dt, noon_alt = find_solar_noon(lat, lon, ds)
            sunset_dt         = find_sunset(lat, lon, ds)
            dusk_dt           = find_dusk(lat, lon, ds, twi_dusk)

            writer.writerow({
                "date"                        : ds,
                f"dawn{tz_suffix}"            : _csv_ts(dawn_dt,    tz),
                f"sunrise{tz_suffix}"         : _csv_ts(sunrise_dt, tz),
                f"solar_noon{tz_suffix}"      : _csv_ts(noon_dt,    tz),
                "solar_noon_altitude_deg"     : f"{noon_alt:.6f}",
                f"sunset{tz_suffix}"          : _csv_ts(sunset_dt,  tz),
                f"dusk{tz_suffix}"            : _csv_ts(dusk_dt,    tz),
                "dawn_altitude_deg"           : twi_dawn,
                "dusk_altitude_deg"           : twi_dusk,
                "rise_set_reference_alt_deg"  : HORIZON_UPPER_LIMB,
                "backend"                     : _backend_name(),
            })

            # Progress line every 30 days (and on the last day)
            if (i + 1) % 30 == 0 or (i + 1) == len(dates):
                rise_s = _csv_ts(sunrise_dt, tz) or "none (polar night/day)"
                set_s  = _csv_ts(sunset_dt,  tz) or "none (polar night/day)"
                print(f"  [{i + 1:3d}/{len(dates)}]  {ds}  "
                      f"rise {rise_s}  |  set {set_s}")

    print(f"\n  Done — {len(dates)} rows written to '{out}'.\n")


# ══════════════════════════════════════════════════════════════════════════════
#  Argument parsing & entry point
# ══════════════════════════════════════════════════════════════════════════════

def _add_latlon(p):
    p.add_argument("lat", type=float, help="Latitude  (decimal °, N positive)")
    p.add_argument("lon", type=float, help="Longitude (decimal °, E positive)")


def _validate_latlon(args):
    if not -90  <= args.lat <= 90:
        sys.exit("ERROR: latitude must be in [−90, 90]")
    if not -180 <= args.lon <= 180:
        sys.exit("ERROR: longitude must be in [−180, 180]")


def main():
    parser = argparse.ArgumentParser(
        prog="sun_times.py",
        description="Compute solar event times with subsecond precision.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # ── altitude ──────────────────────────────────────────────────────────────
    p_alt = sub.add_parser("altitude",
                            help="Time(s) when the Sun's centre crosses a given altitude.")
    _add_latlon(p_alt)
    p_alt.add_argument("date",     type=str,   help="YYYY-MM-DD")
    p_alt.add_argument("alt",      type=float, help="Target altitude in degrees")
    p_alt.add_argument("timezone", nargs="?",  default=None,
                       help="IANA timezone name (optional)")

    # ── events ────────────────────────────────────────────────────────────────
    p_ev = sub.add_parser("events",
                           help="Dawn, sunrise, solar noon, sunset, dusk for one date.")
    _add_latlon(p_ev)
    p_ev.add_argument("date", type=str, help="YYYY-MM-DD")
    p_ev.add_argument("--dawn", type=float, default=-6.0, metavar="DEG",
                      help="Sun-centre altitude for dawn (°) [default: −6, civil]")
    p_ev.add_argument("--dusk", type=float, default=-6.0, metavar="DEG",
                      help="Sun-centre altitude for dusk (°) [default: −6, civil]")
    p_ev.add_argument("--tz", type=str, default=None, metavar="TZ",
                      help="IANA timezone name (optional)")

    # ── year ──────────────────────────────────────────────────────────────────
    p_yr = sub.add_parser("year",
                           help="CSV of all solar events for every day of a year.")
    _add_latlon(p_yr)
    p_yr.add_argument("year", type=int, help="Four-digit year")
    p_yr.add_argument("--dawn", type=float, default=-6.0, metavar="DEG",
                      help="Sun-centre altitude for dawn (°) [default: −6, civil]")
    p_yr.add_argument("--dusk", type=float, default=-6.0, metavar="DEG",
                      help="Sun-centre altitude for dusk (°) [default: −6, civil]")
    p_yr.add_argument("--tz",  type=str, default=None, metavar="TZ",
                      help="IANA timezone name (optional)")
    p_yr.add_argument("--out", type=str, default=None, metavar="FILE",
                      help="Output CSV path [default: sun_times_<lat>_<lon>_<year>.csv]")

    args = parser.parse_args()
    _validate_latlon(args)

    if args.mode == "altitude":
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            sys.exit(f"ERROR: date must be YYYY-MM-DD, got '{args.date}'")
        if not -90 <= args.alt <= 90:
            sys.exit("ERROR: altitude must be in [−90, 90]")
        cmd_altitude(args)

    elif args.mode == "events":
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            sys.exit(f"ERROR: date must be YYYY-MM-DD, got '{args.date}'")
        if not -90 <= args.dawn <= 90:
            sys.exit("ERROR: --dawn must be in [−90, 90]")
        if not -90 <= args.dusk <= 90:
            sys.exit("ERROR: --dusk must be in [−90, 90]")
        
        cmd_events(args)

    elif args.mode == "year":
        if not 1 <= args.year <= 9999:
            sys.exit("ERROR: year must be 1–9999")
        if not -90 <= args.dawn <= 90:
            sys.exit("ERROR: --dawn must be in [−90, 90]")
        if not -90 <= args.dusk <= 90:
            sys.exit("ERROR: --dusk must be in [−90, 90]")
        cmd_year(args)


if __name__ == "__main__":
    main()
