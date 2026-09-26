# Limitações metodológicas da coleta de dados — LEIA ANTES DE APRESENTAR

Este documento existe para deixar claro, de forma explícita, onde os dados
usados pela calculadora são **oficiais/reais** e onde são **proxies/simulações**,
e por quê. Isso deve ser citado no relatório final do grupo.

## Resumo em uma frase

A Lei Estadual 17.575/2022 (alterada pela Lei 18.381/2025) exige dados do
SARESP da rede **municipal**, por município, separados em 2º ano (IQA) e 5º
ano (IQI) — **esse dado não existe em formato público hoje**, porque (a) a
Seduc-SP só publica em dados abertos os resultados da rede **estadual**, e
(b) o painel oficial de monitoramento previsto na lei nova só entra em
operação a partir do ciclo de avaliação de **2027**, com repasse em **2028**.

## O que é dado real e oficial hoje

| Indicador da fórmula | Fonte | Rede | Cobertura | Script |
|---|---|---|---|---|
| Coordenadas dos municípios | IBGE via `geobr` | — | 645/645 | `scripts/coords_sp.py` |
| IF (taxa de reprovação/abandono) | INEP — Taxas de Rendimento Escolar 2024 | **Municipal** | 642/645 | `scripts/coleta_rendimento_inep.py` |
| PATI (% matrículas tempo integral) | INEP — Sinopse Estatística da Educação Básica 2025 (Censo Escolar) | **Municipal** | 645/645 | `scripts/coleta_ise_pati_inep.py` |

Esses três já são a fonte oficial correta, direto do governo, sem
aproximação — o PATI em particular é praticamente a definição literal da
lei (% de matrículas em tempo integral, Anos Iniciais, rede municipal), só
que calculado por nós a partir de duas tabelas brutas do Censo Escolar em
vez de vir pronto de um painel da Seduc-SP.

## O que é PROXY (simulação), e por quê

| Indicador da fórmula | O que a lei pede | O que usamos | Script |
|---|---|---|---|
| IQA (nível/evolução, 2º ano) | SARESP, rede municipal, 2º ano | IDEB/SAEB (INEP), rede municipal, **anos iniciais agregado** | `scripts/coleta_ideb_saeb_inep.py` |
| IQI (nível/evolução, 5º ano) | SARESP, rede municipal, 5º ano | IDEB/SAEB (INEP), rede municipal, **anos iniciais agregado** | `scripts/coleta_ideb_saeb_inep.py` |

**Por que não usamos o SARESP da rede municipal:**
1. Pesquisamos o catálogo completo de dados abertos da Seduc-SP (API CKAN,
   12/09/2026) — os únicos datasets de SARESP/IDESP existentes (`IDESP do
   Estado`, `IDESP por Escola`, `Metas IDESP por Escola`, `IDESP por
   Diretoria de Ensino`, `Questionários SARESP`) cobrem **só a rede
   estadual**. Confirmamos isso inspecionando o CSV real: das 5.068 escolas
   no arquivo `IDESP_ESCOLA_2024.csv`, só 1.299 têm nota em "Anos Iniciais"
   — consistente com a rede estadual quase não rodar mais 1º-5º ano em SP
   (municipalização histórica).
2. A adesão da rede municipal ao SARESP é **voluntária** — mesmo que
   existisse um dataset aberto, ele teria furos (nem todo município adere
   todo ano).
3. A própria Lei 18.381/2025 prevê um "painel de monitoramento" oficial
   com o resultado do IQEM por município, mas ele só existe a partir da
   avaliação de **2027** (repasse em 2028) — ou seja, **o dado que a lei
   nova exige literalmente ainda não foi calculado por ninguém**, nem pela
   própria Seduc-SP, porque o primeiro ciclo da lei nova ainda não rodou.

**Por que escolhemos o IDEB/SAEB (INEP) como proxy:**
- É aplicado obrigatoriamente em **todas as redes**, incluindo a municipal
  (ao contrário do SARESP, que é opcional para município) — sem furos de
  adesão.
- Já é uma nota composta (proficiência × fluxo) na escala **0-10**, a
  mesma escala do IDESP/IQEM — evita ter que inventar uma conversão de
  escala entre dois instrumentos diferentes.
- Tem série histórica por município e rede, permitindo calcular a
  "evolução" que a fórmula do IQA/IQI exige.

