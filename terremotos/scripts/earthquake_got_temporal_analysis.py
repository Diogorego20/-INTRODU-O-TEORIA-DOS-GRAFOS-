"""Análise temporal de terremotos e redes de temporadas de Game of Thrones.

Autor: Diogo da Silva Rego
Matrícula: 20240045381
Curso: Estatística — CCEN/UFPB
Professora: Ana Flávia

O módulo gera:
- intervalo consecutivo de cinco dias com maior número de terremotos;
- dois modelos temporais para terremotos:
  (A) eventos como nós, ligados pela ordem temporal;
  (B) células geográficas como nós, ligadas por transições entre dias;
- centralidades por dia e medidas temporais agregadas;
- mapas-múndi diários estáticos e mapa interativo animado;
- grafos das temporadas 1–8, pesos, união, centralidades e comparação S1/S2;
- tabelas CSV, figuras PNG/PDF/SVG, HTML e resumo JSON.
"""

from __future__ import annotations

import json
import math
import shutil
import urllib.request
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

AUTHOR = "Diogo da Silva Rego"
REGISTRATION = "20240045381"
COURSE = "Estatística"
INSTITUTION = "Centro de Ciências Exatas e da Natureza (CCEN) — UFPB"
PROFESSOR = "Ana Flávia"
AUTHOR_CREDIT = "Autor: Diogo Rego"
WORLD_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"


# -----------------------------------------------------------------------------
# Utilidades gerais
# -----------------------------------------------------------------------------

def minmax(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").fillna(0.0)
    low, high = float(series.min()), float(series.max())
    if math.isclose(low, high):
        return pd.Series(0.5, index=series.index, dtype=float)
    return (series - low) / (high - low)


def safe_slug(value: object) -> str:
    return str(value).replace("-", "").replace(" ", "_").replace(":", "")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def ensure_world_layer(output: Path) -> gpd.GeoDataFrame:
    cache = output / "naturalearth_countries.geojson"
    if not cache.exists():
        urllib.request.urlretrieve(WORLD_URL, cache)
    return gpd.read_file(cache)


# -----------------------------------------------------------------------------
# Terremotos: seleção dos cinco dias mais ativos como intervalo consecutivo
# -----------------------------------------------------------------------------

def load_earthquakes(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"time", "latitude", "longitude", "mag"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no arquivo de terremotos: {sorted(missing)}")
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time", "latitude", "longitude", "mag"]).copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", "mag"])
    df = df.sort_values("time").reset_index(drop=True)
    if "id" in df.columns:
        df["event_id"] = df["id"].astype(str)
    else:
        df["event_id"] = [f"EQ_{i:05d}" for i in range(len(df))]
    df["day"] = df["time"].dt.floor("D")
    df["day_label"] = df["day"].dt.strftime("%Y-%m-%d")
    return df


