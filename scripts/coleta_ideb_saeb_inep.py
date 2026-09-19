# -*- coding: utf-8 -*-
"""
Coleta automatica: IDEB / SAEB - Anos Iniciais, por municipio e rede (INEP).
Fonte oficial: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais/ideb
URL confirmada em 12/09/2026:
https://download.inep.gov.br/ideb/resultados/divulgacao_anos_iniciais_municipios_{ano}.zip

===========================================================================
LIMITACAO METODOLOGICA - LEIA ANTES DE USAR (ver tambem o relatorio final)
===========================================================================
A Lei Estadual 17.575/2022 (alterada pela Lei 18.381/2025) define o IQA e o
IQI com base no SARESP (avaliacao PROPRIA do Estado de SP), separadamente
para o 2o ano (IQA - alfabetizacao) e o 5o ano (IQI - anos iniciais), da
REDE MUNICIPAL de cada cidade.

Essa base municipal do SARESP NAO existe em dados abertos: o catalogo da
Seduc-SP (dadosabertos.des.sp.gov.br e dados.educacao.sp.gov.br) so publica
IDESP/SARESP da rede ESTADUAL (confirmado em 12/09/2026 via API do
catalogo CKAN - datasets 'IDESP do Estado', 'IDESP por Escola', 'IDESP por
Diretoria de Ensino': nenhum tem recorte de rede municipal). A adesao da
rede municipal ao SARESP e' voluntaria, e o resultado dela nao e' publico.

Alem disso, a propria Lei 18.381/2025 (art. sobre o painel de monitoramento)
so entra em vigor a partir do exercicio de 2026, com AVALIACAO em 2027 e
REPASSE em 2028 - ou seja, o dado oficial do IQEM no formato novo AINDA NAO
EXISTE em lugar nenhum, nem internamente na Seduc-SP, porque o primeiro
ciclo de avaliacao da lei nova ainda nao aconteceu.

Por isso, este projeto usa como PROXY o IDEB/SAEB do INEP (federal), que:
  - E' aplicado obrigatoriamente em todas as redes, incluindo a municipal
    (ao contrario do Saresp, que e' de adesao voluntaria para municipios)
  - Ja e' uma nota composta (proficiencia x fluxo) na mesma escala 0-10
    do IDESP/IQEM, o que evita problema de escala ao plugar na formula
  - Tem serie historica por municipio e rede, o que permite calcular
    'evolucao' (delta ano a ano) exigido pela formula do IQA/IQI

APROXIMACAO ASSUMIDA: o IDEB - Anos Iniciais NAO separa 2o ano de 5o ano
(e' um indicador unico para o ciclo 1o-5o ano). Por falta de fonte aberta
com essa granularidade, usamos o MESMO valor de IDEB como proxy tanto para
nota_iqa quanto para nota_iqi. Isso deve ser reportado como limitacao no
relatorio final do projeto - os numeros aqui sao uma SIMULACAO com a
melhor fonte publica disponivel hoje, nao o calculo oficial da Seduc-SP.
===========================================================================
"""

import io
import os
import ssl
import urllib.request
import zipfile

import pandas as pd

URL_BASE = (
    "https://download.inep.gov.br/ideb/resultados/"
    "divulgacao_anos_iniciais_municipios_{ano}.zip"
)

# Linha 9 (0-indexed) da planilha traz os codigos de coluna legiveis.
LINHA_CABECALHO = 9


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # Usa contexto SSL padrao (confia no repositorio de certificados do
    # Windows) em vez de requests/certifi - ver nota em coleta_rendimento_inep.py.
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
        return resp.read()


def coletar_ideb_saeb_sp(ano: int = 2025, ano_anterior: int = 2023, rede: str = "Municipal") -> pd.DataFrame:
    """Baixa o IDEB/SAEB oficial (INEP) e filtra SP na rede informada.

    Retorna, por municipio: nota media do SAEB (0-10), IDEB observado no
    ano e no ano anterior, e a evolucao (delta) entre as duas edicoes -
    ver LIMITACAO METODOLOGICA no topo do arquivo.
    """
    url = URL_BASE.format(ano=ano)
    print(f"Baixando IDEB/SAEB anos iniciais {ano} de: {url}")
    conteudo = _baixar(url)

    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        nome_xlsx = f"divulgacao_anos_iniciais_municipios_{ano}/divulgacao_anos_iniciais_municipios_{ano}.xlsx"
        with zf.open(nome_xlsx) as f:
            df = pd.read_excel(f, header=LINHA_CABECALHO)

    col_ideb_atual = f"VL_OBSERVADO_{ano}"
    col_ideb_anterior = f"VL_OBSERVADO_{ano_anterior}"
    col_saeb_media = f"VL_NOTA_MEDIA_{ano}"

    colunas = {
        "CO_MUNICIPIO": "codigo_ibge",
        "NO_MUNICIPIO": "municipio",
        "REDE": "rede",
        col_saeb_media: "saeb_nota_media",
        col_ideb_atual: "ideb_anos_iniciais",
        col_ideb_anterior: "ideb_anos_iniciais_anterior",
    }

    df_sp = df[(df["SG_UF"] == "SP") & (df["REDE"] == rede)].copy()
    df_sp = df_sp[list(colunas)].rename(columns=colunas)

    for col in ("saeb_nota_media", "ideb_anos_iniciais", "ideb_anos_iniciais_anterior"):
        df_sp[col] = pd.to_numeric(df_sp[col].replace("-", pd.NA), errors="coerce")

    df_sp["evolucao_ideb"] = df_sp["ideb_anos_iniciais"] - df_sp["ideb_anos_iniciais_anterior"]

    print(f"OK: {len(df_sp)} municipios de SP (rede {rede}) com dado de IDEB/SAEB {ano}.")
    faltantes = df_sp["ideb_anos_iniciais"].isna().sum()
    if faltantes:
        print(f"Aviso: {faltantes} municipios sem IDEB {ano} valido (amostra insuficiente ou rede sem dado).")

    return df_sp


if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    df = coletar_ideb_saeb_sp()
    caminho = "data/raw/ideb_saeb_sp_municipal.csv"
    df.to_csv(caminho, index=False)
    print(f"Salvo em {caminho}")
    print()
    print("LEMBRETE: este arquivo e' um PROXY (IDEB/SAEB federal), nao o SARESP")
    print("da rede municipal exigido pela lei estadual - ver docstring do script.")
