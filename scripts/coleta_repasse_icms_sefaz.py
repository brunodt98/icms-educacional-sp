# -*- coding: utf-8 -*-
"""
Coleta automatica: valor em R$ do ICMS efetivamente repassado a cada municipio
de SP, mes a mes, direto do sistema oficial da Sefaz-SP.

Fonte: https://www.fazenda.sp.gov.br/RepasseConsulta/Consulta/repasse.aspx
       ("Repasse de Tributos a Municipios" > Historico Anual)

Essa e' a fonte que faltava para converter a participacao relativa (PRE, que
soma 1,0 entre os municipios) em REAIS - ver a secao "Cadeia ate o valor em
R$" de LIMITACOES_METODOLOGICAS.md.

===========================================================================
O QUE ESSE VALOR E' (E O QUE NAO E') - leia antes de usar
===========================================================================
A coluna "ICMS" do relatorio e' a quota-parte municipal do ICMS
EFETIVAMENTE CREDITADA ao municipio, ou seja:

  - JA E' a parcela dos municipios (os 25% do art. 158, IV da Constituicao),
    nao a arrecadacao total do Estado;
  - JA ESTA LIQUIDA da retencao do FUNDEB. A nota de rodape da propria
    pagina diz: "A partir de marco de 2007 valores liquidos, descontados o
    montante transferido para o FUNDEB, de acordo com a Lei 11.494 de
    20/06/2007 [...] a partir de janeiro de 2009, valores com desconto de
    20%".

Por isso o script grava DUAS colunas:
  - icms_liquido_reais : exatamente o que a Sefaz publica (pos-FUNDEB). E' o
    dinheiro que entra no caixa do municipio.
  - icms_bruto_reais   : icms_liquido / 0,80, ou seja, a quota-parte de 25%
    antes da retencao de 20% do FUNDEB.
Nenhuma das duas e' estimada - a segunda e' a primeira revertendo um
percentual fixado em lei. O painel mostra as duas, rotuladas.

As outras colunas do relatorio (IPVA, Fundo de Exportacao-IPI, Compensacao
Financeira da Lei 7.990/89) sao gravadas tambem, mas NAO entram na cadeia do
ICMS Educacional: usamos so o ICMS, que e' o tributo que a lei estadual do
ICMS Educacional trata.

ANO CORRENTE: o relatorio traz somente os meses ja publicados (em setembro
de 2026, janeiro a setembro). O script detecta o ultimo mes publicado e
grava `meses_publicados` - assim o painel compara periodos comparaveis em
vez de tratar um ano parcial como se fosse fechado.

===========================================================================
DETALHE TECNICO
===========================================================================
Diferente do DIPAM (ver coleta_ipm_sefaz.py, um GET simples), esta pagina e'
um WebForms ASP.NET classico: exige __VIEWSTATE + __EVENTVALIDATION e um
cookie de sessao, e retorna um municipio por requisicao. Implementado so com
biblioteca padrao (urllib + http.cookiejar) DE PROPOSITO, para nao adicionar
dependencia ao projeto (requests/bs4 entrariam so para isso).

Os campos hidden devolvidos em cada resposta servem para a requisicao
seguinte, entao gastamos 1 requisicao por municipio (e nao 2).
"""

import argparse
import html
import http.cookiejar
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

URL = "https://www.fazenda.sp.gov.br/RepasseConsulta/Consulta/repasse.aspx"

CAMPO_MUNICIPIO = "ctl00$ConteudoPagina$ddlMuni"
CAMPO_ANO = "ctl00$ConteudoPagina$ddlAno"
CAMPO_TIPO = "ctl00$ConteudoPagina$rblTipo"
CAMPO_BOTAO = "ctl00$ConteudoPagina$btnConfirmar"

# A pagina da Sefaz mistura codificacoes (o dropdown vem com entidades
# numericas, o corpo da tabela vem em bytes), entao "Marco" as vezes chega
# como "Março" e as vezes como "MarÃ§o". Casamos o mes pelo prefixo de 3
# letras ASCII, que e' unico para os 12 meses e nao depende de acento nenhum.
PREFIXO_MES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# Lei 11.494/2007: 20% da quota-parte municipal do ICMS vao para o FUNDEB
# desde janeiro/2009 (percentuais menores em 2007/2008 - ver rodape da
# pagina da Sefaz). Só suportamos periodos >= 2009, entao a taxa e' fixa.
FUNDEB_RETENCAO = 0.20
PRIMEIRO_ANO_SUPORTADO = 2009


def normalizar_nome_municipio(nome: str) -> str:
    """Mesma normalizacao de coleta_ipm_sefaz.py, para casar as duas fontes."""
    s = str(nome).upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", s).strip()


