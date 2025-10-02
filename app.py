# app.py - Construtor de Formulários 5.0 (com Domínios)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from datetime import date, datetime

st.set_page_config(page_title="Construtor de Formulários 5.0", layout="wide")

# =========================
# Catálogo oficial
# =========================
DOMINIOS = [
    "FormularioDominio",
    "FormularioDominioDinamico",
    "FormularioDominioEstatico",
    "FormularioDominioItem",
    "FormularioDominioItemParametro",
    "FormularioDominioItemValor"
]

ELEMENTOS = [
    "FormularioElementoCMC7",
    "FormularioElementoCNPJ",
    "FormularioElementoCPF",
    "FormularioElementoChave",
    "FormularioElementoChaveItem",
    "FormularioElementoCheck",
    "FormularioElementoConteudo",
    "FormularioElementoConteudoParametro",
    "FormularioElementoConteudoValor",
    "FormularioElementoData",
    "FormularioElementoEmail",
    "FormularioElementoGrade",
    "FormularioElementoGradeItem",
    "FormularioElementoMoeda",
    "FormularioElementoNumerico",
    "FormularioElementoNumeroInteiro",
    "FormularioElementoParagrafo",
    "FormularioElementoRegiao",
    "FormularioElementoRotulo",
    "FormularioElementoSeccao",
    "FormularioElementoSelecao",
    "FormularioElementoSelecaoComboBox",
    "FormularioElementoSelecaoComboFiltro",
    "FormularioElementoSelecaoGrupo",
    "FormularioElementoSelecaoGrupoCheck",
    "FormularioElementoSelecaoGrupoRadio",
    "FormularioElementoTabela",
    "FormularioElementoTabelaCelula",
    "FormularioElementoTabelaLinha",
    "FormularioElementoTelefone",
    "FormularioElementoTexto",
    "FormularioElementoTextoArea"
]

# =========================
# Inicializar estado
# =========================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "5.0",
        "dominios": [],   # lista de dicts {nome, tipo, itens: [{item_tipo, chave, descricao, valor}]}
        "secoes": []      # lista de dicts {nome, campos: [{nome, tipo, obrigatorio, metadados...}]}
    }

# =========================
# Validações por tipo
# =========================
def validar_cnpj(v):
    return bool(re.fullmatch(r"\d{14}", v))

def validar_cpf(v):
    return bool(re.fullmatch(r"\d{11}", v))

def validar_email(v):
    return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", v))

def validar_telefone(v):
    return bool(re.fullmatch(r"\+?\d{8,15}", v))

def validar_moeda_str(v):
    return bool(re.fullmatch(r"^\d+(\.\d{1,2})?$", v))

# valida um valor conforme o tipo do elemento
def validar_valor_por_tipo(tipo, valor):
    if valor is None or valor == "":
        return True, ""
    if tipo == "FormularioElementoCNPJ":
        ok = validar_cnpj(valor)
        return ok, "CNPJ inválido (esperado 14 dígitos numéricos)" if not ok else ("", "")
    if tipo == "FormularioElementoCPF":
        ok = validar_cpf(valor)
        return ok, "CPF inválido (esperado 11 dígitos numéricos)" if not ok else ("", "")
    if tipo == "FormularioElementoEmail":
        ok = validar_email(valor)
        return ok, "E-mail inválido" if not ok else ("", "")
    if tipo == "FormularioElementoTelefone":
        ok = validar_telefone(valor)
        return ok, "Telefone inválido (8-15 dígitos, opcional +)" if not ok else ("", "")
    if tipo == "FormularioElementoMoeda":
        ok = validar_moeda_str(str(valor))
        return ok, "Valor monetário inválido (use 2 casas decimais, ex: 123.45)" if not ok else ("", "")
    if tipo in ("FormularioElementoNumeroInteiro", "FormularioElementoNumerico"):
        try:
            _ = float(valor)
            return True, ""
        except:
            return False, "Deve ser um número"
    if tipo == "FormularioElementoData":
        # aceitamos date ou string YYYY-MM-DD
        if isinstance(valor, date):
            return True, ""
        try:
            datetime.strptime(valor, "%Y-%m-%d")
            return True, ""
        except:
            return False, "Data inválida (formato YYYY-MM-DD)"
    return True, ""

