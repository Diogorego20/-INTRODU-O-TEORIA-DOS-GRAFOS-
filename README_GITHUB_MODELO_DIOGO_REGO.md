# Introdução à Teoria dos Grafos — análise temporal integrada

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Jupyter](https://img.shields.io/badge/Jupyter%20%2F%20Colab-F37626?logo=jupyter&logoColor=white)](https://colab.research.google.com/)
[![Network analysis](https://img.shields.io/badge/Network%20Analysis-python--igraph%20%7C%20Leiden-2E8B57)](https://github.com/igraph/python-igraph)
[![Reproducible](https://img.shields.io/badge/Pipeline-Reproducible-6A5ACD)](https://snakemake.github.io/)

> Projeto acadêmico desenvolvido na disciplina **Introdução à Teoria dos Grafos**.

## Identificação acadêmica

| Campo | Informação |
|---|---|
| **Autor** | Diogo da Silva Rego |
| **Matrícula** | 20240045381 |
| **Curso** | Estatística — DCE |
| **Instituição** | Centro de Ciências Exatas e da Natureza — CCEN/UFPB |
| **Professora** | Ana Flávia |

## Sobre o projeto

Este repositório organiza uma análise integrada de redes temporais, grafos ponderados, centralidades, comunidades e visualização de dados. O projeto reúne três frentes trabalhadas nas atividades da disciplina:

1. **Redes de personagens de Game of Thrones**, analisadas por temporada;
2. **Dados temporais de terremotos**, representados por eventos e células geográficas;
3. **Rede temporal CollegeMsg**, reproduzida a partir do notebook fornecido na atividade.

A implementação foi estruturada com foco em **clareza metodológica, rastreabilidade dos dados, reprodução no Google Colab e comparação temporal válida**.

## Escopo dos dados

Os arquivos de *Game of Thrones* disponibilizados para esta entrega correspondem às temporadas **S2, S3, S4, S5, S6, S7 e S8**.

A temporada 1 não foi incluída porque não foi fornecida nos arquivos recebidos. Também foram comparados os arquivos `got-s2-edges.csv` e `got-s2-edges(1).csv`; a auditoria confirmou que ambos são idênticos, portanto somente um exemplar foi utilizado na análise.

## Principais resultados

### Game of Thrones — temporadas S2–S8

A análise produziu:

- rede agregada com **369 personagens**;
- **2.346 arestas** na união das temporadas;
- **40.640 unidades de força ponderada**;
- **29 personagens presentes nas sete temporadas**;
- **7 comunidades** na rede agregada, detectadas pelo algoritmo Leiden;
- métricas de grau, força ponderada, betweenness, closeness, eigenvector centrality e PageRank;
- comparação de densidade, arestas, centralidades, persistência e comunidades entre temporadas;
- grafos exportados em **GEXF, GraphML e edgelist**;
- figuras estáticas em **PNG e PDF**;
- visualização interativa em **HTML**.

### Terremotos

Foi selecionado o intervalo consecutivo de cinco dias com maior número de eventos. O intervalo identificado foi de **25/09/2026 a 29/09/2026**, com **102 terremotos**.

Foram construídos dois modelos:

- eventos sísmicos como nós conectados pela ordem temporal;
- células geográficas como nós conectados por transições temporais.

Também foram gerados mapas-múndi, centralidades por dia, medidas agregadas e visualização HTML animada.

> Este modelo possui finalidade acadêmica e exploratória. Não representa previsão sísmica nem inferência causal geofísica.

### CollegeMsg

O notebook original `college_msg.ipynb` foi preservado. A URL indicada no arquivo consulta o dataset `email-Eu-core-temporal.txt.gz`, disponibilizado pelo Stanford SNAP.

A análise temporal foi organizada em janelas consecutivas de sete dias e produziu:

- **332.334 interações**;
- **986 nós únicos**;
- **115 janelas temporais**;
- métricas de grau, betweenness, closeness, eigenvector centrality e PageRank;
- evolução temporal da estrutura da rede.

## Decisões metodológicas

### Peso da interação e custo do caminho

O campo original `Weight` foi interpretado como **força ou frequência da interação** e armazenado como `weight_strength`.

Para caminhos mínimos e métricas baseadas em distância, foi criado um custo separado:

```text
cost = 1 / weight_strength
```

Essa separação evita interpretar simultaneamente um peso alto como uma relação forte e como uma distância longa.

### Comunidades

As comunidades foram detectadas com `leidenalg`, utilizando o objetivo `RBConfigurationVertexPartition`. Foram testadas diferentes combinações de:

- resolução;
- seed;
- número de comunidades;
- qualidade da partição;
- modularidade ponderada.

Os rótulos numéricos das comunidades não são comparados diretamente entre temporadas. A comparação considera a composição dos grupos, a qualidade e a estabilidade das partições.

### Layout temporal

O layout dos personagens foi calculado uma única vez sobre a rede agregada S2–S8. As mesmas coordenadas foram reutilizadas nas temporadas individuais.

Isso permite comparar visualmente os snapshots sem confundir uma mudança artificial de layout com uma mudança real na rede.

## Tecnologias utilizadas

- [Python](https://www.python.org/)
- [pandas](https://pandas.pydata.org/)
- [NumPy](https://numpy.org/)
- [Matplotlib](https://matplotlib.org/)
- [Seaborn](https://seaborn.pydata.org/)
- [NetworkX](https://github.com/networkx/networkx)
- [python-igraph](https://github.com/igraph/python-igraph)
- [leidenalg](https://github.com/vtraag/leidenalg)
- [Plotly](https://plotly.com/python/)
- [GeoPandas](https://geopandas.org/)
- [Snakemake](https://snakemake.github.io/)
- [Google Colab](https://colab.research.google.com/)

## Estrutura do repositório

```text
.
├── README.md
├── INDICE_RESULTADOS.md
├── Snakefile
├── manifesto.json
├── requirements.txt
│
├── config/
│   └── config.yaml
│
├── data/
│   └── raw/
│       ├── got-s2-edges.csv
│       ├── got-s3-edges.csv
│       ├── got-s4-edges.csv
│       ├── got-s5-edges.csv
│       ├── got-s6-edges.csv
│       ├── got-s7-edges.csv
│       ├── got-s8-edges.csv
│       ├── terremotos.csv
│       └── college_msg.ipynb
│
├── notebooks/
│   └── analise_grafo_temporal_got_colab.ipynb
│
├── scripts/
│   ├── got_temporal_modern.py
│   ├── earthquakes_temporal_modern.py
│   ├── earthquake_got_temporal_analysis.py
│   ├── college_msg_temporal.py
│   └── run_pipeline.py
│
├── results/
│   ├── got_s02_s08/
│   ├── terremotos/
│   └── college_msg/
│
├── docs/
│   ├── decisoes_metodologicas.md
│   └── analise_repositorios_github.md
│
└── tests/
    └── test_integridade.py
```

## Como executar

### Google Colab

1. Abra o notebook [`notebooks/analise_grafo_temporal_got_colab.ipynb`](notebooks/analise_grafo_temporal_got_colab.ipynb).
2. Execute a célula de instalação das dependências.
3. Faça upload dos arquivos presentes em `data/raw/`.
4. Execute as células na ordem apresentada.
5. Consulte as tabelas e figuras produzidas em `/content/resultados_atividade_integrada/`.

### Execução local

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Execute o pipeline completo:

```bash
python scripts/run_pipeline.py
```

Execute somente a análise de Game of Thrones:

```bash
python scripts/got_temporal_modern.py \
  --input-dir data/raw \
  --output-dir results/got_s02_s08 \
  --duplicate-s2 'data/raw/got-s2-edges(1).csv'
```

Execute somente a análise de terremotos:

```bash
python scripts/earthquakes_temporal_modern.py \
  --earthquakes data/raw/terremotos.csv \
  --output-dir results/terremotos
```

Execute somente a análise CollegeMsg:

```bash
python scripts/college_msg_temporal.py \
  --output-dir results/college_msg \
  --window-days 7
```

### Snakemake

Verifique o pipeline sem executar:

```bash
snakemake -n --cores 1
```

Execute o workflow:

```bash
snakemake --cores 1
```

Gere o diagrama das etapas:

```bash
snakemake --dag | dot -Tsvg > results/workflow_dag.svg
```

## Resultados visuais

Os principais resultados estão disponíveis no [índice navegável](INDICE_RESULTADOS.md).

Arquivos importantes:

- [Grafo agregado S2–S8](results/got_s02_s08/figuras/got_uniao_s02_s08_comunidades.png);
- [Heatmap das centralidades](results/got_s02_s08/figuras/heatmap_centralidades_top15.png);
- [Evolução das métricas GOT](results/got_s02_s08/figuras/evolucao_temporal_metricas.png);
- [Mapa-múndi dos terremotos](results/terremotos/mapa_mundi_intervalo_cinco_dias.png);
- [Evolução temporal CollegeMsg](results/college_msg/figuras/college_msg_evolucao_rede.png);
- [Grafo GOT interativo](results/got_s02_s08/interativo/got_temporal_s02_s08_interativo.html).

## Limitações

- Uma rede por temporada é um snapshot, não um modelo temporal completo com caminhos tempo-respeitantes.
- As comunidades dependem do algoritmo, dos pesos, das seeds e da resolução escolhida.
- A posição em um layout não representa diretamente uma medida de centralidade.
- O modelo de terremotos é exploratório e não substitui um modelo geofísico.
- A qualidade da rede depende da definição original de interação e dos arquivos disponibilizados.
- As bibliotecas `pathpyG`, Gephi, Sigma.js e NetworKit foram avaliadas como extensões, mas não foram tornadas obrigatórias para manter o fluxo principal confiável no Google Colab.

## Referências

- [python-igraph](https://github.com/igraph/python-igraph)
- [leidenalg](https://github.com/vtraag/leidenalg)
- [NetworkX](https://github.com/networkx/networkx)
- [Snakemake](https://github.com/snakemake/snakemake)
- [pathpyG](https://github.com/pathpy/pathpyG)
- [Gephi](https://github.com/gephi/gephi)
- [Sigma.js](https://github.com/jacomyal/sigma.js)
- [NetworKit](https://github.com/networkit/networkit)
- [Stanford SNAP — temporal email network](https://snap.stanford.edu/data/email-Eu-core-temporal.html)

A análise comparativa das tecnologias está documentada em [`docs/analise_repositorios_github.md`](docs/analise_repositorios_github.md).

## Autoria

**Diogo da Silva Rego**  
Matrícula: **20240045381**  
Estatística — CCEN/UFPB

> Projeto acadêmico desenvolvido para a disciplina Introdução à Teoria dos Grafos.
