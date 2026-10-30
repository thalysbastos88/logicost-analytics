# Dicionário de dados

| Campo | Descrição | Unidade |
|---|---|---|
| delivery_id | Identificador único da entrega | texto |
| delivery_date | Data da entrega | data |
| region | Região operacional | categoria |
| route_id | Identificador da rota | texto |
| vehicle_id | Identificador do veículo | texto |
| carrier | Modalidade / transportadora | categoria |
| distance_km | Distância atribuída à entrega | km |
| fuel_efficiency_km_l | Eficiência média | km/L |
| fuel_liters | Litros consumidos estimados | L |
| fuel_price_brl_l | Preço médio do combustível | R$/L |
| fuel_cost_brl | Custo de combustível | R$ |
| toll_cost_brl | Pedágios | R$ |
| driver_cost_brl | Custo de motorista alocado | R$ |
| maintenance_cost_brl | Manutenção alocada | R$ |
| third_party_cost_brl | Custo de terceiro | R$ |
| warehouse_cost_brl | Custo de armazenagem/manuseio | R$ |
| other_cost_brl | Outros custos | R$ |
| total_logistics_cost_brl | Soma dos componentes | R$ |
| freight_revenue_brl | Receita de frete atribuída | R$ |
| delivery_status | Situação da entrega | categoria |
| delay_days | Dias de atraso | dias |
| cost_reconciliation_brl | Diferença entre componentes e custo logístico total | R$ |
| cost_reconciliation_ok | Resultado da regra de conciliação de custos | booleano |
| contribution_brl | Receita menos custo logístico | R$ |
| contribution_margin_pct | Resultado dividido pela receita de frete | % |
| cost_per_km_brl | Custo logístico dividido pela distância | R$/km |
| cost_per_delivery_brl | Custo logístico atribuído à entrega | R$ |
| year_month | Competência da entrega no formato AAAA-MM | texto |
| is_on_time | Indica entrega concluída no prazo | booleano |

Granularidade: uma linha por entrega. Valores gerados sinteticamente; custos são alocações simuladas. A média por km dos KPIs executivos é ponderada: custo total dividido pela distância total.
