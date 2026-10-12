# Síntese final: práticas e tecnologias modernas para a entrega acadêmica de Diogo Rego

## 1. Resposta direta

A combinação mais adequada para a entrega é:

1. **`python-igraph` como motor principal de grafos e métricas**, pela implementação em C, construção em lote, suporte a pesos, caminhos, centralidades e várias famílias de comunidades. Isso é mais justificável que escolher uma biblioteca apenas por popularidade: o projeto documenta explicitamente a interface para redes grandes, algoritmos estruturais e integração com pandas, SciPy, NetworkX e visualização. [1][2]
2. **`leidenalg` como componente principal de detecção e comparação de comunidades**, porque acrescenta ao igraph objetivos configuráveis, resolução, sementes, iterações, multiplexação e slices temporais. A escolha permite testar estabilidade em vez de apresentar uma única partição como verdade definitiva. [3][4]
3. **`Snakemake` como camada de reprodutibilidade e orquestração**, não como biblioteca de grafos. Ele organiza ingestão, limpeza, construção de snapshots, métricas, figuras e relatórios em um DAG parametrizado, com ambientes, logs, recursos e testes. [5][6]
4. **`NetworkX` como baseline de validação e alternativa didática**, especialmente para verificar amostras pequenas e algoritmos clássicos. Ele é muito expressivo, mas sua camada temporal é especializada, e a versão atual do checkout consultado impõe requisitos de Python que precisam ser conferidos no Colab. [7][8]
5. **`pathpyG` somente como extensão metodológica de maior risco**, quando a pergunta realmente exigir caminhos tempo-respeitantes, eventos e memória de ordem superior. É o repositório mais diretamente orientado a temporalidade/higher-order, mas está em estado alpha, tem dependências PyTorch/PyG/CUDA variáveis e não deve ser a única base da entrega. [9][10]
6. **Gephi para exploração visual temporal em desktop** e **Sigma.js para um painel interativo web opcional**. Gephi é forte em Timeline, GEXF, filtros, layouts e exportação, mas não é notebook-native; Sigma.js é apropriado para uma interface no navegador, porém exige WebGL 2 e uma ponte JavaScript que terá de ser construída no Colab. [11][12]

Em termos práticos, a recomendação é entregar um **pipeline reprodutível no Google Colab**, com resultados analíticos gerados por igraph/leidenalg, validações amostrais em NetworkX, e figuras estáticas com coordenadas estáveis. A visualização interativa deve ser um complemento: Gephi em uma máquina desktop ou Sigma.js em uma página HTML versionada. O componente temporal nativo/higher-order de pathpyG deve ficar como experimento adicional, não como dependência obrigatória do resultado principal.

## 2. Escopo dos dados e pergunta metodológica

Os dados fornecidos para o estudo de *Game of Thrones* cobrem **as temporadas 2 a 8 (S2–S8)**. A comparação longitudinal deve, portanto, produzir no mínimo sete redes comparáveis — uma por temporada — e uma rede agregada S2–S8 para referência. Não se deve misturar a ausência de uma personagem em uma temporada com peso zero sem explicar se isso significa “não apareceu”, “não foi observada” ou “não pertence ao universo amostrado”.

Para o estudo de terremotos, a unidade temporal precisa ser definida pelo domínio: eventos, estações, regiões, células espaciais ou relações entre elas. A decisão pode usar dias, semanas, episódios de atividade, janelas após um sismo ou snapshots de tamanho fixo. A biblioteca não pode escolher por si só o que é uma interação cientificamente válida; a janela, a direção, o peso e o tratamento de dados ausentes fazem parte do método de Diogo Rego.

### Esquema mínimo recomendado

Manter os dados tabulares originais, além dos grafos derivados:

- **Nós:** `node_id` estável, `label`, `node_type`, latitude/longitude quando aplicável, atributos de domínio e intervalos de presença.
- **Interações/eventos:** `source`, `target`, `season` ou `time_start`/`time_end`, `episode` ou identificador do evento, `relation_type`, `weight_raw` e uma indicação de qualidade/observação.
- **Arestas agregadas:** `weight_strength` para frequência/intensidade e, quando necessário, `cost` para caminhos mínimos.
- **Metadados:** versão da biblioteca, regra de agregação, direção, unidade temporal, filtros, seed, parâmetros de comunidade e hardware.

