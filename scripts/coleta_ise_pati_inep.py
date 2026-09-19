# -*- coding: utf-8 -*-
"""
Coleta automatica: ISE (nivel socioeconomico) e PATI (% tempo integral),
por municipio, rede MUNICIPAL, para os Anos Iniciais do Ensino Fundamental.
Fontes oficiais (INEP):
  - ISE: Indicador de Nivel Socioeconomico (Inse) - Saeb 2023, por municipio.
    URL confirmada em 12/09/2026 (aba do ano -> link "Municipios"):
    https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2023/nivel_socioeconomico/INSE_2023_municipios.xlsx
  - PATI: Sinopse Estatistica da Educacao Basica 2025 - Censo Escolar,
    tabelas 1.23 (matricula total, Anos Iniciais, por dependencia) e 1.27
    (matricula em tempo integral, Anos Iniciais, por dependencia).
    URL confirmada em 12/09/2026 (aba do ano -> link de download):
    https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/sinopse_estatistica_censo_escolar_2025.zip

ATENCAO - arquivo da Sinopse e' GRANDE (~230 MB o zip, ~200 MB o xlsx com
268 abas). O download e a leitura das 2 abas relevantes podem demorar.

ISE: o Inse (escala ~0-10, media nacional em torno de 5) mede o nivel
socioeconomico dos alunos (educacao dos pais + posse de bens). A formula
da calculadora espera 'indice_socioeconomico' como vulnerabilidade (0-1,
maior = mais vulneravel). Como o Inse mede o oposto (maior = mais
favorecido), convertemos para uma vulnerabilidade normalizada dentro do
universo de municipios de SP:
    vulnerabilidade = (MEDIA_INSE_maximo_SP - MEDIA_INSE_municipio)
                       / (MEDIA_INSE_maximo_SP - MEDIA_INSE_minimo_SP)
Isso e' uma escolha de normalizacao (min-max dentro de SP) ainda NAO
confirmada contra a formula exata do Anexo Unico da Lei 17.575/2022 (que
esta publicado como imagem, nao texto - ver LIMITACOES_METODOLOGICAS.md).
Reportar tambem PC_NIVEL_1 + PC_NIVEL_2 (percentual de alunos nos dois
niveis socioeconomicos mais baixos) como alternativa mais direta/auditavel
de 'proporcao de alunos vulneraveis', caso a formula real use isso.

PATI: percentual de matriculas em tempo integral / total de matriculas,
Anos Iniciais, rede Municipal:
    PATI = matriculas_tempo_integral_municipal / matriculas_total_municipal
"""

import io
import os
import ssl
import urllib.request
import zipfile

import pandas as pd

URL_INSE = (
    "https://download.inep.gov.br/informacoes_estatisticas/"
    "indicadores_educacionais/2023/nivel_socioeconomico/INSE_2023_municipios.xlsx"
)
URL_SINOPSE = (
    "https://download.inep.gov.br/dados_abertos/sinopses_estatisticas/"
    "sinopse_estatistica_censo_escolar_2025.zip"
)

TP_TIPO_REDE_MUNICIPAL = 3   # ver aba 'Dicionário' do INSE
TP_LOCALIZACAO_TOTAL = 0     # Total (Urbana e Rural)

COD_UF_SP_MIN = 3500000
COD_UF_SP_MAX = 3600000


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # ssl.create_default_context() usa o repositorio de certificados do
    # Windows - requests/certifi falha com CERTIFICATE_VERIFY_FAILED neste
    # ambiente para os hosts do INEP (ver coleta_rendimento_inep.py).
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=180) as resp:
        return resp.read()


