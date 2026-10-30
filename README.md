# LOGICOST Analytics
### Inteligência de custos e rentabilidade para operações logísticas

[![CI](https://github.com/thalysbastos88/logicost-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/thalysbastos88/logicost-analytics/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

> Projeto de portfólio com dados 100% sintéticos. Não representa resultados de uma empresa real.

## Problema de negócio
Operações logísticas precisam entender como combustível, pedágios, mão de obra, manutenção, armazenagem e contratação de terceiros afetam o custo por entrega, o custo por quilômetro e a rentabilidade. O LOGICOST consolida esses dados para apoiar decisões de gestão.

## Objetivos
- Consolidar custos e receitas por entrega.
- Calcular custo por entrega, custo por km e margem de contribuição.
- Comparar rotas, regiões, veículos e transportadoras.
- Monitorar atrasos e devoluções como dimensões operacionais relacionadas ao custo.
- Identificar desvios e apoiar priorização de investigações.

## Stack
Python, Pandas, NumPy, PostgreSQL, SQL, Plotly, Streamlit e Power BI (DAX).

## Arquitetura
CSV sintético (raw) -> validação e transformação Python (processed) -> PostgreSQL (camada analítica) -> Power BI.

```mermaid
flowchart LR
    A[Gerador Python / CSV bruto] --> B[ETL e regras de qualidade]
    B --> C[CSV enriquecido]
    C --> D[PostgreSQL / esquema estrela]
    D --> E[Consultas SQL e Power BI]
```

## Estrutura
- `data/raw/deliveries.csv`: base sintética de 5.000 entregas.
- `data/processed/deliveries_enriched.csv`: resultado do ETL; gerado localmente.
- `src/generate_data.py`: geração reproduzível dos dados.
- `src/etl.py`: validações, conciliação e métricas derivadas.
- `src/kpis.py`: resumo de indicadores.
- `src/load_postgres.py`: carga idempotente para o PostgreSQL.
- `src/create_analytics.py`: cria as views analíticas no PostgreSQL.
- `src/dashboard.py`: dashboard interativo com filtros, sete análises e simulador.
- `sql/`: DDL e consultas analíticas.
- `powerbi/measures.dax`: medidas para o modelo Power BI.
- `docs/`: dicionário e roteiro de dashboard.
- `.github/workflows/ci.yml`: testes automatizados e integração com PostgreSQL em pull requests e pushes.

## Como executar
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.generate_data
python -m src.etl
python -m src.kpis
python -m pytest -q
```

## Dashboard interativo
Instale as dependências do projeto e, a partir da pasta raiz, execute:

```bash
python -m streamlit run src/dashboard.py
```

O dashboard valida a base sintética ao carregar, atualiza os indicadores por período, região, transportadora, rota, veículo e situação e permite exportar as entregas filtradas para CSV. As abas incluem desempenho mensal, composição e rentabilidade, operação e frota e um simulador ajustável de economia potencial em combustível. O dashboard funciona sem PostgreSQL; o banco de dados é necessário apenas para as cargas e views analíticas. A simulação é hipotética e não representa economia realizada ou recomendação operacional.

## Modelo de dados
O esquema estrela `analytics` tem uma linha por entrega em `fact_deliveries` e dimensões conformadas para data, região, rota, veículo, transportadora e situação. A view `analytics.vw_deliveries_analytics` simplifica consultas e consumo no Power BI. `sql/schema.sql` é o esquema plano legado; para a implementação dimensional, use `sql/schema_star.sql`.

## Definições dos KPIs
- Custo logístico total: soma dos componentes de custo.
- Custo médio por entrega: custo total / quantidade de entregas.
- Custo por km: custo total / km total.
- Resultado operacional simplificado: receita de frete - custo logístico.
- Margem de contribuição: resultado / receita de frete.
- Entregas no prazo: entregas com status `Entregue no prazo` / total de entregas.
- Taxa de devolução: devolvidas / total de entregas.

**Nota metodológica:** resultado operacional aqui é uma contribuição simplificada do conjunto de custos incluídos na base; não equivale a uma DRE contábil completa. Não há impostos, despesas administrativas, depreciação, custo financeiro ou reconhecimento contábil.

## Dashboard Power BI sugerido
1. **Desempenho mensal:** receita, custo, resultado, margem e evolução mensal.
2. **Composição dos custos:** participação de combustível, pedágio, mão de obra, manutenção, terceiros e armazenagem.
3. **Rentabilidade por rota:** custo por entrega, custo por km e margem de contribuição.
4. **Transportadoras:** custo, pontualidade e taxa de devoluções.
5. **Rentabilidade regional:** receita, custo e margem por região.
6. **Eficiência da frota:** consumo de combustível e custo por quilômetro.
7. **Alertas e qualidade:** rotas acima da média geral, atrasos e devoluções; use os alertas para investigação, não como recomendação automática.

## Controles de qualidade
- Identificador de entrega único.
- Campos obrigatórios presentes e sem nulos ou texto em branco.
- Datas e categorias de situação válidas; consistência entre situação e dias de atraso.
- Métricas não negativas e distância/consumo/preço de combustível maiores que zero.
- Conciliação entre componentes e custo total, e entre litros, preço e custo de combustível.
- Dados reproduzíveis via seed fixa.
- Testes automatizados para dados inválidos, conciliação e cálculo dos KPIs.

## Limitações e próximos passos
- Dados sintéticos e distribuições simuladas; não usar para decisões reais.
- Adicionar custos de capacidade ociosa, manutenção por ordem de serviço e custo de reentrega.
- Orquestração agendada e monitoramento contínuo.
- Comparar rotas realmente equivalentes antes de investigar ou propor mudanças operacionais.
- ML só após existir histórico real e definição clara do alvo; evitar previsões artificiais sem validação.

## Ética e transparência
Todos os dados são fictícios, gerados para fins educacionais. Indicadores e conclusões apresentados em publicações devem ser identificados como simulações.


## PostgreSQL: modelagem e carga
1. Crie um banco chamado `logicost_db` no PostgreSQL.
2. Copie `.env.example` para `.env` e informe host, porta, banco, usuário e senha. Nunca publique `.env`.
3. Execute `sql/schema_star.sql` no banco `logicost_db` (pgAdmin ou psql).
4. Instale as dependências atualizadas: `pip install -r requirements.txt`.
5. Gere e valide os dados: `python -m src.generate_data` e `python -m src.etl`.
6. Calcule os indicadores locais: `python -m src.kpis`.
7. Carregue o CSV processado, dimensões e fato: `python -m src.load_postgres`.
8. Valide com `sql/validation_queries.sql`.
9. Crie as sete visões analíticas e a simulação de custos: `python -m src.create_analytics`.
10. Abra `sql/analytics_validation.sql` no pgAdmin e execute as consultas para explorar as análises.

A carga usa `ON CONFLICT` para permitir reexecução sem duplicar entregas. Execute os comandos a partir da raiz do projeto. As métricas por km nos KPIs são ponderadas (`custo total / distância total`), e o custo por entrega inclui entregas devolvidas, pois seus custos também foram incorridos.

## Nova camada de inteligência
`sql/analytics_views.sql` define sete views: `vw_monthly_performance`, `vw_cost_composition`, `vw_route_profitability`, `vw_carrier_performance`, `vw_regional_profitability`, `vw_fleet_efficiency` e `vw_cost_alerts`. A view `vw_fuel_savings_scenario` acrescenta uma simulação hipotética de redução de 8% nos custos atuais de combustível. Execute `sql/analytics_validation.sql` para consultar todas as análises e verificar conciliações.

Na amostra atual, o cenário calcula R$ 387.348,76 em combustível, R$ 30.987,90 de economia potencial e R$ 1.083.272,47 em custo logístico estimado após a redução hipotética. O benchmark de alertas é a média global de custo por entrega; uma rota só aparece se tiver pelo menos 30 entregas e custo médio acima do benchmark. Isso sinaliza uma investigação, não identifica a causa do custo e não recomenda alteração operacional. A simulação estima a economia potencial no mesmo escopo dos dados. Não é uma economia realizada nem uma recomendação: decisões operacionais exigem comparar rotas e operações semelhantes, controlar diferenças de distância, veículo, transportadora e nível de serviço, e validar os resultados com dados reais.

## Exemplo da base sintética
Na amostra reproduzível de 5.000 registros, o pipeline calcula custo logístico de R$ 1.114.260,37, receita de frete de R$ 926.650,04 e margem de contribuição de -20,25%. Esses valores são apenas resultados simulados e não representam uma operação real. O [perfil completo da amostra](docs/sample_data_profile.json) detalha os indicadores e a composição de custos.