**Aproximação assumida, para deixar 100% explícita:** o IDEB "Anos
Iniciais" é um indicador único para o ciclo 1º-5º ano — **não separa
especificamente o 2º ano do 5º ano**. Por falta de fonte aberta com essa
granularidade, a calculadora usa o **mesmo valor de IDEB** como proxy tanto
para `nota_iqa` quanto para `nota_iqi`. Isso deve ser dito com todas as
letras no relatório: os números da calculadora são uma **simulação
com a melhor fonte pública disponível hoje**, não o cálculo oficial da
Seduc-SP (que ainda não existe).

## ISE — proxy adicional, também documentado

| Indicador da fórmula | O que a lei pede | O que usamos | Script |
|---|---|---|---|
| ISE (equidade socioeconômica) | Nível socioeconômico dos educandos da rede municipal (metodologia exata no Anexo Único, publicado como imagem — não legível por automação) | INEP — Inse (Indicador de Nível Socioeconômico) 2023, rede Municipal, normalizado 0-1 dentro do universo de SP | `scripts/coleta_ise_pati_inep.py` |

O Inse mede o nível socioeconômico dos alunos (escolaridade dos pais +
posse de bens), na escala nacional do SAEB — é o índice oficial mais
próximo do que a lei descreve, mas **não é necessariamente idêntico** ao
"ISE" do Anexo Único (cujos pesos/fórmula exata não conseguimos ler, pois
estão em imagem no site da Alesp). Convertemos o Inse (maior = mais
favorecido) em uma vulnerabilidade normalizada (maior = mais vulnerável,
0-1) por min-max **dentro do universo dos municípios de SP** — essa
normalização é uma escolha nossa, não uma definição oficial. Por isso o
script também calcula `pc_niveis_1_2_vulneraveis` (% de alunos nos dois
níveis socioeconômicos mais baixos do Inse) como alternativa mais direta e
auditável, caso a fórmula real do Anexo Único seja mais parecida com uma
proporção de alunos vulneráveis do que com uma média normalizada.

## O que ainda falta decidir/coletar

- Confirmar a fórmula exata do Anexo Único da Lei 17.575/2022 (pesos e
  definição precisa do ISE) — hoje só temos o texto legal (sem a tabela,
  publicada como imagem) e a reconstrução via `ICMS_Fundeb_CD.pptx`/
  apresentação pi5.pptx que o grupo já tinha feito manualmente.
- ~~Validação de ordem de grandeza contra o IPM~~ — **feito em 12/09/2026**,
  ver seção "Comparação com o IPM real" abaixo.

## Cálculo consolidado (IQEM, PRE real vs. máxima hipotética)

`consolidar_calcular_sp.py` junta as 4 fontes acima por código IBGE, monta
um `IndicadoresMunicipio` por cidade e calcula, para os 618 municípios com
todos os dados disponíveis: o IQEM real, a participação relativa no rateio
(`pre_real`) e a participação num **cenário de desempenho máximo**
hipotético (`pre_maxima_hipotetica`) — notas 10, 100% tempo integral,
mantendo a mesma matrícula e o mesmo ISE (que reflete a população
atendida, não uma meta de política pública). A diferença entre os dois é
o "quanto o município deixa de ganhar de fatia do bolo" por não estar no
máximo. Saída em `data/processed/painel_icms_sp.csv`.

**Duas pendências levantadas em 12/09/2026 — status atualizado:**

1. **`garantia_fluxo` (gate de fluxo escolar) — pesquisado, resultado
   tranquilizador.** Buscamos o texto da Lei 18.381/2025 (a lei nova) e
   encontramos o seguinte trecho: *"consideração das taxas de reprovação e
   de abandono dos alunos dos anos iniciais do ensino fundamental, através
   da taxa de aprovação que compõe o Índice de Desenvolvimento da
   Educação do Estado de São Paulo (IDESP)"*. Isso sugere que, na
   metodologia da lei NOVA, o fluxo escolar entra de forma **contínua**
   (via taxa de aprovação, dentro do próprio IF) e não como um gate
   binário que zera o índice. O "Sem Garantia de Fluxo o índice é
   zerado" (docstring de `iqem_2025`) veio de um slide do grupo
   (`ICMS_Fundeb_CD.pptx`) que pode refletir uma leitura antiga/de outra
   fonte. **Não é 100% conclusivo** (não achamos o texto do Anexo Único
   em formato legível), mas dá suporte a manter `garantia_fluxo=True`
   como padrão razoável, em vez de arbitrar um limiar numérico sem
   fonte. Recomenda-se citar essa fonte no relatório e, se possível,
   confirmar com o professor/Seduc-SP se existe mesmo um gate binário.

