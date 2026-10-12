"""Pipeline reproduzível da análise temporal de terremotos.

Reutiliza as funções cartográficas e de centralidade auditadas do módulo
`earthquake_got_temporal_analysis.py`, separando esta análise da camada S2-S8.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import networkx as nx

import earthquake_got_temporal_analysis as legacy


def run_earthquakes(earthquakes_path: str | Path, output_dir: str | Path, cell_size_degrees: float = 10.0) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    raw = legacy.load_earthquakes(earthquakes_path)
    selected, window_summary = legacy.select_busiest_five_day_window(raw)
    days = sorted(selected["day_label"].unique())
    legacy.write_csv(raw, output / "terremotos_tratados_todos_dias.csv")
    legacy.write_csv(selected, output / "terremotos_intervalo_cinco_dias.csv")
    daily_counts = selected.groupby("day_label").agg(
        terremotos=("event_id", "count"),
        magnitude_media=("mag", "mean"),
        magnitude_maxima=("mag", "max"),
    ).reset_index()
    legacy.write_csv(daily_counts, output / "resumo_diario_terremotos.csv")

    event_graph = legacy.build_event_temporal_graph(selected)
    event_metrics = legacy.calculate_graph_centralities(event_graph)
    legacy.write_csv(event_metrics, output / "centralidades_temporais_eventos.csv")
    legacy.write_csv(pd.DataFrame([{**{"source": left, "target": right}, **data} for left, right, data in event_graph.edges(data=True)]), output / "arestas_grafo_temporal_eventos.csv")

    cell_graph, selected_cells = legacy.build_cell_temporal_graph(selected, cell_size_degrees)
    cell_metrics = legacy.calculate_graph_centralities(cell_graph)
    cell_metadata = selected_cells.groupby("cell_id").agg(
        latitude_media=("latitude", "mean"), longitude_media=("longitude", "mean"),
        eventos=("event_id", "count"), dias_ativos=("day_label", "nunique"), magnitude_media=("mag", "mean"),
    ).reset_index().rename(columns={"cell_id": "no"})
    cell_metrics = cell_metrics.merge(cell_metadata, on="no", how="left")
    legacy.write_csv(cell_metrics, output / "centralidades_temporais_celulas.csv")
    legacy.write_csv(pd.DataFrame([{**{"source": left, "target": right}, **data} for left, right, data in cell_graph.edges(data=True)]), output / "arestas_grafo_temporal_celulas.csv")

    def event_builder(group: pd.DataFrame) -> nx.Graph:
        return legacy.build_event_temporal_graph(group)

    def cell_builder(group: pd.DataFrame) -> nx.Graph:
        graph, _ = legacy.build_cell_temporal_graph(group, cell_size_degrees)
        return graph

    event_daily = legacy.daily_temporal_metrics(selected, event_builder)
    cell_daily = legacy.daily_temporal_metrics(selected, cell_builder)
    legacy.write_csv(event_daily, output / "centralidades_por_dia_eventos.csv")
    legacy.write_csv(cell_daily, output / "centralidades_por_dia_celulas.csv")
    event_temporal = legacy.temporal_aggregate(event_daily)
    cell_temporal = legacy.temporal_aggregate(cell_daily)
    legacy.write_csv(event_temporal, output / "medidas_temporais_agregadas_eventos.csv")
    legacy.write_csv(cell_temporal, output / "medidas_temporais_agregadas_celulas.csv")

    world = legacy.ensure_world_layer(output)
    for day in days:
        legacy.save_earthquake_daily_map(selected, output / f"mapa_mundi_terremotos_{legacy.safe_slug(day)}.png", world, day)
    legacy.save_earthquake_five_day_panel(selected, output / "mapa_mundi_intervalo_cinco_dias.png", world, days)
    legacy.save_earthquake_interactive(selected, output / "mapa_mundi_terremotos_interativo.html", days)
    legacy.save_earthquake_graph_snapshots(selected, output, cell_size_degrees)

    if not cell_daily.empty:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(14, 9), dpi=160, sharex=True)
        for metric, color, label in [("grau", "#2563EB", "Grau médio"), ("forca_peso", "#D97706", "Força média"), ("betweenness", "#7C3AED", "Betweenness média"), ("closeness", "#059669", "Closeness média")]:
            if metric in cell_daily:
                means = cell_daily.groupby("dia")[metric].mean()
                axes[0].plot(means.index, means.values, marker="o", label=label, color=color)
        for cell in cell_temporal.head(5)["no"].tolist():
            subset = cell_daily[cell_daily["no"] == cell]
            axes[1].plot(subset["dia"], subset["centralidade_combinada"], marker="o", label=str(cell))
        axes[0].set_title("Evolução média das centralidades por dia", fontweight="bold")
        axes[0].legend(ncol=2)
        axes[1].set_title("Centralidade combinada das cinco células mais relevantes", fontweight="bold")
        axes[1].legend(ncol=3, fontsize=8)
        for ax in axes:
            ax.grid(alpha=0.25)
            ax.tick_params(axis="x", rotation=30)
        fig.text(0.01, 0.01, f"{legacy.AUTHOR_CREDIT} | Painel superior: médias diárias; painel inferior: cinco células mais relevantes.", fontsize=9, color="#475569")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(output / "evolucao_centralidades_temporais.png", dpi=240, bbox_inches="tight", facecolor="white")
        fig.savefig(output / "evolucao_centralidades_temporais.pdf", bbox_inches="tight", facecolor="white")
        plt.close(fig)

    summary = {
        **window_summary,
        "eventos_total_arquivo": int(len(raw)),
        "dias_total_arquivo": int(raw["day"].nunique()),
        "modelo_eventos": {"nos": event_graph.number_of_nodes(), "arestas": event_graph.number_of_edges()},
        "modelo_celulas": {"nos": cell_graph.number_of_nodes(), "arestas": cell_graph.number_of_edges(), "tamanho_celula_graus": cell_size_degrees},
        "nota_metodologica": "A análise por snapshots/células é um modelo analítico; não representa causalidade nem previsão sísmica.",
    }
    (output / "resumo_terremotos_temporal.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--earthquakes", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cell-size", type=float, default=10.0)
    args = parser.parse_args()
    print(json.dumps(run_earthquakes(args.earthquakes, args.output_dir, args.cell_size), ensure_ascii=False, indent=2))
