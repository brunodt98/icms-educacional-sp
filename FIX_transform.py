# -*- coding: utf-8 -*-
"""
PATCH: corrige bug de cruzamento (join) em scripts/transform.py do pipeline
'Estado de Sao Paulo/documentacao 2026-1/main.zip'.

BUG ENCONTRADO
--------------
Em transform.py, a chave de cruzamento 'Município_Join' e' criada apenas
com .str.upper().str.strip(), sem remover acentuacao. receitas_br.csv e
inabilitados_br.csv trazem os nomes de municipio SEM acento (ex.:
"AGUAS DA PRATA", "SAO JOSE DO RIO PRETO", "COSMOPOLIS"), enquanto
municipios_sp_coords.csv (gerado via geobr/IBGE em coords_sp.py) traz a
grafia OFICIAL com acento ("ÁGUAS DA PRATA", "SÃO JOSÉ DO RIO PRETO",
"COSMÓPOLIS"). Como o merge final usa `how='inner'` contra a base de
coordenadas, qualquer nome cujo par acentuado nao seja identico byte a
byte e' descartado silenciosamente - sem warning, sem log de quantos
registros foram perdidos.

IMPACTO (medido em 04/09/2026, comparando com receitas_br.csv/
inabilitados_br.csv, a fonte nacional completa)
-------------------------------------------------------------------------
- Match exato (bug atual):        363 de 645 municipios de SP (56%)
- Apos normalizar acentos:        632 de 645 municipios de SP (98%)
=> 269 municipios de SP (42%) somem do dataset final (dados_finais_sp.csv)
   e do mapa de calor (mapa_final_sp.html) sem qualquer aviso no pipeline.

Os 13 municipios que ainda nao batem apos a correcao de acentos sao casos
de grafia com apostrofo/hifen ("GUARANI D'OESTE" vs "GUARANI DOESTE",
"MOGI-GUAÇU" vs "MOGI GUACU") ou mudanca de nome ("EMBU" vs "EMBU DAS
ARTES") - exigem um dicionario de excecoes, nao apenas normalizacao.

CORRECAO
--------
Normalizar ambos os lados removendo acentos (unicodedata) antes da chave
de join, em vez de apenas .str.upper().str.strip().

Aplique este patch substituindo as 3 linhas de 'Município_Join' em
scripts/transform.py (e a linha equivalente em scripts/coords_sp.py) pela
funcao `normalizar_nome_municipio` abaixo.
"""

import unicodedata
import pandas as pd


def normalizar_nome_municipio(serie: pd.Series) -> pd.Series:
    """Uppercase + strip + remove acentuacao (NFKD) para uso como chave de join."""
    def _sem_acento(s: str) -> str:
        s = str(s).upper().strip()
        return "".join(
            c for c in unicodedata.normalize("NFKD", s)
            if not unicodedata.combining(c)
        )
    return serie.apply(_sem_acento)


def processar_sp_corrigido():
    """Versao corrigida de transform.processar_sp() - ver bug acima."""
    df_rec = pd.read_csv('data/processed/receitas_br.csv')
    df_ina = pd.read_csv('data/processed/inabilitados_br.csv')
    df_coords = pd.read_csv('data/raw/municipios_sp_coords.csv')

    df_rec.columns = [str(c).replace('\n', ' ').strip() for c in df_rec.columns]
    df_ina.columns = [str(c).replace('\n', ' ').strip() for c in df_ina.columns]

    coluna_motivo = df_ina.columns[-1]

    sp_receitas = df_rec[df_rec.iloc[:, 0].astype(str).str.contains('SP', na=False)].copy()
    sp_inabilitados = df_ina[df_ina.iloc[:, 0].astype(str).str.contains('SP', na=False)].copy()

    # CORRECAO: normalizar removendo acentos nos tres lados do join
    sp_receitas['Município_Join'] = normalizar_nome_municipio(sp_receitas.iloc[:, 2])
    sp_inabilitados['Município_Join'] = normalizar_nome_municipio(sp_inabilitados.iloc[:, 1])
    df_coords['Município_Join'] = normalizar_nome_municipio(df_coords['Município_Join'])

    sp_inabilitados = sp_inabilitados.rename(columns={coluna_motivo: 'Motivo'})

    df_merge_info = pd.merge(
        sp_receitas,
        sp_inabilitados[['Município_Join', 'Motivo']],
        on='Município_Join',
        how='left'
    )

    df_final = pd.merge(
        df_merge_info,
        df_coords[['Município_Join', 'latitude', 'longitude']],
        on='Município_Join',
        how='inner'
    )

    total = len(df_final)
    perdidos = len(sp_receitas) - total  # deveria ser ~1 (GOVERNO DO ESTADO nao tem coord)
    print(f"Municipios processados: {total} (esperado: 645 municipios + eventual ajuste)")
    print(f"Registros de receitas nao casados com coordenada: {perdidos}")

    df_final.to_csv('data/processed/dados_finais_sp_CORRIGIDO.csv', index=False)
    return df_final


if __name__ == "__main__":
    processar_sp_corrigido()
