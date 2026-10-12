from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def test_seasons_are_s02_s08():
    assert [2,3,4,5,6,7,8] == [int(p.stem.split('s')[1].split('-')[0]) for p in sorted((ROOT/'data/raw').glob('got-s*-edges.csv'))]

def test_outputs_exist():
    assert (ROOT/'results/got_s02_s08/resumo_got_temporal.json').exists()
    assert (ROOT/'results/college_msg/resumo_college_msg.json').exists()
    assert (ROOT/'results/terremotos/resumo_terremotos_temporal.json').exists()

def test_notebook_structure():
    notebook = json.loads((ROOT/'notebooks/analise_grafo_temporal_got_colab.ipynb').read_text())
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 8
    assert "analyze_got" in source
    assert "run_earthquakes" in source
    assert "college_msg_temporal" in source

def test_handshake():
    metrics = pd.read_csv(ROOT/'results/got_s02_s08/tabelas/metricas_por_temporada.csv')
    assert metrics['handshake_lemma_ok'].all()

if __name__ == "__main__":
    test_seasons_are_s02_s08()
    test_outputs_exist()
    test_notebook_structure()
    test_handshake()
    print("TESTES_INTEGRIDADE_OK")
