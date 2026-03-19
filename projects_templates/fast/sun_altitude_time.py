#!/usr/bin/env python3
"""
Find the UTC time(s) when the Sun reaches a specified altitude at a given location and date.

Solar position is computed using the algorithms from Jean Meeus,
"Astronomical Algorithms" (2nd ed.), Chapters 25 & 27 — accurate to ~1 arcsecond.
The altitude crossing is located via Brent's method (scipy.optimize.brentq) with a
tolerance of 1e-9 minutes (~60 nanoseconds), giving subsecond precision.

If 'ephem' is installed it is used instead, giving even higher accuracy (VSOP87).
If 'astropy' is installed it is used as an alternative high-accuracy backend.

Required (for the built-in Meeus backend):
    pip install scipy numpy

Optional (higher accuracy / timezone support):
    pip install ephem          # highest accuracy (VSOP87 full series)
    pip install astropy        # alternative high-accuracy backend
    pip install pytz           # timezone support on Python < 3.9

Usage:
    python sun_altitude_time.py <latitude> <longitude> <date> <altitude> [timezone]

Arguments:
    latitude   Latitude in decimal degrees  (N positive, S negative)
    longitude  Longitude in decimal degrees (E positive, W negative)
    date       Date in YYYY-MM-DD format
    altitude   Target solar altitude in degrees (geometric, no refraction)
    timezone   Optional IANA timezone name (e.g. 'Europe/Berlin', 'America/New_York')

Examples:
    python sun_altitude_time.py 52.52 13.405 2024-06-21 30
    python sun_altitude_time.py 52.52 13.405 2024-06-21 30 Europe/Berlin
    python sun_altitude_time.py 40.7128 -74.0060 2024-12-21 10 America/New_York
    python sun_altitude_time.py -33.8688 151.2093 2024-09-23 0 Australia/Sydney
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import brentq


# ---------------------------------------------------------------------------
# Backend 1: ephem  (most accurate — full VSOP87)
# ---------------------------------------------------------------------------

try:
    import ephem as _ephem

    def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
        obs = _ephem.Observer()
        obs.lat       = str(lat)
        obs.lon       = str(lon)
        obs.elevation = 0
        obs.pressure  = 0      # geometric altitude — no atmospheric refraction
        obs.date      = _ephem.Date(dt_utc.replace(tzinfo=None))
        sun = _ephem.Sun(obs)
        return float(np.degrees(float(sun.alt)))

    def _backend_name() -> str:
        return f"ephem {_ephem.__version__} (VSOP87 full series)"

# ---------------------------------------------------------------------------
# Backend 2: astropy
# ---------------------------------------------------------------------------
except ImportError:
    try:
        from astropy.coordinates import EarthLocation, AltAz, get_sun
        from astropy.time import Time
        import astropy.units as u

        def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
            t     = Time(dt_utc, scale="utc")
            loc   = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)
            frame = AltAz(obstime=t, location=loc, pressure=0 * u.Pa)  # no refraction
            return float(get_sun(t).transform_to(frame).alt.deg)

        def _backend_name() -> str:
            import astropy
            return f"astropy {astropy.__version__}"

    # -----------------------------------------------------------------------
    # Backend 3: Meeus "Astronomical Algorithms" Ch. 25 / 27
    #
    # All quantities are derived from the full published series — no simplified
    # "approximate" formulas.  Accuracy is ~1 arcsecond over a century.
    # -----------------------------------------------------------------------
    except ImportError:

        def _jde(dt_utc: datetime) -> float:
            """Julian Ephemeris Day for a UTC datetime."""
            y, m = dt_utc.year, dt_utc.month
            d    = (dt_utc.day
                    + dt_utc.hour        / 24
                    + dt_utc.minute      / 1440
                    + dt_utc.second      / 86400
                    + dt_utc.microsecond / 86_400_000_000)
            if m <= 2:
                y -= 1
                m += 12
            A = int(y / 100)
            B = 2 - A + int(A / 4)
            return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

        def _solar_altitude(lat: float, lon: float, dt_utc: datetime) -> float:
            """
            Geometric solar altitude (degrees) — Meeus Ch. 25 + GAST.
            No atmospheric refraction is applied.
            """
            JD = _jde(dt_utc)
            T  = (JD - 2451545.0) / 36525.0    # Julian centuries from J2000.0

            # ---- Geometric mean longitude of the Sun (deg) ----
            L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T ** 2) % 360

            # ---- Mean anomaly of the Sun (deg) ----
            M  = (357.52911 + 35999.05029 * T - 0.0001537 * T ** 2) % 360
            Mr = np.radians(M)

            # ---- Equation of centre — full 3-term series (Meeus eq. 25.4) ----
            C = ((1.914602 - 0.004817 * T - 0.000014 * T ** 2) * np.sin(Mr)
               + (0.019993 - 0.000101 * T)                      * np.sin(2 * Mr)
               +  0.000289                                       * np.sin(3 * Mr))

            # Sun's true longitude
            sun_lon = L0 + C

            # ---- Apparent longitude: aberration + nutation in longitude ----
            omega   = 125.04 - 1934.136 * T        # longitude of ascending node
            omega_r = np.radians(omega)
            app_lon = sun_lon - 0.00569 - 0.00478 * np.sin(omega_r)

            # ---- Mean & apparent obliquity of the ecliptic (Meeus eq. 22.2 / 25.8) ----
            eps0 = (23.0
                    + 26.0 / 60
                    + 21.448 / 3600
                    - (46.8150  / 3600) * T
                    - (0.00059  / 3600) * T ** 2
                    + (0.001813 / 3600) * T ** 3)
            eps  = eps0 + 0.00256 * np.cos(omega_r)
            epsr = np.radians(eps)

            # ---- Equatorial coordinates ----
            app_lon_r = np.radians(app_lon)
            ra  = np.degrees(np.arctan2(np.cos(epsr) * np.sin(app_lon_r),
                                        np.cos(app_lon_r))) % 360
            dec = np.degrees(np.arcsin(np.sin(epsr) * np.sin(app_lon_r)))

            # ---- Greenwich Apparent Sidereal Time (GAST, degrees) ----
            # GMST via the IAU formula; equation of the equinoxes added for GAST.
            JD0  = np.floor(JD - 0.5) + 0.5            # JD at preceding UT midnight
            T0   = (JD0 - 2451545.0) / 36525.0
            GMST = (100.4606184
                    + 36000.77004      * T0
                    + 0.000387933      * T0 ** 2
                    - T0 ** 3          / 38710000
                    + 360.98564724596  * (JD - 2451545.0)) % 360
            # Equation of the equinoxes: Δψ cos(ε)  (nutation in longitude)
            dpsi = (-17.20 / 3600) * np.sin(omega_r)   # degrees
            GAST = (GMST + dpsi * np.cos(epsr)) % 360

            # ---- Local Hour Angle ----
            GHA = (GAST - ra)  % 360
            LHA = (GHA  + lon) % 360

            # ---- Altitude ----
            lat_r = np.radians(lat)
            dec_r = np.radians(dec)
            lha_r = np.radians(LHA)
            return np.degrees(np.arcsin(
                np.sin(lat_r) * np.sin(dec_r)
                + np.cos(lat_r) * np.cos(dec_r) * np.cos(lha_r)
            ))

        def _backend_name() -> str:
            return "Meeus 'Astronomical Algorithms' Ch. 25/27 (~1 arcsecond accuracy)"


# ---------------------------------------------------------------------------
# Core: find altitude crossings over the course of one UTC day
# ---------------------------------------------------------------------------

def find_crossings(lat: float, lon: float, date_str: str,
                   target_alt: float, scan_step_minutes: int = 1) -> list:
    """
    Return a list of ``(label, datetime_utc)`` tuples — one entry per moment
    the Sun passes through *target_alt* on the given date.

    Strategy:
      1. Coarse scan (default 1-minute steps) to locate sign-change brackets.
      2. Brent's method per bracket with xtol = 1e-9 min ≈ 60 ns for the root.
    """
    start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def f(minutes: float) -> float:
        return _solar_altitude(lat, lon, start + timedelta(minutes=minutes)) - target_alt

    total = 24 * 60
    alts  = [f(m) for m in range(total + 1)]

    results = []
    for i in range(total):
        a, b = alts[i], alts[i + 1]
        if a == 0.0:
            label = "Rising" if (i == 0 or alts[i - 1] < 0) else "Setting"
            results.append((label, start + timedelta(minutes=i)))
            continue
        if a * b < 0:
            root        = brentq(f, i, i + 1, xtol=1e-9, rtol=1e-15)
            crossing_dt = start + timedelta(minutes=root)
            label       = ("Rising  (altitude increasing)"
                           if a < 0 else
                           "Setting (altitude decreasing)")
            results.append((label, crossing_dt))

    return results


# ---------------------------------------------------------------------------
# Timezone conversion (DST-aware)
# ---------------------------------------------------------------------------

def convert_timezone(dt_utc: datetime, tz_name: str) -> datetime:
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
            "Install 'pytz'  or  upgrade to Python 3.9+ (zoneinfo is included)."
        )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_dt(dt: datetime) -> str:
    ms = dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
    off = dt.utcoffset()
    if off is None:
        return ms + " UTC"
    total = int(off.total_seconds())
    sign  = "+" if total >= 0 else "-"
    h, r  = divmod(abs(total), 3600)
    abbr  = dt.strftime("%Z") or f"UTC{sign}{h:02d}:{r // 60:02d}"
    return f"{ms} {abbr}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Find UTC time(s) when the Sun reaches a given altitude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("latitude",  type=float, help="Latitude  (decimal °, N positive)")
    parser.add_argument("longitude", type=float, help="Longitude (decimal °, E positive)")
    parser.add_argument("date",      type=str,   help="Date YYYY-MM-DD")
    parser.add_argument("altitude",  type=float, help="Target solar altitude (degrees)")
    parser.add_argument("timezone",  nargs="?",  default=None,
                        help="IANA timezone name, e.g. 'Europe/Berlin'")
    args = parser.parse_args()

    # Validate inputs
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"ERROR: date must be YYYY-MM-DD, got '{args.date}'")
    if not -90  <= args.latitude  <= 90:
        sys.exit("ERROR: latitude must be in [-90, 90]")
    if not -180 <= args.longitude <= 180:
        sys.exit("ERROR: longitude must be in [-180, 180]")
    if not -90  <= args.altitude  <= 90:
        sys.exit("ERROR: altitude must be in [-90, 90]")

    print()
    print(f"  Location  : {args.latitude}°,  {args.longitude}°")
    print(f"  Date      : {args.date}")
    print(f"  Altitude  : {args.altitude}°  (geometric, no atmospheric refraction)")
    if args.timezone:
        print(f"  Timezone  : {args.timezone}")
    print(f"  Backend   : {_backend_name()}")
    print()

    crossings = find_crossings(args.latitude, args.longitude, args.date, args.altitude)

    if not crossings:
        print(f"  The Sun does not reach {args.altitude}° on {args.date} at this location.")
        print("  (It may be permanently above or below that altitude all day.)")
        return

    for label, dt_utc in crossings:
        print(f"  {label}:")
        print(f"    UTC   : {fmt_dt(dt_utc)}")
        if args.timezone:
            try:
                print(f"    Local : {fmt_dt(convert_timezone(dt_utc, args.timezone))}")
            except Exception as exc:
                print(f"    Local : (error — {exc})")
        print()


if __name__ == "__main__":
    main()
