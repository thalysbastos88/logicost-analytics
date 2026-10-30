from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.etl import OUT, RAW, run as run_etl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / RAW
PROCESSED_FILE = PROJECT_ROOT / OUT
COST_COMPONENTS = {
    "Combustível": "fuel_cost_brl",
    "Pedágios": "toll_cost_brl",
    "Motorista": "driver_cost_brl",
    "Manutenção": "maintenance_cost_brl",
    "Terceiros": "third_party_cost_brl",
    "Armazenagem": "warehouse_cost_brl",
    "Outros": "other_cost_brl",
}
COLORS = {
    "ink": "#142b3b",
    "muted": "#718396",
    "teal": "#00a38b",
    "blue": "#5077e0",
    "orange": "#ed9e4a",
    "red": "#df6270",
    "purple": "#8f6dd7",
    "slate": "#a5b1bd",
    "grid": "#e9eef3",
}
PLOTLY_TEMPLATE = "plotly_white"
STATUS_ORDER = ["Entregue no prazo", "Entregue com atraso", "Devolvida"]
def format_brl(value):
    if pd.isna(value):
        return "—"
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def format_brl_compact(value):
    if pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        formatted = f"{abs(value) / 1_000_000:.2f}".replace(".", ",")
        return f"{'-' if value < 0 else ''}R$ {formatted} mi"
    if abs(value) >= 100_000:
        formatted = f"{abs(value) / 1_000:.0f}"
        return f"{'-' if value < 0 else ''}R$ {formatted} mil"
    if abs(value) >= 1_000:
        formatted = f"{abs(value) / 1_000:.1f}".replace(".", ",")
        return f"{'-' if value < 0 else ''}R$ {formatted} mil"
    return format_brl(value)


def format_pct(value):
    return "—" if pd.isna(value) else f"{value:.1f}%".replace(".", ",")


def apply_filters(
    df,
    start_date,
    end_date,
    regions=None,
    carriers=None,
    routes=None,
    vehicles=None,
    statuses=None,
):
    dates = df["delivery_date"].dt.date
    filtered = df.loc[
        dates.between(start_date, end_date)
    ].copy()
    for column, selected in (
        ("region", regions),
        ("carrier", carriers),
        ("route_id", routes),
        ("vehicle_id", vehicles),
        ("delivery_status", statuses),
    ):
        if selected:
            filtered = filtered.loc[filtered[column].isin(selected)]
    return filtered


def calculate_kpis(df):
    total_cost = float(df["total_logistics_cost_brl"].sum())
    revenue = float(df["freight_revenue_brl"].sum())
    distance = float(df["distance_km"].sum())
    delivery_count = len(df)
    contribution = revenue - total_cost

    return {
        "deliveries": delivery_count,
        "revenue_brl": revenue,
        "cost_brl": total_cost,
        "contribution_brl": contribution,
        "margin_pct": contribution / revenue * 100 if revenue else float("nan"),
        "avg_cost_per_delivery_brl": (
            total_cost / delivery_count if delivery_count else float("nan")
        ),
        "cost_per_km_brl": total_cost / distance if distance else float("nan"),
        "on_time_pct": (
            df["delivery_status"].eq("Entregue no prazo").mean() * 100
            if delivery_count
            else float("nan")
        ),
        "return_pct": (
            df["delivery_status"].eq("Devolvida").mean() * 100
            if delivery_count
            else float("nan")
        ),
    }


def cost_composition(df):
    totals = (
        df[list(COST_COMPONENTS.values())]
        .sum()
        .rename_axis("component")
        .reset_index(name="cost_brl")
    )
    labels = {column: label for label, column in COST_COMPONENTS.items()}
    totals["component"] = totals["component"].map(labels)
    total_cost = totals["cost_brl"].sum()
    totals["share_pct"] = (
        totals["cost_brl"] / total_cost * 100 if total_cost else 0
    )
    return totals.sort_values("cost_brl", ascending=False)