Para *Game of Thrones*, use personagens como nós e cenas, episódios ou coocorrências como eventos. Uma rede não direcionada é natural para coaparição; uma rede direcionada só é adequada se houver emissor e receptor definidos. Interações repetidas devem ser agregadas por par e temporada/episódio quando a métrica não tiver semântica bem definida para multiarestas. O tutorial de igraph documenta pesos e construção em lote, enquanto NetworKit alerta que multiarestas não são suportadas de maneira consistente. [2][13]

## 3. Comparação dos repositórios

| Repositório | Força comprovada | Temporalidade | Comunidades/centralidades | Colab | Decisão para a entrega |
|---|---|---|---|---|---|
| **python-igraph** | Núcleo C vendorizado, construção em lote, redes ponderadas/direcionadas, caminhos, centralidades e I/O | Não documenta um motor temporal nativo; usar snapshots/camadas | Amplo conjunto de centralidades e comunidades, com pesos | **Favorável**, preferindo wheel publicada e versão fixada | **Motor principal** |
| **leidenalg** | Leiden em C++/Python, objetivos, resolução, seeds, multiplex e slices | **Temporal/multiplex por camadas**, com IDs persistentes e acoplamento explícito | Especializado em comunidades; permite análise de sensibilidade | Favorável por `pip`, mas validar igraph e metadados | **Comunidades principais** |
| **NetworkX** | API clara e ampla para Graph/DiGraph/MultiGraph, caminhos, centralidade, comunidades e formatos | Atributos, `cd_index` e matchers time-respecting; não é uma API temporal geral | Muito bom para clássicos e validação | Condicional: conferir Python; extras científicos são opcionais | **Baseline/alternativa** |
| **NetworKit** | Kernels C++ paralelos, grafos ponderados/direcionados, PLM/Leiden e algoritmos dinâmicos | Eventos e algoritmos dinâmicos para alguns problemas, não para todo o pipeline | Forte em escala e paralelismo | Condicional: wheel ou compilação nativa; sem garantia Colab | **Só se a escala exigir** |
| **pathpyG** | `TemporalGraph`, eventos, caminhos temporais, modelos higher-order e DBGNN | **Mais diretamente orientado à temporalidade** | Não substitui a base clássica; foco em ordem superior/aprendizado | Arriscado: alpha, PyTorch/PyG/CUDA | **Extensão experimental** |
| **Gephi** | Timeline, GEXF dinâmico, filtros, layouts, estatísticas e exploração visual | **Muito bom para explorar/exportar** redes por intervalos | PageRank/eigenvector e estatísticas por módulos | Não notebook-native; usar desktop | **Visualização desktop** |
| **Sigma.js** | Renderização WebGL, interação, estados, arestas paralelas/self-loops e exportação de imagens | Não fornece semântica temporal pronta; aplicação controla filtros/estados | É renderer, não motor estatístico | Possível via HTML/JS; exige WebGL 2 | **Painel web opcional** |
| **Snakemake** | DAG de workflow, config, ambientes, logs, recursos, relatórios e testes | Orquestra janelas e temporadas, mas não analisa o grafo | Não calcula métricas | Execução local plausível; não é cluster turnkey no Colab | **Reprodutibilidade** |

A conclusão não é “usar tudo”. Cada componente cobre uma lacuna distinta: igraph calcula, leidenalg particiona, Snakemake organiza, NetworkX confere, pathpyG testa hipóteses temporais/higher-order e Gephi/Sigma.js comunicam resultados. A sobreposição deve ser reduzida para evitar dependências e resultados divergentes sem propósito.

## 4. Diferenças que precisam aparecer no texto acadêmico

### 4.1 Análise temporal não é apenas colocar uma coluna `time`

Há quatro níveis metodológicos diferentes:

1. **Snapshots/camadas:** construir um grafo por temporada, episódio, janela sísmica ou intervalo. É a opção mais transparente e robusta para Colab. Cada snapshot recebe as mesmas regras de nós, arestas e peso; métricas são recalculadas e comparadas.
2. **Atributos temporais em um grafo comum:** guardar timestamps e filtrar arestas/nós segundo uma janela. Isso preserva a origem dos eventos, mas não cria automaticamente caminhos ou centralidades temporais.
3. **Eventos e dinâmica incremental:** representar adição/remoção/alteração de arestas e atualizar algoritmos compatíveis. NetworKit documenta `GraphEvent`, `TIME_STEP`, streams DGS e exemplos de componentes, distância, betweenness e harmonic closeness dinâmicos; os exemplos não demonstram PageRank ou comunidades incrementais universais. [13][14]
4. **Semântica tempo-respeitante/higher-order:** respeitar ordem, delta máximo entre eventos, chegada/partida e memória de sequência. pathpyG implementa `TemporalGraph`, `temporal_shortest_paths`, levantamento de eventos e modelos de ordem superior; por isso é a melhor extensão quando a hipótese científica depende de sequência, não apenas de mudança entre snapshots. [9][15]

