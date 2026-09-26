# -*- coding: utf-8 -*-
"""
Consolida as 4 fontes coletadas (INEP: rendimento, IDEB/SAEB, Inse, Sinopse)
por codigo_ibge, aplica a formula do IQEM (calculadora_icms_vaar_sp.py) para
os 645 municipios de SP, e calcula:

  - IQEM real (com os indicadores tal como coletados)
  - PRE real (participacao no rateio da cota-parte educacao, relativa entre
    os municipios processados)
  - IQEM maximo hipotetico (simulando desempenho maximo controlavel por
    politica publica - ver MAPEAMENTO DE CAMPOS abaixo)
  - PRE maxima hipotetica e a DIFERENCA de participacao (pontos percentuais)
    entre o cenario real e o cenario de desempenho maximo
  - Comparacao contra o IPM REAL e OFICIAL da Sefaz-SP (coluna "Cota Parte
    Educacao", ver scripts/coleta_ipm_sefaz.py) - essa e' a fatia que os
    municipios recebem HOJE, pela formula ANTIGA (metade qualidade, metade
    porte). A diferenca contra o nosso pre_real simulado (formula nova,
    100% qualidade) mostra o IMPACTO DA MUDANCA DE REGRA, nao um erro de
    calculo - documentar isso claramente ao apresentar.

Isso responde a pergunta central do projeto: "quanto cada municipio recebe
vs. quanto poderia ter recebido se tivesse cumprido todas as metas".

===========================================================================
CADEIA COMPLETA ATE O VALOR EM R$ (implementada em 26/09/2026)
===========================================================================
   componentes (IQA, IQI, ISE, PATI)
     -> IQEM                                       [iqem_2025]
     -> PRE = participacao no criterio educacao     [participacao_rateio]
     -> x peso do criterio educacao no IPM          [peso_criterio_educacao]
        = contribuicao do municipio no IPM via educacao
     -> x ICMS repassado aos municipios no periodo  [coleta_repasse_icms_sefaz]
        = parcela repassada em R$
   e, em paralelo, a parcela CHEIA (municipio no maximo, os outros reais)
     -> diferenca em R$ e em %

DUAS DIMENSOES DE CENARIO, materializadas como LINHAS do painel (o CSV e'
longo: uma linha por municipio x periodo x regime):

  periodo = ano civil do repasse (2025 fechado, 2026 acumulado ate o ultimo
    mes publicado). O ano-base do IPM que rege um ano civil e' ano_civil - 2.

  regime  = 'vigente' usa o peso do criterio educacao realmente em vigor
    naquele ano-base (10% em 2023, 11% em 2024, 12% em 2025); 'pleno' usa os
    13% que a lei fixa a partir do ano-base 2026. O regime pleno aplicado a um
    periodo passado e' um CENARIO ("quanto teria sido com a regra madura"),
    nao um valor historico - o painel rotula as duas leituras.

E DUAS ESCALAS DE VALOR, materializadas como COLUNAS:
  liquido = exatamente o que a Sefaz publica (ja descontados os 20% do
    FUNDEB, Lei 11.494/2007). E' o dinheiro que entra no caixa do municipio.
  bruto   = liquido / 0,80, a quota-parte de 25% antes da retencao.
Ver scripts/coleta_repasse_icms_sefaz.py.

RESSALVA IMPORTANTE SOBRE O CASAMENTO DE PERIODOS: a formula do IQEM que
simulamos aqui (Lei 18.381/2025, 100% qualidade) so vale a partir do
ano-base 2026, com repasse em 2028. Aplicar essa formula ao dinheiro de
2025/2026 e' deliberadamente um CONTRAFACTUAL - "como o dinheiro daquele
periodo teria sido dividido se a regra nova valesse" - e nao uma
reconstituicao do que aconteceu. Isso tem que ser dito ao apresentar.

===========================================================================
IMPORTANTE - LEIA JUNTO COM LIMITACOES_METODOLOGICAS.md
===========================================================================
Alem do valor em R$, este script produz a PARTICIPACAO RELATIVA no rateio
(PRE, um numero entre 0 e 1 que soma 1 entre os municipios do universo
processado). A participacao relativa continua sendo o resultado mais
robusto: ela nao depende de casar periodos nem de escolher liquido/bruto.

UNIVERSO: o painel cobre os municipios com todos os dados educacionais
disponiveis (618 dos 645). Como o PRE e' renormalizado nesse universo, os
618 dividem entre si 100% do bolo educacional - os 27 ausentes ficam com
zero. A coluna `cota_parte_educacao_oficial_fora_do_painel_pct` registra o
tamanho dessa distorcao medido na fonte oficial (Sefaz), para nao deixar a
premissa implicita.

MAPEAMENTO DE CAMPOS (dado coletado -> campo da formula) e suas limitacoes:
  - taxa_reprovacao / taxa_abandono   <- INEP Taxas de Rendimento (REAL,
    rede Municipal, Anos Iniciais). Reportado na tabela final, mas o limiar
    oficial de "garantia de fluxo" (Anexo Unico, imagem) nao foi encontrado
    - ver garantia_fluxo abaixo.
  - nota_iqa = nota_iqi               <- IDEB/SAEB Anos Iniciais (PROXY -
    nao separa 2o/5o ano; ver LIMITACOES_METODOLOGICAS.md)
  - evolucao_iqa = evolucao_iqi       <- delta do IDEB entre as 2 ultimas
    edicoes (PROXY, mesma limitacao acima)
  - indice_socioeconomico (ISE)       <- Inse normalizado 0-1 dentro de SP
    (PROXY - normalizacao nossa, nao confirmada contra o Anexo Unico)
  - percentual_tempo_integral (PATI)  <- Sinopse Censo Escolar (REAL,
    matricula tempo integral / matricula total, rede Municipal)
  - numero_matriculas                 <- Sinopse Censo Escolar, matricula
    total Anos Iniciais rede Municipal (REAL)
  - garantia_fluxo                    <- NAO TEMOS o limiar oficial (Anexo
    Unico e' imagem). ASSUMIMOS True para todos os municipios (ninguem e'
    zerado pelo gate). Isso e' uma simplificacao explicita: na pratica,
    qualquer municipio com taxa de abandono/reprovacao muito alta deveria
    provavelmente falhar este gate e ser zerado - o valor de IF calculado
    e' reportado na tabela final para permitir revisao manual/ajuste do
    limiar quando a formula oficial for confirmada.

CENARIO "DESEMPENHO MAXIMO" (para calcular quanto o municipio deixou de
ganhar em participacao) - definicao adotada, TAMBEM uma escolha nossa:
  - nota_iqa = nota_iqi = 10 (nota maxima da escala IDEB/IDESP)
  - evolucao_iqa = evolucao_iqi = MESMO valor real do municipio (corrigido em
    26/09/2026; antes eram zerados). O IQA e' NOTA + EVOLUCAO, soma sem teto,
    entao "nota 10 com evolucao zero" NAO e' o maximo alcancavel: zerando a
    evolucao, o teto de quem ja evoluiu muito cai ABAIXO do real (o caso de
    Santa Maria da Serra, 12,0 real contra 10,0 "maximo"). A evolucao e' dado
    ja realizado, como o ISE e as matriculas, e nao uma meta que a gestao
    "atinge" no cenario. PENDENCIA: se o Anexo Unico impuser teto ao IQA
    (p.ex. IQA <= 10), esta escolha muda.
  - indice_socioeconomico = MESMO valor real do municipio (o ISE reflete a
    composicao socioeconomica dos alunos atendidos, nao e' uma meta de
    politica publica que o municipio "cumpre" ou nao)
  - percentual_tempo_integral = 1.0 (100% das matriculas em tempo integral
    - essa sim e' uma meta de politica publica controlavel)
  - numero_matriculas = mesmo valor real (o "porte" nao muda no cenario
    hipotetico, so o desempenho)
===========================================================================
"""

