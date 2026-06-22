"""A compact global warming system-dynamics model.

The model is intentionally small enough to inspect. It represents one
atmospheric CO2 stock, an aggregate non-CO2 forcing term, and a delayed surface
temperature response. Results are scenario evidence, not a replacement for
full climate-model ensembles.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log


START_YEAR = 2025
END_YEAR = 2040
PREINDUSTRIAL_CO2_PPM = 278.0
GTCO2_PER_PPM = 7.82
FORCING_PER_DOUBLING = 3.71


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    annual_emissions_change: float
    airborne_fraction: float
    non_co2_forcing_2025: float
    non_co2_forcing_change: float
    color: str


DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="rapid",
        name="快速减排",
        annual_emissions_change=-0.080,
        airborne_fraction=0.42,
        non_co2_forcing_2025=0.20,
        non_co2_forcing_change=-0.006,
        color="#2f8f6f",
    ),
    Scenario(
        key="baseline",
        name="缓慢转向",
        annual_emissions_change=-0.005,
        airborne_fraction=0.47,
        non_co2_forcing_2025=0.20,
        non_co2_forcing_change=0.008,
        color="#c17a2f",
    ),
    Scenario(
        key="high",
        name="高排放延续",
        annual_emissions_change=0.018,
        airborne_fraction=0.52,
        non_co2_forcing_2025=0.20,
        non_co2_forcing_change=0.024,
        color="#b23a48",
    ),
)


def simulate_scenario(
    scenario: Scenario,
    *,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    initial_co2_ppm: float = 424.6,
    initial_emissions_gtco2: float = 42.2,
    initial_temperature_c: float = 1.34,
    climate_sensitivity_c: float = 3.0,
    response_years: float = 40.0,
) -> list[dict[str, float | int | str]]:
    """Run an annual Euler-step stock-flow simulation."""

    co2_ppm = initial_co2_ppm
    emissions = initial_emissions_gtco2
    temperature = initial_temperature_c
    non_co2_forcing = scenario.non_co2_forcing_2025
    feedback_gain = climate_sensitivity_c / FORCING_PER_DOUBLING
    rows: list[dict[str, float | int | str]] = []

    for year in range(start_year, end_year + 1):
        co2_forcing = 5.35 * log(co2_ppm / PREINDUSTRIAL_CO2_PPM)
        forcing = co2_forcing + non_co2_forcing
        equilibrium_temperature = feedback_gain * forcing
        rows.append(
            {
                "year": year,
                "scenario": scenario.key,
                "scenario_name": scenario.name,
                "emissions_gtco2": round(emissions, 2),
                "co2_ppm": round(co2_ppm, 2),
                "forcing_wm2": round(forcing, 3),
                "temperature_c": round(temperature, 3),
                "equilibrium_temperature_c": round(equilibrium_temperature, 3),
                "warming_rate_c_per_year": round(
                    (equilibrium_temperature - temperature) / response_years, 4
                ),
            }
        )
        emissions *= 1.0 + scenario.annual_emissions_change
        co2_ppm += emissions * scenario.airborne_fraction / GTCO2_PER_PPM
        non_co2_forcing += scenario.non_co2_forcing_change
        temperature += (equilibrium_temperature - temperature) / response_years

    return rows


def run_default_scenarios() -> dict[str, list[dict[str, float | int | str]]]:
    return {scenario.key: simulate_scenario(scenario) for scenario in DEFAULT_SCENARIOS}


def checkpoint_summary(
    rows_by_scenario: dict[str, list[dict[str, float | int | str]]],
    checkpoints: tuple[int, ...] = (2030, 2035, 2040),
) -> dict[str, dict[int, dict[str, float]]]:
    summary: dict[str, dict[int, dict[str, float]]] = {}
    for scenario_key, rows in rows_by_scenario.items():
        by_year = {int(row["year"]): row for row in rows}
        summary[scenario_key] = {
            year: {
                "temperature_c": float(by_year[year]["temperature_c"]),
                "co2_ppm": float(by_year[year]["co2_ppm"]),
                "emissions_gtco2": float(by_year[year]["emissions_gtco2"]),
            }
            for year in checkpoints
        }
    return summary
