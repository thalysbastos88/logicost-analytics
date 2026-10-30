-- LOGICOST Analytics | Camada de inteligencia e cenarios hipoteticos
-- Requer o esquema analytics criado por sql/schema_star.sql.

CREATE OR REPLACE VIEW analytics.vw_monthly_performance AS
SELECT
    DATE_TRUNC('month', delivery_date)::date AS month,
    COUNT(*) AS deliveries,
    SUM(freight_revenue_brl) AS freight_revenue_brl,
    SUM(total_logistics_cost_brl) AS total_logistics_cost_brl,
    SUM(contribution_brl) AS contribution_brl,
    ROUND(
        100.0 * SUM(contribution_brl)
        / NULLIF(SUM(freight_revenue_brl), 0),
        2
    ) AS contribution_margin_pct
FROM analytics.vw_deliveries_analytics
GROUP BY 1;

CREATE OR REPLACE VIEW analytics.vw_cost_composition AS
WITH cost_totals AS (
    SELECT
        SUM(fuel_cost_brl) AS fuel_cost_brl,
        SUM(toll_cost_brl) AS toll_cost_brl,
        SUM(driver_cost_brl) AS driver_cost_brl,
        SUM(maintenance_cost_brl) AS maintenance_cost_brl,
        SUM(third_party_cost_brl) AS third_party_cost_brl,
        SUM(warehouse_cost_brl) AS warehouse_cost_brl,
        SUM(other_cost_brl) AS other_cost_brl,
        SUM(total_logistics_cost_brl) AS total_logistics_cost_brl
    FROM analytics.vw_deliveries_analytics
)
SELECT
    component.component_name,
    component.component_cost_brl,
    totals.total_logistics_cost_brl,
    ROUND(
        100.0 * component.component_cost_brl
        / NULLIF(totals.total_logistics_cost_brl, 0),
        2
    ) AS cost_share_pct
FROM cost_totals AS totals
CROSS JOIN LATERAL (
    VALUES
        ('Combustível', totals.fuel_cost_brl),
        ('Pedágio', totals.toll_cost_brl),
        ('Motorista', totals.driver_cost_brl),
        ('Manutenção', totals.maintenance_cost_brl),
        ('Terceiros', totals.third_party_cost_brl),
        ('Armazenagem', totals.warehouse_cost_brl),
        ('Outros', totals.other_cost_brl)
) AS component(component_name, component_cost_brl);

CREATE OR REPLACE VIEW analytics.vw_route_profitability AS
SELECT
    route_id,
    COUNT(*) AS deliveries,
    SUM(freight_revenue_brl) AS freight_revenue_brl,
    SUM(total_logistics_cost_brl) AS total_logistics_cost_brl,
    SUM(contribution_brl) AS contribution_brl,
    ROUND(
        100.0 * SUM(contribution_brl)
        / NULLIF(SUM(freight_revenue_brl), 0),
        2
    ) AS contribution_margin_pct,
    ROUND(AVG(total_logistics_cost_brl), 2) AS avg_cost_per_delivery_brl,
    ROUND(
        SUM(total_logistics_cost_brl) / NULLIF(SUM(distance_km), 0),
        2
    ) AS cost_per_km_brl
FROM analytics.vw_deliveries_analytics
GROUP BY route_id;

CREATE OR REPLACE VIEW analytics.vw_carrier_performance AS
SELECT
    carrier,
    COUNT(*) AS deliveries,
    SUM(freight_revenue_brl) AS freight_revenue_brl,
    SUM(total_logistics_cost_brl) AS total_logistics_cost_brl,
    ROUND(AVG(total_logistics_cost_brl), 2) AS avg_cost_per_delivery_brl,
    ROUND(
        SUM(total_logistics_cost_brl) / NULLIF(SUM(distance_km), 0),
        2
    ) AS cost_per_km_brl,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE delivery_status = 'Entregue no prazo'
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS on_time_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE delivery_status = 'Devolvida'
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS return_rate_pct
FROM analytics.vw_deliveries_analytics
GROUP BY carrier;

CREATE OR REPLACE VIEW analytics.vw_regional_profitability AS
SELECT
    region,
    COUNT(*) AS deliveries,
    SUM(freight_revenue_brl) AS freight_revenue_brl,
    SUM(total_logistics_cost_brl) AS total_logistics_cost_brl,
    SUM(contribution_brl) AS contribution_brl,
    ROUND(
        100.0 * SUM(contribution_brl)
        / NULLIF(SUM(freight_revenue_brl), 0),
        2
    ) AS contribution_margin_pct