O NetworkX não deve ser descrito como um framework geral de grafos temporais. O material oficial consultado expõe `cd_index` e matchers de isomorfismo que respeitam tempo, com restrições próprias; o restante exige filtragem, snapshots e lógica implementada no estudo. `cd_index`, por exemplo, requer grafo simples dirigido e atributos temporais nos nós, enquanto os matchers usam restrições temporais nas interações. [16][17]

`leidenalg` ocupa outro nível: sua temporalidade é principalmente uma **partição de slices/camadas com acoplamento**. `find_partition_temporal` identifica vértices persistentes por atributo e liga slices consecutivos; `find_partition_multiplex` pressupõe o mesmo conjunto de vértices em todas as camadas. Isso é adequado para personagens que persistem entre temporadas ou para estações/regiões com IDs estáveis, mas não para um conjunto de eventos que nunca reaparece como o mesmo vértice. [3][4]

### 4.2 Centralidades, caminhos e a semântica de `weight`

As métricas respondem a perguntas distintas:

- **Grau/força ponderada:** quem tem muitas relações ou maior soma de intensidade?
- **Betweenness:** quem intermedeia muitos caminhos mínimos?
- **Closeness/harmonic closeness:** quem alcança os demais com menor distância, geralmente dentro de componentes apropriados?
- **PageRank/eigenvector:** quem está ligado a nós importantes, sob uma direção e normalização escolhidas?
- **Caminho mínimo:** qual é o custo mínimo sob uma função de distância declarada?

O mesmo atributo `weight` não pode ser interpretado automaticamente como “força” e “custo”. Se, em *Game of Thrones*, `weight` for número de cenas ou frequência de interação, um valor maior pode significar laço mais forte para força/grau e comunidades; no caminho mínimo, porém, Dijkstra e funções equivalentes tratam o valor como custo a minimizar. A documentação de NetworkX confirma que `shortest_path` pode receber o nome do atributo ou uma função, e que arestas sem peso recebem 1. [7] Portanto, manter `weight_strength` e derivar explicitamente `cost` — por exemplo, uma transformação inversa justificada — é mais seguro que reutilizar o mesmo campo sem documentação.

Para terremotos, magnitude, energia, correlação, número de coocorrências e confiança não são intercambiáveis. A transformação deve ser defendida pela pergunta científica. Se um peso maior representar conexão mais forte, ele pode ser usado em força e em objetivos de comunidade que aceitem pesos positivos; para caminhos, deve-se definir o que “menor” significa antes de calcular.

O pipeline deve calcular as métricas por snapshot, registrar custo/tempo e lidar com componentes desconectados. Em redes pequenas, calcule todas as métricas; em redes maiores, comece por grau e PageRank, use amostragem de betweenness quando adequada e evite all-pairs sem medir. NetworkX documenta custos que chegam a `O(V^3)` em Floyd–Warshall, enquanto igraph e NetworKit oferecem implementações eficientes, mas nenhuma biblioteca elimina o custo da pergunta. [18][1]

### 4.3 Comunidades: rótulo, objetivo e estabilidade

Uma comunidade não é um fato observável único. A partição depende de objetivo, resolução, pesos, direção, seed e tratamento da temporalidade.

- **Leidenalg** é a escolha principal para a entrega porque permite comparar Modularity, RBConfiguration, RBER, CPM, Significance e Surprise, além de resolução, `n_iterations`, seed, pesos e acoplamento temporal/multiplex. Isso permite uma análise de sensibilidade reportável. [3][4]
- **igraph** fornece métodos como Leiden, multilevel, Infomap, label propagation e walktrap; é uma boa base para um resultado operacional simples e para comparação com Leidenalg. [2]
- **NetworkX** oferece Girvan–Newman, greedy modularity, k-clique, label propagation e Louvain; Leiden não é uma implementação própria garantida no núcleo, mas aparece via backend compatível na release consultada. [19]
- **NetworKit** oferece PLM/Louvain paralelo e ParallelLeiden, útil quando o tamanho justificar threads e memória adicionais, mas sua versão/empacotamento consultados têm inconsistências que prejudicam uma entrega Colab sem teste. [13]
- **pathpyG** deve ser usado para perguntar se a sequência de interações exige ordem superior, não para substituir uma comunidade estática sem hipótese de memória. [15]

