-- 1. Visão mensal de custo, receita e contribuição
SELECT date_trunc('month', delivery_date)::date AS month,
       COUNT(*) AS deliveries,
       SUM(total_logistics_cost_brl) AS total_cost,
       SUM(freight_revenue_brl) AS revenue,
       SUM(freight_revenue_brl-total_logistics_cost_brl) AS contribution,
       ROUND(100.0*SUM(freight_revenue_brl-total_logistics_cost_brl)/NULLIF(SUM(freight_revenue_brl),0),2) AS contribution_margin_pct
FROM analytics.vw_deliveries_analytics GROUP BY 1 ORDER BY 1;

-- 2. Rotas com maior custo médio por entrega
SELECT route_id, COUNT(*) AS deliveries,
       ROUND(AVG(total_logistics_cost_brl),2) AS avg_cost_delivery,
       ROUND(SUM(total_logistics_cost_brl)/NULLIF(SUM(distance_km),0),2) AS cost_per_km
FROM analytics.vw_deliveries_analytics GROUP BY route_id
HAVING COUNT(*) >= 30 ORDER BY avg_cost_delivery DESC;

-- 3. Composição de custos
SELECT SUM(fuel_cost_brl) fuel, SUM(toll_cost_brl) toll,
       SUM(driver_cost_brl) driver, SUM(maintenance_cost_brl) maintenance,
       SUM(third_party_cost_brl) third_party, SUM(warehouse_cost_brl) warehouse,
       SUM(other_cost_brl) other
FROM analytics.vw_deliveries_analytics;

-- 4. Comparativo de transportadoras
SELECT carrier, COUNT(*) deliveries,
       ROUND(AVG(total_logistics_cost_brl),2) avg_cost,
       ROUND(AVG(distance_km),1) avg_distance,
       ROUND(100.0*AVG(CASE WHEN delivery_status='Entregue no prazo' THEN 1.0 ELSE 0.0 END),2) on_time_pct
FROM analytics.vw_deliveries_analytics GROUP BY carrier ORDER BY avg_cost;

-- 5. Diagnóstico regional de devoluções e atraso
SELECT region, COUNT(*) deliveries,
       ROUND(100.0*AVG(CASE WHEN delivery_status='Devolvida' THEN 1.0 ELSE 0.0 END),2) return_pct,
       ROUND(100.0*AVG(CASE WHEN delivery_status='Entregue com atraso' THEN 1.0 ELSE 0.0 END),2) late_pct
FROM analytics.vw_deliveries_analytics GROUP BY region ORDER BY return_pct DESC;
