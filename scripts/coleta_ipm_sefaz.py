# -*- coding: utf-8 -*-
"""
Coleta automatica: IPM (Indice de Participacao dos Municipios) real, oficial,
publicado pela Sefaz-SP - inclui a coluna "Cota Parte Educacao" JA CALCULADA
OFICIALMENTE por municipio.
Fonte: https://www4.fazenda.sp.gov.br/DIPAM.Web/ConsultaIndice/
Endpoint descoberto em 12/09/2026 inspecionando o form da pagina (metodo GET,
sem __VIEWSTATE/postback classico - e' uma app MVC simples):
    https://www4.fazenda.sp.gov.br/DIPAM.Web/ConsultaIndice/ConsultarIndices
    ?tipoRelatorio=indices_finais&TipoIndice=D&AnoBase={ano}
Retorna os 645 municipios de uma vez em uma tabela HTML (nao precisa
consultar municipio por municipio).

===========================================================================
O QUE ESSA FONTE RESOLVE (leia junto com LIMITACOES_METODOLOGICAS.md)
===========================================================================
A coluna "Cota Parte Educacao" e' a participacao real de cada municipio
no criterio educacional do IPM - somei as 645 linhas e da EXATAMENTE 1,0,
confirmando que e' uma fracao normalizada, exatamente no mesmo formato do
`pre_real` que calculamos em consolidar_calcular_sp.py. Isso permite
comparar direto: nosso valor SIMULADO (formula nova, IQEM 2025, com dados
proxy) contra o valor REAL e OFICIAL (formula ainda em vigor hoje).

ATENCAO - datas/metodologia:
  - O "AnoBase" (ex.: 2024) e' o ano dos dados economicos usados para
    calcular o IPM que vale para repasses do ano SEGUINTE (ex.: AnoBase
    2024 -> IPM que vale em 2025/2026, conforme calendario da DIPAM).
  - Este IPM real e' calculado pela formula ANTIGA (Lei 3.201/1981 + Lei
    17.575/2022): metade do criterio educacional por qualidade (IDESP
    antigo), metade por porte populacional. NAO e' a formula nova (IQEM
    2025, 100% qualidade) que modelamos em calculadora_icms_vaar_sp.py -
    aquela so vale a partir da avaliacao de 2027/repasse de 2028.
  - Portanto: comparar pre_real (simulado, formula nova) contra esta
    coluna (real, formula antiga) mostra a DIFERENCA ENTRE AS DUAS REGRAS,
    nao um erro de calculo - documentar isso claramente ao apresentar.

O IPM tambem traz outros criterios (VA = Valor Adicionado, Populacao,
Receita Tributaria, Area Cultivada/Inundada, Indice de Area Protegida,
Vegetacao Nativa, Residuos Solidos) que compoem os outros 24% do indice
(o Valor Adicionado e' hoje a maior fatia, ~76%, definida pela Constituicao
Federal) - fica tudo salvo, mesmo sem uso imediato na calculadora do ICMS
Educacional.
===========================================================================
"""

import html
import os
import re
import ssl
import unicodedata
import urllib.request

import pandas as pd

URL_TEMPLATE = (
    "https://www4.fazenda.sp.gov.br/DIPAM.Web/ConsultaIndice/ConsultarIndices"
    "?tipoRelatorio=indices_finais&TipoIndice={tipo}&AnoBase={ano}"
)

def colunas_relatorio(ano: int) -> list:
    """Colunas da tabela do DIPAM. As duas primeiras de valor adicionado sao o
    ano-base e o ano anterior (o IPM usa a media das duas participacoes)."""
    return [
        "codigo_sefaz", "municipio", f"va_{ano}", f"va_{ano - 1}", "populacao",
        "receita_tributaria", "area_cultivada", "area_inundada",
        "indice_area_protegida", "vegetacao_nativa", "residuos_solidos",
        "cota_parte_educacao", "ipm",
    ]


# Retrocompatibilidade: o CSV que ja esta no repositorio e' do ano-base 2024.
COLUNAS = colunas_relatorio(2024)