def select_busiest_five_day_window(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    counts = df.groupby("day").size().sort_index()
    full_index = pd.date_range(counts.index.min(), counts.index.max(), freq="D", tz="UTC")
    daily_counts = counts.reindex(full_index, fill_value=0)
    rolling = daily_counts.rolling(window=5, min_periods=5).sum()
    max_total = float(rolling.max())
    end = rolling[rolling == max_total].index[0]
    start = end - pd.Timedelta(days=4)
    selected_days = pd.date_range(start, end, freq="D", tz="UTC")
    subset = df[df["day"].isin(selected_days)].copy().sort_values("time").reset_index(drop=True)
    subset["window_day_index"] = (subset["day"] - start).dt.days
    summary = {
        "criterio": "intervalo consecutivo de cinco dias com maior número de terremotos",
        "inicio_utc": start.isoformat(),
        "fim_utc": end.isoformat(),
        "dias": [day.strftime("%Y-%m-%d") for day in selected_days],
        "terremotos_no_intervalo": int(len(subset)),
        "contagem_por_dia": {day.strftime("%Y-%m-%d"): int(daily_counts.get(day, 0)) for day in selected_days},
        "total_maximo_no_intervalo": int(max_total),
    }
    return subset, summary


def _add_weighted_edge(graph: nx.Graph, left: object, right: object, **attrs) -> None:
    if left == right:
        return
    if graph.has_edge(left, right):
        graph[left][right]["weight"] = float(graph[left][right].get("weight", 1.0)) + float(attrs.get("weight", 1.0))
        if "time_gap_hours" in attrs:
            old = float(graph[left][right].get("time_gap_hours_sum", 0.0))
            graph[left][right]["time_gap_hours_sum"] = old + float(attrs["time_gap_hours"])
    else:
        graph.add_edge(left, right, **attrs)


def build_event_temporal_graph(df: pd.DataFrame) -> nx.Graph:
    """Cada terremoto é um nó; eventos consecutivos no tempo formam arestas."""
    graph = nx.Graph(model="eventos_consecutivos")
    for _, row in df.iterrows():
        graph.add_node(
            row["event_id"],
            day=row["day_label"],
            time=row["time"].isoformat(),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            magnitude=float(row["mag"]),
            place=str(row.get("place", "")),
        )

    ordered = df.sort_values("time")
    for previous, current in zip(ordered.iloc[:-1].itertuples(), ordered.iloc[1:].itertuples()):
        gap = float((current.time - previous.time).total_seconds() / 3600.0)
        _add_weighted_edge(
            graph,
            previous.event_id,
            current.event_id,
            weight=1.0,
            time_gap_hours=gap,
            time_gap_hours_sum=gap,
            day_transition=previous.day_label != current.day_label,
        )
    return graph


def _cell_id(latitude: float, longitude: float, cell_size: float = 10.0) -> str:
    lat0 = math.floor(latitude / cell_size) * cell_size
    lon0 = math.floor(longitude / cell_size) * cell_size
    return f"lat_{lat0:g}_lon_{lon0:g}"


def build_cell_temporal_graph(df: pd.DataFrame, cell_size: float = 10.0) -> tuple[nx.Graph, pd.DataFrame]:
    """Células de 10 graus como nós; transições entre eventos consecutivos."""
    data = df.copy()
    data["cell_id"] = [_cell_id(lat, lon, cell_size) for lat, lon in zip(data["latitude"], data["longitude"])]
    graph = nx.Graph(model="celulas_geograficas", cell_size_degrees=cell_size)
    grouped = data.groupby("cell_id", sort=True)
    for cell, group in grouped:
        graph.add_node(
            cell,
            latitude=float(group["latitude"].mean()),
            longitude=float(group["longitude"].mean()),
            events=int(len(group)),
            mean_magnitude=float(group["mag"].mean()),
            active_days=int(group["day"].nunique()),
        )

    for day, group in data.groupby("day", sort=True):
        group = group.sort_values("time")
        cells = group["cell_id"].tolist()
        for left, right in zip(cells[:-1], cells[1:]):
            _add_weighted_edge(
                graph,
                left,
                right,
                weight=1.0,
                day=day.strftime("%Y-%m-%d"),
            )

    # Liga também a última célula de um dia à primeira do dia seguinte.
    days = sorted(data["day"].unique())
    for left_day, right_day in zip(days[:-1], days[1:]):
        left_events = data[data["day"] == left_day].sort_values("time")
        right_events = data[data["day"] == right_day].sort_values("time")
        if len(left_events) and len(right_events):
            _add_weighted_edge(
                graph,
                left_events.iloc[-1]["cell_id"],
                right_events.iloc[0]["cell_id"],
                weight=1.0,
                day_transition=True,
            )
    return graph, data


def largest_component(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0:
        return nx.Graph()
    component = max(nx.connected_components(graph), key=len)
    return graph.subgraph(component).copy()


def calculate_graph_centralities(graph: nx.Graph, node_metadata: dict | None = None) -> pd.DataFrame:
    """Calcula grau, força, betweenness, closeness, eigenvector e PageRank.

    As medidas de caminhos são calculadas na maior componente conexa. A coluna
    `maior_componente` torna explícita essa decisão para redes espaciais
    desconectadas.
    """
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()
    graph = nx.Graph(graph)
    for left, right, data in graph.edges(data=True):
        weight = max(float(data.get("weight", 1.0)), 1e-9)
        data["distance"] = 1.0 / weight

    largest = largest_component(graph)
    component_nodes = set(largest.nodes)
    if largest.number_of_nodes() > 1:
        betweenness = nx.betweenness_centrality(largest, normalized=True, weight="distance")
        closeness = nx.closeness_centrality(largest, distance="distance")
        try:
            eigenvector = nx.eigenvector_centrality(largest, max_iter=3000, weight="weight")
        except nx.PowerIterationFailedConvergence:
            eigenvector = {node: np.nan for node in largest.nodes}
    else:
        only = next(iter(largest.nodes))
        betweenness, closeness, eigenvector = {only: 0.0}, {only: 0.0}, {only: 1.0}
    pagerank = nx.pagerank(graph, weight="weight")

    rows = []
    for node in graph.nodes:
        attrs = graph.nodes[node]
        row = {
            "no": node,
            "grau": int(graph.degree(node)),
            "forca_peso": float(sum(float(data.get("weight", 1.0)) for _, _, data in graph.edges(node, data=True))),
            "betweenness": float(betweenness.get(node, 0.0)),
            "closeness": float(closeness.get(node, 0.0)),
            "eigenvector": float(eigenvector.get(node, 0.0)) if pd.notna(eigenvector.get(node, 0.0)) else np.nan,
            "pagerank": float(pagerank.get(node, 0.0)),
            "maior_componente": node in component_nodes,
            "componente_tamanho": int(len(component_nodes)),
        }
        row.update({key: value for key, value in attrs.items() if key not in row})
        if node_metadata and node in node_metadata:
            row.update(node_metadata[node])
        rows.append(row)
    result = pd.DataFrame(rows)
    for column in ["grau", "forca_peso", "betweenness", "closeness", "eigenvector", "pagerank"]:
        result[f"{column}_normalizado"] = minmax(result[column])
    result["centralidade_combinada"] = (
        0.25 * result["grau_normalizado"]
        + 0.25 * result["forca_peso_normalizado"]
        + 0.25 * result["betweenness_normalizado"]
        + 0.25 * result["closeness_normalizado"]
    )
    return result.sort_values(["centralidade_combinada", "no"], ascending=[False, True]).reset_index(drop=True)


def daily_temporal_metrics(
    df: pd.DataFrame,
    graph_builder,
    node_column: str | None = None,
) -> pd.DataFrame:
    rows = []
    for day, group in df.groupby("day", sort=True):
        graph = graph_builder(group)
        metrics = calculate_graph_centralities(graph)
        if metrics.empty:
            continue
        metrics.insert(0, "dia", day.strftime("%Y-%m-%d"))
        rows.append(metrics)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def temporal_aggregate(metrics: pd.DataFrame, node_column: str = "no") -> pd.DataFrame:
    if metrics.empty:
        return metrics
    numeric = [
        "grau", "forca_peso", "betweenness", "closeness", "eigenvector", "pagerank", "centralidade_combinada"
    ]
    aggregations = {}
    for column in numeric:
        if column in metrics.columns:
            aggregations[column] = ["mean", "max", "sum"]
    out = metrics.groupby(node_column).agg(aggregations)
    out.columns = ["_".join(col) for col in out.columns]
    out = out.reset_index()
    out["dias_ativos"] = metrics.groupby(node_column)["dia"].nunique().values
    out["cobertura_temporal"] = out["dias_ativos"] / metrics["dia"].nunique()
    if "centralidade_combinada_sum" in out:
        out["centralidade_temporal"] = out["centralidade_combinada_sum"] * out["cobertura_temporal"]
    return out.sort_values("centralidade_temporal", ascending=False).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Mapas e gráficos de terremotos
# -----------------------------------------------------------------------------

def save_earthquake_daily_map(df: pd.DataFrame, output: Path, world: gpd.GeoDataFrame, day: str) -> None:
    subset = df[df["day_label"] == day]
    fig, ax = plt.subplots(figsize=(16, 8), dpi=160)
    world.plot(ax=ax, color="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.35)
    sc = ax.scatter(
        subset["longitude"], subset["latitude"],
        s=30 + 120 * (subset["mag"] - subset["mag"].min() + 0.1),
        c=subset["mag"], cmap="plasma", edgecolor="black", linewidth=0.3, alpha=0.84,
    )
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"Terremotos — {day} | n={len(subset)} | tamanho/cor proporcional à magnitude", fontsize=14, fontweight="bold")
    ax.grid(alpha=0.2)
    fig.colorbar(sc, ax=ax, shrink=0.65, label="Magnitude")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Fonte: terremotos.csv | Tamanho e cor dos pontos: magnitude sísmica.", fontsize=8, color="#475569")
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_earthquake_five_day_panel(df: pd.DataFrame, output: Path, world: gpd.GeoDataFrame, days: list[str]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(19, 11), dpi=160)
    axes = axes.ravel()
    for ax, day in zip(axes, days):
        subset = df[df["day_label"] == day]
        world.plot(ax=ax, color="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.25)
        ax.scatter(subset["longitude"], subset["latitude"], s=20 + 90 * (subset["mag"] - 4.4), c=subset["mag"], cmap="plasma", edgecolor="black", linewidth=0.25, alpha=0.82)
        ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
        ax.set_title(f"{day} — {len(subset)} eventos", fontsize=11, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
    axes[-1].axis("off")
    fig.suptitle("Intervalo de cinco dias mais ativo — distribuição mundial de terremotos", fontsize=17, fontweight="bold")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Cor/tamanho: magnitude sísmica | Fonte: terremotos.csv.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(output, dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_earthquake_interactive(df: pd.DataFrame, output: Path, days: list[str]) -> None:
    frames = []
    for day in days:
        subset = df[df["day_label"] == day]
        depth = subset["depth"] if "depth" in subset else pd.Series(np.nan, index=subset.index)
        frames.append(
            go.Frame(
                name=day,
                data=[
                    go.Scattergeo(
                        lon=subset["longitude"],
                        lat=subset["latitude"],
                        mode="markers",
                        text=subset.get("place", pd.Series([""] * len(subset))).astype(str),
                        customdata=np.column_stack([subset["mag"].to_numpy(), depth.to_numpy()]),
                        marker={
                            "size": (5 + 5 * (subset["mag"] - 4.4)).tolist(),
                            "color": subset["mag"].tolist(),
                            "colorscale": "Plasma",
                            "showscale": True,
                            "colorbar": {"title": "Mag."},
                            "line": {"width": 0.5, "color": "black"},
                        },
                        hovertemplate="<b>%{text}</b><br>Magnitude: %{customdata[0]:.1f}<br>Profundidade: %{customdata[1]:.1f} km<extra></extra>",
                        name=day,
                    )
                ],
            )
        )
    initial = frames[0].data[0]
    fig = go.Figure(data=[initial], frames=frames)
    steps = [{"label": day, "method": "animate", "args": [[day], {"mode": "immediate", "frame": {"duration": 700, "redraw": True}, "transition": {"duration": 250}}]} for day in days]
    fig.update_layout(
        title="Mapa-múndi interativo — terremotos por dia",
        geo={"showland": True, "landcolor": "#E2E8F0", "showocean": True, "oceancolor": "#F8FAFC", "showcoastlines": True, "projection_type": "natural earth"},
        sliders=[{"active": 0, "currentvalue": {"prefix": "Dia: "}, "steps": steps}],
        updatemenus=[{"type": "buttons", "showactive": False, "x": 0.05, "y": 1.12, "buttons": [{"label": "Reproduzir", "method": "animate", "args": [None, {"frame": {"duration": 900, "redraw": True}, "fromcurrent": True}]}, {"label": "Pausar", "method": "animate", "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]}]}],
        annotations=[{"text": f"{AUTHOR_CREDIT} | Tamanho/cor: magnitude | Use o seletor para alternar os dias e o hover para consultar cada evento.", "xref": "paper", "yref": "paper", "x": 0, "y": -0.08, "showarrow": False, "font": {"size": 11, "color": "#475569"}}],
        margin={"l": 0, "r": 0, "t": 80, "b": 65},
    )
    fig.write_html(output, include_plotlyjs=True, full_html=True, auto_open=False)


def save_earthquake_graph_snapshots(df: pd.DataFrame, output: Path, cell_size: float = 10.0) -> None:
    graph, data = build_cell_temporal_graph(df, cell_size)
    days = sorted(df["day_label"].unique())
    for day in days:
        subset = data[data["day_label"] == day]
        day_graph, _ = build_cell_temporal_graph(subset, cell_size)
        if day_graph.number_of_nodes() == 0:
            continue
        pos = nx.spring_layout(day_graph, seed=42, k=0.75, iterations=300)
        fig, ax = plt.subplots(figsize=(10, 7), dpi=140)
        widths = [1.0 + 0.8 * float(data_edge.get("weight", 1)) for _, _, data_edge in day_graph.edges(data=True)]
        nx.draw_networkx_edges(day_graph, pos, ax=ax, width=widths, edge_color="#94A3B8", alpha=0.5)
        node_sizes = [100 + 30 * math.sqrt(day_graph.nodes[node].get("events", 1)) for node in day_graph.nodes]
        nx.draw_networkx_nodes(day_graph, pos, ax=ax, node_size=node_sizes, node_color="#2563EB", edgecolors="white")
        labels = {node: node.replace("lat_", "").replace("_lon_", ", ") for node in day_graph.nodes}
        nx.draw_networkx_labels(day_graph, pos, labels=labels, ax=ax, font_size=7)
        ax.set_title(f"Rede temporal por células geográficas — {day}", fontweight="bold")
        ax.text(0.01, 0.01, "Nós = células de 10° × 10° | Arestas = transições temporais", transform=ax.transAxes, fontsize=7, color="#475569")
        ax.axis("off")
        fig.tight_layout()
        fig.text(0.01, 0.01, AUTHOR_CREDIT, fontsize=8, color="#475569")
        fig.savefig(output / f"grafo_celulas_{safe_slug(day)}.png", dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)


# -----------------------------------------------------------------------------
# Game of Thrones: temporadas, pesos e união temporal
# -----------------------------------------------------------------------------

def load_season_graph(path: str | Path, season: int) -> nx.Graph:
    df = pd.read_csv(path)
    lower = {str(col).lower(): col for col in df.columns}
    source = next((lower[c] for c in ("source", "origem", "from") if c in lower), None)
    target = next((lower[c] for c in ("target", "destino", "to") if c in lower), None)
    weight_col = next((lower[c] for c in ("weight", "peso") if c in lower), None)
    if source is None or target is None:
        raise ValueError(f"Arquivo da temporada {season} sem colunas de origem/destino.")
    graph = nx.Graph(season=season)
    for _, row in df.iterrows():
        left, right = row[source], row[target]
        if pd.isna(left) or pd.isna(right) or left == right:
            continue
        weight = float(row[weight_col]) if weight_col and pd.notna(row[weight_col]) else 1.0
        if graph.has_edge(left, right):
            graph[left][right]["weight"] += weight
        else:
            graph.add_edge(left, right, weight=weight, season=season)
    return graph


def component_aware_layout(graph: nx.Graph, seed: int = 42) -> dict[object, np.ndarray]:
    """Centraliza a maior componente e organiza componentes pequenas ao redor."""
    if graph.number_of_nodes() == 0:
        return {}
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    main = graph.subgraph(components[0]).copy()
    pos = nx.spring_layout(
        main,
        seed=seed,
        k=2.6 / math.sqrt(max(main.number_of_nodes(), 1)),
        iterations=800,
        weight=None,
        scale=1.0,
        center=(0.0, 0.0),
    )
    if len(components) > 1:
        radius = 1.35
        small_nodes = [node for component in components[1:] for node in component]
        for index, node in enumerate(small_nodes):
            angle = 2 * math.pi * index / max(len(small_nodes), 1)
            pos[node] = np.array([radius * math.cos(angle), radius * math.sin(angle)])
    return pos


def save_got_graph_static(
    graph: nx.Graph,
    output: Path,
    title: str,
    filename: str,
    top_labels: int = 18,
    color: str = "#2563EB",
    node_colors: dict[object, str] | None = None,
    legend: list[tuple[str, str]] | None = None,
) -> None:
    degree = dict(graph.degree())
    strength = {node: sum(float(data.get("weight", 1)) for _, _, data in graph.edges(node, data=True)) for node in graph.nodes}
    ranking = sorted(graph.nodes, key=lambda node: (strength[node], degree[node], str(node)), reverse=True)
    labels = {node: str(node) for node in ranking[:top_labels]}
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    main = graph.subgraph(components[0]).copy()
    pos = nx.spring_layout(main, seed=42, k=2.6 / math.sqrt(max(main.number_of_nodes(), 1)), iterations=800, weight=None, scale=1.0)
    if len(components) > 1:
        fig, (ax, component_ax) = plt.subplots(1, 2, figsize=(18, 10), dpi=160, gridspec_kw={"width_ratios": [5.2, 1.2]})
        component_ax.set_facecolor("#F8FAFC")
        component_ax.axis("off")
        isolated = [str(node) for component in components[1:] for node in component]
        component_ax.text(0.03, 0.95, "Componentes fora da rede principal", transform=component_ax.transAxes, va="top", fontsize=11, fontweight="bold", color="#0F172A")
        component_ax.text(0.03, 0.88, f"{len(isolated)} personagem(ns)", transform=component_ax.transAxes, va="top", fontsize=10, color="#475569")
        component_ax.text(0.03, 0.80, "\n".join(f"• {node}" for node in sorted(isolated)), transform=component_ax.transAxes, va="top", fontsize=10, color="#334155")
    else:
        fig, ax = plt.subplots(figsize=(16, 10), dpi=160)
        component_ax = None
    ax.set_facecolor("#F8FAFC")
    main_labels = {node: label for node, label in labels.items() if node in main}
    widths = [0.4 + 1.8 * math.sqrt(float(data.get("weight", 1)) / max(max(nx.get_edge_attributes(main, "weight").values(), default=1), 1)) for _, _, data in main.edges(data=True)]
    nx.draw_networkx_edges(main, pos, ax=ax, width=widths, edge_color="#CBD5E1", alpha=0.55)
    nx.draw_networkx_nodes(main, pos, ax=ax, node_size=[80 + 22 * math.sqrt(degree[node] + 1) for node in main.nodes], node_color=[node_colors.get(node, color) for node in main.nodes] if node_colors else color, edgecolors="white", alpha=0.9)
    nx.draw_networkx_labels(main, pos, labels=main_labels, ax=ax, font_size=8, font_weight="bold", bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": color, "alpha": 0.9})
    ax.set_title(f"{title}\nRótulos: {len(main_labels)} nós com maior força de interação", fontsize=16, fontweight="bold")
    ax.text(0, -0.03, f"{AUTHOR_CREDIT} | Pesos representam o número de interações nas arestas. Componentes desconectadas são listadas ao lado.", transform=ax.transAxes, fontsize=9, color="#475569")
    if legend:
        ax.legend(handles=[Line2D([], [], marker="o", linestyle="none", markerfacecolor=legend_color, markeredgecolor="white", markersize=8, label=label) for label, legend_color in legend], loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=True, title="Presença temporal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output / filename, dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig((output / filename).with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_got_union_interactive(graph: nx.Graph, output: Path, memberships: dict[object, str]) -> None:
    # Mesmo princípio do mapa estático: peso na aresta, não na força do layout.
    pos = component_aware_layout(graph, seed=42)
    edge_x, edge_y = [], []
    for left, right in graph.edges:
        edge_x += [pos[left][0], pos[right][0], None]
        edge_y += [pos[left][1], pos[right][1], None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"width": 0.55, "color": "#CBD5E1"}, hoverinfo="skip", name="Arestas")
    metrics = calculate_graph_centralities(graph).set_index("no")
    season_groups = sorted(set(memberships.values()))
    colors = {group: ["#2563EB", "#059669", "#D97706", "#7C3AED", "#DC2626", "#0891B2", "#DB2777", "#65A30D", "#9333EA", "#EA580C"][i % 10] for i, group in enumerate(season_groups)}
    traces = [edge_trace]
    for group in season_groups:
        nodes = [node for node in graph.nodes if memberships[node] == group]
        custom = []
        for node in nodes:
            row = metrics.loc[node]
            custom.append([str(node), memberships[node], int(row["grau"]), float(row["forca_peso"]), float(row["betweenness"]), float(row["pagerank"])])
        traces.append(go.Scatter(x=[pos[node][0] for node in nodes], y=[pos[node][1] for node in nodes], mode="markers", name=group, marker={"size": [8 + 2 * math.sqrt(graph.degree[node] + 1) for node in nodes], "color": colors[group], "line": {"width": 0.8, "color": "white"}}, customdata=custom, hovertemplate="<b>%{customdata[0]}</b><br>Presença: %{customdata[1]}<br>Grau: %{customdata[2]}<br>Força: %{customdata[3]:.1f}<br>Betweenness: %{customdata[4]:.4f}<br>PageRank: %{customdata[5]:.4f}<extra></extra>"))
    fig = go.Figure(traces)
    fig.update_layout(title="União ponderada das temporadas 1–8 — exploração interativa", template="plotly_white", hovermode="closest", showlegend=True, legend={"title": "Presença temporal"}, annotations=[{"text": f"{AUTHOR_CREDIT} | Tamanho do nó: grau | Hover: personagem, presença, grau, força, betweenness e PageRank", "xref": "paper", "yref": "paper", "x": 0, "y": -0.08, "showarrow": False, "font": {"size": 11, "color": "#475569"}}], margin={"l": 20, "r": 180, "t": 70, "b": 70}, xaxis={"showticklabels": False, "showgrid": False, "zeroline": False}, yaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "scaleanchor": "x", "scaleratio": 1})
    fig.write_html(output / "got_uniao_temporadas_interativo.html", include_plotlyjs=True, full_html=True, auto_open=False)


def analyze_got_seasons(base: Path, output: Path) -> dict:
    graphs: dict[int, nx.Graph] = {}
    season_metrics = []
    for season in range(1, 9):
        graph = load_season_graph(base / f"got-s{season}-edges.csv", season)
        graphs[season] = graph
        metrics = calculate_graph_centralities(graph)
        metrics.insert(0, "temporada", season)
        season_metrics.append(metrics)
        save_got_graph_static(graph, output, f"Grafo ponderado — temporada {season}", f"got_grafo_temporada_{season}.png", color=["#2563EB", "#059669", "#D97706", "#7C3AED", "#DC2626", "#0891B2", "#DB2777", "#65A30D"][season - 1])
    all_metrics = pd.concat(season_metrics, ignore_index=True)
    write_csv(all_metrics, output / "got_centralidades_por_temporada.csv")

    union = nx.Graph()
    membership: dict[object, set[int]] = {}
    for season, graph in graphs.items():
        for node in graph.nodes:
            membership.setdefault(node, set()).add(season)
            union.add_node(node)
        for left, right, data in graph.edges(data=True):
            if union.has_edge(left, right):
                union[left][right]["weight"] += float(data.get("weight", 1.0))
                union[left][right].setdefault("seasons", set()).add(season)
            else:
                union.add_edge(left, right, weight=float(data.get("weight", 1.0)), seasons={season})
    union_metrics = calculate_graph_centralities(union)
    write_csv(union_metrics, output / "got_centralidades_uniao_temporadas.csv")
    edge_rows = []
    for left, right, data in union.edges(data=True):
        seasons = sorted(data.get("seasons", set()))
        edge_rows.append({"source": left, "target": right, "peso_total": data.get("weight", 0), "temporadas": ",".join(map(str, seasons)), "numero_temporadas": len(seasons)})
    write_csv(pd.DataFrame(edge_rows).sort_values("peso_total", ascending=False), output / "got_arestas_uniao_temporadas.csv")

    membership_rows = []
    for node, seasons in membership.items():
        membership_rows.append({"personagem": node, "temporadas": ",".join(map(str, sorted(seasons))), "numero_temporadas": len(seasons), "primeira_temporada": min(seasons), "ultima_temporada": max(seasons), "presenca_s1": 1 in seasons, "presenca_s2": 2 in seasons, "classe_s1_s2": "S1 e S2" if {1, 2}.issubset(seasons) else ("Somente S1" if seasons == {1} else ("Somente S2" if seasons == {2} else "Outras/combinação"))})
    membership_df = pd.DataFrame(membership_rows).sort_values(["numero_temporadas", "personagem"], ascending=[False, True])
    write_csv(membership_df, output / "got_membresia_temporal_personagens.csv")

    s1_nodes = set(graphs[1].nodes); s2_nodes = set(graphs[2].nodes)
    comparison = pd.DataFrame([
        {"grupo": "Somente S1", "quantidade_personagens": len(s1_nodes - s2_nodes), "personagens": ", ".join(sorted(map(str, s1_nodes - s2_nodes)))},
        {"grupo": "Somente S2", "quantidade_personagens": len(s2_nodes - s1_nodes), "personagens": ", ".join(sorted(map(str, s2_nodes - s1_nodes)))},
        {"grupo": "S1 e S2", "quantidade_personagens": len(s1_nodes & s2_nodes), "personagens": ", ".join(sorted(map(str, s1_nodes & s2_nodes)))},
    ])
    write_csv(comparison, output / "got_comparacao_temporadas_1_2.csv")

    summary_rows = []
    for season, graph in graphs.items():
        summary_rows.append({"temporada": season, "nos": graph.number_of_nodes(), "arestas": graph.number_of_edges(), "forca_total": sum(float(data.get("weight", 1)) for _, _, data in graph.edges(data=True)), "peso_medio_aresta": float(np.mean([float(data.get("weight", 1)) for _, _, data in graph.edges(data=True)])) if graph.number_of_edges() else 0.0, "grau_medio": float(np.mean([degree for _, degree in graph.degree()])) if graph.number_of_nodes() else 0.0})
    write_csv(pd.DataFrame(summary_rows), output / "got_resumo_temporadas.csv")

    fig, axes = plt.subplots(1, 3, figsize=(17, 5), dpi=160)
    summary_df = pd.DataFrame(summary_rows)
    for ax, column, title, color in zip(axes, ["nos", "arestas", "forca_total"], ["Personagens", "Arestas", "Força total das interações"], ["#2563EB", "#059669", "#D97706"]):
        ax.plot(summary_df["temporada"], summary_df[column], marker="o", linewidth=2.2, color=color)
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Temporada")
        ax.grid(alpha=0.25)
    fig.suptitle("Evolução da estrutura das redes por temporada", fontsize=16, fontweight="bold")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Personagens = nós; arestas = interações; força total = soma dos pesos.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(output / "got_evolucao_temporadas.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "got_evolucao_temporadas.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    membership_labels = {node: ("S1 e S2" if {1, 2}.issubset(seasons) else ("Somente S1" if seasons == {1} else ("Somente S2" if seasons == {2} else f"Temporadas {','.join(map(str, sorted(seasons)))}"))) for node, seasons in membership.items()}
    save_got_graph_static(union, output, "União ponderada dos grafos — temporadas 1 a 8", "got_grafo_uniao_temporadas.png", top_labels=25, color="#475569")
    save_got_union_interactive(union, output, membership_labels)

    return {
        "temporadas": 8,
        "nos_uniao": union.number_of_nodes(),
        "arestas_uniao": union.number_of_edges(),
        "peso_total_uniao": float(sum(float(data.get("weight", 1)) for _, _, data in union.edges(data=True))),
        "personagens_s1": len(s1_nodes),
        "personagens_s2": len(s2_nodes),
        "personagens_s1_s2": len(s1_nodes & s2_nodes),
    }


# -----------------------------------------------------------------------------
# Orquestração
# -----------------------------------------------------------------------------

def run_all_analysis(
    earthquakes_path: str | Path,
    got_dir: str | Path,
    output_dir: str | Path,
    cell_size_degrees: float = 10.0,
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    earthquake_output = output / "terremotos"
    got_output = output / "got_temporadas"
    earthquake_output.mkdir(exist_ok=True)
    got_output.mkdir(exist_ok=True)

    raw = load_earthquakes(earthquakes_path)
    selected, window_summary = select_busiest_five_day_window(raw)
    days = sorted(selected["day_label"].unique())
    write_csv(raw, earthquake_output / "terremotos_tratados_todos_dias.csv")
    write_csv(selected, earthquake_output / "terremotos_intervalo_cinco_dias.csv")
    daily_counts = selected.groupby("day_label").agg(terremotos=("event_id", "count"), magnitude_media=("mag", "mean"), magnitude_maxima=("mag", "max"), profundidade_media_km=("depth", "mean" if "depth" in selected else "count")).reset_index()
    write_csv(daily_counts, earthquake_output / "resumo_diario_terremotos.csv")

    event_graph = build_event_temporal_graph(selected)
    event_metrics = calculate_graph_centralities(event_graph)
    write_csv(event_metrics, earthquake_output / "centralidades_temporais_eventos.csv")
    event_edges = pd.DataFrame([{**{"source": left, "target": right}, **data} for left, right, data in event_graph.edges(data=True)])
    write_csv(event_edges, earthquake_output / "arestas_grafo_temporal_eventos.csv")

    cell_graph, selected_with_cells = build_cell_temporal_graph(selected, cell_size_degrees)
    cell_metrics = calculate_graph_centralities(cell_graph)
    cell_metadata = selected_with_cells.groupby("cell_id").agg(latitude_media=("latitude", "mean"), longitude_media=("longitude", "mean"), eventos=("event_id", "count"), dias_ativos=("day_label", "nunique"), magnitude_media=("mag", "mean")).reset_index().rename(columns={"cell_id": "no"})
    cell_metrics = cell_metrics.merge(cell_metadata, on="no", how="left")
    write_csv(cell_metrics, earthquake_output / "centralidades_temporais_celulas.csv")
    cell_edges = pd.DataFrame([{**{"source": left, "target": right}, **data} for left, right, data in cell_graph.edges(data=True)])
    write_csv(cell_edges, earthquake_output / "arestas_grafo_temporal_celulas.csv")

    def event_daily_builder(group: pd.DataFrame) -> nx.Graph:
        return build_event_temporal_graph(group)

    def cell_daily_builder(group: pd.DataFrame) -> nx.Graph:
        graph, _ = build_cell_temporal_graph(group, cell_size_degrees)
        return graph

    event_daily = daily_temporal_metrics(selected, event_daily_builder)
    cell_daily = daily_temporal_metrics(selected, cell_daily_builder)
    write_csv(event_daily, earthquake_output / "centralidades_por_dia_eventos.csv")
    write_csv(cell_daily, earthquake_output / "centralidades_por_dia_celulas.csv")
    event_temporal = temporal_aggregate(event_daily)
    cell_temporal = temporal_aggregate(cell_daily)
    write_csv(event_temporal, earthquake_output / "medidas_temporais_agregadas_eventos.csv")
    write_csv(cell_temporal, earthquake_output / "medidas_temporais_agregadas_celulas.csv")

    world = ensure_world_layer(earthquake_output)
    for day in days:
        save_earthquake_daily_map(selected, earthquake_output / f"mapa_mundi_terremotos_{safe_slug(day)}.png", world, day)
    save_earthquake_five_day_panel(selected, earthquake_output / "mapa_mundi_intervalo_cinco_dias.png", world, days)
    save_earthquake_interactive(selected, earthquake_output / "mapa_mundi_terremotos_interativo.html", days)
    save_earthquake_graph_snapshots(selected, earthquake_output, cell_size_degrees)

    # Evolução das centralidades das células.
    if not cell_daily.empty:
        fig, axes = plt.subplots(2, 1, figsize=(14, 9), dpi=160, sharex=True)
        for metric, color, label in [("grau", "#2563EB", "Grau médio"), ("forca_peso", "#D97706", "Força média"), ("betweenness", "#7C3AED", "Betweenness média"), ("closeness", "#059669", "Closeness média")]:
            if metric in cell_daily:
                means = cell_daily.groupby("dia")[metric].mean()
                axes[0].plot(means.index, means.values, marker="o", label=label, color=color)
        top_cells = cell_temporal.head(5)["no"].tolist() if not cell_temporal.empty else []
        for cell in top_cells:
            subset = cell_daily[cell_daily["no"] == cell]
            axes[1].plot(subset["dia"], subset["centralidade_combinada"], marker="o", label=str(cell))
        axes[0].set_title("Evolução média das centralidades por dia", fontweight="bold")
        axes[0].legend(ncol=2)
        axes[1].set_title("Centralidade combinada das cinco células mais relevantes", fontweight="bold")
        axes[1].legend(ncol=3, fontsize=8)
        for ax in axes:
            ax.grid(alpha=0.25)
            ax.tick_params(axis="x", rotation=30)
        fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Painel superior: médias diárias; painel inferior: centralidade combinada das cinco células mais relevantes.", fontsize=9, color="#475569")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(earthquake_output / "evolucao_centralidades_temporais.png", dpi=240, bbox_inches="tight", facecolor="white")
        fig.savefig(earthquake_output / "evolucao_centralidades_temporais.pdf", bbox_inches="tight", facecolor="white")
        plt.close(fig)

    got_summary = analyze_got_seasons(Path(got_dir), got_output)
    summary = {
        "autor": AUTHOR,
        "matricula": REGISTRATION,
        "curso": COURSE,
        "instituicao": INSTITUTION,
        "professora": PROFESSOR,
        "terremotos": {
            **window_summary,
            "eventos_total_arquivo": int(len(raw)),
            "dias_total_arquivo": int(raw["day"].nunique()),
            "modelo_eventos": {"nos": event_graph.number_of_nodes(), "arestas": event_graph.number_of_edges()},
            "modelo_celulas": {"nos": cell_graph.number_of_nodes(), "arestas": cell_graph.number_of_edges(), "tamanho_celula_graus": cell_size_degrees},
            "arquivos_principais": [
                "terremotos/centralidades_temporais_eventos.csv",
                "terremotos/centralidades_temporais_celulas.csv",
                "terremotos/medidas_temporais_agregadas_celulas.csv",
                "terremotos/mapa_mundi_intervalo_cinco_dias.png",
                "terremotos/mapa_mundi_terremotos_interativo.html",
            ],
        },
        "got": got_summary,
    }
    (output / "resumo_analise_temporal.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Executa a análise temporal de terremotos e temporadas GOT.")
    parser.add_argument("--earthquakes", required=True, type=Path)
    parser.add_argument("--got-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cell-size", type=float, default=10.0)
    args = parser.parse_args()
    result = run_all_analysis(args.earthquakes, args.got_dir, args.output, args.cell_size)
    print(json.dumps(result, ensure_ascii=False, indent=2))
