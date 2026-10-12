# Introdução à Teoria dos Grafos — análise temporal integrada

**Autor:** Diogo da Silva Rego  
**Matrícula:** 20240045381  
**Professora:** Ana Flávia  
**Curso:** Estatística — DCE/CCEN/UFPB  

## Objetivo

Esta entrega reúne, em um pipeline reprodutível, as atividades de mapas e grafos trabalhadas na disciplina: **redes temporais de terremotos**, o estudo do arquivo `college_msg.ipynb` e a evolução das redes ponderadas de personagens de *Game of Thrones*.

A versão atual foi revisada com base em repositórios oficiais e práticas modernas de análise de redes. O resultado principal utiliza `python-igraph` para construção e métricas, `leidenalg` para comunidades e análise de sensibilidade, NetworkX para validações e Snakemake para organizar a reprodução.

## Escopo correto dos dados

Os arquivos de Game of Thrones recebidos nesta entrega correspondem às temporadas **S2, S3, S4, S5, S6, S7 e S8**. Não foi inventada uma temporada S1. O arquivo `got-s2-edges(1).csv` também foi recebido e auditado: ele é byte a byte idêntico a `got-s2-edges.csv`; por isso, somente um exemplar foi utilizado.

## O que foi produzido

### Game of Thrones — S2–S8

- auditoria de colunas, nulos, duplicidades, loops, pesos e hashes SHA-256;
- limpeza sem modificar os CSVs originais;
- agregação de pares A–B e B–A como uma única relação não direcionada;
- `weight_strength` para força/frequência de interação;
- `cost = 1 / weight_strength` para caminhos ponderados, evitando confundir força com custo;
- grau, força ponderada, betweenness, closeness, eigenvector centrality e PageRank;
- centralidade combinada com normalização min–max;
- comunidades Leiden RBConfiguration com três seeds e três resoluções;
- comparação de personagens, arestas, densidade, comunidades e centralidades entre temporadas;
- layout global fixo no agregado S2–S8, reutilizado em todos os snapshots;
- exportação de cada temporada e do agregado em GEXF, GraphML e edgelist;
- figuras PNG/PDF, heatmap, evolução temporal e HTML interativo com slider S2–S8.

### Terremotos

- seleção do intervalo consecutivo de cinco dias com maior número de eventos;
- dois modelos temporais: eventos como nós e células geográficas como nós;
- centralidades por dia e medidas agregadas;
- mapas-múndi estáticos e HTML animado;
- registro explícito de que o modelo é analítico e não uma previsão causal/geofísica.

### CollegeMsg

O notebook recebido foi preservado como `college_msg.ipynb`. A URL indicada nele é `email-Eu-core-temporal.txt.gz`, do Stanford SNAP; portanto, essa fonte é registrada no resultado para manter rastreabilidade. O código constrói janelas consecutivas de sete dias, agrega interações em `weight` e calcula centralidades temporais, densidade e evolução da rede.

## Resultados resumidos

A análise GOT S2–S8 produziu uma rede agregada com **369 personagens**, **2.346 arestas** e **40.640 unidades de força ponderada**. Há **29 personagens presentes em todas as sete temporadas**. A partição Leiden do agregado encontrou **7 comunidades**, com modularidade ponderada registrada no resumo JSON.

O CollegeMsg foi processado em **115 janelas de sete dias**, com **332.334 interações** e **986 nós únicos**.

## Como reproduzir

O [índice navegável dos resultados](INDICE_RESULTADOS.md) reúne os principais CSVs, figuras, grafos e HTMLs.

### Google Colab

Abra `notebooks/analise_grafo_temporal_got_colab.ipynb`, instale as dependências, faça upload da pasta `data/raw` e execute as células em ordem. O notebook registra as versões efetivamente instaladas.

### Execução local

```bash
python -m pip install -r requirements.txt
python scripts/run_pipeline.py
```

Ou execute por etapas:

```bash
python scripts/got_temporal_modern.py \
  --input-dir data/raw \
  --output-dir results/got_s02_s08 \
  --duplicate-s2 'data/raw/got-s2-edges(1).csv'

python scripts/earthquakes_temporal_modern.py \
  --earthquakes data/raw/terremotos.csv \
  --output-dir results/terremotos

python scripts/college_msg_temporal.py \
  --output-dir results/college_msg \
  --window-days 7
```

Para visualizar o pipeline:

```bash
snakemake -n
snakemake --cores 1
snakemake --dag | dot -Tsvg > results/workflow_dag.svg
```

## Estrutura

```text
.
├── README.md
├── Snakefile
├── config/config.yaml
├── requirements.txt
├── data/raw/                       # CSVs originais e notebooks recebidos
├── scripts/                       # análise GOT, terremotos, CollegeMsg e pipeline
├── notebooks/                     # notebook Colab integrado
├── results/
│   ├── got_s02_s08/               # tabelas, figuras, GEXF, GraphML e HTML
│   ├── terremotos/                # mapas, tabelas e centralidades
│   └── college_msg/               # janelas e centralidades temporais
├── docs/
│   ├── analise_repositorios_github.md
│   └── decisoes_metodologicas.md
└── tests/
```

## Cuidados de interpretação

- Uma rede por temporada é um **snapshot**; ela não é automaticamente uma rede temporal com caminhos tempo-respeitantes.
- Rótulos numéricos de comunidades não têm significado permanente; a comparação usa composição, qualidade, estabilidade e sobreposição.
- O layout fixo permite comparação visual, mas posição no plano não é uma medida de centralidade.
- `Weight` foi interpretado como força/frequência; `cost` foi derivado separadamente para caminhos.
- Os resultados dependem dos dados fornecidos, da definição de interação, da agregação e dos parâmetros registrados.
- `pathpyG`, Sigma.js, Gephi e NetworKit foram avaliados como extensões; não foram adicionados como dependências obrigatórias porque aumentariam o risco de instalação sem melhorar comprovadamente o resultado principal no Colab.

## Referências tecnológicas

A decisão técnica foi fundamentada nos repositórios oficiais de [python-igraph](https://github.com/igraph/python-igraph), [leidenalg](https://github.com/vtraag/leidenalg), [NetworkX](https://github.com/networkx/networkx), [Snakemake](https://github.com/snakemake/snakemake), [pathpyG](https://github.com/pathpy/pathpyG), [Gephi](https://github.com/gephi/gephi), [Sigma.js](https://github.com/jacomyal/sigma.js) e [NetworKit](https://github.com/networkit/networkit). A análise comparativa está em [`docs/analise_repositorios_github.md`](docs/analise_repositorios_github.md).

> **Crédito:** Autor: Diogo Rego. Todas as figuras da entrega registram o autor e a interpretação das codificações visuais.