import os
import re
import sys
import unicodedata

import pandas as pd

from calculadora_icms_vaar_sp import (
    IndicadoresMunicipio,
    PESO_CRITERIO_EDUCACAO_REGIME_PLENO,
    ano_base_do_repasse,
    contribuicao_ipm_educacao,
    iqem_2025,
    participacao_com_um_no_maximo,
    participacao_rateio,
    peso_criterio_educacao,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from coleta_repasse_icms_sefaz import FUNDEB_RETENCAO, resumir_por_ano  # noqa: E402

# Anos civis de repasse que entram no painel. Precisam existir como
# data/raw/repasse_icms_sp_{ano}.csv (rode scripts/coleta_repasse_icms_sefaz.py).
PERIODOS_PADRAO = [2025, 2026]

# 'vigente' = peso do criterio educacao realmente em vigor no ano-base do
# periodo; 'pleno' = os 13% do regime permanente da lei. Ver docstring do modulo.
REGIMES = ["vigente", "pleno"]


# Grafias divergentes entre fontes oficiais, todas conferidas uma a uma: a
# esquerda esta a forma usada pelo sistema de repasse da Sefaz-SP, a direita a
# do INEP/IBGE (que e' a que usamos como canonica). Nao sao municipios
# diferentes nem chutes de similaridade - sao variantes do mesmo nome, e no
# caso de Embu e' o nome antigo (a cidade passou a se chamar Embu das Artes
# em 2011, mas o sistema da Sefaz ainda usa "Embu").
ALIASES_MUNICIPIO = {
    "BADY BASSIT": "BADY BASSITT",
    "EMBU": "EMBU DAS ARTES",
    "LUIZ ANTONIO": "LUIS ANTONIO",
    "SANTA ROSA DO VITERBO": "SANTA ROSA DE VITERBO",
    "SANTANA DO PARNAIBA": "SANTANA DE PARNAIBA",
    "SANTO ANTONIO DA POSSE": "SANTO ANTONIO DE POSSE",
    "SUD MENUCCI": "SUD MENNUCCI",
}


def _normalizar_nome_municipio(nome: str) -> str:
    s = str(nome).upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "").replace("’", "")
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES_MUNICIPIO.get(s, s)


