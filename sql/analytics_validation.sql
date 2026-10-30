-- LOGICOST Analytics | Verificacoes da camada de inteligencia
-- Execute apos sql/schema_star.sql, a carga dos dados e src.create_analytics.

-- Resumo executivo: desempenho mensal.
SELECT *
FROM analytics.vw_monthly_performance
ORDER BY month;

-- Composicao total do custo; cost_share_pct deve somar aproximadamente 100%.
SELECT *
FROM analytics.vw_cost_composition
ORDER BY component_cost_brl DESC;

-- Rentabilidade por rota.
SELECT *
FROM analytics.vw_route_profitability
ORDER BY contribution_margin_pct NULLS FIRST, avg_cost_per_delivery_brl DESC;

-- Desempenho de transportadoras, incluindo devolucoes.
SELECT *
FROM analytics.vw_carrier_performance
ORDER BY avg_cost_per_delivery_brl;

-- Rentabilidade regional.
SELECT *
FROM analytics.vw_regional_profitability
ORDER BY contribution_margin_pct NULLS FIRST;

-- Eficiencia de combustivel e custos da frota.
SELECT *
FROM analytics.vw_fleet_efficiency
ORDER BY fuel_efficiency_km_l DESC;

-- Alertas para rotas pelo menos 30 entregas acima da media geral por entrega.
-- Alertas sinalizam itens para investigacao e nao recomendam mudancas operacionais.
SELECT *
FROM analytics.vw_cost_alerts
ORDER BY above_company_avg_pct DESC, deliveries DESC;

-- Simulacao hipotetica: reducao de 8% no gasto total com combustivel.
SELECT *
FROM analytics.vw_fuel_savings_scenario;

-- Verificacoes de integridade: todos os contadores abaixo devem ser zero.
SELECT
    COUNT(*) FILTER (
        WHERE ABS(
            fuel_cost_brl + toll_cost_brl + driver_cost_brl
            + maintenance_cost_brl + third_party_cost_brl
            + warehouse_cost_brl + other_cost_brl
            - total_logistics_cost_brl
        ) >= 0.02
    ) AS cost_reconciliation_errors,
    COUNT(*) FILTER (
        WHERE ABS(fuel_liters * fuel_price_brl_l - fuel_cost_brl) >= 0.02
    ) AS fuel_reconciliation_errors
FROM analytics.fact_deliveries;

-- As participacoes dos componentes devem somar 100% (tolerancia para arredondamento).
SELECT ROUND(SUM(cost_share_pct), 2) AS total_cost_share_pct
FROM analytics.vw_cost_composition;

-- O cenario deve usar exatamente 8%; a economia e potencial, nunca realizada.
SELECT
    assumed_fuel_reduction_pct = 8.00 AS uses_expected_reduction,
    potential_fuel_savings_brl <= current_fuel_cost_brl AS savings_within_fuel_cost,
    estimated_new_logistics_cost_brl <= current_logistics_cost_brl
        AS estimated_cost_not_above_current,
    scenario_notice
FROM analytics.vw_fuel_savings_scenario;

-- Faz o script falhar se a integridade, a composicao ou as premissas nao passarem.
DO $$
DECLARE
    cost_errors bigint;
    fuel_errors bigint;
    cost_share_pct numeric;
    assumed_reduction_pct numeric;
    savings_brl numeric;
    current_fuel_brl numeric;
    estimated_cost_brl numeric;
    current_cost_brl numeric;
BEGIN
    SELECT COUNT(*) FILTER (
        WHERE ABS(
            fuel_cost_brl + toll_cost_brl + driver_cost_brl
            + maintenance_cost_brl + third_party_cost_brl
            + warehouse_cost_brl + other_cost_brl
            - total_logistics_cost_brl
        ) >= 0.02
    ), COUNT(*) FILTER (
        WHERE ABS(fuel_liters * fuel_price_brl_l - fuel_cost_brl) >= 0.02
    )
    INTO cost_errors, fuel_errors
    FROM analytics.fact_deliveries;

    IF cost_errors <> 0 OR fuel_errors <> 0 THEN
        RAISE EXCEPTION
            'Cost or fuel reconciliation failed: cost errors %, fuel errors %',
            cost_errors, fuel_errors;
    END IF;

    SELECT ROUND(SUM(composition.cost_share_pct), 2)
    INTO cost_share_pct
    FROM analytics.vw_cost_composition AS composition;

    IF ABS(cost_share_pct - 100.00) > 0.07 THEN
        RAISE EXCEPTION 'Cost component shares must sum to 100%%; got %',
            cost_share_pct;
    END IF;

    SELECT
        assumed_fuel_reduction_pct,
        potential_fuel_savings_brl,
        current_fuel_cost_brl,
        estimated_new_logistics_cost_brl,
        current_logistics_cost_brl
    INTO
        assumed_reduction_pct,
        savings_brl,
        current_fuel_brl,
        estimated_cost_brl,
        current_cost_brl
    FROM analytics.vw_fuel_savings_scenario;

    IF assumed_reduction_pct <> 8.00
       OR savings_brl > current_fuel_brl
       OR estimated_cost_brl > current_cost_brl THEN
        RAISE EXCEPTION 'Fuel savings scenario does not match the stated assumptions';
    END IF;
END $$;
