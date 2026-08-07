# Evidência para o business case (MBA USP/Esalq)

Todos os números abaixo são produzidos pelos notebooks e regravados a cada execução.
Nenhum foi digitado à mão: as fontes estão indicadas em cada tabela.

Janela do estudo: **1994-01-01 a 2026-05-21** · universo: AAPL, MSFT, NVDA, GOOGL, AMZN,
META, TSLA, AMD, INTC, ORCL.

---

## 1. Comparação antes × depois — base de dados

Fonte: `data/data_quality_report.csv`, gerado pelo notebook 02. As duas colunas são
calculadas **pela mesma função**, aplicando as regras de cada pipeline aos mesmos arquivos
brutos.

| Indicador | Antes | Depois | Variação |
|---|---|---|---|
| Janela de observação | 2015–2026 | 1994–2026 | +21 anos |
| Observações de mercado | 28.630 | 67.912 | +137% |
| Registros de disclosure (10-K/10-Q/8-K) | 1.092 | 3.941 | +261% |
| Unicidade de registros | 81,2% | 100,0% | +18,8 p.p. |
| Cobertura de linhagem societária | 80,0% | 100,0% | +20,0 p.p. |
| Cobertura temporal na janela | 42,2% | 100,0% | +57,8 p.p. |
| Regimes de crise cobertos | 0 | 4 | dot-com, 2008, COVID, 2022 |

Figura de apoio: `fig-cobertura-dados.png`.

---

## 2. Comparação antes × depois — método

| Aspecto | Antes | Depois |
|---|---|---|
| Modelos avaliados | 1 (Isolation Forest) | 10, em 6 famílias |
| Critério de avaliação | nenhum | rótulo forward-looking externo |
| Validação temporal | nenhuma | walk-forward, 11 anos, refit anual |
| Teste estatístico de comparação | nenhum | Friedman + Wilcoxon com correção de Holm |
| Junção de fundamentos | data de fim do período | data de protocolo (filing date) |
| Look-ahead nos fundamentos | mediana de 19 dias em 37,5% das linhas | nenhum, testado |
| Uso de valores reapresentados | valor mais recente, retroativo | primeira publicação apenas |
| Auditoria de vazamento | nenhuma | reconstrução ponto-no-tempo, 120 testes |
| Controle de redundância | nenhum | VIF máximo 7,8 após poda |
| Explicabilidade | nenhuma | SHAP + tipo de alerta |

---

## 3. Resultado do modelo

Fonte: `model/training_metrics.json`, notebook 06.

**Critério.** Um dia é material se o retorno anormal absoluto do **pregão seguinte** superar 4× a
volatilidade anormal dos 63 pregões anteriores daquele emissor. O horizonte foi medido, não
arbitrado: a ROC-AUC cai de 0,742 (1 pregão) para 0,535 (10 pregões), e a escolha de 1 pregão
se justifica porque um alerta que antecipa a sessão seguinte é acionável. O
rótulo usa exclusivamente informação posterior à data pontuada — nenhum modelo poderia
tê-lo ajustado.

| Métrica | Valor |
|---|---|
| Taxa base de dias materiais | 0,88% |
| ROC-AUC (escore primário) | **0,742** |
| Precisão no orçamento de 1% de alertas | 7,6% |
| **Ganho sobre inspeção aleatória** | **8,68×** |
| Precisão em dias de mercado calmo | 8,9% (ganho de 10,6×) |
| Blocos emissor-ano comparados | 84 |
| Friedman | χ² = 45,0; p = 9,3 × 10⁻⁷ |

Figuras: `fig-discriminacao-modelos.png`, `fig-walk-forward.png`, `fig-atribuicao-shap.png`.

### O resultado central, e ele é contraintuitivo

Dois resultados respondem a perguntas diferentes. **Em ordenação, os dez detectores são
estatisticamente indistinguíveis**: todos ficam entre 0,66 e 0,74 de ROC-AUC, o Friedman
rejeita igualdade global, mas nenhuma comparação par a par sobrevive à correção de Holm.
**Na métrica operacional, a separação é decisiva**: sob orçamento de 1%, o baseline
condicional acerta 7,6% contra 1,4% a 3,8% dos demais.

A leitura: **o valor está sobretudo na construção condicional das variáveis, não na
sofisticação do modelo**. A ROC-AUC avalia a ordenação inteira; a operação depende só do
topo dela. É um achado que só um benchmark com baseline poderia produzir.

---

## 4. Viabilidade operacional — tradução para o negócio

Com orçamento de 1% de alertas sobre 10 emissores, o sistema produz 635 alertas em 32 anos:
cerca de **20 alertas por ano**, ou menos de dois por mês para toda a carteira. A cada 100
dias inspecionados pela fila do modelo, entre 7 e 8 são seguidos de movimento material no
pregão seguinte, contra menos de 1 numa inspeção aleatória de mesmo tamanho.

Em outras palavras: o analista chega ao mesmo número de eventos relevantes examinando cerca
de **um nono do volume** que examinaria sem priorização.

---

## 5. Limitações a declarar no texto

1. **O critério recompensa antecipar movimento.** Um dia genuinamente relevante que não
   moveu o preço conta como falso positivo, e uma configuração estruturalmente estranha
   (volume alto sem movimento) é invisível ao rótulo. É nesse aspecto específico que os
   modelos multivariados ficam subavaliados — e por isso um deles segue publicado como
   escore secundário.
2. **A janela ampliada melhora a detecção.** Treinar desde 1994 em vez de 2015 elevou a
   ROC-AUC de 0,688 para 0,742 e reduziu a concentração de alertas na janela COVID de 9,0%
   para 7,1%.
3. **O universo é de dez empresas de tecnologia de grande porte** numa única bolsa. Nada
   aqui deve ser extrapolado para small caps ou outros setores sem reajuste.
4. **Eventos se agrupam no calendário**, o que infla a significância dos testes
   transversais do event study. Os p-valores devem ser lidos como indicativos.
5. **Os fundamentos não pagam seu custo** na janela atual: exigi-los reduz o painel a 27%
   das linhas e elimina as duas crises do período de treino. Seguem no dataset como
   contexto, não como entrada do modelo.

---

## 6. Mapa de figuras

| Arquivo no repositório do TCC | Origem | Uso sugerido |
|---|---|---|
| `fig-cobertura-dados.png` | notebook 02 | Caracterização do objeto de estudo |
| `fig-regimes-volatilidade.png` | notebook 03 | Diagnóstico do problema |
| `fig-event-study.png` | notebook 03 | Métodos utilizados |
| `fig-discriminacao-modelos.png` | notebook 06 | Discussão dos resultados |
| `fig-walk-forward.png` | notebook 06 | Discussão dos resultados |
| `fig-atribuicao-shap.png` | notebook 06 | Viabilidade operacional |

Todas as figuras estão em `images/figures/` no repositório do projeto e foram copiadas para
`images/` no repositório do business case.