def carregar_fontes() -> pd.DataFrame:
    rendimento = pd.read_csv("data/raw/taxas_rendimento_sp_municipal_2024.csv")
    ideb = pd.read_csv("data/raw/ideb_saeb_sp_municipal.csv")
    ise = pd.read_csv("data/raw/ise_sp_municipal.csv")
    pati = pd.read_csv("data/raw/pati_sp_municipal.csv")

    for df in (rendimento, ideb, ise, pati):
        df["codigo_ibge"] = df["codigo_ibge"].astype(float).astype(int)

    base = pati[["codigo_ibge", "municipio", "matriculas_anos_iniciais_municipal", "pati"]]
    base = base.merge(
        rendimento[["codigo_ibge", "taxa_reprovacao_anos_iniciais", "taxa_abandono_anos_iniciais"]],
        on="codigo_ibge", how="left",
    )
    base = base.merge(
        ideb[["codigo_ibge", "ideb_anos_iniciais", "evolucao_ideb"]],
        on="codigo_ibge", how="left",
    )
    base = base.merge(
        ise[["codigo_ibge", "ise_vulnerabilidade_normalizada"]],
        on="codigo_ibge", how="left",
    )
    return base


def construir_municipios(df: pd.DataFrame) -> list[IndicadoresMunicipio]:
    campos_obrigatorios = [
        "ideb_anos_iniciais", "evolucao_ideb", "ise_vulnerabilidade_normalizada",
        "pati", "matriculas_anos_iniciais_municipal",
        "taxa_reprovacao_anos_iniciais", "taxa_abandono_anos_iniciais",
    ]
    municipios = []
    descartados = 0
    for _, row in df.iterrows():
        if row[campos_obrigatorios].isna().any():
            descartados += 1
            continue  # sem algum dado obrigatorio (ver avisos dos coletores)
        municipios.append(IndicadoresMunicipio(
            nome=row["municipio"],
            taxa_reprovacao=(row["taxa_reprovacao_anos_iniciais"] or 0) / 100,
            taxa_abandono=(row["taxa_abandono_anos_iniciais"] or 0) / 100,
            garantia_fluxo=True,  # assumido - ver docstring do modulo
            nota_iqa=row["ideb_anos_iniciais"],
            evolucao_iqa=row["evolucao_ideb"],
            nota_iqi=row["ideb_anos_iniciais"],
            evolucao_iqi=row["evolucao_ideb"],
            indice_socioeconomico=row["ise_vulnerabilidade_normalizada"],
            percentual_tempo_integral=row["pati"],
            numero_matriculas=row["matriculas_anos_iniciais_municipal"],
        ))
    if descartados:
        print(f"Aviso: {descartados} municipios descartados por falta de algum dado obrigatorio.")
    return municipios