# =========================
# Utilitários XML
# =========================
def prettify(elem):
    raw = ET.tostring(elem, 'utf-8')
    return minidom.parseString(raw).toprettyxml(indent="  ")

def exportar_xml(formulario):
    root = ET.Element("formulario", versao=formulario["versao"], nome=formulario.get("nome",""))
    # DOMINIOS
    dominios_el = ET.SubElement(root, "dominios")
    for d in formulario["dominios"]:
        # cria elemento de domínio com tag = tipo da classe Java (p.ex. FormularioDominioEstatico)
        dominio_elem = ET.SubElement(dominios_el, d["tipo"], nome=d["nome"])
        # itens
        for it in d.get("itens", []):
            item_tag = it.get("item_tipo", "dominioItem")
            # para compatibilidade com nomes do Java: use item_tag quando for 'FormularioDominioItemParametro' -> tag 'dominioItemParametro'
            # vamos mapear classes conhecidas para tags
            tag = item_tag
            # se veio com prefixo 'Formulario', convertemos para nome do xml semelhante ao Java XmlType: remover 'Formulario' e deixar em camelCase simples
            if item_tag.startswith("Formulario"):
                tag = item_tag[len("Formulario"):].lstrip()
                # opcional: transformar a primeira letra para minúscula? O Java XmlType no arquivo tinha @XmlType(name="dominioItemParametro")
                # Para preservar similaridade, se tag começa com 'DominioItemParametro' -> usamos 'dominioItemParametro'
                tag = tag[0].lower() + tag[1:] if tag else tag
            # montar elemento
            if it.get("chave") is not None:
                # atributos: chave, descricao, valor (quando existentes)
                attribs = {}
                if it.get("chave") is not None:
                    attribs["chave"] = it["chave"]
                if it.get("descricao") is not None:
                    attribs["descricao"] = it["descricao"]
                if it.get("valor") is not None:
                    attribs["valor"] = it["valor"]
                ET.SubElement(dominio_elem, tag, attrib=attribs)
            else:
                # item sem chave: só descricao/valor como subelemento
                item_el = ET.SubElement(dominio_elem, tag)
                if it.get("descricao"):
                    desc_el = ET.SubElement(item_el, "descricao")
                    desc_el.text = it["descricao"]
                if it.get("valor"):
                    val_el = ET.SubElement(item_el, "valor")
                    val_el.text = it["valor"]

    # SECOES E ELEMENTOS
    secoes_el = ET.SubElement(root, "secoes")
    for s in formulario["secoes"]:
        secao_el = ET.SubElement(secoes_el, "secao", nome=s["nome"])
        for c in s.get("campos", []):
            # cria elemento com tag igual ao tipo (classe Java)
            campo_el = ET.SubElement(secao_el, c["tipo"], nome=c["nome"])
            # incluir obrigatorio como atributo se marcado
            if c.get("obrigatorio"):
                campo_el.set("obrigatorio", "true")
            # detalhes específicos: se seleção, exportar opções; se tabela, exportar linhas/células; se tiver valor, colocar como texto
            if c["tipo"] in ("FormularioElementoSelecao", "FormularioElementoSelecaoComboBox",
                             "FormularioElementoSelecaoComboFiltro", "FormularioElementoSelecaoGrupo",
                             "FormularioElementoSelecaoGrupoCheck", "FormularioElementoSelecaoGrupoRadio"):
                # exportar opções
                for opt in c.get("opcoes", []):
                    ET.SubElement(campo_el, "opcao", chave=opt.get("chave", opt.get("valor", opt.get("label",""))),
                                  descricao=opt.get("descricao", opt.get("label", "")), valor=opt.get("valor", opt.get("label","")))
            elif c["tipo"] == "FormularioElementoTabela":
                for row in c.get("linhas", []):
                    row_el = ET.SubElement(campo_el, "linha")
                    for cell in row.get("celulas", []):
                        ET.SubElement(row_el, "celula", valor=str(cell.get("valor","")))
            else:
                # valor simples como texto do elemento
                if c.get("valor") not in (None, ""):
                    campo_el.text = str(c.get("valor"))
    return prettify(root)

