# -*- coding: utf-8 -*-
"""
Dashboard interativo - ICMS Educacional SP (Streamlit).

Le data/processed/painel_icms_sp.csv (gerado por consolidar_calcular_sp.py)
e mostra, por municipio e no agregado do Estado:
  - as metricas que compoem o IQEM (IQA/IQI proxy via IDEB, ISE, PATI) e
    o IF (fluxo), cada uma comparada contra a MEDIA dos municipios
    processados (nao existe uma "meta de 100%" oficial - ver
    LIMITACOES_METODOLOGICAS.md: o ICMS Educacional-SP e' uma fatia
    PROPORCIONAL, nao um limiar de aprovacao)
  - a participacao real (simulada, formula nova) vs a maxima hipotetica
    (desempenho maximo) vs a oficial da Sefaz-SP (formula antiga, em
    vigor hoje)

Rodar com: streamlit run app.py
"""

from math import log10
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

BASE_DIR = Path(__file__).parent

st.set_page_config(
    page_title="ICMS Educacional SP",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ===========================================================================
# DESIGN TOKENS
# ===========================================================================
SURFACE = "#fcfcfb"
PLANE = "#f9f9f7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

BLUE = "#2a78d6"        # cenario simulado (formula nova)
BLUE_SOFT = "#9ec5f4"   # cenario maximo hipotetico
BLUE_DEEP = "#184f95"
NEUTRAL = "#898781"     # baseline: oficial de hoje (formula antiga)
CRITICAL = "#d03b3b"    # linha de media / alerta
ORANGE = "#eb6834"

SEQ_BLUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]
DIV_BLUE_RED = [
    [0.0, "#d03b3b"], [0.25, "#e88f8f"], [0.5, "#f0efec"],
    [0.75, "#86b6ef"], [1.0, "#184f95"],
]
SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

# ===========================================================================
# TEMPLATE PLOTLY
# ===========================================================================
_axis = dict(
    showgrid=False,
    zeroline=False,
    linecolor=AXIS,
    linewidth=1,
    ticks="outside",
    tickcolor=AXIS,
    ticklen=4,
    tickfont=dict(size=11, color=MUTED),
    title=dict(font=dict(size=11, color=MUTED)),
    automargin=True,
)
pio.templates["icms"] = go.layout.Template(
    layout=dict(
        font=dict(family=SANS, size=12, color=INK_2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[BLUE, ORANGE, "#1baf7a", "#eda100", "#e87ba4"],
        xaxis={**_axis},
        yaxis={**_axis, "showgrid": True, "gridcolor": GRID, "gridwidth": 1},
        margin=dict(l=4, r=4, t=8, b=4),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=AXIS, font=dict(family=SANS, size=12, color=INK)
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(size=11, color=INK_2), bgcolor="rgba(0,0,0,0)",
        ),
        colorscale=dict(sequential=SEQ_BLUE, diverging=DIV_BLUE_RED),
        coloraxis=dict(
            colorbar=dict(
                outlinewidth=0, thickness=10, len=0.7, tickfont=dict(size=10, color=MUTED),
                title=dict(font=dict(size=10, color=MUTED)),
            )
        ),
    )
)
pio.templates.default = "icms"

PLOT_CFG = {"displayModeBar": False, "scrollZoom": False}

# ===========================================================================
# CSS
# ===========================================================================
st.markdown(
    f"""
<style>
  .stApp {{ background: {PLANE}; }}
  [data-testid="stHeader"] {{ background: transparent; }}
  [data-testid="stMainBlockContainer"] {{
      padding: 2.2rem 2.4rem 4rem; max-width: 1480px;
  }}
  html, body, [class*="st-"] {{ font-family: {SANS}; }}

  /* ---------- cabecalho ---------- */
  .eyebrow {{
      font-size: .72rem; font-weight: 600; letter-spacing: .09em;
      text-transform: uppercase; color: {MUTED}; margin-bottom: .5rem;
  }}
  h1.hero {{
      font-size: 2.15rem; font-weight: 680; letter-spacing: -.022em;
      color: {INK}; margin: 0 0 .5rem; line-height: 1.15;
  }}
  .lede {{
      font-size: .98rem; color: {INK_2}; max-width: 68ch;
      line-height: 1.55; margin-bottom: 1rem;
  }}
  .badge {{
      display: inline-flex; align-items: center; gap: .5rem;
      font-size: .78rem; color: {INK_2}; background: #fff6e6;
      border: 1px solid #f0d9a8; border-radius: 999px;
      padding: .32rem .85rem; margin-bottom: .2rem;
  }}
  .badge b {{ color: #8a5d00; font-weight: 640; }}
  .rule {{ height: 1px; background: {GRID}; margin: 1.6rem 0 1.4rem; border: 0; }}

  /* ---------- titulos de secao ---------- */
  .sec {{ margin: 1.9rem 0 .85rem; }}
  .sec h2 {{
      font-size: 1.02rem; font-weight: 640; color: {INK};
      margin: 0 0 .2rem; letter-spacing: -.01em;
  }}
  .sec p {{ font-size: .82rem; color: {MUTED}; margin: 0; line-height: 1.5; }}

  /* ---------- stat tiles ---------- */
  [data-testid="stMetric"] {{
      background: {SURFACE}; border: 1px solid {GRID};
      border-radius: 10px; padding: .95rem 1.05rem;
  }}
  [data-testid="stMetricLabel"] p {{
      font-size: .76rem !important; font-weight: 550; color: {MUTED};
      letter-spacing: .01em; line-height: 1.3;
  }}
  [data-testid="stMetricValue"] {{
      font-size: 1.72rem !important; font-weight: 640; color: {INK};
      letter-spacing: -.02em; font-variant-numeric: proportional-nums;
  }}
  [data-testid="stMetricDelta"] {{ font-size: .76rem !important; font-weight: 550; }}

  /* ---------- cards de grafico ---------- */
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
      border-radius: 10px;
  }}
  .card-head {{ margin-bottom: .7rem; }}
  .card-head h3 {{
      font-size: .92rem; font-weight: 620; color: {INK};
      margin: 0 0 .18rem; letter-spacing: -.005em;
  }}
  .card-head p {{ font-size: .78rem; color: {MUTED}; margin: 0; line-height: 1.45; }}

  /* ---------- mini charts (distribuicoes) ---------- */
  .mini h4 {{
      font-size: .78rem; font-weight: 620; color: {INK};
      margin: 0 0 .1rem; line-height: 1.3;
  }}
  .mini p {{ font-size: .7rem; color: {MUTED}; margin: 0 0 .1rem; }}
  .mini .avg {{ font-size: .72rem; color: {CRITICAL}; font-weight: 580; }}

  /* ---------- abas ---------- */
  .stTabs [data-baseweb="tab-list"] {{
      gap: .35rem; border-bottom: 1px solid {GRID}; padding-bottom: 0;
  }}
  .stTabs [data-baseweb="tab"] {{
      height: 2.5rem; padding: 0 .95rem; font-size: .88rem; font-weight: 550;
      color: {MUTED}; background: transparent; border-radius: 8px 8px 0 0;
  }}
  .stTabs [aria-selected="true"] {{ color: {BLUE}; font-weight: 620; }}
  .stTabs [data-baseweb="tab-highlight"] {{ background: {BLUE}; height: 2px; }}
  .stTabs [data-baseweb="tab-border"] {{ display: none; }}

  /* ---------- nota final ---------- */
  .note {{
      background: {SURFACE}; border: 1px solid {GRID}; border-left: 3px solid {BLUE};
      border-radius: 8px; padding: .9rem 1.1rem; font-size: .88rem;
      color: {INK_2}; line-height: 1.6;
  }}
  .note b {{ color: {INK}; font-weight: 620; }}

  /* ---------- metodologia ---------- */
  [data-testid="stColumn"]:has(.meth), [data-testid="stColumn"]:has(.meth) > div {{
      height: 100%;
  }}
  .meth {{
      background: {SURFACE}; border: 1px solid {GRID}; border-radius: 10px;
      padding: 1.1rem 1.25rem; height: 100%; box-sizing: border-box;
  }}
  .meth h3 {{ font-size: .9rem; font-weight: 640; margin: 0 0 .1rem; }}
  .meth .tag {{ font-size: .72rem; color: {MUTED}; margin-bottom: .75rem; }}
  .meth ul {{ margin: 0; padding-left: 1.05rem; }}
  .meth li {{ font-size: .85rem; color: {INK_2}; line-height: 1.65; margin-bottom: .5rem; }}
  .meth li b {{ color: {INK}; font-weight: 620; }}

  /* ---------- cadeia de calculo ate o R$ ---------- */
  .cadeia {{
      background: {SURFACE}; border: 1px solid {GRID}; border-radius: 10px;
      padding: 1rem 1.15rem;
  }}
  .cadeia ol {{ margin: 0; padding-left: 1.15rem; }}
  .cadeia li {{
      font-size: .85rem; color: {INK_2}; line-height: 1.75; margin-bottom: .3rem;
  }}
  .cadeia li b {{ color: {INK}; font-weight: 620; }}
  .cadeia .passo {{ color: {MUTED}; font-size: .78rem; }}

  [data-testid="stElementToolbar"] {{ display: none; }}
</style>
""",
    unsafe_allow_html=True,
)