def cenario_maximo(m: IndicadoresMunicipio) -> IndicadoresMunicipio:
    """Mesmo municipio, com desempenho maximo controlavel - ver docstring do modulo.

    A EVOLUCAO e' mantida no valor REAL, e nao zerada (mudanca de 26/09/2026).
    Motivo: o IQA da formula e' NOTA + EVOLUCAO, uma soma sem teto. Zerando a
    evolucao, o "maximo" de um municipio que ja evoluiu muito fica ABAIXO do
    real - Santa Maria da Serra tinha 9,1 + 2,9 = 12,0 no real contra 10,0 + 0,0
    = 10,0 no "maximo", e aparecia no painel recebendo R$ 310 mil a MENOS por
    melhorar. Com a evolucao real preservada ela vai a 10,0 + 2,9 = 12,9, acima
    do real, como um teto deve ser.

    A evolucao entra aqui na mesma categoria do ISE e do numero de matriculas:
    dado ja realizado, que a gestao nao "atinge" como meta no cenario. Os itens
    que a gestao controla (notas, reprovacao, abandono, tempo integral) e' que
    vao ao maximo.

    PENDENCIA: se o Anexo Unico da Lei 17.575/2022 impuser teto ao IQA (por
    exemplo, IQA <= 10), esta escolha muda - ver LIMITACOES_METODOLOGICAS.md.
    """
    return IndicadoresMunicipio(
        nome=m.nome,
        taxa_reprovacao=0.0,
        taxa_abandono=0.0,
        garantia_fluxo=True,
        nota_iqa=10.0,
        evolucao_iqa=m.evolucao_iqa,
        nota_iqi=10.0,
        evolucao_iqi=m.evolucao_iqi,
        indice_socioeconomico=m.indice_socioeconomico,
        percentual_tempo_integral=1.0,
        numero_matriculas=m.numero_matriculas,
    )


def calcular_painel() -> pd.DataFrame:
    df = carregar_fontes()
    municipios = construir_municipios(df)
    municipios_max = [cenario_maximo(m) for m in municipios]

    pre_real = participacao_rateio(municipios)
    pre_maxima = participacao_rateio(municipios_max)
    # Cenario INDIVIDUAL: um municipio de cada vez no maximo, os outros reais.
    # E' esse que responde "quanto ESTE municipio receberia se batesse as
    # metas" - o coletivo acima serve a outra pergunta (isolar o efeito da
    # qualidade), ver docstring de participacao_com_um_no_maximo.
    pre_cheia = participacao_com_um_no_maximo(municipios, cenario_maximo)

    linhas = []
    for m in municipios:
        linhas.append({
            "municipio": m.nome,
            "numero_matriculas": m.numero_matriculas,
            "taxa_reprovacao_pct": m.taxa_reprovacao * 100,
            "taxa_abandono_pct": m.taxa_abandono * 100,
            "ideb_anos_iniciais_proxy": m.nota_iqa,
            "evolucao_ideb_proxy": m.evolucao_iqa,
            "ise_vulnerabilidade": m.indice_socioeconomico,
            "pati": m.percentual_tempo_integral,
            "iqem_real": iqem_2025(m),
            "iqem_maximo_individual": iqem_2025(cenario_maximo(m)),
            "pre_real": pre_real[m.nome],
            "pre_maxima_hipotetica": pre_maxima[m.nome],
            "pre_cheia_individual": pre_cheia[m.nome],
        })

    painel = pd.DataFrame(linhas)
    painel["diferenca_pontos_percentuais_pre"] = (
        painel["pre_maxima_hipotetica"] - painel["pre_real"]
    ) * 100
    painel["diferenca_pp_pre_cheia_individual"] = (
        painel["pre_cheia_individual"] - painel["pre_real"]
    ) * 100

    # --- Comparacao contra o IPM real, oficial, publicado pela Sefaz-SP ---
    # (formula ANTIGA, ainda em vigor - ver docstring do modulo e
    # scripts/coleta_ipm_sefaz.py para o porque de nao ser a mesma regra).
    ipm_path = "data/raw/ipm_sefaz_sp_2024.csv"
    if os.path.exists(ipm_path):
        ipm = pd.read_csv(ipm_path)
        ipm["chave"] = ipm["municipio"].apply(_normalizar_nome_municipio)
        painel["chave"] = painel["municipio"].apply(_normalizar_nome_municipio)
        painel = painel.merge(
            ipm[["chave", "cota_parte_educacao"]].rename(
                columns={"cota_parte_educacao": "pre_real_oficial_sefaz_formula_antiga"}
            ),
            on="chave", how="left",
        ).drop(columns="chave")
        painel["diferenca_pp_simulado_vs_oficial"] = (
            painel["pre_real"] - painel["pre_real_oficial_sefaz_formula_antiga"]
        ) * 100
        # Tamanho da distorcao de universo: quanto da cota-parte educacao
        # OFICIAL pertence aos municipios que ficaram fora do painel (e que,
        # na nossa renormalizacao, recebem zero). Ver docstring do modulo.
        no_painel = set(painel["municipio"].apply(_normalizar_nome_municipio))
        fora = ipm[~ipm["chave"].isin(no_painel)]
        painel["cota_parte_educacao_oficial_fora_do_painel_pct"] = (
            fora["cota_parte_educacao"].sum() * 100
        )
        print(f"Universo: {len(painel)} de {len(ipm)} municipios. Os {len(fora)} ausentes detem "
              f"{fora['cota_parte_educacao'].sum() * 100:.3f}% da cota-parte educacao oficial.")
    else:
        print(f"Aviso: {ipm_path} nao encontrado - rode scripts/coleta_ipm_sefaz.py antes "
              "para incluir a comparacao contra o IPM real da Sefaz-SP.")

    # --- Coordenadas (para o mapa do dashboard) ---
    coords_path = "data/raw/municipios_sp_coords.csv"
    if os.path.exists(coords_path):
        coords = pd.read_csv(coords_path)
        coords["chave"] = coords["Município_Join"].apply(_normalizar_nome_municipio)
        painel["chave"] = painel["municipio"].apply(_normalizar_nome_municipio)
        painel = painel.merge(
            coords[["chave", "latitude", "longitude"]], on="chave", how="left"
        ).drop(columns="chave")
    else:
        print(f"Aviso: {coords_path} nao encontrado - rode scripts/coords_sp.py antes "
              "para incluir coordenadas (usadas no mapa do dashboard).")

    painel = painel.sort_values("diferenca_pontos_percentuais_pre", ascending=False)
    return painel


