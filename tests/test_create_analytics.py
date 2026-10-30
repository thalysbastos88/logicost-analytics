import pytest

from src import create_analytics


class FakeCursor:
    def __init__(self, base_view_exists):
        self.base_view_exists = base_view_exists
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        self.statements.append(statement)

    def fetchone(self):
        return ("analytics.vw_deliveries_analytics" if self.base_view_exists else None,)


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.fake_cursor


def test_create_analytics_requires_base_schema(monkeypatch):
    cursor = FakeCursor(base_view_exists=False)
    monkeypatch.setattr(
        create_analytics, "get_connection", lambda: FakeConnection(cursor)
    )

    with pytest.raises(RuntimeError, match="sql/schema_star.sql"):
        create_analytics.create_analytics()

    assert len(cursor.statements) == 1


def test_create_analytics_installs_all_seven_views_and_hypothetical_scenario(
    monkeypatch, capsys
):
    cursor = FakeCursor(base_view_exists=True)
    monkeypatch.setattr(
        create_analytics, "get_connection", lambda: FakeConnection(cursor)
    )

    create_analytics.create_analytics()

    assert len(cursor.statements) == 2
    script = cursor.statements[1]
    expected_views = {
        "vw_monthly_performance",
        "vw_cost_composition",
        "vw_route_profitability",
        "vw_carrier_performance",
        "vw_regional_profitability",
        "vw_fleet_efficiency",
        "vw_cost_alerts",
        "vw_fuel_savings_scenario",
    }
    assert sum(
        f"CREATE OR REPLACE VIEW analytics.{view}" in script
        for view in expected_views
    ) == len(expected_views)
    assert "0.08::numeric AS assumed_fuel_reduction_pct" in script
    assert "current_costs.current_logistics_cost_brl" in script
    assert "Simulacao hipotetica" in script
    assert "nao representa economia realizada" in script
    assert "Camada analítica criada" in capsys.readouterr().out


def test_analytics_validation_covers_all_views_and_scenario_checks():
    validation_sql = (
        create_analytics.ANALYTICS_SQL.parent / "analytics_validation.sql"
    ).read_text(encoding="utf-8")

    for view in (
        "vw_monthly_performance",
        "vw_cost_composition",
        "vw_route_profitability",
        "vw_carrier_performance",
        "vw_regional_profitability",
        "vw_fleet_efficiency",
        "vw_cost_alerts",
        "vw_fuel_savings_scenario",
    ):
        assert f"analytics.{view}" in validation_sql

    assert "uses_expected_reduction" in validation_sql
    assert "total_cost_share_pct" in validation_sql
    assert "cost_reconciliation_errors" in validation_sql
