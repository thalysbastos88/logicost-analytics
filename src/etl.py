import argparse
from pathlib import Path

import numpy as np
import pandas as pd


RAW = Path("data/raw/deliveries.csv")
OUT = Path("data/processed/deliveries_enriched.csv")

REQUIRED_COLUMNS = [
    "delivery_id",
    "delivery_date",
    "region",
    "route_id",
    "vehicle_id",
    "carrier",
    "distance_km",
    "fuel_efficiency_km_l",
    "fuel_liters",
    "fuel_price_brl_l",
    "fuel_cost_brl",
    "toll_cost_brl",
    "driver_cost_brl",
    "maintenance_cost_brl",
    "third_party_cost_brl",
    "warehouse_cost_brl",
    "other_cost_brl",
    "total_logistics_cost_brl",
    "freight_revenue_brl",
    "delivery_status",
    "delay_days",
]

COST_COLUMNS = [
    "fuel_cost_brl",
    "toll_cost_brl",
    "driver_cost_brl",
    "maintenance_cost_brl",
    "third_party_cost_brl",
    "warehouse_cost_brl",
    "other_cost_brl",
]

NON_NEGATIVE_COLUMNS = [
    "distance_km",
    "fuel_efficiency_km_l",
    "fuel_liters",
    "fuel_price_brl_l",
    *COST_COLUMNS,
    "total_logistics_cost_brl",
    "freight_revenue_brl",
    "delay_days",
]

DELIVERY_STATUSES = {
    "Entregue no prazo",
    "Entregue com atraso",
    "Devolvida",
}


def _validate_input(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
    if df.empty:
        raise ValueError("A base de entregas está vazia.")

    df = df[REQUIRED_COLUMNS].copy()
    if df.isna().any().any():
        missing_fields = df.columns[df.isna().any()].tolist()
        raise ValueError(f"Existem valores nulos em campos obrigatórios: {missing_fields}")

    for column in ("delivery_id", "region", "route_id", "vehicle_id", "carrier", "delivery_status"):
        df[column] = df[column].astype("string").str.strip()
        if df[column].eq("").any():
            raise ValueError(f"Existem valores vazios no campo {column}.")

    df["delivery_date"] = pd.to_datetime(
        df["delivery_date"], errors="coerce", format="mixed"
    )
    if df["delivery_date"].isna().any():
        raise ValueError("Existem datas de entrega inválidas.")

    for column in NON_NEGATIVE_COLUMNS:
        converted = pd.to_numeric(df[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"Existem valores numéricos inválidos no campo {column}.")
        df[column] = converted

    if not np.isfinite(df[NON_NEGATIVE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Existem valores numéricos não finitos na base.")
    if df["delivery_id"].duplicated().any():
        raise ValueError("delivery_id duplicado.")
    if df[NON_NEGATIVE_COLUMNS].lt(0).any().any():
        raise ValueError("Existem valores negativos em métricas não permitidas.")
    if df[["distance_km", "fuel_efficiency_km_l", "fuel_liters", "fuel_price_brl_l"]].eq(0).any().any():
        raise ValueError("Distância e métricas de consumo/preço de combustível devem ser maiores que zero.")
    if not df["delay_days"].mod(1).eq(0).all():
        raise ValueError("delay_days deve conter apenas números inteiros.")

    invalid_statuses = sorted(set(df["delivery_status"]) - DELIVERY_STATUSES)
    if invalid_statuses:
        raise ValueError(f"delivery_status contém categorias inválidas: {invalid_statuses}")

    late_without_delay = df["delivery_status"].eq("Entregue com atraso") & df["delay_days"].eq(0)
    on_time_with_delay = df["delivery_status"].eq("Entregue no prazo") & df["delay_days"].gt(0)
    if late_without_delay.any() or on_time_with_delay.any():
        raise ValueError("delivery_status e delay_days possuem valores inconsistentes.")

    reconciled_cost = df[COST_COLUMNS].sum(axis=1)
    difference = (reconciled_cost - df["total_logistics_cost_brl"]).round(2)
    if difference.abs().ge(0.02).any():
        count = int(difference.abs().ge(0.02).sum())
        raise ValueError(f"Conciliação de custos falhou em {count} entrega(s).")

    fuel_difference = (
        df["fuel_liters"] * df["fuel_price_brl_l"] - df["fuel_cost_brl"]
    ).abs()
    if fuel_difference.ge(0.02).any():
        raise ValueError("Custo de combustível diverge de litros consumidos vezes preço por litro.")

    return df


def run(raw_path=RAW, output_path=OUT):
    raw_path = Path(raw_path)
    output_path = Path(output_path)
    if not raw_path.is_file():
        raise FileNotFoundError(f"Base de entrada não encontrada: {raw_path}")

    df = _validate_input(pd.read_csv(raw_path))
    df["cost_reconciliation_brl"] = (
        df[COST_COLUMNS].sum(axis=1) - df["total_logistics_cost_brl"]
    ).round(2)
    df["cost_reconciliation_ok"] = df["cost_reconciliation_brl"].abs().lt(0.02)
    df["contribution_brl"] = (
        df["freight_revenue_brl"] - df["total_logistics_cost_brl"]
    ).round(2)
    revenue_for_margin = df["freight_revenue_brl"].where(
        df["freight_revenue_brl"].ne(0)
    )
    df["contribution_margin_pct"] = (
        df["contribution_brl"] / revenue_for_margin * 100
    ).round(2)
    df["cost_per_km_brl"] = (
        df["total_logistics_cost_brl"] / df["distance_km"]
    ).round(2)
    df["cost_per_delivery_brl"] = df["total_logistics_cost_brl"].round(2)
    df["year_month"] = df["delivery_date"].dt.to_period("M").astype(str)
    df["is_on_time"] = df["delivery_status"].eq("Entregue no prazo")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(
        f"ETL concluído: {len(df):,} registros; "
        f"conciliação OK: {df['cost_reconciliation_ok'].mean():.1%}"
    )
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida e enriquece a base de entregas.")
    parser.add_argument("--input", type=Path, default=RAW, help="CSV bruto de entregas.")
    parser.add_argument("--output", type=Path, default=OUT, help="Destino do CSV processado.")
    args = parser.parse_args()
    run(raw_path=args.input, output_path=args.output)