# ===========================================================================
# ETAPA EM R$: periodo (ano civil do repasse) x regime (peso do criterio)
# ===========================================================================

def carregar_periodo(ano_civil: int) -> dict:
    """Le o repasse coletado de um ano civil e monta os parametros do periodo.

    Devolve o total do Estado (liquido e bruto), quantos meses estao publicados
    e o ano-base do IPM correspondente (ano_civil - 2).
    """
    caminho = f"data/raw/repasse_icms_sp_{ano_civil}.csv"
    if not os.path.exists(caminho):
        raise FileNotFoundError(
            f"{caminho} nao encontrado - rode "
            f"'python scripts/coleta_repasse_icms_sefaz.py {ano_civil}' antes."
        )
    resumo = resumir_por_ano(pd.read_csv(caminho))
    resumo["chave"] = resumo["municipio"].apply(_normalizar_nome_municipio)
    meses = int(resumo["meses_publicados"].max())
    return {
        "periodo": ano_civil,
        "ano_base_ipm": ano_base_do_repasse(ano_civil),
        "meses_publicados": meses,
        "periodo_fechado": meses == 12,
        "icms_estado_liquido_reais": float(resumo["icms_liquido_reais"].sum()),
        "icms_estado_bruto_reais": float(resumo["icms_bruto_reais"].sum()),
        "repasse_por_municipio": resumo,
    }