def coletar_ise_sp() -> pd.DataFrame:
    """ISE (Inse 2023) por municipio de SP, rede Municipal, localizacao Total."""
    print(f"Baixando INSE 2023 de: {URL_INSE}")
    conteudo = _baixar(URL_INSE)

    df = pd.read_excel(io.BytesIO(conteudo), sheet_name="INSE_MUN_2023")
    df_sp = df[
        (df["SG_UF"] == "SP")
        & (df["TP_TIPO_REDE"] == TP_TIPO_REDE_MUNICIPAL)
        & (df["TP_LOCALIZACAO"] == TP_LOCALIZACAO_TOTAL)
    ].copy()

    minimo, maximo = df_sp["MEDIA_INSE"].min(), df_sp["MEDIA_INSE"].max()
    df_sp["ise_vulnerabilidade_normalizada"] = (maximo - df_sp["MEDIA_INSE"]) / (maximo - minimo)
    df_sp["pc_niveis_1_2_vulneraveis"] = df_sp["PC_NIVEL_1"] + df_sp["PC_NIVEL_2"]

    df_sp = df_sp.rename(columns={"CO_MUNICIPIO": "codigo_ibge", "NO_MUNICIPIO": "municipio"})
    colunas = [
        "codigo_ibge", "municipio", "QTD_ALUNOS_INSE", "MEDIA_INSE",
        "ise_vulnerabilidade_normalizada", "pc_niveis_1_2_vulneraveis",
    ]
    print(f"OK: {len(df_sp)} municipios de SP (rede Municipal) com INSE 2023.")
    return df_sp[colunas]


def coletar_pati_sp() -> pd.DataFrame:
    """PATI (% tempo integral, Anos Iniciais) por municipio de SP, rede Municipal."""
    print(f"Baixando Sinopse Estatistica 2025 de: {URL_SINOPSE} (arquivo grande, pode demorar)")
    conteudo = _baixar(URL_SINOPSE)

    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        nome_xlsx = next(n for n in zf.namelist() if n.endswith(".xlsx"))
        with zf.open(nome_xlsx) as f:
            dados_xlsx = f.read()

    # Tabela 1.23: matricula TOTAL (Anos Iniciais) por dependencia -> denominador
    df_total = pd.read_excel(
        io.BytesIO(dados_xlsx), sheet_name="1.23", header=None, skiprows=9,
    )
    df_total = df_total.iloc[:, [1, 2, 3, 8]]
    df_total.columns = ["uf", "municipio", "codigo_ibge", "matriculas_anos_iniciais_municipal"]

    # Tabela 1.27: matricula em TEMPO INTEGRAL (Anos Iniciais) por dependencia -> numerador
    df_integral = pd.read_excel(
        io.BytesIO(dados_xlsx), sheet_name="1.27", header=None, skiprows=9,
    )
    df_integral = df_integral.iloc[:, [3, 9]]
    df_integral.columns = ["codigo_ibge", "matriculas_tempo_integral_municipal"]

    for df_ in (df_total, df_integral):
        df_["codigo_ibge"] = pd.to_numeric(df_["codigo_ibge"], errors="coerce")

    # Filtra so linhas de municipio (nao Brasil/Regiao/UF) dentro do codigo IBGE de SP.
    df_total = df_total[
        df_total["codigo_ibge"].between(COD_UF_SP_MIN, COD_UF_SP_MAX, inclusive="left")
    ].copy()

    df = pd.merge(df_total, df_integral, on="codigo_ibge", how="left")
    for col in ("matriculas_anos_iniciais_municipal", "matriculas_tempo_integral_municipal"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["municipio"] = df["municipio"].str.strip()
    df["pati"] = df["matriculas_tempo_integral_municipal"] / df["matriculas_anos_iniciais_municipal"]

    print(f"OK: {len(df)} municipios de SP com dado de matricula (Anos Iniciais, rede Municipal).")
    sem_rede_municipal = (df["matriculas_anos_iniciais_municipal"] == 0).sum()
    if sem_rede_municipal:
        print(f"Aviso: {sem_rede_municipal} municipios sem matricula na rede municipal (Anos Iniciais).")

    return df[["codigo_ibge", "municipio", "matriculas_anos_iniciais_municipal",
               "matriculas_tempo_integral_municipal", "pati"]]


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

    df_ise = coletar_ise_sp()
    df_ise.to_csv("data/raw/ise_sp_municipal.csv", index=False)
    print("Salvo em data/raw/ise_sp_municipal.csv")

    df_pati = coletar_pati_sp()
    df_pati.to_csv("data/raw/pati_sp_municipal.csv", index=False)
    print("Salvo em data/raw/pati_sp_municipal.csv")

    print()
    print("LEMBRETE: normalizacao do ISE e escopo do PATI (so Anos Iniciais)")
    print("sao escolhas registradas em LIMITACOES_METODOLOGICAS.md - confirmar")
    print("contra o Anexo Unico da Lei 17.575/2022 quando possivel.")