A comparação entre S2 e S8 não deve igualar o número do rótulo de comunidade. Rótulos podem ser renumerados a cada execução ou temporada; comparar composição de membros, sobreposição (por exemplo, Jaccard/ARI/NMI quando apropriado), qualidade e estabilidade entre seeds. Em `leidenalg`, variar `resolution_parameter`, `layer_weights` e `interslice_weight`; salvar as partições, não apenas a tabela final. O próprio projeto não promete uma solução ótima global para redes gerais, portanto uma partição única não deve ser tratada como verdade definitiva. [4]

### 4.4 Layouts estáveis não são uma métrica temporal

Um layout estável responde à pergunta visual “a posição de uma entidade pode ser comparada entre períodos?”. Ele não prova que a entidade manteve centralidade ou comunidade.

A prática recomendada é:

1. construir um grafo agregado S2–S8 ou um grafo de referência;
2. calcular um layout uma única vez, com seed fixada;
3. reutilizar `x`/`y` nos snapshots, acrescentando ou removendo nós de modo documentado;
4. manter uma legenda que diferencie mudança de posição visual, tamanho, cor e arestas;
5. exportar os coordenados e parâmetros junto com os dados.

Para terremotos, posições geográficas devem prevalecer quando a pergunta for espacial; um force-directed layout pode ser mostrado como visão complementar. Para *Game of Thrones*, um layout global evita que cada temporada reorganize todos os personagens e torne a evolução visual enganosa. Não é necessário alegar que Gephi ou Sigma.js “resolvem” estabilidade temporal: os repositórios fornecem layouts ou posições, mas a política de ancoragem e a comparação entre snapshots são escolhas da análise. Sigma.js, por exemplo, espera atributos visuais como `x`, `y`, `size`, `color` e `label`, o que facilita carregar coordenadas já calculadas. [12]

### 4.5 Visualização interativa versus reprodutibilidade

**Gephi** é mais adequado para exploração visual: tem Timeline, importação/exportação GEXF dinâmico, filtros, estatísticas, layouts e ações interativas. O formato GEXF permite preservar pesos e intervalos quando configurado corretamente. A rota segura é gerar e validar GEXF no Colab e abrir a versão fixada do Gephi no desktop; o repositório não oferece um procedimento oficial para executar a interface no Google Colab, e a renderização depende de Java/OpenGL/display. [11][20]

**Sigma.js v4** é mais adequado para uma página web com hover, clique, destaque de comunidades, filtros de temporada e snapshots. Ele usa WebGL 2 e suporta estados, arestas paralelas, self-loops, estilos e exportação de imagem; contudo, não oferece uma timeline semântica nem análise estatística pronta. No Colab, Python deve produzir JSON/CSV e uma página JavaScript versionada deve instanciar Graphology/Sigma. WebGL 2 deve ser verificado no navegador do público; uma imagem estática precisa ser o fallback. [12]

A visualização interativa não substitui uma figura estática reproduzível. A entrega deve incluir PDFs/PNGs com layout, legenda, escala e versão, além do HTML opcional. Um usuário não deve precisar de uma sessão ativa do Colab ou de um estado oculto de Gephi para verificar a conclusão.

## 5. O que é realmente aplicável no Google Colab

### 5.1 Rota recomendada

No início do notebook, verificar e registrar:

```python
import sys
print(sys.version)

# Depois de instalar versões fixadas:
import igraph, leidenalg
print("igraph:", igraph.__version__)
print("leidenalg:", leidenalg.__version__)
```

A rota inicial deve ser CPU e baseada em wheels publicadas:

```bash
pip install -q "python-igraph==VERSAO_FIXADA" "leidenalg==VERSAO_FIXADA" \
  "pandas==VERSAO_FIXADA" "numpy==VERSAO_FIXADA" \
  "snakemake==9.27.0"
```