def normalizar_nome_municipio(nome: str) -> str:
    """Uppercase + sem acento + sem apostrofo + hifen tratado como espaco.

    Alinhado com o mesmo tipo de normalizacao usada em FIX_transform.py -
    trata os casos conhecidos de grafia divergente entre fontes oficiais
    (ex.: "GUARANI D'OESTE" vs "GUARANI DOESTE", "BIRITIBA-MIRIM" vs
    "BIRITIBA MIRIM").
    """
    s = str(nome).upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", s).strip()


def _parse_numero_br(s: str):
    s = s.strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _baixar_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def coletar_ipm_sp(ano: int = 2024, tipo: str = "D") -> pd.DataFrame:
    """Baixa o IPM oficial (Sefaz-SP) para os 645 municipios de SP.

    ano: AnoBase (dados economicos usados no calculo - ver nota no topo).
    tipo: 'D' = Definitivo, 'P' = Provisorio.
    """
    colunas = colunas_relatorio(ano)
    url = URL_TEMPLATE.format(tipo=tipo, ano=ano)
    print(f"Baixando IPM Sefaz-SP (AnoBase {ano}, tipo {tipo}) de: {url}")
    pagina_html = _baixar_html(url)

    linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", pagina_html, re.S)
    if not linhas:
        raise ValueError("Nenhuma linha de tabela encontrada - o site pode ter mudado de formato.")

    registros = []
    for linha in linhas[1:]:  # linha[0] e' o cabecalho
        celulas = re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)
        celulas = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in celulas]
        if len(celulas) != len(colunas):
            continue
        registro = dict(zip(colunas, celulas))
        for campo in colunas:
            if campo not in ("municipio",):
                registro[campo] = _parse_numero_br(registro[campo])
        registros.append(registro)

    df = pd.DataFrame(registros)
    df["municipio_chave"] = df["municipio"].apply(normalizar_nome_municipio)

    print(f"OK: {len(df)} municipios de SP processados.")
    soma_edu = df["cota_parte_educacao"].sum()
    print(f"Soma da coluna 'Cota Parte Educacao': {soma_edu:.6f} (esperado: 1.0)")
    if abs(soma_edu - 1.0) > 0.001:
        print("Aviso: soma diferente de 1.0 - conferir se o formato da pagina mudou.")

    return df


# ===========================================================================
# DECOMPOSICAO DOS PESOS DO IPM - de onde sai o "peso do criterio educacao"
# ===========================================================================
# O IPM publicado e' uma soma ponderada das participacoes de cada criterio:
#
#   IPM_i = soma_k ( peso_k  x  participacao_i_no_criterio_k )
#
# Todas as participacoes estao no proprio relatorio do DIPAM (algumas em R$ ou
# em hectares, que normalizamos para fracao do Estado; outras ja normalizadas).
# Com isso da para RECUPERAR os pesos por minimos quadrados e conferir contra a
# lei, em vez de cravar "13%" no codigo a partir de uma fonte secundaria.
#
# O resultado reproduz o IPM oficial com erro da ordem de 1e-6 ponto percentual
# (praticamente ponto flutuante), e bate exatamente com a Lei 17.575/2022,
# art. 2o, I (inciso X do art. 1o da Lei 3.201/1981): criterio educacao em 10%
# (ano-base 2023), 11% (2024), 12% (2025) e 13% (2026), com o criterio
# populacao caindo 3% / 2% / 1% / extinto no mesmo ritmo.
#
# ATENCAO: a coluna de valor adicionado do IPM e' a MEDIA DAS PARTICIPACOES dos
# dois anos - nao a participacao da media dos valores. Usar a segunda forma
# deixa um residuo ~600x maior e distorce os pesos recuperados (o de educacao
# sai 11,03% em vez de 11,00%).
ERRO_MAXIMO_TOLERADO_PP = 1e-4