# =========================
# UI - Cabeçalho
# =========================
st.title("Construtor de Formulários 5.0")
col1, col2 = st.columns([3,1])
with col1:
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
with col2:
    st.write("Versão:", st.session_state.formulario["versao"])

st.markdown("---")

# =========================
# UI - Gerenciar Domínios
# =========================
st.header("Domínios")
with st.expander("Adicionar novo Domínio"):
    dn = st.text_input("Nome do Domínio", key="novo_dominio_nome")
    dt = st.selectbox("Tipo do Domínio", DOMINIOS, key="novo_dominio_tipo")
    if st.button("Criar Domínio"):
        if not dn.strip():
            st.error("Informe um nome para o domínio.")
        else:
            st.session_state.formulario["dominios"].append({"nome": dn.strip(), "tipo": dt, "itens": []})
            st.success(f"Domínio '{dn}' criado.")
            st.session_state["novo_dominio_nome"] = ""

# listar domínios existentes e permitir editar/Adicionar itens
if st.session_state.formulario["dominios"]:
    for idx, dom in enumerate(st.session_state.formulario["dominios"]):
        with st.expander(f"Domínio: {dom['nome']}  —  tipo: {dom['tipo']}"):
            # rename domain
            new_name = st.text_input(f"Nome do domínio (editar) [{dom['nome']}]", value=dom['nome'], key=f"dom_name_{idx}")
            new_tipo = st.selectbox("Tipo do domínio (alterar)", DOMINIOS, index=DOMINIOS.index(dom['tipo']), key=f"dom_tipo_{idx}")
            if st.button("Salvar alterações do domínio", key=f"save_dom_{idx}"):
                dom['nome'] = new_name.strip()
                dom['tipo'] = new_tipo
                st.success("Domínio atualizado.")

            st.markdown("**Itens do domínio**")
            # adicionar item
            with st.form(f"form_add_item_{idx}", clear_on_submit=True):
                item_kind = st.selectbox("Tipo do item", ["FormularioDominioItemParametro", "FormularioDominioItemValor", "FormularioDominioItem"], key=f"item_kind_{idx}")
                chave = st.text_input("Chave (opcional — necessária para item parametro/valor)", key=f"item_chave_{idx}")
                descricao = st.text_input("Descrição", key=f"item_desc_{idx}")
                valor = st.text_input("Valor", key=f"item_val_{idx}")
                submitted = st.form_submit_button("Adicionar item")
                if submitted:
                    item = {"item_tipo": item_kind, "chave": chave.strip() if chave else None,
                            "descricao": descricao.strip() if descricao else None,
                            "valor": valor.strip() if valor else None}
                    dom["itens"].append(item)
                    st.success("Item adicionado.")

            # Listar itens
            if dom.get("itens"):
                for j, it in enumerate(dom["itens"]):
                    st.write(f"- [{j}] tipo: {it.get('item_tipo')} | chave: {it.get('chave')} | descricao: {it.get('descricao')} | valor: {it.get('valor')}")
                    cols = st.columns([1,1,1])
                    if cols[0].button("Remover", key=f"rm_dom_{idx}_{j}"):
                        dom["itens"].pop(j)
                        st.experimental_rerun()

st.markdown("---")

# =========================
# UI - Seções e Elementos
# =========================
st.header("Seções e Elementos")
with st.expander("Adicionar nova Seção"):
    nome_sec = st.text_input("Nome da seção", key="novo_nome_secao")
    if st.button("Criar seção"):
        if not nome_sec.strip():
            st.error("Informe um nome para a seção.")
        else:
            st.session_state.formulario["secoes"].append({"nome": nome_sec.strip(), "campos": []})
            st.success(f"Seção '{nome_sec}' criada.")
            st.session_state["novo_nome_secao"] = ""

