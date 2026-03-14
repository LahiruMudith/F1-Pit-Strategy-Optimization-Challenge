#!/usr/bin/env python3
"""Box Box Box - F1 Race Simulator (baseline + parametric tire model).

This is a *skeleton that runs* and produces a deterministic ordering given a
parameterized lap-time model. It is designed so you can iteratively fit/tune
params using historical data.

I/O:
- Reads a JSON test case from stdin
- Writes {race_id, finishing_positions} JSON to stdout

Notes:
- No car-to-car interaction (time trial), per challenge regulations.
- All times are floating point seconds.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional


COMPOUNDS = ("SOFT", "MEDIUM", "HARD")

def pit_stop_to_dict(pit_stop: PitStop) -> Dict[str, Any]:
    return {
        "lap": pit_stop.lap,
        "from_tire": pit_stop.from_tire,
        "to_tire": pit_stop.to_tire
    }

@dataclass(frozen=True)
class PitStop:
    lap: int
    from_tire: str
    to_tire: str

@dataclass
class DriverPlan:
    driver_id: str
    starting_tire: str
    pit_stops: List[PitStop]

@dataclass
class RaceConfig:
    track: str
    total_laps: int
    base_lap_time: float
    pit_lane_time: float
    track_temp: int

@dataclass
class TireParams:
    compound_offset: Dict[str, float]
    warmup_laps: Dict[str, int]
    deg_a: Dict[str, float]
    deg_b: Dict[str, float]
    temp_ref: float
    temp_k: Dict[str, float]


DEFAULT_PARAMS = TireParams(
    compound_offset={"SOFT": -0.60, "MEDIUM": 0.00, "HARD": 0.55},
    warmup_laps={"SOFT": 2, "MEDIUM": 2, "HARD": 2},
    deg_a={"SOFT": 0.0040, "MEDIUM": 0.0022, "HARD": 0.0014},
    deg_b={"SOFT": 0.0180, "MEDIUM": 0.0105, "HARD": 0.0075},
    temp_ref=30.0,
    temp_k={"SOFT": -0.010, "MEDIUM": -0.006, "HARD": -0.004},
)

def _load_params(path: str = "solution/params.json") -> TireParams:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return DEFAULT_PARAMS

    def _dflt_map(key: str, d: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(d)
        out.update(raw.get(key, {}))
        return out

    return TireParams(
        compound_offset={c: float(v) for c, v in _dflt_map("compound_offset", DEFAULT_PARAMS.compound_offset).items()},
        warmup_laps={c: int(v) for c, v in _dflt_map("warmup_laps", DEFAULT_PARAMS.warmup_laps).items()},
        deg_a={c: float(v) for c, v in _dflt_map("deg_a", DEFAULT_PARAMS.deg_a).items()},
        deg_b={c: float(v) for c, v in _dflt_map("deg_b", DEFAULT_PARAMS.deg_b).items()},
        temp_ref=float(raw.get("temp_ref", DEFAULT_PARAMS.temp_ref)),
        temp_k={c: float(v) for c, v in _dflt_map("temp_k", DEFAULT_PARAMS.temp_k).items()},
    )

def parse_race_config(d: Dict[str, Any]) -> RaceConfig:
    return RaceConfig(
        track=str(d["track"]),
        total_laps=int(d["total_laps"]),
        base_lap_time=float(d["base_lap_time"]),
        pit_lane_time=float(d["pit_lane_time"]),
        track_temp=int(d["track_temp"]),
    )

def parse_strategies(strategies: Dict[str, Any]) -> List[DriverPlan]:
    plans: List[DriverPlan] = []
    for pos in sorted(strategies.keys(), key=lambda s: int(s.replace("pos", ""))):
        s = strategies[pos]
        pit_stops = [
            PitStop(lap=int(p["lap"], from_tire=str(p["from_tire"]), to_tire=str(p["to_tire"]))
            for p in s.get("pit_stops", [])
        ]
        pit_stops.sort(key=lambda p: p.lap)
        plans.append(DriverPlan(driver_id=str(s["driver_id"]), starting_tire=str(s["starting_tire"]), pit_stops=pit_stops))
    return plans

def lap_time(
    *,
    base_lap_time: float,
    compound: str,
    tire_age: int,
    track_temp: float,
    params: TireParams,
) -> float:
    if compound not in COMPOUNDS:
        raise ValueError(f"Unknown compound: {compound}")

    t = base_lap_time
    t += params.compound_offset[compound]

    t += params.temp_k[compound] * (track_temp - params.temp_ref)

    w = params.warmup_laps[compound]
    if tire_age <= w:
        deg = 0.0
    else:
        x = float(tire_age - w)
        deg = params.deg_a[compound] * x * x + params.deg_b[compound] * x

    return t + deg

def simulate_total_time(race: RaceConfig, plan: DriverPlan, params: TireParams) -> float:
    pit_map: Dict[int, PitStop] = {p.lap: p for p in plan.pit_stops}

    compound = plan.starting_tire
    tire_age = 0

    total = 0.0
    for lap in range(1, race.total_laps + 1):
        total += lap_time(
            base_lap_time=race.base_lap_time,
            compound=compound,
            tire_age=tire_age,
            track_temp=float(race.track_temp),
            params=params,
        )

        if lap in pit_map:
            pit = pit_map[lap]
            total += race.pit_lane_time
            compound = pit.to_tire
            tire_age = 0
        else:
            tire_age += 1

    return total

def simulate_race(race_config: Dict[str, Any], strategies: Dict[str, Any], params: Optional[TireParams] = None) -> List[str]:
    params = params or _load_params()

    race = parse_race_config(race_config)
    plans = parse_strategies(strategies)

    times: List[Tuple[float, str]] = []
    for plan in plans:
        t = simulate_total_time(race, plan, params)
        times.append((t, plan.driver_id))

    times.sort(key=lambda x: x[0])
    return [driver_id for _, driver_id in times]

def main() -> None:
    test_case = json.load(sys.stdin)

    race_id = test_case["race_id"]
    race_config = test_case["race_config"]
    strategies = test_case["strategies"]

    finishing_positions = simulate_race(race_config, strategies)

    out = {"race_id": race_id, "finishing_positions": finishing_positions}
    sys.stdout.write(json.dumps(out))

if __name__ == "__main__":
    main()