def section(titulo: str, sub: str = "") -> None:
    st.markdown(
        f"<div class='sec'><h2>{titulo}</h2>{f'<p>{sub}</p>' if sub else ''}</div>",
        unsafe_allow_html=True,
    )


def card_head(titulo: str, sub: str = "") -> None:
    st.markdown(
        f"<div class='card-head'><h3>{titulo}</h3>{f'<p>{sub}</p>' if sub else ''}</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# DADOS
# ===========================================================================
METRICAS = {
    "ideb_anos_iniciais_proxy": {
        "label": "IDEB/SAEB", "peso": "proxy do IQA + IQI · 80%",
        "melhor": "maior", "fmt": "{:.2f}", "dmult": 1, "dfmt": "{:+.2f}",
    },
    "taxa_reprovacao_pct": {
        "label": "Reprovação", "peso": "compõe o IF (fluxo)",
        "melhor": "menor", "fmt": "{:.1f}%", "dmult": 1, "dfmt": "{:+.1f} p.p.",
    },
    "taxa_abandono_pct": {
        "label": "Abandono", "peso": "compõe o IF (fluxo)",
        "melhor": "menor", "fmt": "{:.1f}%", "dmult": 1, "dfmt": "{:+.1f} p.p.",
    },
    "pati": {
        "label": "PATI — tempo integral", "peso": "10% do IQEM",
        "melhor": "maior", "fmt": "{:.1%}", "dmult": 100, "dfmt": "{:+.1f} p.p.",
    },
    "ise_vulnerabilidade": {
        "label": "ISE — vulnerabilidade", "peso": "10% do IQEM",
        "melhor": "neutro", "fmt": "{:.2f}", "dmult": 1, "dfmt": "{:+.2f}",
    },
}


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    """Le o painel LONGO (municipio x periodo x regime de peso do criterio)."""
    df = pd.read_csv(BASE_DIR / "data" / "processed" / "painel_icms_sp.csv")
    df["pre_real_pct"] = df["pre_real"] * 100
    df["pre_maxima_pct"] = df["pre_maxima_hipotetica"] * 100
    df["pre_cheia_pct"] = df["pre_cheia_individual"] * 100
    df["pre_oficial_pct"] = df["pre_real_oficial_sefaz_formula_antiga"] * 100
    df["pati_pct"] = df["pati"] * 100
    df["contribuicao_ipm_pct"] = df["contribuicao_ipm_educacao"] * 100
    # No cenario "todos no maximo" o IQEM se iguala e o rateio vira proporcional
    # as matriculas (corr = 1.0 com o share de matriculas). A diferenca contra a
    # participacao simulada e', portanto, o efeito liquido da QUALIDADE da rede
    # sobre a fatia: positivo = a qualidade rende fatia acima do porte.
    df["efeito_qualidade_pp"] = -df["diferenca_pontos_percentuais_pre"]
    return df


def brl(valor: float, casas: int = 0) -> str:
    """Formata em reais no padrao pt-BR (1.234.567,89)."""
    if pd.isna(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return "R$ " + texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def brl_curto(valor: float) -> str:
    """Reais em escala legivel: R$ 37,4 bi / R$ 1,2 mi / R$ 840 mil."""
    if pd.isna(valor):
        return "—"
    sinal = "-" if valor < 0 else ""
    v = abs(valor)
    for corte, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if v >= corte:
            return f"{sinal}R$ {v / corte:,.1f} {sufixo}".replace(".", ",")
    return sinal + brl(v, 2)


TODOS = carregar_dados()
N = TODOS["municipio"].nunique()
MESES_NOME = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

# ===========================================================================
# CABECALHO
# ===========================================================================
st.markdown(
    f"""
<div class='eyebrow'>Projeto Integrador V · FATEC Cotia · Grupo 2</div>
<h1 class='hero'>ICMS Educacional de São Paulo</h1>
<p class='lede'>
  Simulação de quanto cada município receberia na cota-parte educacional do ICMS
  sob a fórmula da Lei 17.575/2022, alterada pela Lei 18.381/2025 — métrica por
  métrica, para {N} dos 645 municípios do Estado.
</p>
<div class='badge'><b>Simulação</b> · IQA/IQI usam IDEB/SAEB como proxy do SARESP
municipal — resultado oficial só a partir de 2027/2028</div>
<hr class='rule'>
""",
    unsafe_allow_html=True,
)

# ===========================================================================
# CONTROLES GLOBAIS - periodo, regime de peso e escala do valor
# ===========================================================================
# Ficam acima das abas de proposito: o periodo muda o valor em R$ mostrado em
# "Visão geral" e em "Por município", e um seletor por aba sairia do ar de
# sincronia entre as duas.
ctrl_periodo, ctrl_regime, ctrl_escala = st.columns([1, 1.5, 1.5], gap="medium")

periodos = sorted(TODOS["periodo"].unique(), reverse=True)


def rotulo_periodo(p: int) -> str:
    linha = TODOS[TODOS["periodo"] == p].iloc[0]
    if linha["periodo_fechado"]:
        return f"{p} · ano fechado"
    return f"{p} · até {MESES_NOME[int(linha['meses_publicados'])]}"


periodo_sel = ctrl_periodo.selectbox(
    "Período do repasse", periodos, format_func=rotulo_periodo,
    help="Ano civil em que o ICMS foi repassado aos municípios. O ano corrente "
         "traz o acumulado até o último mês publicado pela Sefaz-SP.",
)

_linha_periodo = TODOS[TODOS["periodo"] == periodo_sel].iloc[0]
ANO_BASE = int(_linha_periodo["ano_base_ipm"])
MESES_PUB = int(_linha_periodo["meses_publicados"])
_peso_vigente = TODOS[
    (TODOS["periodo"] == periodo_sel) & (TODOS["regime_peso"] == "vigente")
]["peso_criterio_educacao"].iloc[0]

regime_sel = ctrl_regime.radio(
    "Peso do critério educação no IPM",
    ["vigente", "pleno"], horizontal=True,
    format_func=lambda r: (
        f"Vigente · {_peso_vigente:.0%} (ano-base {ANO_BASE})" if r == "vigente"
        else "Regime pleno · 13%"
    ),
    help="A Lei 17.575/2022 (art. 2º, I) escalona o critério educação: 10% no ano-base "
         "2023, 11% em 2024, 12% em 2025 e 13% a partir de 2026. 'Vigente' usa o peso "
         "realmente em vigor no período; 'regime pleno' aplica os 13% da regra madura, "
         "o que é um cenário, não um valor histórico.",
)

escala_sel = ctrl_escala.radio(
    "Escala do valor de ICMS",
    ["liquido", "bruto"], horizontal=True,
    format_func=lambda e: (
        "Líquido · pós-Fundeb" if e == "liquido" else "Bruto · cota-parte de 25%"
    ),
    help="A Sefaz-SP publica o valor líquido, já descontados os 20% retidos para o "
         "Fundeb (Lei 11.494/2007) — é o dinheiro que entra no caixa do município. "
         "O bruto é esse valor ÷ 0,80, ou seja, a cota-parte de 25% antes da retenção.",
)

df = TODOS[
    (TODOS["periodo"] == periodo_sel) & (TODOS["regime_peso"] == regime_sel)
].reset_index(drop=True)
medias = df[list(METRICAS)].mean()

COL_REPASSADA = f"parcela_repassada_{escala_sel}_reais"
COL_CHEIA = f"parcela_cheia_{escala_sel}_reais"
COL_DIFERENCA = f"diferenca_{escala_sel}_reais"
COL_ICMS_MUNI = f"icms_municipal_{escala_sel}_reais"
ICMS_ESTADO = float(df[f"icms_estado_{escala_sel}_reais"].iloc[0])
PESO = float(df["peso_criterio_educacao"].iloc[0])
BOLO_EDUCACAO = ICMS_ESTADO * PESO
FORA_DO_PAINEL_PCT = float(df["cota_parte_educacao_oficial_fora_do_painel_pct"].iloc[0])

_nota_periodo = (
    f"ano fechado" if bool(df["periodo_fechado"].iloc[0])
    else f"acumulado de janeiro a {MESES_NOME[MESES_PUB]} ({MESES_PUB} meses)"
)
st.caption(
    f"Exibindo **{periodo_sel}** ({_nota_periodo}), peso do critério educação de "
    f"**{PESO:.0%}** e valor **{'líquido' if escala_sel == 'liquido' else 'bruto'}**. "
    f"A fórmula nova do IQEM só vale a partir do ano-base 2026 (repasse em 2028), "
    f"então aplicá-la ao dinheiro de {periodo_sel} é um contrafactual: mostra como "
    f"aquele valor teria sido dividido sob a regra nova."
)

aba_geral, aba_municipio, aba_tabela, aba_metodologia = st.tabs(
    ["Visão geral", "Por município", "Tabela completa", "Metodologia"]
)

# ===========================================================================
# ABA 1 - VISAO GERAL
# ===========================================================================
with aba_geral:
    ganham = int((df["diferenca_pp_simulado_vs_oficial"] > 0).sum())
    rendem = int((df["efeito_qualidade_pp"] > 0).sum())

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.metric("Municípios simulados", f"{N}", help="De 645 municípios de São Paulo")
    c2.metric("IQEM médio", f"{df['iqem_real'].mean():.2f}", help="Escala 0–10")
    c3.metric(
        "Ganham com a fórmula nova", f"{ganham} de {N}",
        help="Municípios cuja participação simulada é maior que a oficial de hoje "
             "(fórmula antiga da Sefaz-SP)",
    )
    c4.metric(
        "Qualidade rende fatia", f"{rendem} de {N}",
        help="Municípios em que o desempenho da rede rende participação acima da "
             "fatia que teriam num rateio puramente por matrículas",
    )

    section(
        "O dinheiro do período",
        "Do ICMS repassado aos municípios até a parcela de cada rede: "
        "IQEM → participação no critério educação (PRE) → × peso do critério no IPM "
        "→ × ICMS do período.",
    )
    d1, d2, d3, d4 = st.columns(4, gap="medium")
    d1.metric(
        f"ICMS repassado · {periodo_sel}", brl_curto(ICMS_ESTADO),
        help=f"Soma dos 645 municípios no {_nota_periodo}, valor "
             f"{'líquido (pós-Fundeb)' if escala_sel == 'liquido' else 'bruto (cota-parte de 25%)'}. "
             "Fonte: Sefaz-SP, Repasse de Tributos a Municípios.",
    )
    d2.metric(
        "Bolo do critério educação", brl_curto(BOLO_EDUCACAO),
        delta=f"{PESO:.0%} do IPM", delta_color="off",
        help="É o total acima multiplicado pelo peso do critério educação no IPM. "
             "É esse valor que o PRE divide entre os municípios.",
    )
    d3.metric(
        "Parcela mediana por município", brl_curto(df[COL_REPASSADA].median()),
        help=f"Metade dos {N} municípios recebe menos que isso pelo critério educação. "
             "A mediana, e não a média, porque a distribuição é muito assimétrica — "
             "São Paulo concentra uma fatia enorme.",
    )
    d4.metric(
        "Diferença mediana até a parcela cheia", f"{df['diferenca_pct'].median():+.1f}%",
        help="Quanto o município mediano deixa de receber por não estar no desempenho "
             "máximo, em % sobre a própria parcela. Cenário individual: só ele no "
             "máximo, os demais nos valores reais.",
    )
    st.caption(
        f"As parcelas repassadas somam exatamente o bolo do critério ({brl_curto(BOLO_EDUCACAO)}). "
        f"As parcelas **cheias não são somáveis**: cada uma vem de um cenário diferente "
        f"(um município de cada vez no máximo), então somá-las não descreve nenhum "
        f"cenário real. Os {N} municípios simulados dividem aqui 100% do bolo — na fonte "
        f"oficial, os {645 - N} que ficaram fora detêm {FORA_DO_PAINEL_PCT:.2f}% da "
        f"cota-parte educação."
    )

    section(
        "Onde a qualidade da rede rende — e onde custa",
        "No cenário em que todos os municípios atingem o desempenho máximo, o IQEM se "
        "iguala e o rateio passa a ser proporcional às matrículas. A diferença contra a "
        "participação simulada isola, portanto, o efeito da qualidade: em azul, redes "
        "cuja qualidade rende fatia acima do porte; em vermelho, as que ficam abaixo. "
        "A escala de cor satura no percentil 95 — sem isso, São Paulo sozinho "
        "(−1,245 p.p.) deixaria todos os demais municípios em branco.",
    )
    with st.container(border=True):
        lim = df["efeito_qualidade_pp"].abs().quantile(0.95)
        fig_mapa = px.scatter_map(
            df, lat="latitude", lon="longitude",
            size="numero_matriculas", color="efeito_qualidade_pp",
            color_continuous_scale=DIV_BLUE_RED, range_color=[-lim, lim],
            size_max=34, zoom=5.9, hover_name="municipio",
            hover_data={
                "latitude": False, "longitude": False,
                "numero_matriculas": ":,", "iqem_real": ":.2f",
                "pre_real_pct": ":.3f", "efeito_qualidade_pp": ":.3f",
            },
            labels={
                "efeito_qualidade_pp": "Efeito qualidade (p.p.)",
                "numero_matriculas": "Matrículas",
                "iqem_real": "IQEM",
                "pre_real_pct": "Participação simulada (%)",
            },
            map_style="carto-positron", height=500,
            # com zoom explicito o plotly express nao calcula o centro sozinho
            center=dict(
                lat=(df["latitude"].min() + df["latitude"].max()) / 2,
                lon=(df["longitude"].min() + df["longitude"].max()) / 2,
            ),
        )
        fig_mapa.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="Efeito<br>qualidade<br>(p.p.)"),
        )
        st.plotly_chart(fig_mapa, width="stretch", config=PLOT_CFG)

    col_esq, col_dir = st.columns(2, gap="medium")

    with col_esq:
        with st.container(border=True):
            card_head(
                "Quem ganha e quem perde com a fórmula nova",
                "Participação de hoje (Sefaz-SP, fórmula antiga) contra a simulada. "
                "Acima da diagonal = ganharia participação. Escala logarítmica: as "
                "fatias vão de 0,003% a 13,8%.",
            )
            lo = min(df["pre_oficial_pct"].min(), df["pre_real_pct"].min()) * 0.7
            hi = max(df["pre_oficial_pct"].max(), df["pre_real_pct"].max()) * 1.4
            lim_d = df["diferenca_pp_simulado_vs_oficial"].abs().quantile(0.95)
            fig_quad = px.scatter(
                df, x="pre_oficial_pct", y="pre_real_pct",
                hover_name="municipio", size="numero_matriculas", size_max=26,
                color="diferenca_pp_simulado_vs_oficial",
                color_continuous_scale=DIV_BLUE_RED, range_color=[-lim_d, lim_d],
                log_x=True, log_y=True,
                labels={
                    "pre_oficial_pct": "Participação hoje (%)",
                    "pre_real_pct": "Participação simulada (%)",
                    "diferenca_pp_simulado_vs_oficial": "Δ p.p.",
                    "numero_matriculas": "Matrículas",
                },
                hover_data={"numero_matriculas": ":,", "pre_oficial_pct": ":.4f",
                            "pre_real_pct": ":.4f", "diferenca_pp_simulado_vs_oficial": ":.3f"},
                height=420,
            )
            fig_quad.update_traces(
                marker=dict(line=dict(width=0.8, color=AXIS), opacity=0.9)
            )
            fig_quad.add_trace(go.Scatter(
                x=[lo, hi], y=[lo, hi], mode="lines",
                line=dict(color=AXIS, width=1), showlegend=False, hoverinfo="skip",
            ))
            fig_quad.update_layout(
                xaxis=dict(range=[log10(lo), log10(hi)], showgrid=True, gridcolor=GRID),
                yaxis=dict(range=[log10(lo), log10(hi)]),
                coloraxis_colorbar=dict(title="Δ p.p."),
                margin=dict(l=4, r=4, t=4, b=4),
            )
            st.plotly_chart(fig_quad, width="stretch", config=PLOT_CFG)

    with col_dir:
        with st.container(border=True):
            card_head(
                "Onde a qualidade mais pesa na fatia",
                "As 8 redes em que o desempenho mais rende participação acima do porte "
                "e as 8 em que mais custa.",
            )
            # o maior efeito absoluto pode ser grande demais para a escala das outras
            # barras (Sao Paulo tem ~15% das matriculas do Estado); nesse caso ele sai
            # do grafico e vira uma nota, em vez de achatar as demais
            por_efeito = df.reindex(
                df["efeito_qualidade_pp"].abs().sort_values(ascending=False).index
            )
            maior, segundo = por_efeito.iloc[0], por_efeito.iloc[1]
            destacado = None
            base = df
            if abs(maior["efeito_qualidade_pp"]) > 3 * abs(segundo["efeito_qualidade_pp"]):
                destacado = maior
                base = df.drop(maior.name)
            extremos = pd.concat([
                base.nlargest(8, "efeito_qualidade_pp"),
                base.nsmallest(8, "efeito_qualidade_pp"),
            ]).sort_values("efeito_qualidade_pp")
            cores = [BLUE if v > 0 else CRITICAL for v in extremos["efeito_qualidade_pp"]]
            fig_rank = go.Figure(go.Bar(
                y=extremos["municipio"], x=extremos["efeito_qualidade_pp"],
                orientation="h", marker=dict(color=cores), width=0.62,
                customdata=extremos[["iqem_real", "pre_real_pct"]],
                hovertemplate=(
                    "%{y}<br>Efeito da qualidade: %{x:+.3f} p.p."
                    "<br>IQEM: %{customdata[0]:.2f}"
                    "<br>Participação simulada: %{customdata[1]:.3f}%<extra></extra>"
                ),
            ))
            fig_rank.add_vline(x=0, line_color=AXIS, line_width=1)
            fig_rank.update_layout(
                height=420,
                xaxis=dict(title="Efeito da qualidade na fatia (p.p.)",
                           showgrid=True, gridcolor=GRID),
                yaxis=dict(title=None, tickfont=dict(size=11, color=INK_2)),
                margin=dict(l=4, r=4, t=4, b=4),
            )
            st.plotly_chart(fig_rank, width="stretch", config=PLOT_CFG)
            if destacado is not None:
                share = destacado["numero_matriculas"] / df["numero_matriculas"].sum()
                st.caption(
                    f"Fora da escala: **{destacado['municipio']}**, "
                    f"{destacado['efeito_qualidade_pp']:+.3f} p.p. — concentra "
                    f"{share:.0%} das matrículas do Estado, então seu efeito é uma "
                    f"ordem de grandeza maior que o de qualquer outro município."
                )

    section(
        "Distribuição de cada métrica",
        f"A linha vermelha marca a média dos {N} municípios simulados. Não existe meta "
        "oficial fixa — o ICMS Educacional é uma fatia proporcional, não um limiar de "
        "aprovação.",
    )
    with st.container(border=True):
        metric_cols = st.columns(len(METRICAS), gap="medium")
        for col, (chave, info) in zip(metric_cols, METRICAS.items()):
            with col:
                st.markdown(
                    f"<div class='mini'><h4>{info['label']}</h4><p>{info['peso']}</p>"
                    f"<span class='avg'>média {info['fmt'].format(medias[chave])}</span></div>",
                    unsafe_allow_html=True,
                )
                fig_hist = px.histogram(df, x=chave, nbins=28, height=150)
                fig_hist.update_traces(marker=dict(color=BLUE_SOFT, line=dict(width=0)))
                fig_hist.add_vline(x=medias[chave], line_dash="solid",
                                   line_color=CRITICAL, line_width=1.5)
                fig_hist.update_layout(
                    margin=dict(l=0, r=0, t=4, b=0), bargap=0.08, showlegend=False,
                    xaxis=dict(title=None, showgrid=False, tickfont=dict(size=10)),
                    yaxis=dict(visible=False, showgrid=False),
                )
                st.plotly_chart(fig_hist, width="stretch", config=PLOT_CFG)