# Para cada seção: adicionar campos e listar
for s_idx, sec in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"Seção: {sec['nome']}"):
        # editar nome seção
        new_name = st.text_input("Nome da seção (editar)", value=sec['nome'], key=f"sec_name_{s_idx}")
        if st.button("Salvar seção", key=f"save_sec_{s_idx}"):
            sec['nome'] = new_name.strip()
            st.success("Seção atualizada.")

        st.markdown("Adicionar campo/elemento")
        with st.form(f"form_add_campo_{s_idx}", clear_on_submit=True):
            campo_nome = st.text_input("Nome do campo")
            campo_tipo = st.selectbox("Tipo do elemento", ELEMENTOS, key=f"campo_tipo_{s_idx}")
            obrig = st.checkbox("Obrigatório", key=f"campo_obrig_{s_idx}")
            # campos dinâmicos conforme tipo
            metadados = {}
            if campo_tipo == "FormularioElementoTexto":
                metadados["valor"] = st.text_input("Valor padrão (texto)")
            elif campo_tipo == "FormularioElementoTextoArea":
                metadados["valor"] = st.text_area("Valor padrão (texto longo)")
            elif campo_tipo == "FormularioElementoCNPJ":
                v = st.text_input("CNPJ (14 dígitos, somente números)")
                if v and not validar_cnpj(v):
                    st.error("CNPJ deve ter 14 dígitos.")
                metadados["valor"] = v
            elif campo_tipo == "FormularioElementoCPF":
                v = st.text_input("CPF (11 dígitos, somente números)")
                if v and not validar_cpf(v):
                    st.error("CPF deve ter 11 dígitos.")
                metadados["valor"] = v
            elif campo_tipo == "FormularioElementoEmail":
                v = st.text_input("E-mail")
                if v and not validar_email(v):
                    st.error("E-mail inválido.")
                metadados["valor"] = v
            elif campo_tipo == "FormularioElementoTelefone":
                v = st.text_input("Telefone (apenas dígitos, opcional +)")
                if v and v.strip() and not validar_telefone(v):
                    st.error("Telefone inválido.")
                metadados["valor"] = v
            elif campo_tipo == "FormularioElementoMoeda":
                v = st.number_input("Valor monetário (use ponto para decimal)", format="%.2f", step=0.01, key=f"moeda_{s_idx}")
                metadados["valor"] = f"{v:.2f}"
            elif campo_tipo == "FormularioElementoData":
                dflt = date.today()
                v = st.date_input("Data padrão", value=dflt, key=f"date_{s_idx}")
                metadados["valor"] = v.isoformat()
            elif campo_tipo in ("FormularioElementoNumeroInteiro", "FormularioElementoNumerico"):
                v = st.text_input("Valor numérico (digite apenas números)", key=f"num_{s_idx}")
                if v and not re.fullmatch(r"^-?\d+(\.\d+)?$", v):
                    st.error("Valor numérico inválido.")
                metadados["valor"] = v
            elif campo_tipo in ("FormularioElementoSelecao", "FormularioElementoSelecaoComboBox",
                                "FormularioElementoSelecaoComboFiltro", "FormularioElementoSelecaoGrupo",
                                "FormularioElementoSelecaoGrupoCheck", "FormularioElementoSelecaoGrupoRadio"):
                st.write("Defina opções (cada opção tem `label`, `valor` e `chave` opcionais).")
                # colocamos uma mini-lista interativa
                if f"opcoes_{s_idx}" not in st.session_state:
                    st.session_state[f"opcoes_{s_idx}"] = []
                col_a, col_b, col_c = st.columns([3,3,2])
                with col_a:
                    opt_label = st.text_input("Label da opção", key=f"opt_label_{s_idx}")
                with col_b:
                    opt_val = st.text_input("Valor da opção", key=f"opt_val_{s_idx}")
                with col_c:
                    opt_key = st.text_input("Chave (opcional)", key=f"opt_key_{s_idx}")
                if st.button("Adicionar opção", key=f"add_opt_{s_idx}"):
                    if not opt_label and not opt_val:
                        st.error("Informe pelo menos label ou valor.")
                    else:
                        st.session_state[f"opcoes_{s_idx}"].append({"label": opt_label, "valor": opt_val, "chave": opt_key})
                st.write("Opções atuais:")
                for oi, o in enumerate(st.session_state[f"opcoes_{s_idx}"]):
                    cols = st.columns([6,2])
                    cols[0].write(f"- [{oi}] label='{o.get('label')}' valor='{o.get('valor')}' chave='{o.get('chave')}'")
                    if cols[1].button("Remover", key=f"rmopt_{s_idx}_{oi}"):
                        st.session_state[f"opcoes_{s_idx}"].pop(oi)
                metadados["opcoes"] = list(st.session_state.get(f"opcoes_{s_idx}", []))
            elif campo_tipo == "FormularioElementoTabela":
                # Tabela: montar colunas simples e linhas/células
                if f"tabela_{s_idx}" not in st.session_state:
                    st.session_state[f"tabela_{s_idx}"] = {"colunas": [], "linhas": []}
                # adicionar coluna
                col_name = st.text_input("Nome da nova coluna (opcional)", key=f"colname_{s_idx}")
                if st.button("Adicionar coluna", key=f"add_col_{s_idx}") and col_name:
                    st.session_state[f"tabela_{s_idx}"]["colunas"].append(col_name)
                st.write("Colunas:", st.session_state[f"tabela_{s_idx}"]["colunas"])
                # adicionar linha (perguntar valores por coluna)
                if st.session_state[f"tabela_{s_idx}"]["colunas"]:
                    new_linha = []
                    for ccolumn in st.session_state[f"tabela_{s_idx}"]["colunas"]:
                        v = st.text_input(f"Valor coluna '{ccolumn}'", key=f"val_{s_idx}_{ccolumn}")
                        new_linha.append({"col": ccolumn, "valor": v})
                    if st.button("Adicionar linha", key=f"add_row_{s_idx}"):
                        st.session_state[f"tabela_{s_idx}"]["linhas"].append({"celulas": new_linha})
                metadados["linhas"] = st.session_state[f"tabela_{s_idx}"]["linhas"]
            else:
                # fallback campo genérico
                metadados["valor"] = st.text_input("Valor padrão (genérico)", key=f"generic_val_{s_idx}")

            submitted = st.form_submit_button("Adicionar campo")
            if submitted:
                valido, msg = validar_valor_por_tipo(campo_tipo, metadados.get("valor",""))
                if not valido:
                    st.error(msg)
                else:
                    campo = {"nome": campo_nome.strip(), "tipo": campo_tipo, "obrigatorio": obrig}
                    # mesclar metadados
                    campo.update(metadados)
                    sec["campos"].append(campo)
                    st.success(f"Campo '{campo_nome}' adicionado à seção '{sec['nome']}'")
                    # limpar opções/tabela temporárias do session_state
                    if f"opcoes_{s_idx}" in st.session_state:
                        st.session_state[f"opcoes_{s_idx}"] = []
                    if f"tabela_{s_idx}" in st.session_state:
                        st.session_state[f"tabela_{s_idx}"] = {"colunas": [], "linhas": []}

        # listar campos da seção com botões de remoção
        if sec.get("campos"):
            st.markdown("**Campos desta seção**")
            for c_idx, campo in enumerate(sec["campos"]):
                st.write(f"- [{c_idx}] {campo['nome']} ({campo['tipo']}) obrigatorio={campo.get('obrigatorio', False)} valor/payload={campo.get('valor', campo.get('opcoes', campo.get('linhas','')))}")
                if st.button("Remover campo", key=f"rmcampo_{s_idx}_{c_idx}"):
                    sec["campos"].pop(c_idx)
                    st.experimental_rerun()

st.markdown("---")

# =========================
# Exportação XML
# =========================
st.header("Exportar / Visualizar XML")
if st.button("Gerar XML"):
    xml_out = exportar_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", xml_out, file_name="formulario.xml")

# =========================
# Final note
# =========================
st.caption("Observação: nomes de tags XML usam os nomes de classe do catálogo (para manter fidelidade com a documentação Java).\
Você pode ajustar mapeamentos de tag se preferir nomes diferentes no XML.")
