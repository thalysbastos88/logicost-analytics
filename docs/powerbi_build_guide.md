# Dashboards interativos

## App Streamlit
Na pasta raiz, instale as dependências com `python -m pip install -r requirements.txt` e execute `python -m streamlit run src/dashboard.py`. O app carrega e valida os dados sintéticos, permite filtrar o período e as dimensões da operação, e inclui sete análises, exportação CSV e um simulador financeiro hipotético de combustível. O app local não depende de conexão ao PostgreSQL.

## Guia de construção do dashboard no Power BI

1. Na raiz do projeto, execute `python -m src.etl` para gerar `data/processed/deliveries_enriched.csv`.
2. No Power BI Desktop, importe o CSV processado.
3. Defina `delivery_date` como Data e os campos financeiros como Número decimal / Moeda (R$).
4. Crie uma tabela calendário e relacione `Calendar[Date]` com `deliveries_enriched[delivery_date]`.
5. Crie as medidas em `powerbi/measures.dax` (ajuste nomes se usar tabela calendário).
6. Configure segmentadores: período, região, rota, veículo, transportadora e situação.
7. Crie páginas para desempenho mensal, composição de custos, rentabilidade por rota, transportadoras, rentabilidade regional, eficiência da frota, alertas de custo e qualidade operacional.
8. Use títulos dinâmicos e tooltips para explicar granularidade e definições.
9. Exiba as medidas `Economia Potencial Combustível 8%` e `Custo Logístico Simulado Pós Redução` com um rótulo claro de cenário hipotético; não apresente a economia como realizada.

## Layout recomendado
- Linha superior: Receita, Custo, Resultado, Margem.
- Segunda linha: Custo/entrega, Custo/km, Entregas, % no prazo.
- Centro: tendência mensal de custo e receita.
- Rodapé: composição dos custos e ranking de rotas.
- Cores semânticas consistentes e acessibilidade (contraste, rótulos, não depender apenas de cor).

As medidas de custo por km e margem são calculadas como razões entre totais, evitando médias simples de percentuais ou custos unitários por entrega.