def route_profitability(df):
    grouped = df.groupby("route_id", as_index=False).agg(
        deliveries=("delivery_id", "nunique"),
        revenue_brl=("freight_revenue_brl", "sum"),
        cost_brl=("total_logistics_cost_brl", "sum"),
        distance_km=("distance_km", "sum"),
        avg_cost_per_delivery_brl=("total_logistics_cost_brl", "mean"),
    )
    grouped["contribution_brl"] = grouped["revenue_brl"] - grouped["cost_brl"]
    grouped["margin_pct"] = (
        grouped["contribution_brl"] / grouped["revenue_brl"].where(
            grouped["revenue_brl"].ne(0)
        )
        * 100
    )
    grouped["cost_per_km_brl"] = (
        grouped["cost_brl"] / grouped["distance_km"].where(
            grouped["distance_km"].ne(0)
        )
    )
    return grouped


def carrier_performance(df):
    grouped = df.groupby("carrier", as_index=False).agg(
        deliveries=("delivery_id", "nunique"),
        avg_cost_per_delivery_brl=("total_logistics_cost_brl", "mean"),
        revenue_brl=("freight_revenue_brl", "sum"),
        cost_brl=("total_logistics_cost_brl", "sum"),
    )
    status_rates = df.assign(
        on_time=df["delivery_status"].eq("Entregue no prazo"),
        returned=df["delivery_status"].eq("Devolvida"),
    ).groupby("carrier").agg(
        on_time_pct=("on_time", "mean"),
        return_pct=("returned", "mean"),
    )
    grouped = grouped.join(status_rates, on="carrier")
    grouped[["on_time_pct", "return_pct"]] *= 100
    return grouped


def regional_profitability(df):
    grouped = df.groupby("region", as_index=False).agg(
        deliveries=("delivery_id", "nunique"),
        revenue_brl=("freight_revenue_brl", "sum"),
        cost_brl=("total_logistics_cost_brl", "sum"),
    )
    grouped["contribution_brl"] = grouped["revenue_brl"] - grouped["cost_brl"]
    grouped["margin_pct"] = (
        grouped["contribution_brl"] / grouped["revenue_brl"].where(
            grouped["revenue_brl"].ne(0)
        )
        * 100
    )
    return grouped


def fleet_efficiency(df):
    grouped = df.groupby("vehicle_id", as_index=False).agg(
        deliveries=("delivery_id", "nunique"),
        distance_km=("distance_km", "sum"),
        fuel_liters=("fuel_liters", "sum"),
        fuel_cost_brl=("fuel_cost_brl", "sum"),
        total_cost_brl=("total_logistics_cost_brl", "sum"),
    )
    grouped["fuel_efficiency_km_l"] = (
        grouped["distance_km"] / grouped["fuel_liters"].where(
            grouped["fuel_liters"].ne(0)
        )
    )
    grouped["fuel_cost_per_km_brl"] = (
        grouped["fuel_cost_brl"] / grouped["distance_km"].where(
            grouped["distance_km"].ne(0)
        )
    )
    grouped["total_cost_per_km_brl"] = (
        grouped["total_cost_brl"] / grouped["distance_km"].where(
            grouped["distance_km"].ne(0)
        )
    )
    return grouped


def cost_alerts(df, min_deliveries=30):
    grouped = route_profitability(df)
    if grouped.empty:
        return grouped.assign(
            company_avg_cost_per_delivery_brl=pd.Series(dtype=float),
            above_company_avg_pct=pd.Series(dtype=float),
        )
    benchmark = df["total_logistics_cost_brl"].mean()
    grouped["company_avg_cost_per_delivery_brl"] = benchmark
    grouped["above_company_avg_pct"] = (
        (grouped["avg_cost_per_delivery_brl"] / benchmark - 1) * 100
        if benchmark
        else 0
    )
    return grouped.loc[
        grouped["deliveries"].ge(min_deliveries)
        & grouped["avg_cost_per_delivery_brl"].gt(benchmark)
    ].sort_values("above_company_avg_pct", ascending=False)


@st.cache_data(show_spinner=False)
def load_data(source_path, _source_mtime_ns):
    if not Path(source_path).is_file():
        raise FileNotFoundError(f"Arquivo de dados sintéticos não encontrado: {source_path}")

    run_etl(raw_path=source_path, output_path=PROCESSED_FILE)
    return pd.read_csv(PROCESSED_FILE, parse_dates=["delivery_date"])


