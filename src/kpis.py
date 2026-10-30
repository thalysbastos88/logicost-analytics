import argparse
import json

import pandas as pd

from src.etl import COST_COLUMNS, OUT


def build_kpis(path=OUT):
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("Não é possível calcular KPIs para uma base vazia.")

    total_cost = float(df["total_logistics_cost_brl"].sum())
    revenue = float(df["freight_revenue_brl"].sum())
    total_distance = float(df["distance_km"].sum())
    contribution = revenue - total_cost

    return {
        "deliveries": int(len(df)),
        "total_cost_brl": round(total_cost, 2),
        "freight_revenue_brl": round(revenue, 2),
        "contribution_brl": round(contribution, 2),
        "contribution_margin_pct": (
            round(contribution / revenue * 100, 2) if revenue else None
        ),
        "avg_cost_per_delivery_brl": round(total_cost / len(df), 2),
        "avg_cost_per_km_brl": (
            round(total_cost / total_distance, 2) if total_distance else None
        ),
        "on_time_rate_pct": round(
            df["delivery_status"].eq("Entregue no prazo").mean() * 100, 2
        ),
        "return_rate_pct": round(
            df["delivery_status"].eq("Devolvida").mean() * 100, 2
        ),
        "cost_breakdown_brl": {
            column.removesuffix("_cost_brl"): round(float(df[column].sum()), 2)
            for column in COST_COLUMNS
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula KPIs da base processada.")
    parser.add_argument("--input", default=str(OUT), help="CSV processado de entregas.")
    args = parser.parse_args()
    print(json.dumps(build_kpis(args.input), ensure_ascii=False, indent=2))