# ===========================================================================
# ABA 2 - POR MUNICIPIO
# ===========================================================================
with aba_municipio:
    nomes = sorted(df["municipio"])
    municipio_sel = st.selectbox(
        "Município", nomes, width=380,
        index=nomes.index("Cotia") if "Cotia" in nomes else 0,
    )
    linha = df[df["municipio"] == municipio_sel].iloc[0]

    ranking_pos = int((df["efeito_qualidade_pp"] > linha["efeito_qualidade_pp"]).sum()) + 1

    m1, m2, m3, m4 = st.columns(4, gap="medium")
    m1.metric("IQEM simulado", f"{linha['iqem_real']:.2f}",
              delta=f"{linha['iqem_real'] - df['iqem_real'].mean():+.2f} vs média",
              help="Escala 0–10")
    m2.metric("Matrículas", f"{int(linha['numero_matriculas']):,}".replace(",", "."),
              help="Rede municipal, anos iniciais do Ensino Fundamental")
    m3.metric("Participação simulada", f"{linha['pre_real_pct']:.3f}%",
              delta=f"{linha['diferenca_pp_simulado_vs_oficial']:+.3f} p.p. vs hoje",
              help="Fatia do município na cota-parte educacional sob a fórmula nova")
    m4.metric(f"Efeito da qualidade · {ranking_pos}º de {N}",
              f"{linha['efeito_qualidade_pp']:+.3f} p.p.",
              help="Quanto o desempenho da rede rende (+) ou custa (−) em relação à "
                   "fatia que o município teria num rateio puramente por matrículas. "
                   "1º = maior ganho")

    # -----------------------------------------------------------------------
    # PARCELA REPASSADA x PARCELA CHEIA (em R$)
    # -----------------------------------------------------------------------
    section(
        f"Quanto {municipio_sel} recebe pelo critério educação — e quanto receberia no máximo",
        "A parcela cheia é o cenário individual: só este município atinge os índices "
        "máximos, os demais ficam nos valores reais e o rateio é recalculado.",
    )

    r1, r2, r3, r4 = st.columns(4, gap="medium")
    r1.metric(
        "Parcela repassada", brl(linha[COL_REPASSADA], 2),
        help=f"peso do critério ({PESO:.0%}) × PRE ({linha['pre_real_pct']:.4f}%) × "
             f"ICMS do período ({brl_curto(ICMS_ESTADO)}).",
    )
    r2.metric(
        "Parcela cheia", brl(linha[COL_CHEIA], 2),
        help=f"Mesmo cálculo com o PRE do cenário máximo individual "
             f"({linha['pre_cheia_pct']:.4f}%).",
    )
    r3.metric(
        "Diferença", brl(linha[COL_DIFERENCA], 2),
        delta=f"{linha['diferenca_pct']:+.1f}%",
        help="Quanto o município deixa de receber no período por não estar no "
             "desempenho máximo.",
    )
    if pd.notna(linha[COL_ICMS_MUNI]) and linha[COL_ICMS_MUNI]:
        r4.metric(
            "Peso no ICMS total da cidade",
            f"{linha[COL_REPASSADA] / linha[COL_ICMS_MUNI]:.2%}",
            help=f"A parcela educacional dentro de tudo o que {municipio_sel} recebeu de "
                 f"ICMS no período ({brl_curto(linha[COL_ICMS_MUNI])}, todos os critérios "
                 "do IPM somados).",
        )
    else:
        r4.metric("Peso no ICMS total da cidade", "—",
                  help="Repasse total do município não encontrado para este período.")

    col_cad, col_barra = st.columns([1.15, 1], gap="medium")

    with col_cad:
        with st.container(border=True):
            card_head("A cadeia do cálculo, passo a passo",
                      "Os mesmos números acima, na ordem em que a lei os aplica.")
            st.markdown(
                f"""
<div class='cadeia'><ol>
  <li><span class='passo'>Componentes →</span> IQEM =
      <b>{linha['iqem_real']:.3f}</b> <span class='passo'>(0,40·IQA + 0,40·IQI +
      0,10·ISE + 0,10·PATI)</span></li>
  <li><span class='passo'>× matrículas, sobre o total do Estado →</span> PRE =
      <b>{linha['pre_real_pct']:.4f}%</b> <span class='passo'>do critério educação</span></li>
  <li><span class='passo'>× peso do critério no IPM ({PESO:.0%}) →</span> contribuição no IPM =
      <b>{linha['contribuicao_ipm_pct']:.4f}%</b></li>
  <li><span class='passo'>× ICMS repassado no período ({brl_curto(ICMS_ESTADO)}) →</span>
      parcela repassada = <b>{brl(linha[COL_REPASSADA], 2)}</b></li>
  <li><span class='passo'>No cenário máximo individual (PRE
      {linha['pre_cheia_pct']:.4f}%) →</span> parcela cheia =
      <b>{brl(linha[COL_CHEIA], 2)}</b>, diferença de
      <b>{brl(linha[COL_DIFERENCA], 2)}</b> ({linha['diferenca_pct']:+.1f}%)</li>
</ol></div>
""",
                unsafe_allow_html=True,
            )

    with col_barra:
        with st.container(border=True):
            card_head("Repassada × cheia",
                      f"Em reais, no período {periodo_sel}.")
            fig_reais = go.Figure()
            fig_reais.add_trace(go.Bar(
                y=["Parcela cheia", "Parcela repassada"],
                x=[linha[COL_CHEIA], linha[COL_REPASSADA]],
                orientation="h", width=0.5,
                marker=dict(color=[BLUE_SOFT, BLUE]),
                text=[brl_curto(linha[COL_CHEIA]), brl_curto(linha[COL_REPASSADA])],
                textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
            ))
            fig_reais.update_layout(
                height=200,
                xaxis=dict(title=None, showgrid=True, gridcolor=GRID,
                           range=[0, float(linha[COL_CHEIA]) * 1.28]),
                yaxis=dict(title=None, tickfont=dict(size=11, color=INK_2)),
                margin=dict(l=4, r=4, t=4, b=4), showlegend=False,
            )
            st.plotly_chart(fig_reais, width="stretch", config=PLOT_CFG)
            st.caption(
                f"A diferença de {brl_curto(linha[COL_DIFERENCA])} é o que o desempenho "
                f"máximo acrescentaria à fatia de {municipio_sel} neste período — "
                "mantendo matrícula e ISE reais."
            )

    section(
        "Cada métrica contra a média do Estado",
        "O delta compara o município com a média dos municípios simulados.",
    )
    cols = st.columns(len(METRICAS), gap="medium")
    for col, (chave, info) in zip(cols, METRICAS.items()):
        delta = (linha[chave] - medias[chave]) * info["dmult"]
        if info["melhor"] == "neutro":
            delta_color = "off"
        else:
            delta_color = "inverse" if info["melhor"] == "menor" else "normal"
        col.metric(
            info["label"], info["fmt"].format(linha[chave]),
            delta=info["dfmt"].format(delta), delta_color=delta_color,
            help=f"Peso: {info['peso']} · média do Estado: {info['fmt'].format(medias[chave])}",
        )
    st.caption(
        "O ISE não tem 'melhor' nem 'pior': mede o quanto a rede atende alunos "
        "vulneráveis — maior significa mais vulnerabilidade e mais peso no IQEM. "
        "É critério de equidade, não de desempenho."
    )

    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        with st.container(border=True):
            card_head(
                "Composição do IQEM",
                "IQEM = 0,40·IQA + 0,40·IQI + 0,10·ISE + 0,10·PATI. "
                "IQA e IQI somam nota e evolução.",
            )
            nota_evolucao = linha["ideb_anos_iniciais_proxy"] + linha["evolucao_ideb_proxy"]
            partes = [
                ("IQA · alfabetização (40%)", 0.40 * nota_evolucao, BLUE_DEEP),
                ("IQI · anos iniciais (40%)", 0.40 * nota_evolucao, BLUE),
                ("ISE · equidade (10%)", 0.10 * linha["ise_vulnerabilidade"], "#6da7ec"),
                ("PATI · tempo integral (10%)", 0.10 * linha["pati"], BLUE_SOFT),
            ]
            fig_iqem = go.Figure()
            for nome, valor, cor in partes:
                fig_iqem.add_trace(go.Bar(
                    x=[valor], y=["IQEM"], orientation="h", name=nome,
                    marker=dict(color=cor, line=dict(color=SURFACE, width=2)),
                    hovertemplate=f"{nome}<br>%{{x:.3f}} pontos<extra></extra>",
                ))
            fig_iqem.update_layout(
                barmode="stack", height=200,
                xaxis=dict(title="Contribuição para o IQEM (0–10)",
                           showgrid=True, gridcolor=GRID, range=[0, 10]),
                yaxis=dict(visible=False),
                legend=dict(orientation="h", y=-0.42, x=0, font=dict(size=10)),
                margin=dict(l=4, r=4, t=4, b=4),
            )
            st.plotly_chart(fig_iqem, width="stretch", config=PLOT_CFG)

    with col_b:
        with st.container(border=True):
            card_head(
                "Participação na cota-parte",
                "A fórmula em vigor hoje, a simulada pela fórmula nova e a fatia que "
                "caberia num rateio só por matrículas (cenário de desempenho máximo "
                "para todos).",
            )
            cenarios = [
                ("Só por matrículas", linha["pre_maxima_pct"], BLUE_SOFT),
                ("Simulada · fórmula nova", linha["pre_real_pct"], BLUE),
                ("Oficial hoje · fórmula antiga", linha["pre_oficial_pct"], NEUTRAL),
            ]
            fig_part = go.Figure(go.Bar(
                y=[c[0] for c in cenarios], x=[c[1] for c in cenarios],
                orientation="h", marker=dict(color=[c[2] for c in cenarios]),
                text=[f"{c[1]:.3f}%" for c in cenarios], textposition="outside",
                textfont=dict(size=11, color=INK_2), width=0.58,
                hovertemplate="%{y}<br>%{x:.4f}%<extra></extra>",
            ))
            fig_part.update_layout(
                height=200,
                xaxis=dict(title="Participação (%)", showgrid=True, gridcolor=GRID,
                           range=[0, max(c[1] for c in cenarios) * 1.25]),
                yaxis=dict(title=None, tickfont=dict(size=11, color=INK_2)),
                margin=dict(l=4, r=4, t=4, b=4),
            )
            st.plotly_chart(fig_part, width="stretch", config=PLOT_CFG)

    diff_regra = linha["diferenca_pp_simulado_vs_oficial"]
    sentido = "ganharia" if diff_regra > 0 else "perderia"
    efeito = linha["efeito_qualidade_pp"]
    verbo = "rende" if efeito > 0 else "custa"
    st.markdown(
        f"<div class='note'>Com a fórmula nova (100% por qualidade), "
        f"<b>{municipio_sel} {sentido} {abs(diff_regra):.3f} pontos percentuais</b> "
        f"de participação em relação à fórmula antiga, hoje em vigor. Em relação a um "
        f"rateio puramente por matrículas, a qualidade da rede <b>{verbo} "
        f"{abs(efeito):.3f} p.p.</b> — o {ranking_pos}º maior ganho entre os {N} "
        f"municípios simulados.</div>",
        unsafe_allow_html=True,
    )

