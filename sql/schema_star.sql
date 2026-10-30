-- LOGICOST Analytics | Modelo dimensional (star schema)
-- Execute este arquivo no banco logicost_db.

CREATE SCHEMA IF NOT EXISTS analytics;
SET search_path TO analytics, public;

CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    year SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    day SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_region (
    region_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_name VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_route (
    route_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_code VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_vehicle (
    vehicle_key INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_code VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_carrier (
    carrier_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    carrier_name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_delivery_status (
    status_key SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status_name VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_deliveries (
    delivery_id VARCHAR(20) PRIMARY KEY,
    delivery_date DATE NOT NULL REFERENCES dim_date(date_key),
    region_key SMALLINT NOT NULL REFERENCES dim_region(region_key),
    route_key INTEGER NOT NULL REFERENCES dim_route(route_key),
    vehicle_key INTEGER NOT NULL REFERENCES dim_vehicle(vehicle_key),
    carrier_key SMALLINT NOT NULL REFERENCES dim_carrier(carrier_key),
    status_key SMALLINT NOT NULL REFERENCES dim_delivery_status(status_key),

    distance_km NUMERIC(12,2) NOT NULL CHECK (distance_km > 0),
    fuel_efficiency_km_l NUMERIC(8,2) NOT NULL CHECK (fuel_efficiency_km_l > 0),
    fuel_liters NUMERIC(12,2) NOT NULL CHECK (fuel_liters > 0),
    fuel_price_brl_l NUMERIC(10,2) NOT NULL CHECK (fuel_price_brl_l > 0),
    fuel_cost_brl NUMERIC(12,2) NOT NULL CHECK (fuel_cost_brl >= 0),
    toll_cost_brl NUMERIC(12,2) NOT NULL CHECK (toll_cost_brl >= 0),
    driver_cost_brl NUMERIC(12,2) NOT NULL CHECK (driver_cost_brl >= 0),
    maintenance_cost_brl NUMERIC(12,2) NOT NULL CHECK (maintenance_cost_brl >= 0),
    third_party_cost_brl NUMERIC(12,2) NOT NULL CHECK (third_party_cost_brl >= 0),
    warehouse_cost_brl NUMERIC(12,2) NOT NULL CHECK (warehouse_cost_brl >= 0),
    other_cost_brl NUMERIC(12,2) NOT NULL CHECK (other_cost_brl >= 0),
    total_logistics_cost_brl NUMERIC(12,2) NOT NULL CHECK (total_logistics_cost_brl >= 0),
    freight_revenue_brl NUMERIC(12,2) NOT NULL CHECK (freight_revenue_brl >= 0),
    delay_days INTEGER NOT NULL DEFAULT 0 CHECK (delay_days >= 0),

    CHECK (
        ABS(fuel_liters * fuel_price_brl_l - fuel_cost_brl) < 0.02
    ),
    CHECK (
        ABS(
            fuel_cost_brl + toll_cost_brl + driver_cost_brl +
            maintenance_cost_brl + third_party_cost_brl +
            warehouse_cost_brl + other_cost_brl - total_logistics_cost_brl
        ) < 0.02
    ),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_deliveries_date ON fact_deliveries(delivery_date);
CREATE INDEX IF NOT EXISTS idx_fact_deliveries_region ON fact_deliveries(region_key);
CREATE INDEX IF NOT EXISTS idx_fact_deliveries_route ON fact_deliveries(route_key);
CREATE INDEX IF NOT EXISTS idx_fact_deliveries_carrier ON fact_deliveries(carrier_key);
CREATE INDEX IF NOT EXISTS idx_fact_deliveries_status ON fact_deliveries(status_key);

-- View para consumo simplificado no Power BI e em análises exploratórias.
CREATE OR REPLACE VIEW vw_deliveries_analytics AS
SELECT
    f.delivery_id, f.delivery_date,
    EXTRACT(YEAR FROM f.delivery_date)::INT AS year,
    EXTRACT(MONTH FROM f.delivery_date)::INT AS month,
    r.region_name AS region,
    rt.route_code AS route_id,
    v.vehicle_code AS vehicle_id,
    c.carrier_name AS carrier,
    s.status_name AS delivery_status,
    f.distance_km, f.fuel_efficiency_km_l, f.fuel_liters, f.fuel_price_brl_l,
    f.fuel_cost_brl, f.toll_cost_brl, f.driver_cost_brl,
    f.maintenance_cost_brl, f.third_party_cost_brl, f.warehouse_cost_brl,
    f.other_cost_brl, f.total_logistics_cost_brl, f.freight_revenue_brl,
    (f.freight_revenue_brl - f.total_logistics_cost_brl) AS contribution_brl,
    ROUND(100.0 * (f.freight_revenue_brl - f.total_logistics_cost_brl)
        / NULLIF(f.freight_revenue_brl, 0), 2) AS contribution_margin_pct,
    ROUND(f.total_logistics_cost_brl / NULLIF(f.distance_km, 0), 2) AS cost_per_km_brl,
    f.delay_days
FROM fact_deliveries f
JOIN dim_region r ON r.region_key = f.region_key
JOIN dim_route rt ON rt.route_key = f.route_key
JOIN dim_vehicle v ON v.vehicle_key = f.vehicle_key
JOIN dim_carrier c ON c.carrier_key = f.carrier_key
JOIN dim_delivery_status s ON s.status_key = f.status_key;
