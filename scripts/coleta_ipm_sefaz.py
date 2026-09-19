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

COLUNAS = [
    "codigo_sefaz", "municipio", "va_2024", "va_2023", "populacao",
    "receita_tributaria", "area_cultivada", "area_inundada",
    "indice_area_protegida", "vegetacao_nativa", "residuos_solidos",
    "cota_parte_educacao", "ipm",
]


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
        if len(celulas) != len(COLUNAS):
            continue
        registro = dict(zip(COLUNAS, celulas))
        for campo in COLUNAS:
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


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    df = coletar_ipm_sp()
    caminho = "data/raw/ipm_sefaz_sp_2024.csv"
    df.to_csv(caminho, index=False)
    print(f"Salvo em {caminho}")