Os números `VERSAO_FIXADA` devem ser preenchidos após testar uma combinação compatível com o Python efetivo do runtime; não é recomendável copiar `main` ou instalar a versão mais nova sem registrar o resultado. O README de igraph documenta `pip install igraph` e wheels para versões comuns de Python; o pyproject de leidenalg exige igraph compatível, mas os resultados consultados registram divergências entre os requisitos de Python do README e dos metadados. [2][21]

**Aplicável com baixo risco no Colab:**

- leitura e validação de CSV/Parquet;
- agregação por episódio, temporada, janela ou região;
- construção em lote de igraph;
- grau, força, caminhos, PageRank, betweenness amostrada, componentes;
- Leiden/multilevel e análise de sensibilidade;
- tabelas, gráficos estáticos, exportação GraphML/GEXF/JSON/edgelist;
- execução local do Snakefile em pequena escala, depois de validar `snakemake -n`;
- geração de JSON e HTML para uma visualização Sigma.js opcional.

**Aplicável, mas condicional:**

- **NetworkX:** usar se o Python do runtime satisfizer a versão do checkout atual. A documentação consultada informa núcleo instalável por pip e extras `default`, mas o `pyproject.toml` principal declara `>=3.12` e exclusão de `3.14.1`; confirmar antes de escolher a versão. [8]
- **NetworKit:** tentar `pip install networkit` em uma célula limpa; se não houver wheel, a instalação pode exigir C++/OpenMP/CMake/Make ou Ninja. Registrar a versão realmente importada e o número de threads. [13]
- **pathpyG:** começar em CPU, com subset pequeno, e somente depois testar GPU. Os extras atuais combinam PyTorch/PyG/CUDA de forma sensível ao runtime; o projeto está em alpha e não há garantia específica para Colab. [9][10]
- **Gephi:** não usar a interface como etapa essencial no Colab. Gerar GEXF no notebook e abrir no desktop é o fluxo mais confiável.
- **Sigma.js:** viável como artefato web, não como API Python. O notebook precisa produzir/servir o HTML e o navegador precisa de WebGL 2.

### 5.2 O que não deve ser prometido

Não afirmar que:

- NetworkX, igraph ou Leidenalg oferecem automaticamente caminhos/centralidades/comunidades temporais;
- `cd_index` é um algoritmo geral de rede temporal;
- NetworKit atualiza qualquer métrica incremental sem recalcular;
- pathpyG é uma solução madura/estável para produção;
- Gephi executará a interface interativa de forma oficial dentro do Colab;
- GPU ou CUDA do Colab será compatível com o extra `cu129` do pathpyG;
- um layout independente por temporada permite comparar posições;
- uma única execução do Leiden é suficiente para provar a comunidade “real”.

## 6. Pipeline acadêmico recomendado

### Etapa A — preparação e auditoria dos dados

1. Versionar os arquivos brutos ou registrar checksum e origem.
2. Validar IDs, duplicatas, entidades ausentes, timestamps e categorias.
3. Definir previamente o que constitui uma interação em *Game of Thrones* e o que constitui uma relação/evento sísmico.
4. Especificar `weight_strength`, `cost`, direção e política de agregação.
5. Registrar que a análise de *Game of Thrones* é limitada a S2–S8.

### Etapa B — redes de referência

Construir:

- `got_s02`, ..., `got_s08`;
- `got_s02_s08_aggregate`;
- snapshots de terremotos segundo janelas justificadas;
- opcionalmente, um grafo de eventos para pathpyG.

Use IDs externos estáveis. Em *Game of Thrones*, personagens persistentes podem usar `character_id`; para terremotos, estações/regiões devem ter IDs estáveis, enquanto eventos sísmicos individuais podem receber IDs próprios e não devem ser confundidos com entidades persistentes.

### Etapa C — métricas estruturais

Para cada rede/snapshot:

- número de nós, arestas, densidade e componentes;
- grau e força ponderada;
- betweenness e closeness/harmonic closeness com tratamento de desconexão;
- PageRank/eigenvector quando a direção e a pergunta forem compatíveis;
- distribuição de pesos e sensibilidade à agregação;
- custo de execução e memória.

Guardar resultados em tabelas longas com colunas `dataset`, `season`/`window`, `node_id`, `metric`, `value`, `parameters`.

### Etapa D — comunidades

Executar, ao menos, uma configuração principal Leiden e uma análise de sensibilidade:

