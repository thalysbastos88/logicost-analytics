import pandas as pd
import pytest

from src.etl import run
from src.generate_data import generate
from src.kpis import build_kpis


def _generate_input(tmp_path, n=100):
    source = tmp_path / "raw" / "deliveries.csv"
    generate(n=n, output=source)
    return source


def test_pipeline_smoke(tmp_path):
    source = _generate_input(tmp_path)
    output = tmp_path / "processed" / "deliveries_enriched.csv"

    df = run(raw_path=source, output_path=output)

    assert len(df) == 100
    assert df["delivery_id"].is_unique
    assert df["cost_reconciliation_ok"].all()
    assert output.is_file()
    assert df["year_month"].str.fullmatch(r"\d{4}-\d{2}").all()


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("distance_km", -1, "valores negativos"),
        ("total_logistics_cost_brl", 1, "Conciliação de custos"),
        ("delivery_status", "Status inválido", "categorias inválidas"),
        ("delivery_date", "data inválida", "datas de entrega inválidas"),
    ],
)
def test_etl_rejects_invalid_data(tmp_path, column, value, message):
    source = _generate_input(tmp_path)
    df = pd.read_csv(source)
    df.loc[0, column] = value
    df.to_csv(source, index=False)

    with pytest.raises(ValueError, match=message):
        run(raw_path=source, output_path=tmp_path / "processed.csv")

    assert not (tmp_path / "processed.csv").exists()


def test_etl_rejects_duplicate_delivery_ids(tmp_path):
    source = _generate_input(tmp_path)
    df = pd.read_csv(source)
    df.loc[1, "delivery_id"] = df.loc[0, "delivery_id"]
    df.to_csv(source, index=False)

    with pytest.raises(ValueError, match="delivery_id duplicado"):
        run(raw_path=source, output_path=tmp_path / "processed.csv")


def test_etl_rejects_missing_required_columns(tmp_path):
    source = _generate_input(tmp_path)
    df = pd.read_csv(source).drop(columns="carrier")
    df.to_csv(source, index=False)

    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        run(raw_path=source, output_path=tmp_path / "processed.csv")


def test_kpis_use_weighted_cost_per_km_and_guard_zero_revenue(tmp_path):
    source = _generate_input(tmp_path, n=2)
    df = pd.read_csv(source)
    df["freight_revenue_brl"] = 0
    df.to_csv(source, index=False)
    processed = tmp_path / "processed.csv"
    enriched = run(raw_path=source, output_path=processed)

    kpis = build_kpis(processed)

    assert kpis["contribution_margin_pct"] is None
    assert kpis["avg_cost_per_km_brl"] == round(
        enriched["total_logistics_cost_brl"].sum() / enriched["distance_km"].sum(), 2
    )
    assert kpis["avg_cost_per_delivery_brl"] == round(
        enriched["total_logistics_cost_brl"].sum() / len(enriched), 2
    )