def decompor_pesos_ipm(df: pd.DataFrame, ano: int) -> tuple:
    """Recupera os pesos de cada criterio do IPM a partir do relatorio oficial.

    Devolve (pesos_em_percentual, erro_maximo_em_pontos_percentuais).
    """
    import numpy as np

    fracao = lambda serie: serie / serie.sum()  # noqa: E731
    n = len(df)
    participacoes = {
        # media das participacoes do ano-base e do ano anterior
        "valor_adicionado": (fracao(df[f"va_{ano}"]) + fracao(df[f"va_{ano - 1}"])) / 2,
        "cota_parte_educacao": df["cota_parte_educacao"],
        "receita_tributaria": fracao(df["receita_tributaria"]),
        "area_cultivada": fracao(df["area_cultivada"]),
        "populacao": fracao(df["populacao"]),
        "igual_para_todos": pd.Series([1 / n] * n, index=df.index),
        "indice_area_protegida": df["indice_area_protegida"] / 100,
        "vegetacao_nativa": df["vegetacao_nativa"],
        "area_inundada": df["area_inundada"],
        "residuos_solidos": df["residuos_solidos"],
    }
    matriz = pd.DataFrame(participacoes).values
    alvo = df["ipm"].values / 100  # o IPM publicado esta em percentual
    pesos, *_ = np.linalg.lstsq(matriz, alvo, rcond=None)
    erro_maximo_pp = float(np.abs(matriz @ pesos - alvo).max() * 100)
    return {nome: float(p * 100) for nome, p in zip(participacoes, pesos)}, erro_maximo_pp


def salvar_pesos_ipm(df: pd.DataFrame, ano: int, destino_dir: str = "data/processed") -> str:
    """Grava a decomposicao como CSV auditavel e valida a reproducao do IPM."""
    pesos, erro_pp = decompor_pesos_ipm(df, ano)
    print(f"\nPesos do IPM recuperados do relatorio oficial (ano-base {ano}):")
    for nome, peso in sorted(pesos.items(), key=lambda kv: -kv[1]):
        print(f"  {nome:22s} {peso:7.3f}%")
    print(f"  {'SOMA':22s} {sum(pesos.values()):7.3f}%")
    print(f"Erro maximo na reproducao do IPM oficial: {erro_pp:.2e} p.p.")
    if erro_pp > ERRO_MAXIMO_TOLERADO_PP:
        print(
            f"AVISO: erro acima do tolerado ({ERRO_MAXIMO_TOLERADO_PP:.0e} p.p.) - a Sefaz pode "
            "ter mudado os criterios do IPM. NAO use esses pesos sem conferir na legislacao."
        )

    os.makedirs(destino_dir, exist_ok=True)
    caminho = os.path.join(destino_dir, f"pesos_ipm_{ano}.csv")
    saida = pd.DataFrame(
        [{"ano_base": ano, "criterio": k, "peso_pct": v} for k, v in pesos.items()]
    ).sort_values("peso_pct", ascending=False)
    saida["erro_maximo_reproducao_pp"] = erro_pp
    saida["fonte"] = "decomposicao do IPM oficial (DIPAM/Sefaz-SP) por minimos quadrados"
    saida["confere_com"] = "Lei 17.575/2022, art. 2o, I (inciso X do art. 1o da Lei 3.201/1981)"
    saida.to_csv(caminho, index=False)
    print(f"Pesos salvos em {caminho}")
    return caminho


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Coleta o IPM oficial da Sefaz-SP (DIPAM).")
    ap.add_argument("anos", nargs="*", type=int, default=[2024, 2025],
                    help="anos-base a coletar (padrao: 2024 2025)")
    ap.add_argument("--tipo", default="D", choices=["D", "P"], help="D=definitivo, P=provisorio")
    args = ap.parse_args()

    os.makedirs("data/raw", exist_ok=True)
    for ano in args.anos:
        df = coletar_ipm_sp(ano=ano, tipo=args.tipo)
        caminho = f"data/raw/ipm_sefaz_sp_{ano}.csv"
        df.to_csv(caminho, index=False)
        print(f"Salvo em {caminho}")
        salvar_pesos_ipm(df, ano)