2. **Valor total do "bolo" de ICMS Educacional (R$) — RESOLVIDO em
   26/09/2026.** A pendência abaixo (registrada em 12/09) está superada:
   encontramos a fonte oficial do valor repassado e confirmamos, na
   legislação, o peso do critério educação. Ver a seção **"Cadeia até o
   valor em R$"** no fim deste documento. Em resumo: a premissa que
   estávamos supondo — de que os 13% incidem sobre a cota-parte municipal
   (os 25% do ICMS), e não sobre o ICMS total do Estado — **está
   confirmada**, porque o critério educação é um dos critérios do IPM, e o
   IPM é justamente o índice que rateia a cota-parte municipal. O registro
   original da dúvida fica abaixo, para rastreabilidade:
   - Uma reportagem (Agência Brasil, 10/2025) escreveu: *"o valor total em
     discussão é de cerca de R$ 800 milhões, ou 13% do valor arrecadado
     com o ICMS no estado"* — mas isso é **matematicamente incompatível**
     com o ICMS total do Estado (R$ 226,3 bilhões em 2024, segundo
     Sefaz-SP): 13% disso seriam ~R$ 29,4 bilhões, não R$ 800 milhões.
   - Múltiplas outras fontes (incluindo a pesquisa que o próprio grupo já
     tinha feito, registrada em `checklist_dump.txt`) dizem que os
     **R$ 800 milhões são o valor REDISTRIBUÍDO entre municípios** por
     causa da mudança de critério (ou seja, o quanto muda de mãos entre
     municípios que ganham e municípios que perdem) — **não o total do
     bolo**. Essa leitura é consistente entre si; a frase da Agência
     Brasil parece uma imprecisão jornalística que confundiu as duas
     coisas.
   - **Nossa estimativa própria do total do bolo** (não confirmada em
     nenhuma fonte oficial direta): 13% × 25% × R$ 226,3 bi (ICMS total
     SP 2024, Sefaz-SP) ≈ **R$ 7,3 bilhões**, partindo do pressuposto de
     que os "13%" incidem sobre a cota-parte municipal do ICMS (25% do
     total, regra constitucional), não sobre o ICMS total do Estado. Essa
     premissa (os 13% incidem sobre os 25% municipais) **precisa ser
     confirmada** contra o texto da Lei 3.201/1981 antes de usar esse
     número no relatório.
   - **Recomendação:** não usar nenhum desses valores como "o número
     oficial" sem confirmar na Lei Orçamentária Anual (LOA) do Estado de
     SP ou diretamente com a Sefaz-SP/Seduc-SP. Até lá, `pre_real` e
     `pre_maxima_hipotetica` (participação relativa, base 1,0) continuam
     sendo o resultado mais seguro para apresentar.

## Comparação com o IPM real (Sefaz-SP)

`scripts/coleta_ipm_sefaz.py` baixa diretamente do sistema de consulta da
Sefaz-SP (`https://www4.fazenda.sp.gov.br/DIPAM.Web/ConsultaIndice/` — é um
GET simples com parâmetros na URL, não precisa simular formulário nem
sessão) a tabela oficial dos 645 municípios, que já traz uma coluna
**"Cota Parte Educação"**: a participação real e oficial de cada município
no critério educacional do IPM. Confirmamos que essa coluna soma
exatamente 1,0 entre os 645 municípios — ou seja, é diretamente comparável
ao nosso `pre_real` simulado. Está integrado em `painel_icms_sp.csv` como
`pre_real_oficial_sefaz_formula_antiga` e `diferenca_pp_simulado_vs_oficial`.

**Isso não é o "gabarito" da fórmula nova** — é a fórmula ANTIGA (metade
por qualidade/IDESP antigo, metade por porte populacional), que é a que
está em vigor hoje. A fórmula nova (IQEM 2025, 100% qualidade) só afeta
repasse de verdade a partir de 2028. A diferença entre os dois números
mostra o **impacto da mudança de regra**, não um erro do nosso cálculo.
Achado principal: São Paulo capital cairia de ~22,4% (hoje, fórmula
antiga) para ~13,8% (simulado, fórmula nova) de participação — a fórmula
antiga super-representa cidades grandes só pelo tamanho da população;
cidades médias com bom desempenho relativo (Guarulhos, Osasco, Barueri)
ganhariam participação.

## Cadeia até o valor em R$ (implementada em 26/09/2026)

Até 12/09/2026 o painel parava na **participação relativa** (`pre_real`,
que soma 1,0 entre os municípios). Faltavam duas etapas para chegar em
reais, e as duas foram fechadas com fonte oficial:

```
componentes (IQA, IQI, ISE, PATI)
  → IQEM
  → PRE = participação no critério educação
  → × peso do critério educação no IPM        (etapa 1)
     = contribuição do município no IPM via educação
  → × ICMS repassado aos municípios no período (etapa 2)
     = parcela repassada em R$
```

