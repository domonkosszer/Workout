#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # fallback if needed

DAY_TO_OFFSET = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}

@dataclass
class Event:
    title: str
    day: str
    start: str
    duration_min: int

def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def parse_time(s: str) -> time:
    return datetime.strptime(s, "%H:%M").time()

def stable_uid(week_file: str, title: str, dtstart_local: datetime) -> str:
    raw = f"{week_file}|{title}|{dtstart_local.isoformat()}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{h}@workout"

def fmt_local_dt(dt: datetime) -> str:
    # ICS local datetime format (no Z)
    return dt.strftime("%Y%m%dT%H%M%S")

def build_ics(week_name: str, tzid: str, week_start: date, events: list[Event]) -> str:
    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Workout//Training Plan//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    # TZID is used inline (DTSTART;TZID=...)
    for ev in events:
        day = ev.day.strip().upper()
        if day not in DAY_TO_OFFSET:
            raise ValueError(f"Invalid day '{ev.day}' in {week_name}")

        start_dt = datetime.combine(
            week_start + timedelta(days=DAY_TO_OFFSET[day]),
            parse_time(ev.start),
        )
        end_dt = start_dt + timedelta(minutes=int(ev.duration_min))

        uid = stable_uid(week_name, ev.title, start_dt)

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID={tzid}:{fmt_local_dt(start_dt)}",
            f"DTEND;TZID={tzid}:{fmt_local_dt(end_dt)}",
            f"SUMMARY:{ev.title}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"

def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]  # /calendar/scripts -> repo root
    weeks_dir = repo_root / "calendar" / "weeks"
    out_dir = repo_root / "calendar" / "ics"
    out_dir.mkdir(parents=True, exist_ok=True)

    week_files = sorted(weeks_dir.glob("*.toml"))
    if not week_files:
        print(f"No week files found in {weeks_dir}")
        return 1

    for wf in week_files:
        data = tomllib.loads(wf.read_text(encoding="utf-8"))
        tzid = data["timezone"]
        week_start = parse_date(data["week_start"])
        events_raw = data.get("events", [])

        events = [
            Event(
                title=e["title"],
                day=e["day"],
                start=e["start"],
                duration_min=int(e["duration_min"]),
            )
            for e in events_raw
        ]

        ics_text = build_ics(wf.stem, tzid, week_start, events)
        out_path = out_dir / f"{wf.stem}.ics"
        out_path.write_text(ics_text, encoding="utf-8")
        print(f"Wrote {out_path}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