# ===========================================================================
# ABA 3 - TABELA COMPLETA
# ===========================================================================
with aba_tabela:
    section("Todos os municípios simulados",
            "Ordenado pelo efeito da qualidade na fatia. Use a busca para filtrar.")

    busca = st.text_input("Buscar município", placeholder="Buscar município...",
                          label_visibility="collapsed", width=380)
    dados_tabela = df
    if busca:
        # regex=False: sem isso um "[" digitado na busca quebra a pagina inteira,
        # e um padrao patologico vira um DoS trivial num app publico
        dados_tabela = dados_tabela[
            dados_tabela["municipio"].str.contains(
                busca, case=False, na=False, regex=False
            )
        ]

    colunas_exibir = [
        "municipio", "numero_matriculas", "ideb_anos_iniciais_proxy",
        "taxa_reprovacao_pct", "taxa_abandono_pct", "pati_pct", "ise_vulnerabilidade",
        "iqem_real", "pre_oficial_pct", "pre_real_pct", "pre_maxima_pct",
        "efeito_qualidade_pp",
        "contribuicao_ipm_pct", COL_REPASSADA, COL_CHEIA, COL_DIFERENCA, "diferenca_pct",
    ]
    visao = dados_tabela[colunas_exibir].sort_values(
        COL_DIFERENCA, ascending=False
    )
    st.caption(
        f"{len(visao)} de {N} municípios · valores em R$ referentes a {periodo_sel} "
        f"({_nota_periodo}), peso de {PESO:.0%}, escala "
        f"{'líquida' if escala_sel == 'liquido' else 'bruta'}"
    )
    st.dataframe(
        visao, width="stretch", height=520, hide_index=True,
        column_config={
            "municipio": st.column_config.TextColumn("Município", pinned=True),
            "numero_matriculas": st.column_config.NumberColumn("Matrículas", format="%d"),
            "ideb_anos_iniciais_proxy": st.column_config.NumberColumn("IDEB proxy", format="%.2f"),
            "taxa_reprovacao_pct": st.column_config.NumberColumn("Reprov. %", format="%.1f"),
            "taxa_abandono_pct": st.column_config.NumberColumn("Aband. %", format="%.1f"),
            "pati_pct": st.column_config.NumberColumn("PATI %", format="%.1f"),
            "ise_vulnerabilidade": st.column_config.NumberColumn("ISE vuln.", format="%.2f"),
            "iqem_real": st.column_config.ProgressColumn(
                "IQEM", format="%.2f", min_value=0, max_value=10
            ),
            "pre_oficial_pct": st.column_config.NumberColumn("Part. hoje %", format="%.4f"),
            "pre_real_pct": st.column_config.NumberColumn("Part. simulada %", format="%.4f"),
            "pre_maxima_pct": st.column_config.NumberColumn(
                "Part. só por matrículas %", format="%.4f"
            ),
            "efeito_qualidade_pp": st.column_config.NumberColumn(
                "Efeito qualidade p.p.", format="%+.3f",
                help="Positivo = a qualidade da rede rende fatia acima do porte",
            ),
            "contribuicao_ipm_pct": st.column_config.NumberColumn(
                "Contrib. no IPM %", format="%.4f",
                help=f"Peso do critério educação ({PESO:.0%}) × participação no critério. "
                     "Somada entre todos os municípios, dá o próprio peso do critério.",
            ),
            COL_REPASSADA: st.column_config.NumberColumn(
                "Parcela repassada R$", format="localized",
                help="Contribuição no IPM × ICMS repassado aos municípios no período.",
            ),
            COL_CHEIA: st.column_config.NumberColumn(
                "Parcela cheia R$", format="localized",
                help="Cenário individual: só este município no máximo, os demais reais. "
                     "Coluna não somável.",
            ),
            COL_DIFERENCA: st.column_config.NumberColumn(
                "Diferença R$", format="localized",
                help="Parcela cheia − parcela repassada.",
            ),
            "diferenca_pct": st.column_config.NumberColumn(
                "Diferença %", format="%+.1f",
                help="Diferença sobre a própria parcela repassada.",
            ),
        },
    )
    st.download_button(
        "Baixar CSV filtrado", visao.to_csv(index=False).encode("utf-8"),
        file_name=f"painel_icms_sp_{periodo_sel}_{regime_sel}_{escala_sel}.csv",
        mime="text/csv",
    )
    st.caption(
        "O CSV completo, com todos os períodos e regimes de peso lado a lado, é o "
        "`data/processed/painel_icms_sp.csv` do repositório."
    )