def expandir_periodos(painel: pd.DataFrame, periodos: list) -> pd.DataFrame:
    """Expande o painel (1 linha por municipio) em municipio x periodo x regime,
    acrescentando a etapa em R$."""
    blocos = []
    for ano_civil in periodos:
        p = carregar_periodo(ano_civil)
        repasse = p["repasse_por_municipio"]
        for regime in REGIMES:
            peso = peso_criterio_educacao(p["ano_base_ipm"], regime_pleno=(regime == "pleno"))
            bloco = painel.copy()
            bloco["periodo"] = p["periodo"]
            bloco["ano_base_ipm"] = p["ano_base_ipm"]
            bloco["meses_publicados"] = p["meses_publicados"]
            bloco["periodo_fechado"] = p["periodo_fechado"]
            bloco["regime_peso"] = regime
            bloco["peso_criterio_educacao"] = peso
            bloco["icms_estado_liquido_reais"] = p["icms_estado_liquido_reais"]
            bloco["icms_estado_bruto_reais"] = p["icms_estado_bruto_reais"]

            # Repasse total do proprio municipio no periodo (todos os criterios
            # do IPM, nao so educacao). Serve de contexto: mostra o peso da
            # parcela educacional dentro do que a cidade recebe de ICMS.
            bloco["chave"] = bloco["municipio"].apply(_normalizar_nome_municipio)
            bloco = bloco.merge(
                repasse[["chave", "icms_liquido_reais", "icms_bruto_reais"]].rename(columns={
                    "icms_liquido_reais": "icms_municipal_liquido_reais",
                    "icms_bruto_reais": "icms_municipal_bruto_reais",
                }),
                on="chave", how="left",
            ).drop(columns="chave")

            # Contribuicao do municipio no IPM vinda do criterio educacao.
            bloco["contribuicao_ipm_educacao"] = contribuicao_ipm_educacao(
                bloco["pre_real"], peso
            )
            bloco["contribuicao_ipm_educacao_cheia"] = contribuicao_ipm_educacao(
                bloco["pre_cheia_individual"], peso
            )

            for escala in ("liquido", "bruto"):
                total_estado = p[f"icms_estado_{escala}_reais"]
                bloco[f"parcela_repassada_{escala}_reais"] = (
                    bloco["contribuicao_ipm_educacao"] * total_estado
                )
                bloco[f"parcela_cheia_{escala}_reais"] = (
                    bloco["contribuicao_ipm_educacao_cheia"] * total_estado
                )
                bloco[f"diferenca_{escala}_reais"] = (
                    bloco[f"parcela_cheia_{escala}_reais"]
                    - bloco[f"parcela_repassada_{escala}_reais"]
                )

            # A diferenca relativa e' a mesma nas duas escalas (razao identica).
            bloco["diferenca_pct"] = (
                bloco["diferenca_liquido_reais"] / bloco["parcela_repassada_liquido_reais"] * 100
            )
            blocos.append(bloco)

    longo = pd.concat(blocos, ignore_index=True)
    longo["fundeb_retencao_aplicada"] = FUNDEB_RETENCAO
    return longo.sort_values(
        ["periodo", "regime_peso", "diferenca_liquido_reais"], ascending=[True, True, False]
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Consolida as fontes e calcula o painel do ICMS SP.")
    ap.add_argument("--periodos", nargs="*", type=int, default=PERIODOS_PADRAO,
                    help=f"anos civis de repasse (padrao: {PERIODOS_PADRAO})")
    args = ap.parse_args()

    os.makedirs("data/processed", exist_ok=True)
    base = calcular_painel()
    painel = expandir_periodos(base, args.periodos)
    caminho = "data/processed/painel_icms_sp.csv"
    painel.to_csv(caminho, index=False)

    print(f"\nOK: {len(base)} municipios x {len(args.periodos)} periodos x {len(REGIMES)} regimes "
          f"= {len(painel)} linhas. Salvo em {caminho}")

    for (periodo, regime), g in painel.groupby(["periodo", "regime_peso"]):
        peso = g["peso_criterio_educacao"].iloc[0]
        meses = g["meses_publicados"].iloc[0]
        total = g["icms_estado_liquido_reais"].iloc[0]
        bolo = total * peso
        print(f"\n--- periodo {periodo} ({meses} meses) | regime {regime} "
              f"| peso do criterio educacao {peso:.0%} | ano-base {g['ano_base_ipm'].iloc[0]}")
        print(f"    ICMS liquido repassado no Estado: R$ {total:,.2f}")
        print(f"    Bolo do criterio educacao:        R$ {bolo:,.2f}")
        print(f"    Soma das parcelas repassadas:     R$ {g['parcela_repassada_liquido_reais'].sum():,.2f}"
              "  (deve fechar com o bolo)")

    ultimo = painel[(painel["periodo"] == max(args.periodos)) & (painel["regime_peso"] == "vigente")]
    print("\nTop 10 municipios que mais deixam de receber em R$ por nao estarem no maximo")
    print("(cenario INDIVIDUAL: so ele no maximo, os outros nos valores reais):")
    print(ultimo[["municipio", "parcela_repassada_liquido_reais", "parcela_cheia_liquido_reais",
                  "diferenca_liquido_reais", "diferenca_pct"]].head(10).to_string(index=False))
