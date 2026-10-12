# Decisões metodológicas

## 1. Temporadas disponíveis

A pasta de dados recebida contém as temporadas 2 a 8. A análise não fabrica uma temporada 1. A ausência de uma personagem em uma temporada significa que ela não aparece no arquivo daquele snapshot; não é convertida silenciosamente em peso zero em uma rede agregada.

## 2. Limpeza das arestas

Os identificadores são aparados, linhas inválidas são descartadas, loops são removidos e pares invertidos são tratados como a mesma relação. Arestas repetidas são somadas. Os CSVs originais permanecem intactos e a auditoria registra o hash SHA-256 e todas as decisões.

## 3. Peso e custo

`Weight` é usado como `weight_strength`, isto é, força/frequência da interação. Como caminhos mínimos procuram valores baixos, o custo derivado é:

```text
cost = 1 / weight_strength
```

A transformação é registrada no `configuracao_analise.json`. Não se usa diretamente o mesmo campo para responder perguntas de força e de distância.

## 4. Comunidades

A partição principal usa Leiden com `RBConfigurationVertexPartition`, três seeds e três resoluções. A tabela guarda a qualidade objetiva, a modularidade ponderada, o número de comunidades e os principais personagens. A partição é uma solução algorítmica dependente de parâmetros, não uma verdade única.

## 5. Comparação temporal

Cada temporada é um snapshot. São calculadas persistência de personagens, Jaccard de vértices/arestas, mudanças consecutivas e correlação das centralidades nos personagens compartilhados. A posição dos nós é calculada no grafo agregado e reaproveitada em todos os snapshots para evitar a falsa impressão de movimento causada por layouts independentes.

## 6. Terremotos

O intervalo de cinco dias é escolhido por contagem de eventos em janelas consecutivas. Os dois modelos — eventos e células geográficas — são representações analíticas diferentes. Eles não devem ser interpretados como um modelo físico de propagação, previsão ou causalidade sísmica.

## 7. CollegeMsg

O arquivo `college_msg.ipynb` recebido consulta `email-Eu-core-temporal.txt.gz`. A atividade e a fonte foram mantidas separadas no relatório. A análise adicional usa janelas consecutivas de sete dias e agrega interações repetidas como peso da aresta.

## 8. Reprodutibilidade

São registrados: versões, Python, plataforma, seed, resoluções, seeds de sensibilidade, regras de peso, escopo temporal, hashes, tabelas, figuras e formatos de intercâmbio. O Snakefile organiza o pipeline, mas o DAG do workflow não é confundido com o grafo científico.