- objetivo: Modularity ou RBConfiguration para pesos positivos, conforme justificativa;
- `resolution_parameter`: mais de um valor;
- seed: várias seeds;
- `n_iterations`: explicitamente definido;
- temporalidade: `find_partition_temporal` quando IDs persistirem e houver acoplamento justificável; caso contrário, partições independentes por snapshot com comparação de sobreposição;
- salvar composição, qualidade e estabilidade.

Leidenalg documenta restrições importantes: vários objetivos não aceitam pesos negativos; multiplex exige conjunto de vértices comum; slices com objetivos específicos podem exigir `node_sizes`. Esses limites devem aparecer na seção de métodos, não apenas no código. [4]

### Etapa E — tempo e hipótese de ordem superior

O resultado principal deve ser o baseline por snapshots, por ser mais auditável. Se o estudo perguntar se a ordem das interações importa, acrescentar pathpyG:

- escolher `delta` com justificativa de domínio;
- testar `max_order` pequeno;
- comparar ordem 1 contra higher-order;
- usar `temporal_shortest_paths` somente quando chegada e ordem forem cientificamente relevantes;
- medir tempo e memória;
- manter o baseline estático para que o ganho metodológico seja verificável.

`TemporalGraph.to_static_graph(weighted=True)` agrega eventos repetidos por contagem; isso é útil para uma camada de referência, mas não substitui uma decisão sobre pesos físicos ou semântica de interação. [15]

### Etapa F — layouts e visualização

- calcular uma posição global por rede agregada;
- reutilizar coordenadas nos snapshots;
- reservar cor para comunidade e tamanho para força/grau, sem sobrecarregar a figura;
- fazer uma figura estática por temporada selecionada e uma matriz S2–S8;
- exportar GEXF para Gephi;
- opcionalmente publicar HTML Sigma.js com filtros de temporada e destaque de comunidades;
- incluir fallback PNG/SVG e tabela de dados.

### Etapa G — reprodução

O repositório deve conter, no mínimo:

```text
project/
  Snakefile
  config/config.yaml
  data/raw/
  data/processed/
  envs/colab.yml ou requirements.txt
  scripts/
  notebooks/
  results/tables/
  results/figures/
  results/interactive/
  tests/
  README.md
```

O Snakefile deve parametrizar `season: [2,3,4,5,6,7,8]`, gerar cada saída por wildcard e declarar threads/resources. O Snakemake documenta configs, wildcards, logs, ambientes, testes unitários, `--dag` e `--report`; seu DAG deve ser apresentado como documentação do pipeline, não como o grafo científico. [5][6][22]

## 7. Decisão técnica por prioridade

### Prioridade alta — fazer nesta entrega

1. **Adotar igraph + leidenalg como núcleo analítico.** A justificativa é a combinação verificável de desempenho em C, construção em lote, centralidades, caminhos, pesos, comunidades, resolução, seeds e camadas temporais. [2][3]
2. **Implementar snapshots comparáveis para terremotos e S2–S8 de *Game of Thrones*.** O baseline temporal deve ser explícito e auditável; não depender de uma promessa de “temporalidade automática”.
3. **Definir e separar força de conexão e custo de caminho.** Manter `weight_strength` e `cost`; documentar direção, agregação e transformação.
4. **Fixar ambiente e parâmetros no Colab.** Registrar Python, versões efetivas, seed, número de iterações, resolução, janela/delta, threads, hardware e memória.
5. **Usar IDs estáveis e layouts estáveis.** Calcular coordenadas globais, reutilizá-las entre snapshots e guardar os valores.
6. **Executar análise de sensibilidade de comunidades.** Variar seed/resolução e reportar composição, qualidade e estabilidade, em vez de apenas o número de clusters.
7. **Orquestrar o pipeline com Snakemake** se a entrega tiver mais de uma temporada, janela, figura ou ambiente. Incluir dry-run, logs, testes pequenos e `report`/ZIP.
8. **Entregar figuras estáticas reproduzíveis e tabelas**, mesmo que haja uma interface interativa.

### Prioridade média — fazer se houver tempo ou pergunta científica clara

