# -*- coding: utf-8 -*-
"""
Coleta automatica: Taxas de Rendimento Escolar por municipio (INEP/Censo Escolar).
Fonte oficial: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais/taxas-de-rendimento-escolar
Padrao de URL confirmado manualmente em 12/09/2026 (aba do ano -> link "Municipios").

Alimenta o Indice de Fluxo Escolar (IF) da formula do ICMS Educacional-SP:
taxa de reprovacao e taxa de abandono, na rede MUNICIPAL, para os anos
iniciais do Ensino Fundamental - inclui o 2o ano (base do IQA) e o 5o ano
(base do IQI) isolados, alem do agregado 'Anos Iniciais'.

Usa o codigo IBGE do municipio (CO_MUNICIPIO) como chave - o mesmo padrao
usado pelo geobr em coords_sp.py. Isso evita o bug de acentuacao que afeta
hoje o cruzamento por nome em transform.py (ver FIX_transform.py): nomes
sem acento dos PDFs nacionais x nomes com acento oficial do geobr. Cruzando
por codigo numerico esse problema nao existe.
"""

import io
import os
import ssl
import urllib.request
import zipfile

import pandas as pd

URL_BASE = (
    "https://download.inep.gov.br/informacoes_estatisticas/"
    "indicadores_educacionais/{ano}/tx_rend_municipios_{ano}.zip"
)

# A planilha 'MUNICIPIOS ' tem cabecalho em 3 linhas mescladas; a ultima
# (indice 8, 0-based) ja traz os codigos de coluna legiveis por maquina.
# Blocos de 18 colunas cada, repetidos 3x:
#   1_CAT_FUN_* = Taxa de Aprovacao | 2_CAT_FUN_* = Reprovacao | 3_CAT_FUN_* = Abandono
LINHA_CABECALHO = 8

COLUNAS_INTERESSE = {
    "CO_MUNICIPIO": "codigo_ibge",
    "NO_MUNICIPIO": "municipio",
    "NO_CATEGORIA": "localizacao",
    "NO_DEPENDENCIA": "rede",
    "2_CAT_FUN_AI": "taxa_reprovacao_anos_iniciais",
    "2_CAT_FUN_02": "taxa_reprovacao_2ano",
    "2_CAT_FUN_05": "taxa_reprovacao_5ano",
    "3_CAT_FUN_AI": "taxa_abandono_anos_iniciais",
    "3_CAT_FUN_02": "taxa_abandono_2ano",
    "3_CAT_FUN_05": "taxa_abandono_5ano",
}


def coletar_taxas_rendimento_sp(ano: int = 2024, rede: str = "Municipal") -> pd.DataFrame:
    """Baixa o arquivo oficial do INEP e filtra as taxas de rendimento dos municipios de SP.

    rede: 'Municipal' (rede propria do municipio - a relevante para o ICMS
    Educacional-SP), 'Total' (soma de todas as redes no territorio) ou
    'Estadual'/'Privada'/'Federal'/'Publica'.
    """
    url = URL_BASE.format(ano=ano)
    print(f"Baixando taxas de rendimento {ano} de: {url}")

    # Usa urllib + contexto SSL padrao (confia no repositorio de certificados
    # do Windows) em vez de requests/certifi: o bundle de CAs do certifi nao
    # reconhece a cadeia de certificado do download.inep.gov.br neste
    # ambiente e a conexao cai com CERTIFICATE_VERIFY_FAILED.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
        conteudo = resp.read()

    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        nome_xlsx = f"tx_rend_municipios_{ano}/tx_rend_municipios_{ano}.xlsx"
        with zf.open(nome_xlsx) as f:
            df = pd.read_excel(f, sheet_name="MUNICIPIOS ", header=LINHA_CABECALHO)

    df_sp = df[
        (df["SG_UF"] == "SP")
        & (df["NO_CATEGORIA"] == "Total")
        & (df["NO_DEPENDENCIA"] == rede)
    ].copy()

    df_sp = df_sp[list(COLUNAS_INTERESSE)].rename(columns=COLUNAS_INTERESSE)

    for col in df_sp.columns:
        if col.startswith("taxa_"):
            df_sp[col] = pd.to_numeric(df_sp[col].replace("--", pd.NA), errors="coerce")

    print(f"OK: {len(df_sp)} municipios de SP (rede {rede}) processados.")
    faltantes = 645 - len(df_sp)
    if faltantes > 0:
        print(f"Aviso: {faltantes} municipios sem rede '{rede}' propria (provavelmente atendidos so pela rede estadual).")

    return df_sp


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    df = coletar_taxas_rendimento_sp()
    caminho = "data/raw/taxas_rendimento_sp_municipal_2024.csv"
    df.to_csv(caminho, index=False)
    print(f"Salvo em {caminho}")
