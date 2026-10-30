from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import dashboard


@pytest.fixture
def sample_deliveries():
    return pd.DataFrame(
        [
            {
                "delivery_id": "ENT-001",
                "delivery_date": pd.Timestamp("2025-01-05"),
                "region": "Sudeste",
                "carrier": "Frota própria",
                "route_id": "ROTA-01",
                "vehicle_id": "VEIC-001",
                "delivery_status": "Entregue no prazo",
                "distance_km": 100.0,
                "fuel_liters": 10.0,
                "fuel_cost_brl": 50.0,
                "toll_cost_brl": 10.0,
                "driver_cost_brl": 20.0,
                "maintenance_cost_brl": 5.0,
                "third_party_cost_brl": 0.0,
                "warehouse_cost_brl": 3.0,
                "other_cost_brl": 2.0,
                "total_logistics_cost_brl": 90.0,
                "freight_revenue_brl": 120.0,
                "cost_reconciliation_ok": True,
            },
            {
                "delivery_id": "ENT-002",
                "delivery_date": pd.Timestamp("2025-01-06"),
                "region": "Sul",
                "carrier": "Transportadora Alfa",
                "route_id": "ROTA-02",
                "vehicle_id": "VEIC-002",
                "delivery_status": "Devolvida",
                "distance_km": 200.0,
                "fuel_liters": 40.0,
                "fuel_cost_brl": 200.0,
                "toll_cost_brl": 20.0,
                "driver_cost_brl": 60.0,
                "maintenance_cost_brl": 10.0,
                "third_party_cost_brl": 30.0,
                "warehouse_cost_brl": 10.0,
                "other_cost_brl": 5.0,
                "total_logistics_cost_brl": 335.0,
                "freight_revenue_brl": 180.0,
                "cost_reconciliation_ok": True,
            },
        ]
    )


def test_format_brl_uses_brazilian_number_format():
    assert dashboard.format_brl(1234567.89) == "R$ 1.234.567,89"
    assert dashboard.format_brl(float("nan")) == "—"
    assert dashboard.format_brl_compact(1114260.37) == "R$ 1,11 mi"
    assert dashboard.format_brl_compact(-187610.33) == "-R$ 188 mil"
    assert dashboard.format_brl_compact(1419.71) == "R$ 1,4 mil"


def test_filters_apply_dates_and_selected_categories(sample_deliveries):
    filtered = dashboard.apply_filters(
        sample_deliveries,
        date(2025, 1, 5),
        date(2025, 1, 5),
        regions=["Sudeste"],
    )

    assert filtered["delivery_id"].tolist() == ["ENT-001"]


def test_kpis_use_weighted_cost_per_km_and_include_returns(sample_deliveries):
    kpis = dashboard.calculate_kpis(sample_deliveries)

    assert kpis["deliveries"] == 2
    assert kpis["cost_brl"] == 425
    assert kpis["avg_cost_per_delivery_brl"] == 212.5
    assert kpis["cost_per_km_brl"] == pytest.approx(425 / 300)
    assert kpis["margin_pct"] == pytest.approx((300 - 425) / 300 * 100)
    assert kpis["on_time_pct"] == 50
    assert kpis["return_pct"] == 50


def test_cost_composition_sums_to_total(sample_deliveries):
    composition = dashboard.cost_composition(sample_deliveries)

    assert composition["cost_brl"].sum() == 425
    assert composition["share_pct"].sum() == pytest.approx(100)


def test_route_profitability_calculates_weighted_unit_cost(sample_deliveries):
    profitability = dashboard.route_profitability(sample_deliveries)

    route_1 = profitability.set_index("route_id").loc["ROTA-01"]
    route_2 = profitability.set_index("route_id").loc["ROTA-02"]
    assert route_1["cost_per_km_brl"] == 0.9
    assert route_2["margin_pct"] == pytest.approx((180 - 335) / 180 * 100)


def test_carrier_rates_and_fleet_efficiency(sample_deliveries):
    carriers = dashboard.carrier_performance(sample_deliveries)
    fleet = dashboard.fleet_efficiency(sample_deliveries).set_index("vehicle_id")

    carrier = carriers.set_index("carrier")
    assert carrier.loc["Frota própria", "on_time_pct"] == 100
    assert carrier.loc["Transportadora Alfa", "return_pct"] == 100
    assert fleet.loc["VEIC-001", "fuel_efficiency_km_l"] == 10
    assert fleet.loc["VEIC-002", "total_cost_per_km_brl"] == pytest.approx(1.675)


def test_cost_alerts_respect_minimum_sample_and_benchmark(sample_deliveries):
    deliveries = pd.concat([sample_deliveries] * 30, ignore_index=True)
    deliveries["delivery_id"] = [
        f"ENT-{number:03d}" for number in range(len(deliveries))
    ]

    alerts = dashboard.cost_alerts(deliveries, min_deliveries=30)

    assert alerts["route_id"].tolist() == ["ROTA-02"]
    assert alerts.iloc[0]["above_company_avg_pct"] > 0


def test_analytical_charts_render(sample_deliveries):
    assert len(dashboard.monthly_performance_chart(sample_deliveries).data) == 3
    assert len(dashboard.render_cost_composition(sample_deliveries).data) == 1
    assert len(dashboard.render_route_chart(sample_deliveries).data) == 1
    assert len(dashboard.render_carrier_chart(sample_deliveries).data) == 3
    assert len(dashboard.render_regional_chart(sample_deliveries).data) == 3
    assert len(dashboard.render_fleet_chart(sample_deliveries).data) == 1


def test_streamlit_dashboard_loads_without_errors():
    app_file = Path(__file__).resolve().parents[1] / "src" / "dashboard.py"
    app = AppTest.from_file(str(app_file), default_timeout=60).run()

    assert not app.exception
    assert any("Visão executiva" in item.value for item in app.markdown)
    assert len(app.get("metric")) >= 8
    assert len(app.get("tab")) == 4
