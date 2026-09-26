# -*- coding: utf-8 -*-
"""
Calculadora ICMS Educacional (SP) + Elegibilidade VAAR (Fundeb)
Projeto Integrador V - Grupo 2 (ICMS Educacional - SP)

Implementa as regras extraidas de:
- ICMS_Fundeb_CD.pptx (formulas do ICMS Educacional-SP, Lei Estadual 17.575/2022
  e alteracao legislativa de 2025, com efeitos a partir de 2026)
- Lei Federal 14.113/2020, art. 14 (condicionalidades e indicadores do VAAR)
- apresentacao pi5.pptx (atualizacao 2025/2026): confirma a formula do
  repasse final (IQEM x porte / total do estado) e a existencia das
  formulas de Condicionalidade III e melhoria de atendimento.
- VERIFICADO NA WEB (05/09/2026) contra fontes oficiais/jornalisticas:
  * Resolucao CIF no 24/2026: aprova a metodologia das condicionalidades
    I, IV e V (NAO II como constava numa leitura inicial do slide) para o
    ciclo 2026/2027. Prazo de registro no Simec: 31/08/2026 (JA VENCIDO
    na data desta verificacao).
  * Resolucao CIF no 25/2026, de 23/07/2026: aprova a Nota Tecnica no
    3/2026/CGEFE/DIRED-INEP, com a metodologia EXATA do VAAR-Atendimento
    e VAAR-Aprendizagem para o exercicio financeiro de 2027 (PDF oficial
    do MEC, 43 paginas). A tabela de faixas por porte de rede implementada
    abaixo bate exatamente com o documento oficial.
  * CORRECAO DE SEMANTICA (ver houve_melhoria_atendimento): a faixa de
    flutuacao e uma TOLERANCIA para pequenas quedas, nao uma "meta de
    reducao exigida" - qualquer melhora real (delta > 0) sempre habilita.

Status: rascunho funcional (checkpoint Semana 5). Falta calibrar os pesos
oficiais (alfa_IEO/IEN/CSE nao se aplicam aqui - isso e do modelo de SC;
em SP os pesos 40/40/10/10 vieram da Lei estadual de dez/2025, confirmados
via reportagem da Seduc-SP) com a base de dados oficial da SEDUC/SEFAZ-SP
assim que disponibilizada pelo grupo.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. ICMS EDUCACIONAL - SAO PAULO (Lei Estadual 17.575/2022 + alteracao 2025)
# ---------------------------------------------------------------------------

@dataclass
class IndicadoresMunicipio:
    nome: str
    # Indice de Fluxo Escolar (condicionalidade eliminatoria)
    taxa_reprovacao: float          # TR
    taxa_abandono: float            # TA
    garantia_fluxo: bool            # gate: se False, zera IQA/IQI/IQEM
    # Alfabetizacao (2o ano) e Anos Iniciais (5o ano)
    nota_iqa: float
    evolucao_iqa: float
    nota_iqi: float
    evolucao_iqi: float
    # Formula 2025 (efeitos 2026)
    indice_socioeconomico: float    # ISE (0-1, maior = mais vulneravel/mais peso)
    percentual_tempo_integral: float  # PATI (0-1)
    numero_matriculas: float        # NM - matriculas anos iniciais do EF


def indice_fluxo_escolar(taxa_reprovacao: float, taxa_abandono: float) -> float:
    """IF = 0,40*(1-TR) + 0,60*(1-TA)  (slide 6, ICMS_Fundeb_CD.pptx)"""
    return 0.40 * (1 - taxa_reprovacao) + 0.60 * (1 - taxa_abandono)


def iqa(nota: float, evolucao: float) -> float:
    """Indice de Qualidade da Alfabetizacao (2o ano) = NOTA + EVOLUCAO"""
    return nota + evolucao


def iqi(nota: float, evolucao: float) -> float:
    """Indice de Qualidade dos Anos Iniciais (5o ano) = NOTA + EVOLUCAO"""
    return nota + evolucao


def iqem_2025(m: IndicadoresMunicipio) -> float:
    """
    Indice de Qualidade da Educacao Municipal, formula da alteracao
    legislativa de 2025 (efeitos a partir de 2026):
        IQEM = 0,40*IQA + 0,40*IQI + 0,10*ISE + 0,10*PATI
    Sem garantia de fluxo (condicionalidade do IF), o indice e zerado -
    "Sem Garantia de Fluxo todo o trabalho nos demais indices e descartado"
    (slide 6).
    """
    if not m.garantia_fluxo:
        return 0.0
    _iqa = iqa(m.nota_iqa, m.evolucao_iqa)
    _iqi = iqi(m.nota_iqi, m.evolucao_iqi)
    return (
        0.40 * _iqa
        + 0.40 * _iqi
        + 0.10 * m.indice_socioeconomico
        + 0.10 * m.percentual_tempo_integral
    )


def participacao_rateio(municipios: list[IndicadoresMunicipio]) -> dict:
    """
    PRE_it: participacao no rateio da cota-parte educacao do municipio i,
    ponderada por IQEM e numero de matriculas:
        PRE_i = (IQEM_i * NM_i) / soma_j(IQEM_j * NM_j)

    Confirmado por duas fontes independentes do grupo:
    - ICMS_Fundeb_CD.pptx, slide 7: "PRE_it e a participacao no rateio...
      IQEM_it... NM_it e o numero de matriculas..."
    - apresentacao pi5.pptx, slide 7: "Repasse Final: o valor financeiro e
      obtido multiplicando o IQEM do municipio pelo seu respectivo porte
      (numero de matriculas) sobre o total do estado."
    """
    pesos = {m.nome: iqem_2025(m) * m.numero_matriculas for m in municipios}
    total = sum(pesos.values())
    if total == 0:
        return {nome: 0.0 for nome in pesos}
    return {nome: valor / total for nome, valor in pesos.items()}


def participacao_com_um_no_maximo(municipios: list[IndicadoresMunicipio],
                                   cenario_maximo) -> dict:
    """
    PRE de cada municipio no cenario INDIVIDUAL: so aquele municipio atinge o
    desempenho maximo, todos os outros ficam nos valores reais, e o rateio e'
    renormalizado.

    E' a resposta a pergunta "quanto ESTE municipio receberia se batesse os
    indices maximos?" - diferente do cenario COLETIVO (todos no maximo ao mesmo
    tempo), em que o IQEM de todos se iguala e o rateio degenera para uma
    divisao proporcional as matriculas.

    `cenario_maximo` e' uma funcao IndicadoresMunicipio -> IndicadoresMunicipio
    (definida em consolidar_calcular_sp.py, onde estao documentadas as escolhas
    do que e' "maximo").

    ATENCAO ao interpretar: os valores devolvidos NAO somam 1,0. Cada um vem de
    um cenario contrafactual diferente (um municipio de cada vez no maximo),
    entao eles nao formam um rateio unico e nao podem ser somados.
    """
    pesos = {m.nome: iqem_2025(m) * m.numero_matriculas for m in municipios}
    total = sum(pesos.values())
    resultado = {}
    for m in municipios:
        peso_maximo = iqem_2025(cenario_maximo(m)) * m.numero_matriculas
        denominador = total - pesos[m.nome] + peso_maximo
        resultado[m.nome] = peso_maximo / denominador if denominador else 0.0
    return resultado


# ---------------------------------------------------------------------------
# 1b. DO PRE AO VALOR EM R$ (peso do criterio educacao dentro do IPM)
# ---------------------------------------------------------------------------
# O PRE e' uma participacao relativa DENTRO do criterio educacao. Para chegar em
# reais faltam duas etapas: (1) quanto o criterio educacao pesa no IPM, e (2)
# qual o valor de ICMS repassado aos municipios no periodo.
#
# FONTE DO PESO (etapa 1) - Lei 17.575/2022, art. 2o, inciso I, que acrescenta o
# inciso X ao art. 1o da Lei 3.201/1981: o criterio educacao entra escalonado em
# 10% (ano-base 2023), 11% (2024), 12% (2025) e 13% (2026). Em paralelo, o art.
# 1o, inciso I da mesma lei reduz o criterio populacao (3%, 2%, 1%, extinto em
# 2026) - ou seja, o criterio educacao ocupa progressivamente o espaco que era
# da populacao.
#
# VALIDACAO INDEPENDENTE: esses pesos nao foram apenas lidos na lei, eles foram
# REPRODUZIDOS a partir do IPM oficial publicado pela Sefaz-SP. A decomposicao
# em scripts/coleta_ipm_sefaz.py recalcula o IPM dos 645 municipios a partir das
# participacoes de cada criterio e recupera os pesos com erro da ordem de 1e-6
# ponto percentual - confirmando 11% para o ano-base 2024 e 12% para 2025.
PESO_CRITERIO_EDUCACAO_POR_ANO_BASE = {
    2023: 0.10,
    2024: 0.11,
    2025: 0.12,
    2026: 0.13,
}
# Regime pleno: a partir do ano-base 2026 o peso estabiliza em 13% e o criterio
# populacao desaparece. E' o peso que a lei preve em regime permanente.
PESO_CRITERIO_EDUCACAO_REGIME_PLENO = 0.13

# O IPM calculado sobre os dados de um ano-base rege os repasses do ano civil
# ano_base + 2. Verificado empiricamente contra os dados oficiais: com o IPM de
# ano-base 2024, a identidade repasse_i = IPM_i x total_do_Estado reproduz os
# repasses de 2026 com dispersao de 0,04% entre municipios de portes muito
# diferentes (contra ~3% se testada contra 2025, ou seja, outro ano-base).
# Consequencia: o peso de 13% (ano-base 2026) vale para os repasses de 2028 -
# o mesmo exercicio em que a formula nova do IQEM passa a valer.
DEFASAGEM_ANO_BASE_REPASSE = 2


def ano_base_do_repasse(ano_civil_do_repasse: int) -> int:
    """Ano-base do IPM que rege os repasses de um ano civil (ver constante acima)."""
    return ano_civil_do_repasse - DEFASAGEM_ANO_BASE_REPASSE


def peso_criterio_educacao(ano_base: int, regime_pleno: bool = False) -> float:
    """
    Peso do criterio educacao no IPM para um ano-base.

    regime_pleno=True devolve sempre 13% (o peso permanente da lei), para
    simular o efeito da regra ja madura sobre um periodo cujo peso vigente
    ainda e' menor. Isso e' um CENARIO, nao o peso em vigor naquele ano - o
    painel rotula as duas leituras.
    """
    if regime_pleno:
        return PESO_CRITERIO_EDUCACAO_REGIME_PLENO
    if ano_base in PESO_CRITERIO_EDUCACAO_POR_ANO_BASE:
        return PESO_CRITERIO_EDUCACAO_POR_ANO_BASE[ano_base]
    if ano_base > max(PESO_CRITERIO_EDUCACAO_POR_ANO_BASE):
        return PESO_CRITERIO_EDUCACAO_REGIME_PLENO  # a lei estabiliza em 13%
    raise ValueError(
        f"Ano-base {ano_base} anterior a 2023: o criterio educacao nao existia no IPM "
        "(criado pela Lei 17.575/2022, com efeitos a partir do ano-base 2023)."
    )


def contribuicao_ipm_educacao(pre: float, peso_educacao: float) -> float:
    """
    Contribuicao do municipio no IPM vinda do criterio educacao.

        contribuicao = peso_do_criterio x PRE

    Somada entre todos os municipios, da exatamente o peso do criterio (ex.:
    0,11 para o ano-base 2024) - e' a fatia do IPM que a educacao explica.
    """
    return peso_educacao * pre


def parcela_educacao_reais(pre: float, peso_educacao: float,
                           valor_icms_periodo_estado: float) -> float:
    """
    Valor em R$ que o municipio recebe pelo criterio educacao no periodo:

        parcela = peso_do_criterio x PRE x ICMS repassado aos municipios no periodo

    `valor_icms_periodo_estado` e' o total do ESTADO (soma dos 645 municipios),
    nao o repasse do proprio municipio - o PRE e' uma fatia normalizada no
    Estado, entao as duas grandezas tem que estar na mesma escala. Ver
    scripts/coleta_repasse_icms_sefaz.py para a fonte e para a diferenca entre
    valor liquido (pos-FUNDEB, o que a Sefaz publica) e bruto.
    """
    return contribuicao_ipm_educacao(pre, peso_educacao) * valor_icms_periodo_estado


def cota_parte_recebida(valor_icms_total_municipio: float,
                         indice_participacao_icms_educacional: float) -> float:
    """
    ATENCAO - NAO E' A CADEIA OFICIAL. Use parcela_educacao_reais().

    Esta funcao existe so para reproduzir a aritmetica do slide 8 de
    ICMS_Fundeb_CD.pptx (ver exemplo_cotia_2024), preservada para rastrear de
    onde vieram os numeros dos entregaveis de setembro/2026. Ela multiplica o
    valor de ICMS DO PROPRIO MUNICIPIO por um indice que e' normalizado no
    ESTADO (soma 1,0 entre os 645) - as duas escalas nao se combinam, e o
    resultado sai cerca de uma ordem de grandeza abaixo da cadeia correta.
    """
    return valor_icms_total_municipio * indice_participacao_icms_educacional


def perda_receita_estimada(cota_parte_maxima: float, cota_parte_recebida_: float) -> float:
    """Idem: aritmetica do slide, mantida so para rastreabilidade."""
    return cota_parte_maxima - cota_parte_recebida_


# ---------------------------------------------------------------------------
# 2. ELEGIBILIDADE VAAR (Lei Federal 14.113/2020, art. 14, par. 1o)
# ---------------------------------------------------------------------------

@dataclass
class CondicionalidadesVAAR:
    """
    As 5 condicionalidades do art. 14, par. 1o, incisos I a V (Lei 14.113/2020).
    Para o ciclo 2026/2027, as condicionalidades I, IV e V tem metodologia
    de afericao detalhada pela Resolucao CIF no 24/2026 (confirmada via
    pesquisa web em 05/09/2026):
      I  - >50% dos gestores providos por merito/desempenho (26/27),
           progressivo ate 100% em 2029/2030.
      IV - regime de colaboracao / ICMS Educacional - preenchimento no
           Simec e feito SOMENTE pela rede ESTADUAL, nao pela municipal.
      V  - referenciais curriculares alinhados a BNCC + (NOVO 2026/2027)
           Complemento a BNCC de Computacao na Educacao Basica.
    """
    gestao_escolar_por_merito: bool          # I
    participacao_saeb_min_80pct: bool        # II
    reducao_desigualdades: bool              # III
    regime_colaboracao_estado_municipio: bool  # IV (inclui ICMS Educacional estadual)
    referenciais_curriculares_bncc: bool     # V (inclui Complemento de Computacao, 2026/27)


def habilitado_vaar(c: CondicionalidadesVAAR) -> tuple[bool, list[str]]:
    """
    Retorna (habilitado, lista_motivos_descumprimento).
    Cumprir as 5 condicionalidades e necessario, mas NAO garante o
    recebimento automatico do VAAR - a distribuicao do valor ainda
    depende da evolucao dos indicadores (art. 14, par. 2o), que nao
    esta modelada aqui (depende de series historicas do SAEB/Inep).
    """
    motivos = []
    if not c.gestao_escolar_por_merito:
        motivos.append("I - Gestao escolar sem criterio de merito/desempenho")
    if not c.participacao_saeb_min_80pct:
        motivos.append("II - Participacao no SAEB abaixo de 80%")
    if not c.reducao_desigualdades:
        motivos.append("III - Sem reducao das desigualdades educacionais")
    if not c.regime_colaboracao_estado_municipio:
        motivos.append("IV - Sem regime de colaboracao Estado-Municipio")
    if not c.referenciais_curriculares_bncc:
        motivos.append("V - Referenciais curriculares nao alinhados a BNCC")
    return (len(motivos) == 0, motivos)


def habilitado_condicionalidade_III(p_atual: float, p_anterior: float) -> bool:
    """
    Condicionalidade III (reducao das desigualdades) - formula exata
    (apresentacao pi5.pptx, slide 8, Resolucao CIF no 24/2026):

        p = soma(f(x) * w) / soma(w)

    onde f(x) = 1 se a nota do aluno x for inadequada no Saeb (0 caso
    contrario) e w e o peso amostral do aluno; p e portanto a proporcao
    ponderada de alunos vulneraveis abaixo do nivel adequado.

    "Regra de ouro": a rede so se habilita nesta condicionalidade se a
    diferenca entre o p do exercicio atual e o p do exercicio anterior for
    menor ou igual a zero (ou seja, a proporcao de alunos abaixo do nivel
    adequado nao pode ter aumentado).
    """
    return (p_atual - p_anterior) <= 0


def proporcao_alunos_abaixo_do_nivel(notas_inadequadas: list[bool], pesos: list[float]) -> float:
    """p = soma(f(x)*w) / soma(w), com f(x)=1 se a nota for inadequada."""
    numerador = sum(w for inadequada, w in zip(notas_inadequadas, pesos) if inadequada)
    denominador = sum(pesos)
    return numerador / denominador if denominador else 0.0


# Faixas de FLUTUACAO (tolerancia) do delta VAAR-Atendimento por porte da
# rede - confirmado byte a byte contra a Tabela 1 do PDF oficial da Nota
# Tecnica no 3/2026/CGEFE/DIRED-INEP (Resolucao CIF no 25/2026, 23/07/2026).
# Aplica-se somente a variacoes NEGATIVAS (quedas); qualquer delta positivo
# (melhora real) aprova independentemente do porte.
FAIXAS_VAAR_ATENDIMENTO = [
    # (matriculas_min, matriculas_max_ou_None, delta_minimo_tolerado, delta_maximo=0)
    (10_000, None,   -0.0015, 0.0),
    (2_501,  10_000,  -0.0030, 0.0),
    (1_001,  2_500,   -0.0060, 0.0),
    (501,    1_000,   -0.0090, 0.0),
    (251,    500,     -0.0120, 0.0),
    (0,      250,     -0.0150, 0.0),
]


def vaar_atendimento(abandono_total: float, matriculados_total: float, sir_total: float = 0.0) -> float:
    """
    FORMULA CORRIGIDA em 05/09/2026: a apresentacao pi5.pptx (slide 9) trazia
    uma versao simplificada (VAAR-Atendimento = Abandono/Matriculados), mas
    o PDF oficial da Nota Tecnica no 3/2026/CGEFE/DIRED-INEP (pagina 12,
    Equacao 1) mostra a formula real, verificada via pesquisa web:

        VAAR_Atendimento(r,t) = [1 - (ABA/M)] x [1 - 0,5 x (SIR/M)]

    onde ABA = total de abandonos, M = total de matriculados, SIR = total
    de matriculas sem informacao de rendimento/movimento ao final do ano.
    Diferenca crucial: o indicador NAO e a taxa de abandono em si, e sim
    uma taxa de PERMANENCIA (1 - abandono), descontada por um fator de
    penalizacao por falta de informacao (peso 0,5 sobre a taxa de SIR).
    Valores mais proximos de 1 = melhor (mais alunos permaneceram, com
    dados completos); valores mais proximos de 0 = pior.
    """
    if not matriculados_total:
        return 0.0
    fator_abandono = 1 - (abandono_total / matriculados_total)
    fator_sir = 1 - 0.5 * (sir_total / matriculados_total)
    return fator_abandono * fator_sir


def meta_variacao_exigida(numero_matriculas: float) -> tuple[float, float]:
    """Retorna (delta_minimo, delta_maximo) exigido conforme o porte da rede."""
    for minimo, maximo, delta_min, delta_max in FAIXAS_VAAR_ATENDIMENTO:
        teto = maximo if maximo is not None else float("inf")
        if minimo <= numero_matriculas <= teto:
            return (delta_min, delta_max)
    raise ValueError("Porte de rede nao mapeado")


def houve_melhoria_atendimento(vaar_atendimento_atual: float, vaar_atendimento_anterior: float,
                                numero_matriculas: float) -> bool:
    """
    BUG CORRIGIDO em 05/09/2026 apos verificar o texto oficial da Nota
    Tecnica no 3/2026/CGEFE/DIRED-INEP (aprovada pela Resolucao CIF no
    25/2026): a "faixa de flutuacao" NAO e uma meta de reducao exigida -
    e uma banda de TOLERANCIA para pequenas quedas do indicador.

    A rede recebe a parcela VAAR-Atendimento se:
      a) o indicador aumentou (delta > 0) - melhora real, sempre aprova; OU
      b) o indicador ficou estavel (delta == 0), incluindo quedas pequenas
         que caiam dentro da faixa de tolerancia do seu porte (delta >=
         delta_minimo do grupo).

    A versao anterior deste codigo (delta_min <= delta <= delta_max, com
    delta_max = 0) rejeitava incorretamente qualquer delta > 0 - ou seja,
    reprovava redes que tiveram MELHORA real. Corrigido para: aprova
    sempre que delta >= delta_minimo do grupo (nao ha teto superior).
    """
    delta = vaar_atendimento_atual - vaar_atendimento_anterior
    delta_min, _ = meta_variacao_exigida(numero_matriculas)
    return delta >= delta_min


# ---------------------------------------------------------------------------
# 3. EXEMPLO DE VALIDACAO - COTIA/SP 2024 (slide 8, ICMS_Fundeb_CD.pptx)
# ---------------------------------------------------------------------------

def exemplo_cotia_2024():
    """
    Reproduz os numeros publicados no slide 8 para validar a formula de
    cota-parte recebida / perda de receita. Os indices abaixo (IPM, cota
    parte educacao, indice de participacao) sao os VALORES JA PUBLICADOS
    para Cotia em 2024 - nao foram recalculados a partir do IQEM porque a
    base de notas/evolucao/ISE/PATI de Cotia ainda nao foi coletada pelo
    grupo (proximo passo).
    """
    valor_icms_2024 = 341_357_089.75
    indice_participacao_icms_educacional = 0.009307459  # 0,93%
    cota_parte_maxima = 34_135_708.98

    recebida = cota_parte_recebida(valor_icms_2024, indice_participacao_icms_educacional)
    perda = perda_receita_estimada(cota_parte_maxima, recebida)

    print("=== Validacao Cotia/SP 2024 ===")
    print(f"Valor ICMS 2024:            R$ {valor_icms_2024:,.2f}")
    print(f"Indice participacao Educ.:  {indice_participacao_icms_educacional*100:.4f}%")
    print(f"Cota Parte Recebida (calc): R$ {recebida:,.2f}  (publicado: R$ 3.177.167,12)")
    print(f"Cota Parte Maxima:          R$ {cota_parte_maxima:,.2f}")
    print(f"Perda de Receita (calc):    R$ {perda:,.2f}  (publicado: R$ 30.958.541,86)")

    condicionalidades_cotia = CondicionalidadesVAAR(
        gestao_escolar_por_merito=True,
        participacao_saeb_min_80pct=False,  # motivo publicado no slide 8
        reducao_desigualdades=True,
        regime_colaboracao_estado_municipio=True,
        referenciais_curriculares_bncc=True,
    )
    habilitado, motivos = habilitado_vaar(condicionalidades_cotia)
    print(f"\nHabilitado ao VAAR: {habilitado}")
    print("Motivos de inabilitacao:", motivos)


def exemplo_condicionalidade_iii_e_atendimento():
    """
    Exemplo sintetico (sem dados oficiais de aluno-a-aluno ainda coletados)
    so para validar a mecanica das duas formulas trazidas por
    apresentacao pi5.pptx: Condicionalidade III e VAAR-Atendimento.
    """
    print("\n=== Exemplo: Condicionalidade III (reducao de desigualdades) ===")
    notas_2025 = [True, True, False, False, True, False, False, False]  # True = inadequada
    pesos_2025 = [1, 1, 1, 1, 1, 1, 1, 1]
    p_2025 = proporcao_alunos_abaixo_do_nivel(notas_2025, pesos_2025)

    notas_2026 = [True, False, False, False, True, False, False, False]
    pesos_2026 = [1, 1, 1, 1, 1, 1, 1, 1]
    p_2026 = proporcao_alunos_abaixo_do_nivel(notas_2026, pesos_2026)

    print(f"p (2025): {p_2025:.3f}  |  p (2026): {p_2026:.3f}")
    print(f"Habilitado na Cond. III (delta p <= 0): {habilitado_condicionalidade_III(p_2026, p_2025)}")

    print("\n=== Exemplo: Melhoria no Atendimento (VAAR) ===")
    rede_matriculas = 1_800  # grupo 3: 1.001 a 2.500
    vaar_at_anterior = vaar_atendimento(abandono_total=54, matriculados_total=1_800)
    vaar_at_atual = vaar_atendimento(abandono_total=40, matriculados_total=1_800)
    delta_min, _ = meta_variacao_exigida(rede_matriculas)
    print(f"VAAR-Atendimento anterior: {vaar_at_anterior:.4f} | atual: {vaar_at_atual:.4f}  "
          f"(delta = {vaar_at_atual - vaar_at_anterior:+.4f})")
    print(f"Tolerancia do porte ({rede_matriculas} matriculas): delta >= {delta_min}")
    print(f"Recebe a parcela de melhoria no atendimento? "
          f"{houve_melhoria_atendimento(vaar_at_atual, vaar_at_anterior, rede_matriculas)}")

    print("\n--- Caso que o bug antigo reprovava incorretamente (melhora real) ---")
    at_2024 = vaar_atendimento(abandono_total=100, matriculados_total=12_000)  # grupo 1
    at_2025 = vaar_atendimento(abandono_total=60, matriculados_total=12_000)   # abandono caiu
    print(f"Exemplo oficial (Grupo 1, 12.000 matriculas): 2024={at_2024:.4f} -> 2025={at_2025:.4f} "
          f"(delta = {at_2025 - at_2024:+.4f})")
    print(f"Recebe a parcela? {houve_melhoria_atendimento(at_2025, at_2024, 12_000)}  "
          f"(deveria ser True - o bug antigo retornava False para melhoras grandes)")


if __name__ == "__main__":
    exemplo_cotia_2024()
    exemplo_condicionalidade_iii_e_atendimento()
