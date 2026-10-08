# Introdução à Teoria dos Grafos

## Grafos temporais, centralidades e análise de redes

![Status](https://img.shields.io/badge/status-concluído-2ea44f?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-análise_de_grafos-0B5A8F?style=flat-square)
![Google Colab](https://img.shields.io/badge/Google_Colab-reprodução-F9AB00?style=flat-square&logo=googlecolab&logoColor=white)

> Projeto acadêmico desenvolvido para a disciplina **Introdução à Teoria dos Grafos**, integrando redes temporais de terremotos e grafos ponderados de interação entre personagens.

## Identificação acadêmica

| Campo | Informação |
|---|---|
| **Autor** | Diogo da Silva Rego |
| **Matrícula** | 20240045381 |
| **Curso** | Estatística — DCE |
| **Centro** | Centro de Ciências Exatas e da Natureza — CCEN/UFPB |
| **Professora** | Ana Flávia |

## Sobre o projeto

O trabalho aplica conceitos de teoria dos grafos a dois conjuntos de dados:

1. **Terremotos:** construção de grafos temporais a partir da ordem dos eventos e da localização geográfica.
2. **Temporadas 1–8:** análise de redes ponderadas de interação entre personagens, comparação entre temporadas e união das redes.

O processamento é reproduzível no Google Colab, com tabelas CSV, mapas estáticos, mapas HTML interativos e um resumo JSON dos resultados.

## Objetivos

- Selecionar o intervalo consecutivo de cinco dias com maior concentração de terremotos.
- Construir um grafo em que cada terremoto é um nó e eventos consecutivos são conectados.
- Construir um modelo espacial usando células geográficas de 10° × 10°.
- Calcular grau, força ponderada, betweenness, closeness, eigenvector centrality e PageRank.
- Agregar centralidades por dia, considerando recorrência e cobertura temporal.
- Construir os grafos ponderados das temporadas 1 a 8.
- Identificar personagens centrais, exclusivos e compartilhados.
- Criar uma união ponderada das oito temporadas.
- Representar redes grandes com mapas estáticos limpos e versões HTML exploráveis.

## Resultados principais

### Terremotos

O arquivo possui **533 registros distribuídos em 31 dias**. O intervalo consecutivo com maior número de eventos foi de **25 a 29 de setembro de 2026**, com **102 terremotos**:

| Dia | Eventos |
|---|---:|
| 2026-09-25 | 18 |
| 2026-09-26 | 29 |
| 2026-09-27 | 13 |
| 2026-09-28 | 25 |
| 2026-09-29 | 17 |
| **Total** | **102** |

Foram gerados dois modelos:

- **Grafo de eventos:** 102 nós e 101 arestas.
- **Grafo espacial por células:** 39 nós e 65 arestas.

A célula com maior centralidade temporal combinada foi `lat_-30_lon_160`, ativa nos cinco dias selecionados.

### Temporadas 1–8

A união ponderada das redes apresentou:

- **406 personagens**;
- **2.637 arestas únicas**;
- **47.168 interações ponderadas**;
- **403 personagens na componente principal**;
- 3 personagens desconectados, identificados no painel do grafo agregado.

Entre as temporadas 1 e 2 foram identificados 61 personagens somente na S1, 64 somente na S2 e 65 presentes nas duas. Os maiores valores de centralidade combinada na união foram observados em **Tyrion, Jon, Sansa, Daenerys, Arya, Cersei e Jaime**.

## Metodologia resumida

### Terremotos

O primeiro modelo ordena os eventos por tempo e conecta pares consecutivos. O segundo associa cada evento a uma célula geográfica de 10° × 10° e representa transições entre células. As centralidades são calculadas por dia e agregadas com média, máximo, soma, dias ativos e cobertura temporal.

### Temporadas

Cada arquivo `got-sN-edges.csv` é interpretado como uma rede não direcionada e ponderada: nós representam personagens, arestas representam interações e `Weight` representa a intensidade da interação. Na união, pesos de arestas repetidas são somados.

## Legendas e decisões de visualização

Todas as figuras estáticas e HTML incluem o crédito **Autor: Diogo Rego** e uma legenda explicativa. A legenda informa o significado de cores, tamanhos, pesos e centralidades. Nos HTMLs, o `hover` permite consultar todos os nomes e métricas.

Como as redes são grandes, os mapas estáticos rotulam somente os nós com maior força de interação. A união das temporadas apresenta a componente principal e os personagens desconectados em áreas separadas para evitar distorções.

## Estrutura do projeto

```text
.
├── README_atividade_temporal.md
├── introducao/
│   └── README.md
├── analise_temporal_terremotos_got_colab.ipynb
├── earthquake_got_temporal_analysis.py
├── requirements.txt
├── manifesto.json
├── dados_entrada/
│   ├── terremotos.csv
│   ├── terremotos_original.ipynb
│   └── got-s1-edges.csv ... got-s8-edges.csv
└── resultados/
    ├── resumo_analise_temporal.json
    ├── terremotos/
    └── got_temporadas/
```

## Como reproduzir no Google Colab

1. Abra [`analise_temporal_terremotos_got_colab.ipynb`](../analise_temporal_terremotos_got_colab.ipynb).
2. Execute a célula de instalação.
3. Envie os arquivos existentes em [`dados_entrada/`](../dados_entrada/).
4. Execute as células em ordem.
5. Consulte os resultados em `/content/resultados_atividade_temporal`.

O código principal está em [`earthquake_got_temporal_analysis.py`](../earthquake_got_temporal_analysis.py).

## Visualizações principais

- [Painel mundial dos cinco dias de terremotos](../resultados/terremotos/mapa_mundi_intervalo_cinco_dias.png)
- [Mapa-múndi interativo dos terremotos](../resultados/terremotos/mapa_mundi_terremotos_interativo.html)
- [Evolução das centralidades temporais](../resultados/terremotos/evolucao_centralidades_temporais.png)
- [Grafo agregado das temporadas 1–8](../resultados/got_temporadas/got_grafo_uniao_temporadas.png)
- [União interativa das temporadas](../resultados/got_temporadas/got_uniao_temporadas_interativo.html)
- [Evolução das redes por temporada](../resultados/got_temporadas/got_evolucao_temporadas.png)

## Tabelas de análise

- [Centralidades temporais por eventos](../resultados/terremotos/centralidades_temporais_eventos.csv)
- [Centralidades temporais por células](../resultados/terremotos/centralidades_temporais_celulas.csv)
- [Medidas temporais agregadas](../resultados/terremotos/medidas_temporais_agregadas_celulas.csv)
- [Centralidades por temporada](../resultados/got_temporadas/got_centralidades_por_temporada.csv)
- [Centralidades da união](../resultados/got_temporadas/got_centralidades_uniao_temporadas.csv)
- [Comparação entre temporadas 1 e 2](../resultados/got_temporadas/got_comparacao_temporadas_1_2.csv)
- [Membresia temporal dos personagens](../resultados/got_temporadas/got_membresia_temporal_personagens.csv)

## Limitações

A discretização espacial de 10° × 10° é uma escolha analítica e não representa fronteiras administrativas, placas tectônicas ou áreas de risco. A rede de terremotos descreve relações temporais e espaciais entre registros, não causalidade nem previsão sísmica. A interpretação das redes das temporadas depende do significado do campo `Weight` nos dados fornecidos.

## Referências

- GOLDBARG, Marco; GOLDBARG, Elizabeth. *Grafos: conceitos, algoritmos e aplicações*. Elsevier, 2012.
- [NetworkX — documentação oficial](https://networkx.org/documentation/stable/)
- [Plotly — documentação de gráficos interativos](https://plotly.com/python/)
- [USGS — Earthquake Hazards Program](https://www.usgs.gov/programs/earthquake-hazards/earthquakes)
- [USGS — Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/search/)

## Uso acadêmico

Este material foi produzido para fins acadêmicos na disciplina de Introdução à Teoria dos Grafos. Os arquivos de entrada e resultados devem ser utilizados respeitando a origem e as condições de uso dos dados fornecidos.