FROM analytics.vw_deliveries_analytics
GROUP BY region;

CREATE OR REPLACE VIEW analytics.vw_fleet_efficiency AS
SELECT
    vehicle_id,
    COUNT(*) AS deliveries,
    SUM(distance_km) AS distance_km,
    SUM(fuel_liters) AS fuel_liters,
    ROUND(
        SUM(distance_km) / NULLIF(SUM(fuel_liters), 0),
        2
    ) AS fuel_efficiency_km_l,
    SUM(fuel_cost_brl) AS fuel_cost_brl,
    ROUND(
        SUM(fuel_cost_brl) / NULLIF(SUM(distance_km), 0),
        2
    ) AS fuel_cost_per_km_brl,
    ROUND(
        SUM(total_logistics_cost_brl) / NULLIF(SUM(distance_km), 0),
        2
    ) AS total_cost_per_km_brl
FROM analytics.vw_deliveries_analytics
GROUP BY vehicle_id;

CREATE OR REPLACE VIEW analytics.vw_cost_alerts AS
WITH company_benchmark AS (
    SELECT AVG(total_logistics_cost_brl) AS company_avg_cost_per_delivery_brl
    FROM analytics.vw_deliveries_analytics
),
route_costs AS (
    SELECT
        route_id,
        COUNT(*) AS deliveries,
        AVG(total_logistics_cost_brl) AS avg_cost_per_delivery_brl,
        SUM(total_logistics_cost_brl) AS total_logistics_cost_brl,
        SUM(freight_revenue_brl) AS freight_revenue_brl,
        SUM(distance_km) AS distance_km
    FROM analytics.vw_deliveries_analytics
    GROUP BY route_id
)
SELECT
    routes.route_id,
    routes.deliveries,
    ROUND(routes.avg_cost_per_delivery_brl, 2) AS avg_cost_per_delivery_brl,
    ROUND(benchmark.company_avg_cost_per_delivery_brl, 2)
        AS company_avg_cost_per_delivery_brl,
    ROUND(
        100.0 * (
            routes.avg_cost_per_delivery_brl
            / NULLIF(benchmark.company_avg_cost_per_delivery_brl, 0) - 1
        ),
        2
    ) AS above_company_avg_pct,
    ROUND(
        routes.total_logistics_cost_brl / NULLIF(routes.distance_km, 0),
        2
    ) AS cost_per_km_brl,
    ROUND(
        100.0 * (
            routes.freight_revenue_brl - routes.total_logistics_cost_brl
        ) / NULLIF(routes.freight_revenue_brl, 0),
        2
    ) AS contribution_margin_pct,
    'Sinal para investigacao; nao e recomendacao operacional.'::text AS alert_note
FROM route_costs AS routes
CROSS JOIN company_benchmark AS benchmark
WHERE routes.deliveries >= 30
  AND routes.avg_cost_per_delivery_brl > benchmark.company_avg_cost_per_delivery_brl;

-- Simulacao financeira hipotetica. Edite o fator apenas para testar outros
-- cenarios; esta view nao representa economia realizada nem recomendacao.
CREATE OR REPLACE VIEW analytics.vw_fuel_savings_scenario AS
WITH scenario AS (
    SELECT 0.08::numeric AS assumed_fuel_reduction_pct
),
current_costs AS (
    SELECT
        SUM(fuel_cost_brl) AS current_fuel_cost_brl,
        SUM(total_logistics_cost_brl) AS current_logistics_cost_brl
    FROM analytics.vw_deliveries_analytics
)
SELECT
    'Simulacao hipotetica; nao representa economia realizada.'::text
        AS scenario_notice,
    scenario.assumed_fuel_reduction_pct * 100 AS assumed_fuel_reduction_pct,
    current_costs.current_fuel_cost_brl,
    current_costs.current_logistics_cost_brl,
    ROUND(
        current_costs.current_fuel_cost_brl
        * scenario.assumed_fuel_reduction_pct,
        2
    ) AS potential_fuel_savings_brl,
    ROUND(
        current_costs.current_logistics_cost_brl
        - current_costs.current_fuel_cost_brl
        * scenario.assumed_fuel_reduction_pct,
        2
    ) AS estimated_new_logistics_cost_brl
FROM current_costs
CROSS JOIN scenario;