1. **Validar amostras com NetworkX**, comparando grau, caminhos e centralidade em redes pequenas; não misturar sem explicar diferenças de peso, direção ou tolerância.
2. **Usar `find_partition_temporal`/multiplex do leidenalg** quando houver entidades persistentes e hipótese de continuidade entre temporadas/janelas.
3. **Acrescentar pathpyG** para caminhos tempo-respeitantes ou ordem superior, com baseline de snapshots, `delta`/`max_order` fixados e medição de recursos.
4. **Gerar GEXF e explorar no Gephi desktop**, usando Timeline, filtros e exportações para a produção de figuras.
5. **Criar um painel Sigma.js** com filtros S2–S8, estado por comunidade e fallback estático; fixar versões npm e testar WebGL 2.
6. **Testar NetworKit** somente se a rede de terremotos ou a quantidade de snapshots demonstrar gargalo medido; registrar versão/commit e threads.

### Prioridade baixa — não incluir sem evidência de necessidade

1. **Backends GPU ou paralelos de NetworkX/NetworKit** sem benchmark no dataset final; configuração adicional não é benefício automático.
2. **GPU do pathpyG** apenas por ser moderna; usar somente se a hipótese higher-order e o tamanho justificarem, após validar PyTorch/PyG/CUDA.
3. **Executar Gephi dentro do Colab** como parte da entrega principal; display/OpenGL e instalação desktop elevam o risco.
4. **Usar um layout novo por temporada** ou animar mudanças sem coordenadas ancoradas; isso prejudica a comparação visual.
5. **Adicionar múltiplos algoritmos de comunidade sem pergunta ou análise de estabilidade.** Popularidade não é critério metodológico.
6. **Apresentar o DAG do Snakemake como se fosse o grafo de terremotos/personagens.** São objetos diferentes.

## 8. Riscos e controles

- **Incompatibilidade de Python:** verificar `sys.version` antes de instalar; NetworkX principal consultado exige Python `>=3.12` e `!=3.14.1`, igraph documenta linha principal para Python 3.9–3.13, NetworKit exige `>=3.10` e pathpyG `>=3.10`. [8][2][13][9]
- **Dependências que mudam:** fixar versões publicadas, não `main`; salvar `pip freeze` e, idealmente, o commit.
- **Multigrafos:** agregar arestas paralelas quando a métrica exigir uma interpretação única; muitos algoritmos não são bem definidos para multigrafos. [7][13]
- **Memória:** reduzir janelas, comunidades/snapshots ou ordem higher-order; medir antes de ativar GPU/paralelismo.
- **Comparação temporal inválida:** usar mesma regra de extração e peso; guardar IDs e presença; comparar sobreposição de comunidades, não rótulos numéricos.
- **Licenças:** NetworkX, igraph, NetworKit, Sigma.js e Snakemake permitem uso conforme suas licenças; pathpyG é AGPLv3+ e leidenalg GPL-3.0-or-later. Se o notebook for redistribuído como software, revisar obrigações da licença do componente escolhido. [9][3]
- **Reprodutibilidade de algoritmo estocástico:** fixar seed não basta se versão, número de threads ou objetivo mudarem; salvar partições e metadados.

## 9. Conclusão

Para melhorar a entrega acadêmica de Diogo Rego, a prioridade não é empilhar ferramentas populares, e sim separar responsabilidades. O resultado principal deve ser uma análise temporal por snapshots, transparente e comparável, com redes ponderadas corretamente semântizadas para terremotos e para *Game of Thrones* S2–S8. `python-igraph` oferece a base computacional mais equilibrada para o Colab; `leidenalg` dá rigor à comparação de comunidades temporais/multiplex; `Snakemake` torna o pipeline reproduzível; NetworkX serve como verificação; pathpyG entra apenas quando sequência e ordem superior forem hipóteses reais; Gephi e Sigma.js comunicam os resultados, mas não substituem a análise.

A entrega ideal contém: dados e esquema documentados, sete redes de temporada S2–S8 mais um agregado, snapshots sísmicos justificados, métricas com custo, comunidades com seeds/resoluções, layouts estáveis, figuras estáticas, um artefato interativo opcional e um workflow que possa ser executado novamente em um Colab limpo. Assim, a modernidade tecnológica aparece como **melhor controle de hipótese, comparação temporal e reprodução**, e não como uma coleção de dependências difíceis de validar.

## References

