"""Análise moderna e reproduzível dos grafos de Game of Thrones S2--S8.

Autor: Diogo da Silva Rego | Matrícula: 20240045381
Professora: Ana Flávia | Estatística — CCEN/UFPB

Decisões metodológicas principais:
- os arquivos fornecidos cobrem somente as temporadas 2 a 8;
- as relações são tratadas como não direcionadas e ponderadas;
- Weight é força/frequência de interação, não custo de caminho;
- o custo derivado para caminhos é cost = 1 / weight_strength;
- arestas repetidas ou invertidas são agregadas sem alterar os CSVs originais;
- as comunidades principais são detectadas com Leiden e avaliadas em várias seeds;
- métricas e posições dos nós usam layout global estável para permitir comparação.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import igraph as ig
import leidenalg as la
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.lines import Line2D
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

AUTHOR = "Diogo da Silva Rego"
REGISTRATION = "20240045381"
PROFESSOR = "Ana Flávia"
INSTITUTION = "Centro de Ciências Exatas e da Natureza (CCEN) — UFPB"
SEASONS = list(range(2, 9))
SEED = 42
RESOLUTIONS = (0.75, 1.0, 1.25)
SENSITIVITY_SEEDS = (42, 43, 44)
AUTHOR_CREDIT = "Autor: Diogo Rego"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:10000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def read_edges_raw(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    delimiter = detect_delimiter(path)
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            frame = pd.read_csv(path, sep=delimiter, encoding=encoding)
            break
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    else:
        raise ValueError(f"Não foi possível ler {path}: {last_error}")
    frame.columns = [str(column).strip() for column in frame.columns]
    diagnostics = {
        "arquivo": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "delimitador": delimiter,
        "encoding_tentado": encoding,
        "linhas": int(len(frame)),
        "colunas": list(frame.columns),
        "nulos_por_coluna": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "linhas_duplicadas_brutas": int(frame.duplicated().sum()),
        "amostra_5_linhas": frame.head(5).fillna("").astype(str).to_dict("records"),
    }
    return frame, diagnostics


def infer_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    lower = {str(column).strip().lower(): str(column) for column in frame.columns}

    def first(candidates: list[str]) -> str | None:
        for candidate in candidates:
            if candidate in lower:
                return lower[candidate]
        return None

    source = first(["source", "src", "from", "origin", "origem", "u"])
    target = first(["target", "dst", "to", "destination", "destino", "v"])
    weight = first(["weight", "peso", "strength", "forca", "frequency", "frequencia"])
    season = first(["season", "temporada", "snapshot", "period", "periodo"])
    if source is None or target is None:
        raise ValueError(f"Não foi possível identificar Source/Target nas colunas {list(frame.columns)}")
    return {"source": source, "target": target, "weight": weight, "season": season}


def compare_duplicate_s2(primary: Path, duplicate: Path) -> dict[str, Any]:
    primary_df, primary_diag = read_edges_raw(primary)
    duplicate_df, duplicate_diag = read_edges_raw(duplicate)
    byte_equal = primary.read_bytes() == duplicate.read_bytes()
    frame_equal = primary_df.equals(duplicate_df)
    differences: dict[str, Any] = {
        "byte_identical": byte_equal,
        "dataframe_identical": frame_equal,
        "primary": primary_diag,
        "duplicate": duplicate_diag,
        "differences": [],
    }
    if not frame_equal:
        merged = pd.merge(primary_df, duplicate_df, how="outer", indicator=True)
        only_primary = int((merged["_merge"] == "left_only").sum())
        only_duplicate = int((merged["_merge"] == "right_only").sum())
        differences["differences"] = [
            "Os arquivos possuem conteúdo tabular diferente; nenhum deles foi combinado automaticamente.",
            f"Linhas somente no primeiro: {only_primary}",
            f"Linhas somente no duplicado: {only_duplicate}",
        ]
    else:
        differences["differences"] = ["Os arquivos são idênticos; somente got-s2-edges.csv foi usado."]
    return differences


def clean_season_edges(path: Path, season: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw, diagnostics = read_edges_raw(path)
    columns = infer_columns(raw)
    source_col, target_col = columns["source"], columns["target"]
    weight_col, season_col = columns["weight"], columns["season"]
    assert source_col is not None and target_col is not None

    work = pd.DataFrame()
    work["source"] = raw[source_col].astype("string").str.strip()
    work["target"] = raw[target_col].astype("string").str.strip()
    if weight_col is None:
        work["weight_strength"] = 1.0
    else:
        work["weight_strength"] = pd.to_numeric(raw[weight_col], errors="coerce")
    work["season"] = season

    before = len(work)
    missing_rows = int(work[["source", "target", "weight_strength"]].isna().any(axis=1).sum())
    work = work.dropna(subset=["source", "target", "weight_strength"]).copy()
    work = work[(work["source"] != "") & (work["target"] != "")].copy()
    empty_rows_removed = before - len(work)
    loops_removed = int((work["source"] == work["target"]).sum())
    work = work[work["source"] != work["target"]].copy()
    negative_weights = int((work["weight_strength"] < 0).sum())
    if negative_weights:
        raise ValueError(f"Pesos negativos encontrados em {path.name}; a análise Leiden positiva foi interrompida.")

    work["left"] = work[["source", "target"]].min(axis=1)
    work["right"] = work[["source", "target"]].max(axis=1)
    pairs_before = len(work)
    grouped = (
        work.groupby(["left", "right", "season"], as_index=False)["weight_strength"]
        .sum()
        .rename(columns={"left": "source", "right": "target"})
    )
    duplicate_or_reversed_aggregated = pairs_before - len(grouped)
    grouped["cost"] = 1.0 / grouped["weight_strength"].clip(lower=1e-12)
    grouped = grouped[["source", "target", "weight_strength", "cost", "season"]]
    case_variants = int(grouped["source"].str.casefold().duplicated().sum() + grouped["target"].str.casefold().duplicated().sum())

    season_values = []
    if season_col is not None:
        season_values = sorted(pd.to_numeric(raw[season_col], errors="coerce").dropna().unique().tolist())
    report = {
        **diagnostics,
        "temporada_associada": season,
        "colunas_inferidas": columns,
        "valores_temporada_no_arquivo": season_values,
        "linhas_antes_limpeza": int(before),
        "linhas_com_valores_ausentes_removidas": missing_rows,
        "linhas_vazias_ou_invalidas_removidas": int(empty_rows_removed),
        "loops_removidos": loops_removed,
        "pesos_negativos": negative_weights,
        "arestas_depois_agregacao": int(len(grouped)),
        "arestas_duplicadas_ou_invertidas_agregadas": int(duplicate_or_reversed_aggregated),
        "variacoes_de_caixa_detectadas": case_variants,
        "decisoes": [
            "Espaços excedentes foram removidos dos identificadores.",
            "Arestas não direcionadas A-B e B-A foram tratadas como o mesmo par.",
            "Arestas repetidas foram agregadas por soma de weight_strength.",
            "O CSV original não foi alterado.",
        ],
    }
    return grouped, report


def graph_from_frame(frame: pd.DataFrame, season: int | str) -> ig.Graph:
    nodes = sorted(set(frame["source"].astype(str)) | set(frame["target"].astype(str)))
    index = {node: i for i, node in enumerate(nodes)}
    edges = [(index[row.source], index[row.target]) for row in frame.itertuples()]
    graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
    graph.vs["name"] = nodes
    graph.vs["season"] = str(season)
    graph.es["weight_strength"] = [float(value) for value in frame["weight_strength"]]
    graph.es["cost"] = [float(value) for value in frame["cost"]]
    graph.es["season"] = [str(season)] * graph.ecount()
    graph["temporada"] = str(season)
    graph["modelo"] = "grafo não direcionado ponderado"
    return graph


def graph_to_networkx(graph: ig.Graph) -> nx.Graph:
    output = nx.Graph()
    for vertex in graph.vs:
        output.add_node(str(vertex["name"]), season=vertex["season"])
    for edge in graph.es:
        left = str(graph.vs[edge.source]["name"])
        right = str(graph.vs[edge.target]["name"])
        output.add_edge(left, right, weight_strength=float(edge["weight_strength"]), cost=float(edge["cost"]))
    return output


def minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if math.isclose(low, high):
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]


def largest_component_graph(graph: ig.Graph) -> ig.Graph:
    components = graph.components()
    if len(components) == 0:
        return graph
    largest = max(components, key=len)
    return graph.subgraph(largest)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except Exception:
        return default


def structural_metrics(graph: ig.Graph) -> dict[str, Any]:
    n, m = graph.vcount(), graph.ecount()
    degrees = graph.degree()
    strengths = graph.strength(weights="weight_strength") if m else [0.0] * n
    components = graph.components()
    sizes = sorted(components.sizes(), reverse=True) if components else []
    largest = largest_component_graph(graph)
    if n > 1:
        density = graph.density(loops=False)
        degree_mean = float(np.mean(degrees))
        degree_max = int(max(degrees)) if degrees else 0
    else:
        density, degree_mean, degree_max = 0.0, 0.0, 0
    try:
        assortativity = safe_float(graph.assortativity_degree(directed=False), 0.0)
    except Exception:
        assortativity = 0.0
    try:
        transitivity = safe_float(graph.transitivity_undirected(), 0.0)
    except Exception:
        transitivity = 0.0
    try:
        clustering = safe_float(graph.transitivity_avglocal_undirected(mode="zero"), 0.0)
    except Exception:
        clustering = 0.0
    if largest.vcount() > 1:
        try:
            diameter = safe_float(largest.diameter(weights="cost"), 0.0)
        except Exception:
            diameter = safe_float(largest.diameter(), 0.0)
        try:
            radius = safe_float(largest.radius(), 0.0)
        except Exception:
            radius = 0.0
        try:
            mean_path = safe_float(largest.average_path_length(weights="cost", unconn=False), 0.0)
        except Exception:
            mean_path = safe_float(largest.average_path_length(unconn=False), 0.0)
    else:
        diameter = radius = mean_path = 0.0
    return {
        "vertices": int(n),
        "edges": int(m),
        "density": float(density),
        "components": int(len(components)),
        "largest_component": int(max(sizes, default=0)),
        "degree_mean": degree_mean,
        "degree_max": degree_max,
        "strength_mean": float(np.mean(strengths)) if strengths else 0.0,
        "strength_total": float(sum(strengths)) if strengths else 0.0,
        "assortativity_degree": assortativity,
        "transitivity": transitivity,
        "clustering_mean": clustering,
        "diameter_largest_component_cost": diameter,
        "radius_largest_component_unweighted": radius,
        "average_path_largest_component_cost": mean_path,
        "degree_handshake_lhs": int(sum(degrees)),
        "degree_handshake_rhs": int(2 * m),
        "handshake_lemma_ok": bool(sum(degrees) == 2 * m),
    }


def centrality_table(graph: ig.Graph, season: int | str) -> tuple[pd.DataFrame, dict[int, list[str]], float]:
    n = graph.vcount()
    degrees = graph.degree()
    strengths = graph.strength(weights="weight_strength") if graph.ecount() else [0.0] * n
    if n > 1:
        degree_centrality = [value / (n - 1) for value in degrees]
    else:
        degree_centrality = [0.0] * n
    try:
        betweenness = graph.betweenness(weights="cost", directed=False)
        scale = (n - 1) * (n - 2) / 2 if n > 2 else 1.0
        betweenness = [safe_float(value) / scale for value in betweenness]
    except Exception:
        betweenness = [0.0] * n
    try:
        closeness = [safe_float(value) for value in graph.closeness(weights="cost", normalized=True)]
    except Exception:
        closeness = [0.0] * n
    try:
        eigenvector = [safe_float(value) for value in graph.eigenvector_centrality(directed=False, weights="weight_strength")]
    except Exception:
        eigenvector = [0.0] * n
    try:
        pagerank = [safe_float(value) for value in graph.pagerank(directed=False, weights="weight_strength")]
    except Exception:
        pagerank = [0.0] * n

    combined = np.mean(np.array([minmax(degree_centrality), minmax(strengths), minmax(betweenness), minmax(closeness), minmax(eigenvector), minmax(pagerank)]), axis=0)
    try:
        partition = la.find_partition(graph, la.RBConfigurationVertexPartition, weights="weight_strength", resolution_parameter=1.0, seed=SEED, n_iterations=2)
        membership = partition.membership
        quality = safe_float(partition.quality())
    except Exception:
        membership, quality = [0] * n, 0.0
    rows = []
    for index, vertex in enumerate(graph.vs):
        rows.append({
            "season": str(season),
            "character": str(vertex["name"]),
            "degree": int(degrees[index]),
            "degree_centrality": float(degree_centrality[index]),
            "strength_weighted": float(strengths[index]),
            "betweenness": float(betweenness[index]),
            "closeness": float(closeness[index]),
            "eigenvector_centrality": float(eigenvector[index]),
            "pagerank": float(pagerank[index]),
            "centrality_combined": float(combined[index]),
            "community": int(membership[index]),
        })
    return pd.DataFrame(rows), {int(k): [str(graph.vs[i]["name"]) for i, value in enumerate(membership) if value == k] for k in sorted(set(membership))}, quality


def community_sensitivity(graph: ig.Graph, season: int | str) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, list[str]], float, float]:
    records = []
    best_partition = None
    best_quality = -float("inf")
    best_resolution = None
    best_seed = None
    for resolution in RESOLUTIONS:
        for seed in SENSITIVITY_SEEDS:
            partition = la.find_partition(graph, la.RBConfigurationVertexPartition, weights="weight_strength", resolution_parameter=resolution, seed=seed, n_iterations=2)
            quality = safe_float(partition.quality())
            records.append({
                "season": str(season),
                "objective": "RBConfiguration",
                "resolution": resolution,
                "seed": seed,
                "communities": len(set(partition.membership)),
                "quality": quality,
                "vertices": graph.vcount(),
            })
            if quality > best_quality:
                best_quality = quality
                best_partition = partition
                best_resolution = resolution
                best_seed = seed
    assert best_partition is not None
    assert best_resolution is not None and best_seed is not None
    selected_modularity = safe_float(graph.modularity(best_partition.membership, weights="weight_strength"))
    communities = defaultdict(list)
    strengths = graph.strength(weights="weight_strength") if graph.ecount() else [0.0] * graph.vcount()
    for index, community_id in enumerate(best_partition.membership):
        communities[int(community_id)].append(index)
    community_rows = []
    for community_id, indices in sorted(communities.items()):
        ordered = sorted(indices, key=lambda i: strengths[i], reverse=True)
        top = [str(graph.vs[i]["name"]) for i in ordered[:8]]
        community_rows.append({
            "season": str(season),
            "community": community_id,
            "size": len(indices),
            "objective_quality": best_quality,
            "modularity": selected_modularity,
            "resolution_selected": best_resolution,
            "seed_selected": best_seed,
            "top_characters": ", ".join(top),
        })
    return pd.DataFrame(records), pd.DataFrame(community_rows), {key: [str(graph.vs[i]["name"]) for i in value] for key, value in communities.items()}, best_quality, selected_modularity


def export_graphs(graph: ig.Graph, output: Path, stem: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    graph.write_graphml(str(output / f"{stem}.graphml"))
    nx_graph = graph_to_networkx(graph)
    nx.write_gexf(nx_graph, output / f"{stem}.gexf")
    nx.write_edgelist(nx_graph, output / f"{stem}.edgelist", data=["weight_strength", "cost"])


def build_stable_positions(union_graph: nx.Graph) -> dict[str, np.ndarray]:
    if union_graph.number_of_nodes() == 0:
        return {}
    return nx.spring_layout(union_graph, seed=SEED, weight=None, iterations=700, k=2.4 / math.sqrt(max(union_graph.number_of_nodes(), 1)))


def draw_static_graph(graph: nx.Graph, positions: dict[str, np.ndarray], communities: dict[str, int], output: Path, title: str, filename: str, label_count: int = 14) -> None:
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    ax.set_facecolor("#F8FAFC")
    if graph.number_of_nodes() == 0:
        ax.axis("off")
        fig.savefig(output / filename, dpi=240, bbox_inches="tight")
        plt.close(fig)
        return
    strengths = {node: sum(float(data.get("weight_strength", 1.0)) for _, _, data in graph.edges(node, data=True)) for node in graph.nodes}
    max_strength = max(strengths.values(), default=1.0)
    palette = sns.color_palette("tab20", max(1, len(set(communities.values())))).as_hex()
    color_map = {community: palette[i % len(palette)] for i, community in enumerate(sorted(set(communities.values())))}
    widths = [0.2 + 2.2 * math.sqrt(float(data.get("weight_strength", 1.0)) / max(max_strength, 1.0)) for _, _, data in graph.edges(data=True)]
    nx.draw_networkx_edges(graph, positions, ax=ax, width=widths, edge_color="#94A3B8", alpha=0.32)
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=[45 + 15 * math.sqrt(strengths[node] + 1) for node in graph.nodes], node_color=[color_map.get(communities.get(node, 0), "#64748B") for node in graph.nodes], edgecolors="white", linewidths=0.45, alpha=0.9)
    labels = {node: node for node in sorted(graph.nodes, key=lambda value: strengths[value], reverse=True)[:label_count]}
    nx.draw_networkx_labels(graph, positions, labels=labels, ax=ax, font_size=7, font_weight="bold", bbox={"boxstyle": "round,pad=0.14", "facecolor": "white", "edgecolor": "#CBD5E1", "alpha": 0.88})
    handles = [Line2D([], [], marker="o", linestyle="none", markerfacecolor=color_map[key], markeredgecolor="white", markersize=8, label=f"Comunidade {key}") for key in sorted(color_map)[:10]]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), title="Leiden — cores")
    ax.set_title(f"{title}\nPosições globais fixas; rótulos = maiores forças de interação", fontsize=16, fontweight="bold")
    ax.text(0.0, -0.045, f"{AUTHOR_CREDIT} | Tamanho do nó: força ponderada | Espessura: weight_strength | Cores: comunidade Leiden | Relação não direcionada", transform=ax.transAxes, fontsize=9, color="#475569")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output / filename, dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig((output / filename).with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_interactive(graphs: dict[int, nx.Graph], positions: dict[str, np.ndarray], memberships: dict[int, dict[str, int]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    palette = sns.color_palette("tab20", 20).as_hex()
    frames = []
    for season, graph in graphs.items():
        edge_x, edge_y = [], []
        for left, right in graph.edges:
            edge_x.extend([positions[left][0], positions[right][0], None])
            edge_y.extend([positions[left][1], positions[right][1], None])
        edges = go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"width": 0.6, "color": "#CBD5E1"}, hoverinfo="skip", name="Arestas")
        nodes = list(graph.nodes)
        strengths = {node: sum(float(data.get("weight_strength", 1.0)) for _, _, data in graph.edges(node, data=True)) for node in nodes}
        custom = [[node, season, int(graph.degree[node]), float(strengths[node]), int(memberships[season].get(node, 0))] for node in nodes]
        node_trace = go.Scatter(x=[positions[node][0] for node in nodes], y=[positions[node][1] for node in nodes], mode="markers", name=f"Temporada {season}", marker={"size": [7 + 2 * math.sqrt(graph.degree[node] + 1) for node in nodes], "color": [palette[memberships[season].get(node, 0) % len(palette)] for node in nodes], "line": {"width": 0.7, "color": "white"}}, customdata=custom, hovertemplate="<b>%{customdata[0]}</b><br>Temporada: %{customdata[1]}<br>Grau: %{customdata[2]}<br>Força ponderada: %{customdata[3]:.1f}<br>Comunidade Leiden: %{customdata[4]}<extra></extra>")
        frames.append(go.Frame(name=str(season), data=[edges, node_trace]))
    initial = frames[0].data
    steps = [{"label": f"S{season}", "method": "animate", "args": [[str(season)], {"mode": "immediate", "frame": {"duration": 650, "redraw": True}, "transition": {"duration": 250}}]} for season in graphs]
    fig = go.Figure(data=initial, frames=frames)
    fig.update_layout(
        title="Evolução interativa dos grafos ponderados — temporadas 2–8",
        template="plotly_white",
        hovermode="closest",
        showlegend=False,
        sliders=[{"active": 0, "currentvalue": {"prefix": "Temporada: "}, "steps": steps}],
        annotations=[{"text": f"{AUTHOR_CREDIT} | Tamanho: grau | Cor: comunidade Leiden | Hover: personagem, peso e comunidade | Posições globais fixas", "xref": "paper", "yref": "paper", "x": 0, "y": -0.08, "showarrow": False, "font": {"size": 11, "color": "#475569"}}],
        margin={"l": 10, "r": 10, "t": 75, "b": 70},
        xaxis={"showticklabels": False, "showgrid": False, "zeroline": False},
        yaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "scaleanchor": "x", "scaleratio": 1},
    )
    fig.write_html(output / "got_temporal_s02_s08_interativo.html", include_plotlyjs=True, full_html=True, auto_open=False)


def compare_consecutive(graphs: dict[int, ig.Graph], centralities: dict[int, pd.DataFrame], metrics: dict[int, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for left, right in zip(SEASONS[:-1], SEASONS[1:]):
        left_nodes = set(graphs[left].vs["name"])
        right_nodes = set(graphs[right].vs["name"])
        left_edges = {(min(str(graphs[left].vs[e.source]["name"]), str(graphs[left].vs[e.target]["name"])), max(str(graphs[left].vs[e.source]["name"]), str(graphs[left].vs[e.target]["name"]))) for e in graphs[left].es}
        right_edges = {(min(str(graphs[right].vs[e.source]["name"]), str(graphs[right].vs[e.target]["name"])), max(str(graphs[right].vs[e.source]["name"]), str(graphs[right].vs[e.target]["name"]))) for e in graphs[right].es}
        inter_nodes = left_nodes & right_nodes
        if inter_nodes:
            a = centralities[left].set_index("character").loc[sorted(inter_nodes), "centrality_combined"]
            b = centralities[right].set_index("character").loc[sorted(inter_nodes), "centrality_combined"]
            corr = float(a.corr(b)) if len(inter_nodes) > 1 else 1.0
        else:
            corr = 0.0
        rows.append({
            "transicao": f"{left}->{right}",
            "temporada_origem": left,
            "temporada_destino": right,
            "vertices_surgiram": len(right_nodes - left_nodes),
            "vertices_desapareceram": len(left_nodes - right_nodes),
            "arestas_novas": len(right_edges - left_edges),
            "arestas_removidas": len(left_edges - right_edges),
            "persistencia_vertices": len(inter_nodes) / max(len(left_nodes | right_nodes), 1),
            "persistencia_arestas": len(left_edges & right_edges) / max(len(left_edges | right_edges), 1),
            "jaccard_vertices": len(inter_nodes) / max(len(left_nodes | right_nodes), 1),
            "jaccard_arestas": len(left_edges & right_edges) / max(len(left_edges | right_edges), 1),
            "correlacao_centralidade_combinada_intersecao": corr,
            "densidade_origem": metrics[left]["density"],
            "densidade_destino": metrics[right]["density"],
            "grau_medio_origem": metrics[left]["degree_mean"],
            "grau_medio_destino": metrics[right]["degree_mean"],
            "modularidade_origem": metrics[left]["modularity_leiden"],
            "modularidade_destino": metrics[right]["modularity_leiden"],
        })
    return pd.DataFrame(rows)


def save_evolution_figures(summary_df: pd.DataFrame, centralities: pd.DataFrame, comparisons: pd.DataFrame, output: Path) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), dpi=150)
    plots = [("vertices", "Número de vértices"), ("edges", "Número de arestas"), ("density", "Densidade"), ("degree_mean", "Grau médio"), ("modularity_leiden", "Modularidade Leiden"), ("largest_component", "Maior componente")]
    for ax, (column, title) in zip(axes.flat, plots):
        ax.plot(summary_df["season"], summary_df[column], marker="o", linewidth=2.2, color="#2563EB")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Temporada")
        ax.set_xticks(SEASONS)
    fig.suptitle("Evolução estrutural das redes de Game of Thrones — S2–S8", fontsize=17, fontweight="bold")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Cada ponto é um snapshot de temporada; comunidades calculadas com Leiden RBConfiguration.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(output / "evolucao_temporal_metricas.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "evolucao_temporal_metricas.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    top = centralities.groupby("character")["centrality_combined"].mean().nlargest(15).index
    heat = centralities[centralities["character"].isin(top)].pivot_table(index="character", columns="season", values="centrality_combined", fill_value=0).reindex(columns=[str(season) for season in SEASONS], fill_value=0)
    fig, ax = plt.subplots(figsize=(13, 8), dpi=150)
    sns.heatmap(heat, cmap="viridis", annot=True, fmt=".2f", linewidths=0.3, ax=ax)
    ax.set_title("Heatmap — 15 personagens com maior centralidade combinada média", fontweight="bold")
    ax.set_xlabel("Temporada")
    ax.set_ylabel("Personagem")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Centralidade combinada = média min-max de grau, força, betweenness, closeness, eigenvector e PageRank.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output / "heatmap_centralidades_top15.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "heatmap_centralidades_top15.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    persistence = centralities.groupby("character")["season"].nunique().sort_values(ascending=False).head(25).sort_values()
    fig, ax = plt.subplots(figsize=(11, 8), dpi=150)
    persistence.plot.barh(ax=ax, color="#059669")
    ax.set_title("Permanência dos 25 personagens mais presentes", fontweight="bold")
    ax.set_xlabel("Número de temporadas")
    ax.set_ylabel("Personagem")
    ax.set_xlim(0, 7)
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Presença = personagem observado no arquivo correspondente à temporada.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output / "permanencia_personagens.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "permanencia_personagens.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    top_each = centralities.sort_values(["season", "centrality_combined"], ascending=[True, False]).groupby("season").head(10)
    fig, ax = plt.subplots(figsize=(16, 8), dpi=150)
    sns.barplot(data=top_each, x="character", y="centrality_combined", hue="season", ax=ax, dodge=False, palette="tab10")
    ax.set_title("Personagens entre os dez mais centrais em cada temporada", fontweight="bold")
    ax.set_xlabel("Personagem")
    ax.set_ylabel("Centralidade combinada")
    ax.tick_params(axis="x", rotation=65)
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | A seleção é feita separadamente em cada temporada; cores indicam o snapshot.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output / "top10_centralidade_por_temporada.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "top10_centralidade_por_temporada.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    x = np.arange(len(comparisons))
    width = 0.35
    ax.bar(x - width / 2, comparisons["arestas_novas"], width, label="Arestas novas", color="#059669")
    ax.bar(x + width / 2, comparisons["arestas_removidas"], width, label="Arestas removidas", color="#DC2626")
    ax.set_xticks(x, comparisons["transicao"])
    ax.set_ylabel("Quantidade")
    ax.set_title("Mudanças de arestas entre temporadas consecutivas", fontweight="bold")
    ax.legend()
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Arestas são pares não direcionados após limpeza e agregação.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output / "evolucao_arestas_adicionadas_removidas.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / "evolucao_arestas_adicionadas_removidas.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_validation_report(graphs: dict[int, ig.Graph], centralities: dict[int, pd.DataFrame], output: Path) -> dict[str, Any]:
    rows = []
    for season, graph in graphs.items():
        metrics = structural_metrics(graph)
        rows.append({"temporada": season, **metrics, "vertices_vazios": sum(1 for name in graph.vs["name"] if not str(name).strip()), "pesos_nao_negativos": all(float(weight) >= 0 for weight in graph.es["weight_strength"])})
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "validacao_grafos.csv", index=False, encoding="utf-8-sig")
    return {
        "soma_graus_igual_a_duas_arestas": bool(frame["handshake_lemma_ok"].all()),
        "pesos_nao_negativos": bool(frame["pesos_nao_negativos"].all()),
        "identificadores_vazios": int(frame["vertices_vazios"].sum()),
        "temporadas_validadas": SEASONS,
    }


def analyze_got(input_dir: str | Path, output_dir: str | Path, duplicate_s2: str | Path | None = None) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    graph_dir = output_dir / "grafos"
    figure_dir = output_dir / "figuras"
    table_dir = output_dir / "tabelas"
    graph_dir.mkdir(exist_ok=True)
    figure_dir.mkdir(exist_ok=True)
    table_dir.mkdir(exist_ok=True)

    s2_primary = input_dir / "got-s2-edges.csv"
    duplicate = Path(duplicate_s2) if duplicate_s2 else input_dir / "got-s2-edges(1).csv"
    duplicate_report = compare_duplicate_s2(s2_primary, duplicate) if s2_primary.exists() and duplicate.exists() else {"status": "arquivo duplicado não fornecido"}
    (table_dir / "auditoria_got_s2_duplicado.json").write_text(json.dumps(duplicate_report, ensure_ascii=False, indent=2), encoding="utf-8")

    graphs: dict[int, ig.Graph] = {}
    nx_graphs: dict[int, nx.Graph] = {}
    clean_frames: dict[int, pd.DataFrame] = {}
    audits = []
    metric_rows = []
    centrality_tables = []
    community_tables = []
    sensitivity_tables = []
    memberships: dict[int, dict[str, int]] = {}
    community_quality: dict[int, float] = {}

    for season in SEASONS:
        path = input_dir / f"got-s{season}-edges.csv"
        if not path.exists():
            raise FileNotFoundError(f"Arquivo obrigatório ausente: {path}")
        clean, audit = clean_season_edges(path, season)
        clean_frames[season] = clean
        audits.append(audit)
        graph = graph_from_frame(clean, season)
        graphs[season] = graph
        nx_graphs[season] = graph_to_networkx(graph)
        centrality, _, quality = centrality_table(graph, season)
        sensitivity, communities, selected_memberships, selected_quality, selected_modularity = community_sensitivity(graph, season)
        selected_map = {character: int(community) for community, names in selected_memberships.items() for character in names}
        centrality["community"] = centrality["character"].map(selected_map).fillna(-1).astype(int)
        centrality["community_quality"] = selected_modularity
        centrality_tables.append(centrality)
        sensitivity_tables.append(sensitivity)
        community_tables.append(communities)
        memberships[season] = selected_map
        community_quality[season] = selected_quality
        row = {"season": season, **structural_metrics(graph), "modularity_leiden": selected_modularity, "leiden_objective_quality": selected_quality, "leiden_communities": len(selected_memberships)}
        metric_rows.append(row)
        export_graphs(graph, graph_dir, f"got_s{season}")

    audit_frame = pd.DataFrame(audits)
    audit_frame.to_csv(table_dir / "auditoria_arquivos.csv", index=False, encoding="utf-8-sig")
    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(table_dir / "metricas_por_temporada.csv", index=False, encoding="utf-8-sig")
    centralities_df = pd.concat(centrality_tables, ignore_index=True)
    centralities_df.to_csv(table_dir / "centralidades_por_personagem.csv", index=False, encoding="utf-8-sig")
    pd.concat(sensitivity_tables, ignore_index=True).to_csv(table_dir / "sensibilidade_leiden.csv", index=False, encoding="utf-8-sig")
    pd.concat(community_tables, ignore_index=True).to_csv(table_dir / "comunidades_por_temporada.csv", index=False, encoding="utf-8-sig")

    # Agregado S2-S8.
    union_clean = pd.concat(list(clean_frames.values()), ignore_index=True)
    union_clean = union_clean.groupby(["source", "target"], as_index=False).agg(weight_strength=("weight_strength", "sum"), seasons=("season", lambda values: ",".join(map(str, sorted(set(values))))))
    union_clean["cost"] = 1.0 / union_clean["weight_strength"].clip(lower=1e-12)
    union_clean["season"] = "S2-S8"
    union_graph = graph_from_frame(union_clean, "S2-S8")
    union_nx = graph_to_networkx(union_graph)
    union_centrality, _, union_quality = centrality_table(union_graph, "S2-S8")
    union_sensitivity, union_communities, union_membership, union_selected_quality, union_modularity = community_sensitivity(union_graph, "S2-S8")
    union_centrality["community_quality"] = union_selected_quality
    union_centrality.to_csv(table_dir / "centralidades_uniao_s02_s08.csv", index=False, encoding="utf-8-sig")
    union_sensitivity.to_csv(table_dir / "sensibilidade_leiden_uniao.csv", index=False, encoding="utf-8-sig")
    union_communities.to_csv(table_dir / "comunidades_uniao_s02_s08.csv", index=False, encoding="utf-8-sig")
    export_graphs(union_graph, graph_dir, "got_uniao_s02_s08")

    all_cent = pd.concat(centrality_tables, ignore_index=True)
    comparisons = compare_consecutive(graphs, {season: centrality_tables[i] for i, season in enumerate(SEASONS)}, {season: metric_rows[i] for i, season in enumerate(SEASONS)})
    comparisons.to_csv(table_dir / "comparacao_temporadas_consecutivas.csv", index=False, encoding="utf-8-sig")
    all_cent.groupby("character")["season"].nunique().reset_index(name="temporadas_presentes").sort_values(["temporadas_presentes", "character"], ascending=[False, True]).to_csv(table_dir / "persistencia_personagens.csv", index=False, encoding="utf-8-sig")
    all_cent[all_cent["character"].isin(set.intersection(*[set(frame["character"]) for frame in centrality_tables]))].sort_values("character").to_csv(table_dir / "personagens_presentes_todas_temporadas.csv", index=False, encoding="utf-8-sig")

    first_last = all_cent.sort_values(["character", "season"]).groupby("character").agg(primeira_temporada=("season", "first"), ultima_temporada=("season", "last"), centralidade_inicial=("centrality_combined", "first"), centralidade_final=("centrality_combined", "last"), temporadas=("season", "nunique")).reset_index()
    first_last["mudanca_centralidade"] = first_last["centralidade_final"] - first_last["centralidade_inicial"]
    first_last.sort_values("mudanca_centralidade", ascending=False).to_csv(table_dir / "mudanca_centralidade_personagens.csv", index=False, encoding="utf-8-sig")

    positions = build_stable_positions(union_nx)
    for season in SEASONS:
        draw_static_graph(nx_graphs[season], positions, memberships[season], figure_dir, f"Grafo ponderado — temporada {season}", f"got_s{season}_comunidades.png")
    draw_static_graph(union_nx, positions, {node: int(union_membership.get(node, 0)) for node in union_nx.nodes}, figure_dir, "União ponderada dos grafos — temporadas 2 a 8", "got_uniao_s02_s08_comunidades.png", label_count=25)
    save_interactive(nx_graphs, positions, memberships, output_dir / "interativo")
    save_evolution_figures(metrics_df, all_cent, comparisons, figure_dir)

    validation = save_validation_report(graphs, centrality_tables, table_dir)
    config = {
        "temporadas": SEASONS,
        "seed_layout": SEED,
        "sensibilidade_leiden_seeds": list(SENSITIVITY_SEEDS),
        "sensibilidade_leiden_resolutions": list(RESOLUTIONS),
        "weight_strength": "soma de Weight após limpeza e agregação de pares não direcionados",
        "cost": "1 / weight_strength; usado em caminhos, betweenness e closeness ponderadas",
        "direcao": "não direcionado",
        "temporadas_cobertas": "S2-S8; não há arquivo S1 na entrada fornecida",
        "bibliotecas": {"igraph": ig.__version__, "leidenalg": getattr(la, "__version__", "não informado"), "networkx": nx.__version__},
        "python": sys.version,
        "platform": platform.platform(),
    }
    (output_dir / "configuracao_analise.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "auditoria_s2_duplicado.json").write_text(json.dumps(duplicate_report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "autor": AUTHOR,
        "matricula": REGISTRATION,
        "professora": PROFESSOR,
        "escopo": "temporadas 2 a 8; got-s2-edges.csv e got-s2-edges(1).csv foram comparados; somente o primeiro foi utilizado",
        "temporadas": SEASONS,
        "nos_uniao": int(union_graph.vcount()),
        "arestas_uniao": int(union_graph.ecount()),
        "peso_total_uniao": float(sum(union_graph.es["weight_strength"])) if union_graph.ecount() else 0.0,
        "personagens_presentes_todas_temporadas": int(len(set.intersection(*[set(frame["character"]) for frame in centrality_tables]))),
        "comunidades_uniao": int(len(union_membership)),
        "modularidade_leiden_uniao": float(union_modularity),
        "qualidade_objetivo_leiden_uniao": float(union_selected_quality),
        "validacao": validation,
        "saidas": {
            "metricas": "tabelas/metricas_por_temporada.csv",
            "centralidades": "tabelas/centralidades_por_personagem.csv",
            "comunidades": "tabelas/comunidades_por_temporada.csv",
            "comparacao": "tabelas/comparacao_temporadas_consecutivas.csv",
            "interativo": "interativo/got_temporal_s02_s08_interativo.html",
            "gexf": "grafos/got_s2.gexf até got_s8.gexf e got_uniao_s02_s08.gexf",
        },
    }
    (output_dir / "resumo_got_temporal.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analisa as redes GOT S2-S8 com igraph e Leiden.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--duplicate-s2", type=Path, default=None)
    args = parser.parse_args()
    result = analyze_got(args.input_dir, args.output_dir, args.duplicate_s2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