### Etapa 1 — peso do critério educação no IPM

**Fonte legal:** Lei 17.575/2022, **art. 2º, inciso I**, que acrescenta o
**inciso X ao art. 1º da Lei 3.201/1981**. O critério entra escalonado:

| Ano-base | Critério educação | Critério população |
|---|---|---|
| 2023 | 10% | 3% |
| 2024 | 11% | 2% |
| 2025 | 12% | 1% |
| 2026 em diante | **13%** | extinto |

A redução do critério população está no **art. 1º, inciso I** da mesma lei
— ou seja, o critério educação ocupa progressivamente o espaço que era da
população.

**Validação independente, sem depender de fonte secundária:** o IPM
publicado pela Sefaz-SP é uma soma ponderada das participações de cada
critério, e todas essas participações estão no próprio relatório do DIPAM.
`scripts/coleta_ipm_sefaz.py` recupera os pesos por mínimos quadrados e
**reproduz o IPM oficial dos 645 municípios com erro máximo de 5,5 × 10⁻⁶
ponto percentual** — praticamente ponto flutuante. Os pesos recuperados:

| Critério | Ano-base 2024 | Ano-base 2025 |
|---|---|---|
| Valor adicionado (média das participações de 2 anos) | 74% | 74% |
| **Cota-parte educação** | **11%** | **12%** |
| Receita tributária própria | 5% | 5% |
| Área cultivada | 3% | 3% |
| População | 2% | 1% |
| Igual para todos | 2% | 2% |
| Área protegida | 1% | 1% |
| Vegetação nativa | 1% | 1% |
| Área inundada | 0,5% | 0,5% |
| Resíduos sólidos | 0,5% | 0,5% |

Isso bate exatamente com a tabela legal acima — os pesos estão
confirmados por duas vias independentes. A decomposição fica gravada em
`data/processed/pesos_ipm_{ano}.csv`, com o erro de reprodução na própria
tabela, para auditoria.

**Detalhe que muda o resultado:** a coluna de valor adicionado do IPM é a
*média das participações* dos dois anos, não a *participação da média* dos
valores. Usar a segunda forma deixa um resíduo ~600× maior e distorce os
pesos recuperados (educação sai 11,03% em vez de 11,00%).

**Calendário — o "13%" não vale para hoje.** O IPM calculado sobre um
ano-base rege os repasses do ano civil **ano-base + 2**. Verificamos isso
contra o dado oficial: com o IPM de ano-base 2024, a identidade
`repasse_i = IPM_i × total_do_Estado` reproduz os repasses de 2026 com
dispersão de 0,04% entre municípios de portes muito diferentes (contra
~3% se testada contra 2025, isto é, outro ano-base). Logo:

- repasse de 2026 → ano-base 2024 → peso **11%**
- repasse de 2027 → ano-base 2025 → peso **12%**
- repasse de 2028 → ano-base 2026 → peso **13%**

Ou seja, **os 13% valem a partir do repasse de 2028 — o mesmo exercício em
que a fórmula nova do IQEM passa a valer.** O painel mostra as duas
leituras: o peso *vigente* no período escolhido e o *regime pleno* de 13%,
sempre rotuladas.

### Etapa 2 — valor do ICMS repassado no período

**Fonte:** Sefaz-SP, "Repasse de Tributos a Municípios"
(`https://www.fazenda.sp.gov.br/RepasseConsulta/Consulta/repasse.aspx`),
coletado por `scripts/coleta_repasse_icms_sefaz.py`. Município a município,
mês a mês, anos de 1995 a 2026 — o total do Estado é a **soma dos 645
municípios**, não uma estimativa.