def _parse_numero_br(s: str):
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _texto(celula_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", celula_html)).strip()


class SessaoRepasse:
    """Sessao HTTP com cookie + os campos hidden do ASP.NET sempre atualizados."""

    def __init__(self, pausa: float = 0.3):
        self.pausa = pausa
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self._opener.addheaders = [("User-Agent", "Mozilla/5.0"), ("Referer", URL)]
        self._hidden = {}
        self.municipios = {}
        self.anos = []
        self._abrir()

    def _ler(self, req_ou_url) -> str:
        with self._opener.open(req_ou_url, timeout=120) as resp:
            bruto = resp.read()
        # O cabecalho anuncia UTF-8, mas partes da pagina vem em windows-1252.
        # Tenta UTF-8 estrito e cai para cp1252 quando os bytes nao sao UTF-8.
        try:
            return bruto.decode("utf-8")
        except UnicodeDecodeError:
            return bruto.decode("cp1252", errors="replace")

    def _guardar_hidden(self, pagina: str) -> None:
        self._hidden = {
            m.group(1): html.unescape(m.group(2))
            for m in re.finditer(
                r'<input type="hidden" name="(__[A-Z]+)"[^>]*value="([^"]*)"', pagina
            )
        }

    def _abrir(self) -> None:
        pagina = self._ler(URL)
        self._guardar_hidden(pagina)
        self.municipios = self._extrair_opcoes(pagina, "ddlMuni")
        anos = self._extrair_opcoes(pagina, "ddlAno")
        self.anos = sorted(int(v) for v in anos.values() if re.fullmatch(r"\d{4}", v))
        if not self.municipios:
            raise ValueError("Nenhum municipio no dropdown - a pagina mudou de formato?")

    @staticmethod
    def _extrair_opcoes(pagina: str, id_select: str) -> dict:
        """{rotulo: valor} do <select> indicado (so o bloco daquele select)."""
        bloco = re.search(
            r'<select[^>]*id="[^"]*' + id_select + r'"[^>]*>(.*?)</select>', pagina, re.S
        )
        if not bloco:
            return {}
        opcoes = re.findall(
            r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', bloco.group(1), re.S
        )
        return {_texto(rotulo): valor for valor, rotulo in opcoes if valor.strip()}

    def consultar(self, codigo_municipio: str, ano: int, tentativas: int = 3) -> list:
        """Retorna uma lista de dicts (um por mes publicado) para o municipio/ano."""
        erro_final = None
        for tentativa in range(tentativas):
            dados = {
                **self._hidden,
                CAMPO_MUNICIPIO: codigo_municipio,
                CAMPO_ANO: str(ano),
                CAMPO_TIPO: "ANO",
                CAMPO_BOTAO: "Confirmar",
            }
            corpo = urllib.parse.urlencode(
                dados, encoding="cp1252", errors="replace"
            ).encode("cp1252")
            try:
                pagina = self._ler(urllib.request.Request(URL, data=corpo))
                self._guardar_hidden(pagina)  # reaproveita na proxima requisicao
                time.sleep(self.pausa)        # nao martelar o servidor do Estado
                return self._extrair_meses(pagina)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                erro_final = e
                time.sleep(2 * (tentativa + 1))
                self._abrir()  # sessao pode ter expirado: recomeca
        raise RuntimeError("Falha apos " + str(tentativas) + " tentativas: " + str(erro_final))

    @staticmethod
    def _extrair_meses(pagina: str) -> list:
        """Le a tabela 'Meses | ICMS | IPVA | Fund.Exp-IPI | Comp. | Total'."""
        linhas = []
        for tabela in re.findall(r"<table.*?</table>", pagina, re.S):
            for linha in re.findall(r"<tr[^>]*>(.*?)</tr>", tabela, re.S):
                celulas = [
                    _texto(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", linha, re.S)
                ]
                if len(celulas) != 6:
                    continue
                mes = PREFIXO_MES.get(celulas[0][:3].lower())
                if mes is None:
                    continue  # ignora cabecalho e a linha "Total" (recalculamos)
                linhas.append({
                    "mes_nome": MESES[mes - 1],
                    "mes": mes,
                    "icms_liquido_reais": _parse_numero_br(celulas[1]),
                    "ipva_reais": _parse_numero_br(celulas[2]),
                    "fundo_exportacao_ipi_reais": _parse_numero_br(celulas[3]),
                    "compensacao_financeira_reais": _parse_numero_br(celulas[4]),
                })
        return linhas


def coletar_repasse_ano(ano: int, limite=None, pausa: float = 0.3) -> pd.DataFrame:
    """Coleta o repasse mensal de todos os municipios de SP para um ano civil."""
    if ano < PRIMEIRO_ANO_SUPORTADO:
        raise ValueError(
            "Ano " + str(ano) + " anterior a " + str(PRIMEIRO_ANO_SUPORTADO) + ": a retencao "
            "do FUNDEB era diferente (ver rodape da pagina da Sefaz) e icms_bruto_reais "
            "ficaria errado."
        )
    sessao = SessaoRepasse(pausa=pausa)
    if ano not in sessao.anos:
        raise ValueError("Ano " + str(ano) + " indisponivel. Disponiveis: " + str(sessao.anos))

    ignorar = {"---", " ", ""}
    itens = sorted((n, c) for n, c in sessao.municipios.items() if n not in ignorar)
    if limite:
        itens = itens[:limite]
    print("Coletando repasse de ICMS de " + str(len(itens)) + " municipios para " + str(ano)
          + " (1 requisicao por municipio, pausa " + str(pausa) + "s)...")

    registros, falhas = [], []
    for i, (nome, codigo) in enumerate(itens, start=1):
        try:
            meses = sessao.consultar(codigo, ano)
        except RuntimeError as e:
            falhas.append(nome)
            print("  [" + str(i) + "/" + str(len(itens)) + "] FALHOU " + nome + ": " + str(e))
            continue
        for linha in meses:
            registro = {
                "municipio": nome,
                "municipio_chave": normalizar_nome_municipio(nome),
                "codigo_repasse_sefaz": codigo,
                "ano": ano,
            }
            registro.update(linha)
            registros.append(registro)
        if i % 50 == 0 or i == len(itens):
            print("  [" + str(i) + "/" + str(len(itens)) + "] " + nome)

    if falhas:
        print("Aviso: " + str(len(falhas)) + " municipios falharam: " + str(falhas[:10]))

    df = pd.DataFrame(registros)
    if df.empty:
        raise ValueError("Nenhum dado coletado - a pagina pode ter mudado de formato.")
    df["icms_bruto_reais"] = df["icms_liquido_reais"] / (1 - FUNDEB_RETENCAO)
    return df.sort_values(["municipio", "mes"])


def resumir_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega o mensal em um total por municipio/ano, com o numero de meses publicados."""
    resumo = df.groupby(["ano", "municipio", "municipio_chave"], as_index=False).agg(
        icms_liquido_reais=("icms_liquido_reais", "sum"),
        icms_bruto_reais=("icms_bruto_reais", "sum"),
        meses_publicados=("mes", "nunique"),
        ultimo_mes=("mes", "max"),
    )
    resumo["periodo_fechado"] = resumo["meses_publicados"] == 12
    return resumo


def carregar_repasse(ano: int, base_dir: str = ".") -> pd.DataFrame:
    """Le o CSV mensal ja coletado e devolve o resumo por municipio (usado no consolidador)."""
    caminho = os.path.join(base_dir, "data", "raw", "repasse_icms_sp_" + str(ano) + ".csv")
    return resumir_por_ano(pd.read_csv(caminho))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Coleta o repasse de ICMS da Sefaz-SP por municipio.")
    ap.add_argument("anos", nargs="*", type=int, default=[2025, 2026],
                    help="anos civis a coletar (padrao: 2025 2026)")
    ap.add_argument("--limite", type=int, default=None,
                    help="so os N primeiros municipios (para teste rapido)")
    ap.add_argument("--pausa", type=float, default=0.3, help="pausa entre requisicoes, em segundos")
    ap.add_argument("--forcar", action="store_true", help="recoleta mesmo se o CSV do ano existir")
    args = ap.parse_args()

    os.makedirs("data/raw", exist_ok=True)
    for ano in args.anos:
        destino = "data/raw/repasse_icms_sp_" + str(ano) + ".csv"
        if os.path.exists(destino) and not args.forcar and not args.limite:
            print(destino + " ja existe - use --forcar para recoletar. Pulando " + str(ano) + ".")
            continue
        df = coletar_repasse_ano(ano, limite=args.limite, pausa=args.pausa)
        if not args.limite:
            df.to_csv(destino, index=False)
        resumo = resumir_por_ano(df)
        print("OK " + str(ano) + ": " + str(len(resumo)) + " municipios, meses publicados "
              + str(sorted(resumo["meses_publicados"].unique())))
        print("   ICMS liquido repassado: R$ {:,.2f}".format(resumo["icms_liquido_reais"].sum()))
        print("   ICMS bruto (/0,80):     R$ {:,.2f}".format(resumo["icms_bruto_reais"].sum()))
        if not args.limite:
            print("   Salvo em " + destino)