[1] python-igraph — README oficial. https://github.com/igraph/python-igraph/blob/main/README.md  
[2] python-igraph — tutorial e API de `Graph`. https://python.igraph.org/en/latest/tutorial.html ; https://python.igraph.org/en/latest/api/igraph.Graph.html  
[3] leidenalg — README oficial. https://raw.githubusercontent.com/vtraag/leidenalg/main/README.rst  
[4] leidenalg — documentação avançada e multiplex/temporal. https://raw.githubusercontent.com/vtraag/leidenalg/main/doc/source/advanced.rst ; https://raw.githubusercontent.com/vtraag/leidenalg/main/doc/source/multiplex.rst ; https://leidenalg.readthedocs.io/en/stable/reference.html  
[5] Snakemake — README oficial. https://github.com/snakemake/snakemake/blob/main/README.md  
[6] Snakemake — deployment, reporting e testing. https://github.com/snakemake/snakemake/blob/main/docs/snakefiles/deployment.rst ; https://github.com/snakemake/snakemake/blob/main/docs/snakefiles/reporting.rst ; https://github.com/snakemake/snakemake/blob/main/docs/snakefiles/testing.rst  
[7] NetworkX — tutorial, classes e caminhos mínimos. https://networkx.org/documentation/stable/tutorial.html ; https://networkx.org/documentation/stable/reference/classes/index.html ; https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html  
[8] NetworkX — instalação e metadados do projeto. https://networkx.org/documentation/stable/install.html ; https://raw.githubusercontent.com/networkx/networkx/main/pyproject.toml  
[9] pathpyG — README e getting started. https://github.com/pathpy/pathpyG ; https://raw.githubusercontent.com/pathpy/pathpyG/main/docs/getting_started.md  
[10] pathpyG — releases e configuração do projeto. https://github.com/pathpy/pathpyG/releases ; https://raw.githubusercontent.com/pathpy/pathpyG/main/pyproject.toml  
[11] Gephi — README e Timeline API. https://github.com/gephi/gephi/blob/master/README.md ; https://github.com/gephi/gephi/blob/master/modules/TimelineAPI/src/main/java/org/gephi/timeline/api/TimelineModel.java  
[12] Sigma.js — README, changelog e pacote. https://github.com/jacomyal/sigma.js ; https://raw.githubusercontent.com/jacomyal/sigma.js/main/CHANGELOG.md ; https://raw.githubusercontent.com/jacomyal/sigma.js/main/packages/sigma/package.json  
[13] NetworKit — README, instalação e APIs. https://github.com/networkit/networkit ; https://networkit.github.io/get_started.html ; https://networkit.github.io/dev-docs/python_api/community.html  
[14] NetworKit — dinâmica e notebooks oficiais. https://networkit.github.io/dev-docs/python_api/dynamics.html ; https://networkit.github.io/dev-docs/notebooks/Dynamics.html  
[15] pathpyG — grafos temporais, modelos multiordem e algoritmos temporais. https://github.com/pathpy/pathpyG/blob/main/src/pathpyG/core/temporal_graph.py ; https://github.com/pathpy/pathpyG/blob/main/src/pathpyG/core/multi_order_model.py ; https://github.com/pathpy/pathpyG/blob/main/src/pathpyG/algorithms/temporal.py  
[16] NetworkX — algoritmos dependentes do tempo. https://networkx.org/documentation/stable/reference/algorithms/time_dependent.html ; https://github.com/networkx/networkx/blob/main/networkx/algorithms/time_dependent.py  
[17] NetworkX — matchers de isomorfismo que respeitam tempo. https://github.com/networkx/networkx/blob/main/networkx/algorithms/isomorphism/temporalisomorphvf2.py  
[18] NetworkX — tabela de complexidade de caminhos e exemplos de centralidade. https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html ; https://github.com/networkx/networkx/blob/main/examples/algorithms/plot_betweenness_centrality.py  
[19] NetworkX — comunidades. https://networkx.org/documentation/stable/reference/algorithms/community.html  
[20] Gephi — importação/exportação GEXF e releases. https://github.com/gephi/gephi/blob/master/modules/ExportPlugin/src/main/java/org/gephi/io/exporter/plugin/ExporterGEXF.java ; https://github.com/gephi/gephi/releases/tag/v0.11.1  
[21] leidenalg — instalação e metadados. https://raw.githubusercontent.com/vtraag/leidenalg/main/doc/source/install.rst ; https://raw.githubusercontent.com/vtraag/leidenalg/main/pyproject.toml  
[22] Snakemake — CLI, tutorial e relatórios. https://github.com/snakemake/snakemake/blob/main/docs/executing/cli.rst ; https://github.com/snakemake/snakemake/blob/main/docs/tutorial/basics.rst ; https://github.com/snakemake/snakemake/blob/main/docs/snakefiles/reporting.rst