def style_chart(figure, height=360):
    figure.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        margin=dict(l=12, r=12, t=36, b=12),
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["ink"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#142b3b", font_color="white"),
    )
    figure.update_xaxes(showgrid=False, linecolor=COLORS["grid"])
    figure.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    return figure


def monthly_performance_chart(df):
    monthly = (
        df.assign(month=df["delivery_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(
            revenue_brl=("freight_revenue_brl", "sum"),
            cost_brl=("total_logistics_cost_brl", "sum"),
        )
    )
    monthly["contribution_brl"] = monthly["revenue_brl"] - monthly["cost_brl"]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["revenue_brl"],
            name="Receita",
            mode="lines+markers",
            line=dict(color=COLORS["blue"], width=3),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["cost_brl"],
            name="Custos",
            mode="lines+markers",
            line=dict(color=COLORS["orange"], width=3),
        )
    )
    figure.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["contribution_brl"],
            name="Resultado",
            marker_color=COLORS["teal"],
            opacity=0.36,
        )
    )
    figure.update_layout(barmode="overlay", hovermode="x unified")
    figure.update_yaxes(title="Valor (R$)", tickprefix="R$ ")
    figure.update_xaxes(title=None)
    return style_chart(figure, 385)


def render_cost_composition(df):
    composition = cost_composition(df)
    figure = px.pie(
        composition,
        names="component",
        values="cost_brl",
        hole=0.65,
        color_discrete_sequence=[
            COLORS["teal"],
            COLORS["blue"],
            COLORS["orange"],
            COLORS["purple"],
            COLORS["red"],
            COLORS["slate"],
            "#4eaaa6",
        ],
    )
    figure.update_traces(
        textposition="inside",
        texttemplate="%{percent:.1%}",
        hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
    )
    figure.update_layout(showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5))
    return style_chart(figure, 390)


def render_route_chart(df):
    routes = route_profitability(df)
    figure = px.scatter(
        routes,
        x="cost_per_km_brl",
        y="margin_pct",
        size="deliveries",
        color="margin_pct",
        color_continuous_scale=["#df6270", "#edc16c", "#00a38b"],
        hover_name="route_id",
        hover_data={
            "deliveries": True,
            "avg_cost_per_delivery_brl": ":.2f",
            "cost_per_km_brl": ":.2f",
            "margin_pct": ":.1f",
            "revenue_brl": ":.2f",
        },
        labels={
            "cost_per_km_brl": "Custo por km (R$)",
            "margin_pct": "Margem (%)",
            "deliveries": "Entregas",
        },
    )
    figure.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"])
    figure.add_vline(
        x=df["total_logistics_cost_brl"].sum() / df["distance_km"].sum(),
        line_dash="dot",
        line_color=COLORS["blue"],
        annotation_text="Média ponderada",
    )
    figure.update_layout(coloraxis_showscale=False)
    return style_chart(figure, 410)


def render_carrier_chart(df):
    carriers = carrier_performance(df).sort_values(
        "avg_cost_per_delivery_brl", ascending=True
    )
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(
            x=carriers["carrier"],
            y=carriers["avg_cost_per_delivery_brl"],
            name="Custo médio / entrega",
            marker_color=COLORS["blue"],
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=carriers["carrier"],
            y=carriers["on_time_pct"],
            name="No prazo",
            mode="lines+markers",
            line=dict(color=COLORS["teal"], width=3),
        ),
        secondary_y=True,
    )
    figure.add_trace(
        go.Scatter(
            x=carriers["carrier"],
            y=carriers["return_pct"],
            name="Devoluções",
            mode="lines+markers",
            line=dict(color=COLORS["red"], width=3, dash="dot"),
        ),
        secondary_y=True,
    )
    figure.update_yaxes(title_text="Custo médio (R$)", secondary_y=False)
    figure.update_yaxes(title_text="Entregas (%)", ticksuffix="%", secondary_y=True)
    figure.update_layout(hovermode="x unified")
    return style_chart(figure, 410)


