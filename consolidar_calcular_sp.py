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
IMPORTANTE - LEIA JUNTO COM LIMITACOES_METODOLOGICAS.md
===========================================================================
Este script produz uma SIMULACAO da PARTICIPACAO RELATIVA no rateio
(PRE, um numero entre 0 e 1 que soma 1 entre todos os municipios do
universo processado), NAO o valor em R$ que cada municipio recebe.

Para converter PRE em R$ falta UM dado que ainda nao coletamos: o valor
total do "bolo" de ICMS Educacional do Estado de SP no exercicio de
referencia (os 13% do ICMS estadual destinados a educacao, base para o
rateio por qualidade). O exemplo `exemplo_cotia_2024()` na calculadora usa
um valor ja publicado especificamente para Cotia - nao temos o equivalente
estadual agregado ainda. Enquanto isso nao for coletado, use as colunas
`pre_real` e `pre_maxima` (e a diferenca entre elas) como o resultado
principal: elas mostram, em termos relativos, o quanto cada municipio
ganha ou perde de fatia do bolo por causa do seu desempenho.

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
  - evolucao_iqa = evolucao_iqi = 0 (ja no maximo, sem espaco de evolucao)
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
import unicodedata

import pandas as pd

from calculadora_icms_vaar_sp import IndicadoresMunicipio, iqem_2025, participacao_rateio


def _normalizar_nome_municipio(nome: str) -> str:
    s = str(nome).upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", s).strip()


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
    """Mesmo municipio, com desempenho maximo controlavel - ver docstring do modulo."""
    return IndicadoresMunicipio(
        nome=m.nome,
        taxa_reprovacao=0.0,
        taxa_abandono=0.0,
        garantia_fluxo=True,
        nota_iqa=10.0,
        evolucao_iqa=0.0,
        nota_iqi=10.0,
        evolucao_iqi=0.0,
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
            "pre_real": pre_real[m.nome],
            "pre_maxima_hipotetica": pre_maxima[m.nome],
        })

    painel = pd.DataFrame(linhas)
    painel["diferenca_pontos_percentuais_pre"] = (
        painel["pre_maxima_hipotetica"] - painel["pre_real"]
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


if __name__ == "__main__":
    os.makedirs("data/processed", exist_ok=True)
    painel = calcular_painel()
    caminho = "data/processed/painel_icms_sp.csv"
    painel.to_csv(caminho, index=False)

    print(f"OK: {len(painel)} municipios calculados. Salvo em {caminho}")
    print()
    print("Top 10 municipios que MAIS perdem participacao por nao estarem no")
    print("cenario de desempenho maximo (ver definicao na docstring do script):")
    print(painel[["municipio", "pre_real", "pre_maxima_hipotetica",
                  "diferenca_pontos_percentuais_pre"]].head(10).to_string(index=False))
