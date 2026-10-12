"""Análise temporal do dataset usado pelo notebook college_msg.ipynb.

Observação de rastreabilidade: o notebook recebido aponta para
email-Eu-core-temporal.txt.gz do Stanford SNAP, apesar do nome do arquivo ser
college_msg.ipynb. Essa nomenclatura é preservada e explicitada no relatório.
"""
from __future__ import annotations

import gzip
import io
import json
import platform
import sys
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

AUTHOR = "Diogo da Silva Rego"
REGISTRATION = "20240045381"
AUTHOR_CREDIT = "Autor: Diogo Rego"
SOURCE_URL = "https://snap.stanford.edu/data/email-Eu-core-temporal.txt.gz"


def download_source(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / "email-Eu-core-temporal.txt.gz"
    if not target.exists():
        urllib.request.urlretrieve(SOURCE_URL, target)
    return target


def load_temporal_edges(path: Path) -> pd.DataFrame:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            source, target, timestamp = map(int, line.split())
            rows.append({"source": source, "target": target, "timestamp": timestamp})
    frame = pd.DataFrame(rows)
    frame["datetime"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    frame["date"] = frame["datetime"].dt.floor("D")
    return frame


def graph_at_window(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> nx.Graph:
    subset = frame[(frame["datetime"] >= start) & (frame["datetime"] < end)]
    graph = nx.Graph(window_start=start.isoformat(), window_end=end.isoformat())
    for row in subset.itertuples():
        if row.source == row.target:
            continue
        if graph.has_edge(row.source, row.target):
            graph[row.source][row.target]["weight"] += 1.0
        else:
            graph.add_edge(row.source, row.target, weight=1.0)
    return graph


def centralities(graph: nx.Graph) -> pd.DataFrame:
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=["node", "degree", "degree_centrality", "betweenness", "closeness", "eigenvector", "pagerank"])
    degree = dict(graph.degree())
    degree_c = nx.degree_centrality(graph)
    betweenness = nx.betweenness_centrality(graph, weight=None, normalized=True)
    closeness = nx.closeness_centrality(graph, distance=None)
    try:
        eigenvector = nx.eigenvector_centrality(graph, max_iter=1000, weight="weight")
    except nx.PowerIterationFailedConvergence:
        eigenvector = {node: 0.0 for node in graph.nodes}
    pagerank = nx.pagerank(graph, weight="weight")
    rows = []
    for node in graph.nodes:
        rows.append({"node": int(node), "degree": degree[node], "degree_centrality": degree_c[node], "betweenness": betweenness[node], "closeness": closeness[node], "eigenvector": eigenvector[node], "pagerank": pagerank[node]})
    return pd.DataFrame(rows)


def run(output_dir: str | Path, window_days: int = 7) -> dict:
    output = Path(output_dir)
    data_dir = output / "dados"
    table_dir = output / "tabelas"
    figure_dir = output / "figuras"
    for folder in (data_dir, table_dir, figure_dir):
        folder.mkdir(parents=True, exist_ok=True)
    source = download_source(data_dir)
    frame = load_temporal_edges(source)
    frame.to_csv(table_dir / "college_msg_eventos_temporais.csv", index=False, encoding="utf-8-sig")
    start = frame["datetime"].min().floor("D")
    last = frame["datetime"].max()
    rows = []
    all_cent = []
    current = start
    window_index = 0
    while current <= last:
        end = current + pd.Timedelta(days=window_days)
        graph = graph_at_window(frame, current, end)
        if graph.number_of_nodes() > 0:
            cent = centralities(graph)
            cent["window"] = window_index
            cent["window_start"] = current.isoformat()
            cent["window_end"] = end.isoformat()
            all_cent.append(cent)
        rows.append({"window": window_index, "window_start": current.isoformat(), "window_end": end.isoformat(), "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(), "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0.0, "weight_total": float(sum(data.get("weight", 1.0) for _, _, data in graph.edges(data=True))), "components": nx.number_connected_components(graph) if graph.number_of_nodes() else 0})
        current = end
        window_index += 1
    summary = pd.DataFrame(rows)
    centrality_frame = pd.concat(all_cent, ignore_index=True) if all_cent else pd.DataFrame()
    summary.to_csv(table_dir / "college_msg_metricas_por_janela.csv", index=False, encoding="utf-8-sig")
    centrality_frame.to_csv(table_dir / "college_msg_centralidades_temporais.csv", index=False, encoding="utf-8-sig")
    if not centrality_frame.empty:
        top = centrality_frame.sort_values(["window", "betweenness"], ascending=[True, False]).groupby("window").head(10)
        top.to_csv(table_dir / "college_msg_top10_betweenness_por_janela.csv", index=False, encoding="utf-8-sig")
        node = int(centrality_frame["node"].value_counts().index[0])
        person = centrality_frame[centrality_frame["node"] == node].sort_values("window_start")
        person.to_csv(table_dir / "college_msg_evolucao_no_mais_frequente.csv", index=False, encoding="utf-8-sig")
        fig, axes = plt.subplots(3, 2, figsize=(15, 11), dpi=150, sharex=True)
        for ax, metric in zip(axes.flat, ["degree_centrality", "betweenness", "closeness", "eigenvector", "pagerank"]):
            ax.plot(pd.to_datetime(person["window_start"]), person[metric], marker="o", color="#2563EB")
            ax.set_title(metric.replace("_", " ").title(), fontweight="bold")
            ax.grid(alpha=0.25)
        axes[-1, -1].axis("off")
        fig.suptitle(f"Evolução das centralidades do nó {node} — janelas de {window_days} dias", fontsize=16, fontweight="bold")
        fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Fonte: Stanford SNAP email-Eu-core-temporal | Nó acompanhado: {node}.", fontsize=9, color="#475569")
        fig.tight_layout(rect=(0, 0.04, 1, 0.95))
        fig.savefig(figure_dir / "college_msg_evolucao_centralidades.png", dpi=240, bbox_inches="tight", facecolor="white")
        fig.savefig(figure_dir / "college_msg_evolucao_centralidades.pdf", bbox_inches="tight", facecolor="white")
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=150)
    for ax, column, title in zip(axes.flat, ["nodes", "edges", "density", "weight_total"], ["Nós por janela", "Arestas por janela", "Densidade por janela", "Força total por janela"]):
        ax.plot(summary["window"], summary[column], marker="o", color="#059669")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Janela temporal")
        ax.grid(alpha=0.25)
    fig.suptitle("Evolução estrutural do grafo temporal CollegeMsg", fontsize=16, fontweight="bold")
    fig.text(0.01, 0.01, f"{AUTHOR_CREDIT} | Janelas consecutivas de {window_days} dias | Arestas repetidas agregadas em weight.", fontsize=9, color="#475569")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(figure_dir / "college_msg_evolucao_rede.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(figure_dir / "college_msg_evolucao_rede.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    result = {"autor": AUTHOR, "matricula": REGISTRATION, "source_url": SOURCE_URL, "arquivo_notebook": "college_msg.ipynb", "observacao": "O notebook recebido usa a URL email-Eu-core-temporal.txt.gz; o nome college_msg.ipynb foi preservado como identificação da atividade.", "interacoes": int(len(frame)), "nos_unicos": int(len(set(frame["source"]) | set(frame["target"]))), "inicio_utc": frame["datetime"].min().isoformat(), "fim_utc": frame["datetime"].max().isoformat(), "janelas": int(len(summary)), "janela_dias": window_days, "saidas": ["tabelas/college_msg_metricas_por_janela.csv", "tabelas/college_msg_centralidades_temporais.csv", "figuras/college_msg_evolucao_centralidades.png", "figuras/college_msg_evolucao_rede.png"], "python": sys.version, "platform": platform.platform()}
    (output / "resumo_college_msg.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--window-days", type=int, default=7)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.window_days), ensure_ascii=False, indent=2))
