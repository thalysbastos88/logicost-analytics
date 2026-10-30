import pandas as pd
from psycopg import sql
from src.db import get_connection
from src.etl import run as run_etl

def load_data():
    df = run_etl()

    rows = df.to_dict("records")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Dimensões: cargas idempotentes (reexecução não duplica registros).
            dates = sorted({pd.Timestamp(value).date() for value in df["delivery_date"]})
            cur.executemany(
                """INSERT INTO analytics.dim_date
                   (date_key, year, quarter, month, month_name, day, day_of_week, is_weekend)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (date_key) DO NOTHING""",
                [(d, d.year, (d.month-1)//3+1, d.month, d.strftime("%B"),
                  d.day, d.isoweekday(), d.isoweekday() >= 6) for d in dates]
            )

            dimension_specs = [
                ("region", "dim_region", "region_name"),
                ("route_id", "dim_route", "route_code"),
                ("vehicle_id", "dim_vehicle", "vehicle_code"),
                ("carrier", "dim_carrier", "carrier_name"),
                ("delivery_status", "dim_delivery_status", "status_name")
            ]
            for source_col, table, target_col in dimension_specs:
                values = sorted(df[source_col].dropna().unique().tolist())
                query = sql.SQL(
                    "INSERT INTO analytics.{} ({}) VALUES (%s) ON CONFLICT ({}) DO NOTHING"
                ).format(sql.Identifier(table), sql.Identifier(target_col),
                         sql.Identifier(target_col))
                cur.executemany(query, [(value,) for value in values])

            # Mapeamento das chaves substitutas.
            def lookup(table, key_col, value_col):
                cur.execute(
                    sql.SQL("SELECT {}, {} FROM analytics.{}").format(
                        sql.Identifier(key_col), sql.Identifier(value_col),
                        sql.Identifier(table)
                    )
                )
                return {value: key for key, value in cur.fetchall()}

            region_map = lookup("dim_region", "region_key", "region_name")
            route_map = lookup("dim_route", "route_key", "route_code")
            vehicle_map = lookup("dim_vehicle", "vehicle_key", "vehicle_code")
            carrier_map = lookup("dim_carrier", "carrier_key", "carrier_name")
            status_map = lookup("dim_delivery_status", "status_key", "status_name")

            fact_rows = []
            for row in rows:
                fact_rows.append((
                    row["delivery_id"], pd.Timestamp(row["delivery_date"]).date(),
                    region_map[row["region"]], route_map[row["route_id"]],
                    vehicle_map[row["vehicle_id"]], carrier_map[row["carrier"]],
                    status_map[row["delivery_status"]],
                    row["distance_km"], row["fuel_efficiency_km_l"], row["fuel_liters"],
                    row["fuel_price_brl_l"], row["fuel_cost_brl"], row["toll_cost_brl"],
                    row["driver_cost_brl"], row["maintenance_cost_brl"],
                    row["third_party_cost_brl"], row["warehouse_cost_brl"],
                    row["other_cost_brl"], row["total_logistics_cost_brl"],
                    row["freight_revenue_brl"], int(row["delay_days"])
                ))

            cur.executemany(
                """INSERT INTO analytics.fact_deliveries (
                    delivery_id, delivery_date, region_key, route_key, vehicle_key,
                    carrier_key, status_key, distance_km, fuel_efficiency_km_l,
                    fuel_liters, fuel_price_brl_l, fuel_cost_brl, toll_cost_brl,
                    driver_cost_brl, maintenance_cost_brl, third_party_cost_brl,
                    warehouse_cost_brl, other_cost_brl, total_logistics_cost_brl,
                    freight_revenue_brl, delay_days
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (delivery_id) DO UPDATE SET
                    delivery_date=EXCLUDED.delivery_date,
                    region_key=EXCLUDED.region_key, route_key=EXCLUDED.route_key,
                    vehicle_key=EXCLUDED.vehicle_key, carrier_key=EXCLUDED.carrier_key,
                    status_key=EXCLUDED.status_key, distance_km=EXCLUDED.distance_km,
                    fuel_efficiency_km_l=EXCLUDED.fuel_efficiency_km_l,
                    fuel_liters=EXCLUDED.fuel_liters, fuel_price_brl_l=EXCLUDED.fuel_price_brl_l,
                    fuel_cost_brl=EXCLUDED.fuel_cost_brl, toll_cost_brl=EXCLUDED.toll_cost_brl,
                    driver_cost_brl=EXCLUDED.driver_cost_brl,
                    maintenance_cost_brl=EXCLUDED.maintenance_cost_brl,
                    third_party_cost_brl=EXCLUDED.third_party_cost_brl,
                    warehouse_cost_brl=EXCLUDED.warehouse_cost_brl,
                    other_cost_brl=EXCLUDED.other_cost_brl,
                    total_logistics_cost_brl=EXCLUDED.total_logistics_cost_brl,
                    freight_revenue_brl=EXCLUDED.freight_revenue_brl,
                    delay_days=EXCLUDED.delay_days""",
                fact_rows
            )

            cur.execute("SELECT COUNT(*) FROM analytics.fact_deliveries")
            total = cur.fetchone()[0]

    print(f"Carga concluída. Entregas processadas: {len(df):,}; registros na fato: {total:,}")
    print("View disponível: analytics.vw_deliveries_analytics")

if __name__ == "__main__":
    load_data()