# ===========================================================================
# ABA 4 - METODOLOGIA
# ===========================================================================
with aba_metodologia:
    section("O que é dado real e o que é simulação",
            "A separação entre fonte oficial e aproximação está documentada campo a campo.")

    col_real, col_proxy = st.columns(2, gap="medium")
    with col_real:
        st.markdown(
            """
<div class='meth'>
  <h3 style='color:#006300'>Dado real e oficial</h3>
  <div class='tag'>Fontes públicas, sem transformação além da consolidação</div>
  <ul>
    <li><b>Reprovação e abandono</b> — INEP, Taxas de Rendimento Escolar 2024,
        rede municipal (642 de 645 municípios)</li>
    <li><b>PATI</b> — INEP, Sinopse Estatística do Censo Escolar 2025,
        rede municipal (645 de 645)</li>
    <li><b>Coordenadas</b> — IBGE via <code>geobr</code> (645 de 645)</li>
    <li><b>Participação oficial de hoje</b> — Sefaz-SP, IPM / Cota Parte Educação
        (645 de 645, fórmula antiga)</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )
    with col_proxy:
        st.markdown(
            """
<div class='meth'>
  <h3 style='color:#8a5d00'>Proxy e simulação documentada</h3>
  <div class='tag'>Aproximações necessárias — cada uma com sua justificativa</div>
  <ul>
    <li><b>IQA e IQI</b> — a lei exige SARESP da rede municipal (2º e 5º ano), que não
        existe em dados abertos. Usamos IDEB/SAEB (INEP, federal) como aproximação.</li>
    <li><b>ISE</b> — usamos o Inse (INEP), normalizado dentro do universo de SP;
        a fórmula exata do Anexo Único está publicada como imagem.</li>
    <li><b>Garantia de fluxo</b> — assumida sempre cumprida, sem limiar oficial legível.</li>
    <li><b>Cenário máximo</b> — nota 10 e 100% de tempo integral para <i>todos</i> os
        municípios, mantendo matrícula e ISE reais. Definição nossa, não oficial.
        Como o rateio é proporcional e o IQEM se iguala, esse cenário equivale a
        distribuir a cota-parte só por matrículas — por isso a diferença contra a
        participação simulada isola o efeito da qualidade, e soma zero no Estado.</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='rule'>", unsafe_allow_html=True)

    section("Como o valor em R$ é obtido",
            "A participação relativa (PRE) vira dinheiro em duas etapas: o peso do "
            "critério educação dentro do IPM e o ICMS repassado no período.")

    col_cadeia, col_pesos = st.columns(2, gap="medium")
    with col_cadeia:
        st.markdown(
            f"""
<div class='meth'>
  <h3 style='color:#006300'>Fonte do valor e escala</h3>
  <div class='tag'>Sefaz-SP · Repasse de Tributos a Municípios</div>
  <ul>
    <li><b>Valor coletado município a município</b>, mês a mês, e somado para o
        Estado. Nada é estimado: o total do período é a soma dos 645 municípios.</li>
    <li><b>Líquido</b> é o que a Sefaz publica — já descontados os 20% retidos para o
        Fundeb (Lei 11.494/2007, desde jan/2009). É o dinheiro que entra no caixa
        do município.</li>
    <li><b>Bruto</b> é esse valor ÷ 0,80: a cota-parte de 25% do ICMS
        (art. 158, IV da Constituição) antes da retenção. As duas escalas estão
        no painel, rotuladas — nenhuma delas é estimativa.</li>
    <li><b>Ano corrente</b> traz o acumulado até o último mês publicado
        ({MESES_NOME[MESES_PUB]} de {periodo_sel}, {MESES_PUB} meses), não um ano
        projetado.</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )
    with col_pesos:
        st.markdown(
            """
<div class='meth'>
  <h3 style='color:#006300'>Peso do critério educação no IPM</h3>
  <div class='tag'>Lei 17.575/2022, art. 2º, I — inciso X do art. 1º da Lei 3.201/1981</div>
  <ul>
    <li>A lei escalona o critério: <b>10%</b> no ano-base 2023, <b>11%</b> em 2024,
        <b>12%</b> em 2025 e <b>13%</b> a partir de 2026. Em paralelo, o critério
        população cai 3% → 2% → 1% → extinto.</li>
    <li><b>Conferido contra o dado oficial</b>, não só lido na lei: a decomposição do
        IPM publicado pela Sefaz recupera os pesos de todos os critérios com erro da
        ordem de 1&nbsp;×&nbsp;10⁻⁶ ponto percentual — 11% em 2024 e 12% em 2025,
        exatamente como na lei.</li>
    <li>O IPM de um ano-base rege os repasses de <b>dois anos depois</b>. Logo os 13%
        valem para o repasse de <b>2028</b> — o mesmo exercício em que a fórmula nova
        do IQEM começa a valer.</li>
    <li>Os demais pesos vigentes: 74% valor adicionado, 5% receita tributária, 3% área
        cultivada, 2% igual para todos, 1% área protegida, 1% vegetação nativa,
        0,5% área inundada, 0,5% resíduos sólidos.</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
<div class='note' style='margin-top:1rem'>
  <b>Três ressalvas para citar ao apresentar.</b>
  <b>1.</b> A fórmula do IQEM simulada aqui só vale a partir do ano-base 2026
  (repasse em 2028); aplicá-la ao dinheiro de {periodo_sel} é um contrafactual —
  mostra como aquele valor teria sido dividido sob a regra nova, não o que aconteceu.
  <b>2.</b> A parcela cheia não é somável: cada uma é um cenário em que só aquele
  município atinge o máximo, então a soma da coluna não descreve cenário nenhum.
  <b>3.</b> Os {N} municípios simulados dividem 100% do bolo do critério; na fonte
  oficial, os {645 - N} que ficaram fora por falta de dado educacional detêm
  {FORA_DO_PAINEL_PCT:.2f}% da cota-parte educação.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("<hr class='rule'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='note'>O detalhamento completo, com trechos de lei e links das "
        "fontes, está em <b>LIMITACOES_METODOLOGICAS.md</b> no repositório do "
        "projeto.</div>",
        unsafe_allow_html=True,
    )