**O que esse valor é** (respondendo à pergunta "já é a cota-parte de 25% ou
é o total arrecadado?"): é a **quota-parte municipal efetivamente
creditada**, ou seja, já é a parcela dos municípios (os 25% do art. 158,
IV da Constituição) **e já está líquida da retenção de 20% do FUNDEB**.
Isso está na nota de rodapé da própria página: *"A partir de março de 2007
valores líquidos, descontados o montante transferido para o FUNDEB, de
acordo com a Lei 11.494 de 20/06/2007 [...] a partir de janeiro de 2009,
valores com desconto de 20%"*.

Por isso o painel traz **duas escalas**, ambas rotuladas e nenhuma
estimada:

- **líquido** — exatamente o que a Sefaz publica (pós-FUNDEB). É o dinheiro
  que entra no caixa do município.
- **bruto** — líquido ÷ 0,80, a cota-parte de 25% antes da retenção.

**Ano corrente:** o relatório traz apenas os meses já publicados. O script
detecta o último mês e grava `meses_publicados`, e o painel rotula o
período ("2026 · até setembro"), para não comparar um ano parcial com um
ano fechado sem avisar.

**Ordem de grandeza conferida contra outra fonte da própria Sefaz:** a
assessoria da Sefaz-SP noticiou que nos onze primeiros meses de 2025 os
repasses de ICMS aos municípios somaram R$ 42,95 bilhões — consistente com
o total anual que a coleta produz.

### Parcela cheia — cenário individual, não coletivo

O `pre_maxima_hipotetica` que já existia coloca **todos** os municípios no
máximo ao mesmo tempo. Como o IQEM de todos se iguala (~8,1), o rateio
degenera para uma divisão proporcional às matrículas. Isso é útil para
**isolar o efeito da qualidade** sobre a fatia, mas não responde "quanto
este município receberia se batesse as metas" — num cenário em que todos
melhoram junto, ninguém ganha participação.

A **parcela cheia** usa o cenário **individual**
(`participacao_com_um_no_maximo`): só aquele município vai ao máximo, os
demais ficam nos valores reais, e o rateio é renormalizado. As duas
colunas convivem no painel, cada uma com seu rótulo.

**Ressalva obrigatória:** a coluna de parcela cheia **não é somável**. Cada
valor vem de um cenário contrafactual diferente, então a soma da coluna não
descreve cenário nenhum. A soma das parcelas *repassadas*, sim, fecha
exatamente com o bolo do critério (peso × ICMS do período).

### Casamento de períodos — o contrafactual é deliberado

A fórmula do IQEM que simulamos (Lei 18.381/2025, 100% qualidade) só vale a
partir do ano-base 2026, com repasse em 2028. Aplicá-la ao dinheiro de
2025/2026 é **deliberadamente um contrafactual**: mostra como aquele valor
teria sido dividido se a regra nova já valesse — não uma reconstituição do
que aconteceu. O painel diz isso na tela, e o relatório precisa dizer
também.

### Universo de 618 municípios

Como o PRE é renormalizado no universo processado, os 618 municípios com
dado educacional completo dividem entre si **100%** do bolo do critério, e
os 27 ausentes ficam com zero. Medimos o tamanho dessa distorção na fonte
oficial: **os 27 ausentes detêm 0,835% da cota-parte educação da Sefaz**, e
0,63 p.p. disso é um único município (Mauá). O número vai no painel, na
coluna `cota_parte_educacao_oficial_fora_do_painel_pct`, para não deixar a
premissa implícita.

## Correção pendente nos entregáveis de setembro/2026

O exemplo de Cotia (`exemplo_cotia_2024()` na calculadora, vindo do slide 8
de `ICMS_Fundeb_CD.pptx`) tem uma **inconsistência de escala** que
provavelmente contaminou o número de "perda de receita" dos entregáveis:

- `recebida = 341.357.089,75 × 0,009307459` multiplica o valor de ICMS **do
  próprio município** por um índice que é **normalizado no Estado** (soma
  1,0 entre os 645). As duas escalas não se combinam.
- `cota_parte_maxima = 34.135.708,98` é, exatamente, **10% de
  341.357.089,75** — o peso do critério educação aplicado ao repasse do
  próprio município (o que equivale a supor PRE = IPM), não um cenário de
  desempenho máximo.
- Além disso, R$ 341.357.089,75 é o ICMS repassado a Cotia no ano civil
  **2025** (confere centavo a centavo com a consulta da Sefaz), e não em
  2024 como diz o rótulo do slide.

Pela cadeia correta (`peso × PRE × total do Estado`), a parcela educacional
de Cotia fica **cerca de uma ordem de grandeza acima** dos R$ 3,18 milhões
do slide. As funções `cota_parte_recebida()` e `perda_receita_estimada()`
foram **mantidas** no código, com aviso no docstring, só para rastrear de
onde vieram os números antigos — a cadeia correta está em
`parcela_educacao_reais()`. **Decisão pendente com o professor:** corrigir
ou não o relatório e a apresentação de setembro.

## Recomendação para o relatório final

Citar este documento (ou reproduzir esta tabela) na seção de metodologia,
deixando claro que a calculadora demonstra o **mecanismo** da nova lei com
dados reais sempre que possível, e com a melhor aproximação pública
disponível quando o dado oficial ainda não existe — o que é uma limitação
do calendário da própria lei (vigência 2026, avaliação 2027, repasse 2028),
não uma falha de pesquisa do grupo.
