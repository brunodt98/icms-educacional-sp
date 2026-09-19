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

2. **Valor total do "bolo" de ICMS Educacional (R$) — achamos números
   conflitantes na imprensa, sinalizando com clareza a ambiguidade em vez
   de escolher um às cegas:**
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

## Recomendação para o relatório final

Citar este documento (ou reproduzir esta tabela) na seção de metodologia,
deixando claro que a calculadora demonstra o **mecanismo** da nova lei com
dados reais sempre que possível, e com a melhor aproximação pública
disponível quando o dado oficial ainda não existe — o que é uma limitação
do calendário da própria lei (vigência 2026, avaliação 2027, repasse 2028),
não uma falha de pesquisa do grupo.
