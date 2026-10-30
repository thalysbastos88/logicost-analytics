-- Conferência geral da carga
SELECT COUNT(*) AS total_entregas,
       COUNT(DISTINCT delivery_id) AS ids_unicos,
       SUM(total_logistics_cost_brl) AS custo_total,
       SUM(freight_revenue_brl) AS receita_total
FROM analytics.fact_deliveries;

-- Conciliação dos componentes de custo
SELECT COUNT(*) AS divergencias
FROM analytics.fact_deliveries
WHERE ABS(
    fuel_cost_brl + toll_cost_brl + driver_cost_brl +
    maintenance_cost_brl + third_party_cost_brl +
    warehouse_cost_brl + other_cost_brl - total_logistics_cost_brl
) >= 0.02;

-- Conciliação de combustível
SELECT COUNT(*) AS divergencias_combustivel
FROM analytics.fact_deliveries
WHERE ABS(fuel_liters * fuel_price_brl_l - fuel_cost_brl) >= 0.02;

-- Situação e atraso inconsistentes
SELECT COUNT(*) AS situacoes_inconsistentes
FROM analytics.vw_deliveries_analytics
WHERE (delivery_status = 'Entregue com atraso' AND delay_days = 0)
   OR (delivery_status = 'Entregue no prazo' AND delay_days > 0);

-- View de consumo analítico
SELECT region, COUNT(*) AS entregas,
       ROUND(AVG(total_logistics_cost_brl),2) AS custo_medio_entrega,
       ROUND(SUM(total_logistics_cost_brl) / NULLIF(SUM(distance_km),0),2) AS custo_por_km,
       ROUND(100.0 * SUM(contribution_brl) / NULLIF(SUM(freight_revenue_brl),0),2) AS margem_pct
FROM analytics.vw_deliveries_analytics
GROUP BY region
ORDER BY custo_medio_entrega DESC;