def render_regional_chart(df):
    regions = regional_profitability(df).sort_values("margin_pct")
    figure = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "bar"}, {"type": "bar"}]],
        subplot_titles=("Receita e custo", "Margem de contribuição"),
        horizontal_spacing=0.18,
    )
    figure.add_trace(
        go.Bar(
            y=regions["region"],
            x=regions["revenue_brl"],
            orientation="h",
            name="Receita",
            marker_color=COLORS["blue"],
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            y=regions["region"],
            x=regions["cost_brl"],
            orientation="h",
            name="Custo",
            marker_color=COLORS["orange"],
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            y=regions["region"],
            x=regions["margin_pct"],
            orientation="h",
            name="Margem",
            marker_color=[
                COLORS["teal"] if value >= 0 else COLORS["red"]
                for value in regions["margin_pct"]
            ],
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    figure.update_layout(barmode="group")
    figure.update_xaxes(title_text="Valor (R$)", tickprefix="R$ ", row=1, col=1)
    figure.update_xaxes(title_text="Margem (%)", ticksuffix="%", row=1, col=2)
    return style_chart(figure, 370)


def render_fleet_chart(df):
    fleet = fleet_efficiency(df)
    figure = px.scatter(
        fleet,
        x="fuel_efficiency_km_l",
        y="total_cost_per_km_brl",
        size="deliveries",
        color="fuel_cost_per_km_brl",
        color_continuous_scale=["#bde6da", COLORS["teal"]],
        hover_name="vehicle_id",
        hover_data={
            "deliveries": True,
            "distance_km": ":.0f",
            "fuel_liters": ":.1f",
            "fuel_efficiency_km_l": ":.2f",
            "fuel_cost_per_km_brl": ":.2f",
            "total_cost_per_km_brl": ":.2f",
        },
        labels={
            "fuel_efficiency_km_l": "Eficiência (km/L)",
            "total_cost_per_km_brl": "Custo logístico por km (R$)",
            "fuel_cost_per_km_brl": "Combustível (R$/km)",
            "deliveries": "Entregas",
        },
    )
    return style_chart(figure, 410)


def render_alerts_chart(df):
    alerts = cost_alerts(df)
    if alerts.empty:
        st.info(
            "Nenhuma rota superou a média no período filtrado com pelo menos "
            "30 entregas. Amplie o período ou ajuste os filtros."
        )
        return
    alerts = alerts.sort_values("above_company_avg_pct", ascending=True)
    figure = px.bar(
        alerts,
        x="above_company_avg_pct",
        y="route_id",
        orientation="h",
        color="above_company_avg_pct",
        color_continuous_scale=["#edbf71", "#df6270"],
        text="above_company_avg_pct",
        hover_data={
            "deliveries": True,
            "avg_cost_per_delivery_brl": ":.2f",
            "company_avg_cost_per_delivery_brl": ":.2f",
            "cost_per_km_brl": ":.2f",
        },
        labels={
            "route_id": "Rota",
            "above_company_avg_pct": "Acima da média (%)",
            "deliveries": "Entregas",
        },
    )
    figure.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    figure.update_layout(coloraxis_showscale=False)
    st.plotly_chart(style_chart(figure, max(330, 42 * len(alerts))), use_container_width=True)
    st.caption(
        "Referência: média de custo por entrega de todas as rotas no recorte atual. "
        "O filtro mínimo é 30 entregas. Alertas servem para investigação, não "
        "comparam necessariamente rotas equivalentes e não recomendam mudanças."
    )


def render_table(df, money_columns=(), percent_columns=(), height=360):
    formatted = df.copy()
    for column in money_columns:
        if column in formatted:
            formatted[column] = formatted[column].map(format_brl)
    for column in percent_columns:
        if column in formatted:
            formatted[column] = formatted[column].map(format_pct)
    st.dataframe(
        formatted,
        use_container_width=True,
        hide_index=True,
        height=height,
    )


def main():
    st.set_page_config(
        page_title="LOGICOST | Inteligência Logística",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --logicost-ink: #142b3b;
            --logicost-muted: #718396;
            --logicost-teal: #008f79;
            --logicost-canvas: #f3f6fa;
            --logicost-line: #e4ebf2;
        }
        .stApp { background: var(--logicost-canvas); }
        [data-testid="stHeader"] { background: rgba(243,246,250,.94); }
        .block-container {
            max-width: 1540px; padding-top: 1.65rem; padding-bottom: 3rem;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102637 0%, #17384a 100%);
            border-right: 1px solid rgba(255,255,255,.07);
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #d3e2e8;
        }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 { color: #ffffff; }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
            letter-spacing: .12em; font-weight: 800;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,.13);
        }
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: .75rem;
        }
        section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
        section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
            border-radius: 10px;
        }
        [data-testid="stMetric"] {
            min-height: 100px; background: #ffffff; padding: 17px 18px;
            border: 1px solid var(--logicost-line); border-radius: 14px;
            box-shadow: 0 4px 16px rgba(20,43,59,.045);
            transition: transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(20,43,59,.08);
        }
        [data-testid="stMetricLabel"] p {
            color: var(--logicost-muted); font-size: .8rem; font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: var(--logicost-ink); font-size: 1.42rem; font-weight: 720;
        }
        [data-testid="stTabs"] button {
            font-weight: 650; color: var(--logicost-muted);
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--logicost-teal);
        }
        [data-testid="stTabs"] button[aria-selected="true"] p {
            color: var(--logicost-teal);
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--logicost-teal);
        }
        [data-testid="stTabs"] [data-baseweb="tab-border"] {
            background-color: var(--logicost-line);
        }
        @media (max-width: 1050px) {
            [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
            [data-testid="stMetric"] { padding: 14px 12px; }
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff; border-radius: 16px;
            border-color: var(--logicost-line); padding: 14px 16px;
            box-shadow: 0 3px 14px rgba(20,43,59,.035);
        }
        .logicost-hero {
            position: relative; overflow: hidden; color: white;
            background: linear-gradient(115deg, #122b3d 0%, #173d4d 62%, #116b67 100%);
            border: 1px solid rgba(255,255,255,.08); border-radius: 20px;
            padding: 28px 32px 26px; margin: 0 0 20px;
            box-shadow: 0 14px 32px rgba(20,43,59,.12);
        }
        .logicost-hero:after {
            content: ""; position: absolute; width: 280px; height: 280px;
            right: -72px; top: -150px; border-radius: 50%;
            background: rgba(69,213,181,.12);
            box-shadow: 0 0 0 30px rgba(69,213,181,.04);
        }
        .logicost-eyebrow {
            color: #71dfc7; font-weight: 700; font-size: .72rem;
            letter-spacing: .14em; text-transform: uppercase; margin-bottom: .35rem;
        }
        .logicost-title {
            color: #ffffff; font-weight: 750; letter-spacing: -.04em;
            font-size: 2.25rem; line-height: 1.1; margin: 0;
        }
        .logicost-subtitle { color: #d4e5e9; font-size: .96rem; margin-top: .55rem; }
        .logicost-badge {
            position: relative; z-index: 1; display: inline-block;
            background: rgba(255,255,255,.1); color: #d6fff5;
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 999px; padding: 6px 11px; font-size: .7rem;
            font-weight: 700; letter-spacing: .035em; margin-top: 15px;
        }
        .logicost-section-label {
            color: #718396; font-size: .74rem; font-weight: 700;
            letter-spacing: .1em; text-transform: uppercase;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--logicost-line); border-radius: 10px;
            overflow: hidden;
        }
        [data-testid="stDownloadButton"] button {
            min-height: 44px; font-weight: 650;
            border: 1px solid rgba(255,255,255,.28);
            background: rgba(255,255,255,.08); color: #ffffff;
        }
        [data-testid="stDownloadButton"] button:hover {
            border-color: #71dfc7; color: #71dfc7;
            background: rgba(255,255,255,.12);
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        [data-testid="stPlotlyChart"] { border-radius: 12px; }
        .logicost-footer {
            color: #718396; font-size: .8rem; line-height: 1.6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("## LOGICOST")
    st.sidebar.caption("INTELIGÊNCIA DE CUSTOS LOGÍSTICOS")
    st.sidebar.divider()
    st.sidebar.markdown("### Filtros")

    try:
        if not RAW_FILE.is_file():
            raise FileNotFoundError(f"Base bruta não encontrada: {RAW_FILE}")
        source_mtime = RAW_FILE.stat().st_mtime_ns
        df = load_data(str(RAW_FILE), source_mtime)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        st.error(f"Não foi possível carregar ou validar a base: {error}")
        st.stop()

    min_date = df["delivery_date"].min().date()
    max_date = df["delivery_date"].max().date()
    selected_dates = st.sidebar.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Selecione o período das entregas incluídas nos indicadores.",
    )
    if not isinstance(selected_dates, (list, tuple)) or len(selected_dates) != 2:
        st.sidebar.info("Selecione uma data inicial e uma data final.")
        st.stop()

    selected_regions = st.sidebar.multiselect("Região", sorted(df["region"].unique()))
    selected_carriers = st.sidebar.multiselect("Transportadora", sorted(df["carrier"].unique()))
    selected_routes = st.sidebar.multiselect("Rota", sorted(df["route_id"].unique()))
    selected_vehicles = st.sidebar.multiselect("Veículo", sorted(df["vehicle_id"].unique()))
    selected_statuses = st.sidebar.multiselect(
        "Situação", [status for status in STATUS_ORDER if status in df["delivery_status"].unique()]
    )

    filtered = apply_filters(
        df,
        selected_dates[0],
        selected_dates[1],
        regions=selected_regions,
        carriers=selected_carriers,
        routes=selected_routes,
        vehicles=selected_vehicles,
        statuses=selected_statuses,
    )
    if filtered.empty:
        st.warning("Nenhuma entrega corresponde aos filtros selecionados.")
        st.stop()

    st.markdown(
        """
        <div class="logicost-hero">
            <div class="logicost-eyebrow">Logistics performance &amp; cost intelligence</div>
            <h1 class="logicost-title">Visão executiva</h1>
            <div class="logicost-subtitle">
                Rentabilidade, eficiência operacional e estrutura de custos em uma só visão.
            </div>
            <div class="logicost-badge">● &nbsp; AMBIENTE DEMONSTRATIVO · DADOS 100% SINTÉTICOS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpis = calculate_kpis(filtered)
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Receita frete",
        format_brl_compact(kpis["revenue_brl"]),
        help=format_brl(kpis["revenue_brl"]),
    )
    metric_columns[1].metric(
        "Custo logístico",
        format_brl_compact(kpis["cost_brl"]),
        help=format_brl(kpis["cost_brl"]),
    )
    metric_columns[2].metric(
        "Resultado",
        format_brl_compact(kpis["contribution_brl"]),
        help="Contribuição simplificada do escopo analisado; não equivale a uma DRE.",
    )
    metric_columns[3].metric(
        "Margem",
        format_pct(kpis["margin_pct"]),
        help="Resultado operacional simplificado dividido pela receita de frete.",
    )

    metric_columns = st.columns(4)
    metric_columns[0].metric("Entregas", f"{kpis['deliveries']:,}".replace(",", "."))
    metric_columns[1].metric(
        "Custo por entrega", format_brl(kpis["avg_cost_per_delivery_brl"])
    )
    metric_columns[2].metric("Custo por km", format_brl(kpis["cost_per_km_brl"]))
    metric_columns[3].metric(
        "Entregas no prazo", format_pct(kpis["on_time_pct"])
    )
    st.caption(
        "O custo por entrega inclui entregas devolvidas; resultado simplificado não equivale "
        "a uma DRE contábil. Indicadores de pontualidade e devolução usam todas as entregas "
        "do recorte como denominador."
    )

    overview_tab, cost_tab, operations_tab, scenario_tab = st.tabs(
        ["Visão geral", "Custos & rentabilidade", "Operação & frota", "Simulador"]
    )

    with overview_tab:
        st.subheader("Desempenho mensal")
        st.caption("Receita, custos logísticos e resultado no período selecionado.")
        st.plotly_chart(
            monthly_performance_chart(filtered),
            use_container_width=True,
            key="monthly_performance",
        )
        st.subheader("Resumo do recorte")
        overview_metrics = [
            ("Devoluções", format_pct(kpis["return_pct"])),
            ("Combustível", format_brl(filtered["fuel_cost_brl"].sum())),
            ("Pontualidade", format_pct(kpis["on_time_pct"])),
            ("Conciliação de custos", f"{filtered['cost_reconciliation_ok'].mean():.0%}"),
        ]
        overview_columns = st.columns(4)
        for column, (label, value) in zip(overview_columns, overview_metrics):
            column.metric(label, value)

    with cost_tab:
        st.subheader("Composição dos custos")
        left, right = st.columns([0.85, 1.15], gap="large")
        with left:
            st.plotly_chart(
                render_cost_composition(filtered),
                use_container_width=True,
                key="cost_composition",
            )
        with right:
            composition = cost_composition(filtered).rename(
                columns={
                    "component": "Componente",
                    "cost_brl": "Custo",
                    "share_pct": "Participação",
                }
            )
            st.markdown("##### Detalhamento por componente")
            render_table(
                composition,
                money_columns=("Custo",),
                percent_columns=("Participação",),
                height=380,
            )

        st.subheader("Rentabilidade por rota")
        st.caption("Cada ponto representa uma rota; tamanho indica volume de entregas.")
        st.plotly_chart(
            render_route_chart(filtered),
            use_container_width=True,
            key="route_profitability",
        )
        routes = route_profitability(filtered).sort_values(
            ["margin_pct", "avg_cost_per_delivery_brl"],
            ascending=[True, False],
        )
        route_table = routes[
            [
                "route_id",
                "deliveries",
                "avg_cost_per_delivery_brl",
                "cost_per_km_brl",
                "contribution_brl",
                "margin_pct",
            ]
        ].rename(
            columns={
                "route_id": "Rota",
                "deliveries": "Entregas",
                "avg_cost_per_delivery_brl": "Custo médio / entrega",
                "cost_per_km_brl": "Custo / km",
                "contribution_brl": "Resultado",
                "margin_pct": "Margem",
            }
        )
        render_table(
            route_table,
            money_columns=("Custo médio / entrega", "Custo / km", "Resultado"),
            percent_columns=("Margem",),
        )

        st.subheader("Alertas de custos")
        render_alerts_chart(filtered)

    with operations_tab:
        st.markdown(
            '<div class="logicost-section-label">Performance de parceiros</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.subheader("Desempenho das transportadoras")
            st.caption(
                "Compare custo médio por entrega, pontualidade e devoluções por parceiro."
            )
            st.plotly_chart(
                render_carrier_chart(filtered),
                use_container_width=True,
                key="carrier_performance",
            )
            carriers = carrier_performance(filtered).sort_values(
                "avg_cost_per_delivery_brl"
            )
            carrier_table = carriers[
                [
                    "carrier",
                    "deliveries",
                    "avg_cost_per_delivery_brl",
                    "on_time_pct",
                    "return_pct",
                ]
            ].rename(
                columns={
                    "carrier": "Transportadora",
                    "deliveries": "Entregas",
                    "avg_cost_per_delivery_brl": "Custo médio / entrega",
                    "on_time_pct": "No prazo",
                    "return_pct": "Devoluções",
                }
            )
            render_table(
                carrier_table,
                money_columns=("Custo médio / entrega",),
                percent_columns=("No prazo", "Devoluções"),
            )

        st.markdown(
            '<div class="logicost-section-label">Visão por região</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.subheader("Rentabilidade regional")
            st.caption(
                "Receita e custo de frete com a margem de contribuição por região."
            )
            st.plotly_chart(
                render_regional_chart(filtered),
                use_container_width=True,
                key="regional_profitability",
            )

        st.markdown(
            '<div class="logicost-section-label">Frota &amp; eficiência</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.subheader("Eficiência da frota")
            st.caption(
                "Consumo ponderado (km/L) e custo total por quilômetro de cada veículo."
            )
            st.plotly_chart(
                render_fleet_chart(filtered),
                use_container_width=True,
                key="fleet_efficiency",
            )
            fleet = fleet_efficiency(filtered).sort_values(
                "total_cost_per_km_brl", ascending=False
            )
            fleet_table = fleet[
                [
                    "vehicle_id",
                    "deliveries",
                    "fuel_efficiency_km_l",
                    "fuel_cost_per_km_brl",
                    "total_cost_per_km_brl",
                ]
            ].rename(
                columns={
                    "vehicle_id": "Veículo",
                    "deliveries": "Entregas",
                    "fuel_efficiency_km_l": "Eficiência (km/L)",
                    "fuel_cost_per_km_brl": "Combustível / km",
                    "total_cost_per_km_brl": "Custo total / km",
                }
            )
            render_table(
                fleet_table,
                money_columns=("Combustível / km", "Custo total / km"),
                height=440,
            )

    with scenario_tab:
        st.subheader("Simulador de economia potencial")
        st.warning(
            "Cenário hipotético: não representa economia realizada, previsão nem "
            "recomendação operacional. A simulação considera apenas a redução do gasto "
            "com combustível, mantendo todo o restante do custo constante."
        )
        reduction_pct = st.slider(
            "Redução hipotética no custo com combustível (%)",
            min_value=0,
            max_value=30,
            value=8,
            step=1,
            format="%d%%",
            help="Apenas para análise de sensibilidade; não é uma meta nem uma previsão.",
        )
        current_fuel_cost = float(filtered["fuel_cost_brl"].sum())
        current_logistics_cost = kpis["cost_brl"]
        potential_savings = current_fuel_cost * reduction_pct / 100
        estimated_new_cost = current_logistics_cost - potential_savings
        estimated_contribution = kpis["revenue_brl"] - estimated_new_cost
        estimated_margin = (
            estimated_contribution / kpis["revenue_brl"] * 100
            if kpis["revenue_brl"]
            else float("nan")
        )

        scenario_columns = st.columns(4)
        scenario_columns[0].metric(
            "Combustível atual",
            format_brl_compact(current_fuel_cost),
            help=format_brl(current_fuel_cost),
        )
        scenario_columns[1].metric(
            "Economia potencial",
            format_brl_compact(potential_savings),
            delta=f"{reduction_pct}% hipotético",
            delta_color="off",
            help=format_brl(potential_savings),
        )
        scenario_columns[2].metric(
            "Novo custo estimado",
            format_brl_compact(estimated_new_cost),
            help=format_brl(estimated_new_cost),
        )
        scenario_columns[3].metric(
            "Margem estimada",
            format_pct(estimated_margin),
            help="Cenário hipotético com receita constante e redução aplicada apenas ao combustível.",
        )

        waterfall = go.Figure(
            go.Waterfall(
                name="Cenário hipotético",
                orientation="v",
                measure=["absolute", "relative", "total"],
                x=["Custo logístico atual", "Redução simulada", "Custo estimado"],
                y=[current_logistics_cost, -potential_savings, 0],
                text=[
                    format_brl(current_logistics_cost),
                    f"- {format_brl(potential_savings)}",
                    format_brl(estimated_new_cost),
                ],
                textposition="outside",
                connector={"line": {"color": COLORS["slate"]}},
                increasing={"marker": {"color": COLORS["blue"]}},
                decreasing={"marker": {"color": COLORS["teal"]}},
                totals={"marker": {"color": COLORS["ink"]}},
            )
        )
        waterfall.update_yaxes(title="Valor (R$)", tickprefix="R$ ")
        st.plotly_chart(
            style_chart(waterfall, 390),
            use_container_width=True,
            key="fuel_savings_scenario",
        )
        st.info(
            "Antes de avaliar qualquer mudança, compare rotas e operações semelhantes "
            "e controle distância, veículo, transportadora e nível de serviço. Os alertas "
            "da aba de custos usam uma média geral e não fazem esse pareamento."
        )

    download = filtered.to_csv(index=False).encode("utf-8-sig")
    st.sidebar.divider()
    st.sidebar.download_button(
        "⬇  Exportar dados filtrados",
        data=download,
        file_name="logicost_entregas_filtradas.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.sidebar.caption(
        f"{len(filtered):,} de {len(df):,} entregas · "
        f"{min_date:%d/%m/%Y} – {max_date:%d/%m/%Y}"
    )
    st.divider()
    st.caption(
        "LOGICOST Analytics · Projeto demonstrativo com dados 100% sintéticos. "
        "Resultado operacional é uma contribuição simplificada, não uma DRE. "
        "Alertas identificam pontos para investigação e não substituem análise de "
        "operações comparáveis.",
    )


if __name__ == "__main__":
    main()
