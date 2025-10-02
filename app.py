# app.py - Construtor de Formulários 5.0 (corrigido e com preview lateral)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from datetime import date, datetime

st.set_page_config(page_title="Construtor de Formulários 5.0", layout="wide")

# =========================
# Catálogo oficial (extraído dos arquivos Java)
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
# Inicialização segura do session_state
# =========================
# Estrutura principal do formulário
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "5.0",
        "dominios": [],   # cada domínio -> {nome, tipo, itens: [{item_tipo, chave, descricao, valor}]}
        "secoes": []      # cada seção -> {nome, campos: [{nome, tipo, obrigatorio, ...}]}
    }

# Contadores/flags temporários para garantir chaves únicas se necessário
if "ui_counters" not in st.session_state:
    st.session_state.ui_counters = {"dom": 0, "sec": 0, "campo": 0, "opcao": 0, "tabela": 0}

# Para armazenar opções/tabela temporárias por seção (cada seção terá seu índice)
# Observação: usaremos forms com clear_on_submit para a maior parte das entradas, minimizando a necessidade desses estados.
# Ainda assim inicializamos um dicionário vazio para segurança.
if "temp" not in st.session_state:
    st.session_state.temp = {}

# =========================
# Funções de validação por tipo
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

def validar_valor_por_tipo(tipo, valor):
    if valor is None or valor == "":
        return True, ""
    if tipo == "FormularioElementoCNPJ":
        ok = validar_cnpj(valor)
        return ok, "CNPJ inválido (esperado 14 dígitos numéricos)" if not ok else (True, "")
    if tipo == "FormularioElementoCPF":
        ok = validar_cpf(valor)
        return ok, "CPF inválido (esperado 11 dígitos numéricos)" if not ok else (True, "")
    if tipo == "FormularioElementoEmail":
        ok = validar_email(valor)
        return ok, "E-mail inválido" if not ok else (True, "")
    if tipo == "FormularioElementoTelefone":
        ok = validar_telefone(valor)
        return ok, "Telefone inválido (8-15 dígitos, opcional +)" if not ok else (True, "")
    if tipo == "FormularioElementoMoeda":
        ok = validar_moeda_str(str(valor))
        return ok, "Valor monetário inválido (use 2 casas decimais, ex: 123.45)" if not ok else (True, "")
    if tipo in ("FormularioElementoNumeroInteiro", "FormularioElementoNumerico"):
        try:
            float(valor)
            return True, ""
        except:
            return False, "Deve ser um número"
    if tipo == "FormularioElementoData":
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
        dominio_elem = ET.SubElement(dominios_el, d["tipo"], nome=d["nome"])
        for it in d.get("itens", []):
            # derive tag a partir do item_tipo: 
            item_tag = it.get("item_tipo", "dominioItem")
            # se vier com prefixo 'Formulario', remova esse prefixo para formar algo semelhante ao XmlType nos Java files
            tag = item_tag
            if item_tag.startswith("Formulario"):
                tag = item_tag[len("Formulario"):].lstrip()
                if tag:
                    tag = tag[0].lower() + tag[1:]
            # atributos (chave, descricao, valor) quando existirem
            attribs = {}
            if it.get("chave") not in (None, ""):
                attribs["chave"] = it.get("chave")
            if it.get("descricao") not in (None, ""):
                attribs["descricao"] = it.get("descricao")
            if it.get("valor") not in (None, ""):
                attribs["valor"] = it.get("valor")
            ET.SubElement(dominio_elem, tag, attrib=attribs)

    # SECOES E ELEMENTOS
    secoes_el = ET.SubElement(root, "secoes")
    for s in formulario["secoes"]:
        secao_el = ET.SubElement(secoes_el, "secao", nome=s["nome"])
        for c in s.get("campos", []):
            campo_el = ET.SubElement(secao_el, c["tipo"], nome=c["nome"])
            if c.get("obrigatorio"):
                campo_el.set("obrigatorio", "true")
            # seleção -> exporta opções
            if c["tipo"] in ("FormularioElementoSelecao", "FormularioElementoSelecaoComboBox",
                             "FormularioElementoSelecaoComboFiltro", "FormularioElementoSelecaoGrupo",
                             "FormularioElementoSelecaoGrupoCheck", "FormularioElementoSelecaoGrupoRadio"):
                for opt in c.get("opcoes", []):
                    ET.SubElement(campo_el, "opcao", chave=opt.get("chave", opt.get("valor", opt.get("label",""))),
                                  descricao=opt.get("descricao", opt.get("label", "")), valor=opt.get("valor", opt.get("label","")))
            elif c["tipo"] == "FormularioElementoTabela":
                for row in c.get("linhas", []):
                    row_el = ET.SubElement(campo_el, "linha")
                    for cell in row.get("celulas", []):
                        ET.SubElement(row_el, "celula", valor=str(cell.get("valor","")))
            else:
                if c.get("valor") not in (None, ""):
                    campo_el.text = str(c.get("valor"))
    return prettify(root)

# =========================
# UI - Layout: controles (esquerda) e preview (direita)
# =========================
st.title("Construtor de Formulários 5.0 (corrigido)")

col_controles, col_preview = st.columns([2.6,1.4])

with col_controles:
    # Header: nome do formulário e versão
    st.subheader("Configuração")
    nome_form = st.text_input("Nome do Formulário", value=st.session_state.formulario.get("nome",""))
    # atualizar o nome do formulário diretamente no estado (não conflita com widget)
    st.session_state.formulario["nome"] = nome_form

    st.markdown("---")

    # -------------------------
    # Gerenciar DOMÍNIOS (usando form com clear_on_submit)
    # -------------------------
    st.header("Domínios")
    with st.form("form_add_dom", clear_on_submit=True):
        dn = st.text_input("Nome do Domínio", key="form_dom_nome")
        dt = st.selectbox("Tipo do Domínio", DOMINIOS, index=0, key="form_dom_tipo")
        submitted_dom = st.form_submit_button("Criar Domínio")
        if submitted_dom:
            if not dn or not dn.strip():
                st.error("Informe um nome para o domínio.")
            else:
                st.session_state.formulario["dominios"].append({"nome": dn.strip(), "tipo": dt, "itens": []})
                st.success(f"Domínio '{dn.strip()}' criado.")

    # Exibir/editar domínios
    if st.session_state.formulario["dominios"]:
        for idx, dom in enumerate(st.session_state.formulario["dominios"]):
            with st.expander(f"Domínio [{idx}] — {dom['nome']} ({dom['tipo']})", expanded=False):
                # edição do nome/tipo - widgets com chaves únicas
                new_name = st.text_input("Nome do domínio", value=dom['nome'], key=f"dom_name_{idx}")
                new_type = st.selectbox("Tipo do domínio", DOMINIOS, index=DOMINIOS.index(dom['tipo']), key=f"dom_type_{idx}")
                if st.button("Salvar alterações do domínio", key=f"save_dom_{idx}"):
                    dom['nome'] = new_name.strip()
                    dom['tipo'] = new_type
                    st.success("Domínio atualizado.")

                # adicionar item ao domínio (form interno)
                with st.form(f"form_add_dom_item_{idx}", clear_on_submit=True):
                    item_kind = st.selectbox("Tipo do item", ["FormularioDominioItemParametro", "FormularioDominioItemValor", "FormularioDominioItem"], key=f"item_kind_{idx}")
                    chave = st.text_input("Chave (opcional)", key=f"item_chave_{idx}")
                    descricao = st.text_input("Descrição", key=f"item_desc_{idx}")
                    valor = st.text_input("Valor", key=f"item_val_{idx}")
                    add_item = st.form_submit_button("Adicionar item")
                    if add_item:
                        dom["itens"].append({
                            "item_tipo": item_kind,
                            "chave": chave.strip() if chave else None,
                            "descricao": descricao.strip() if descricao else None,
                            "valor": valor.strip() if valor else None
                        })
                        st.success("Item adicionado ao domínio.")

                # listar itens do domínio com opções de remoção
                if dom.get("itens"):
                    st.write("Itens do domínio:")
                    for j, it in enumerate(list(dom["itens"])):  # create copy to safely iterate/rem
                        cols = st.columns([6,1])
                        cols[0].write(f"- [{j}] tipo={it.get('item_tipo')} | chave={it.get('chave')} | descricao={it.get('descricao')} | valor={it.get('valor')}")
                        if cols[1].button("Remover", key=f"rm_dom_{idx}_{j}"):
                            dom["itens"].pop(j)
                            st.experimental_rerun()

    st.markdown("---")

    # -------------------------
    # Gerenciar SEÇÕES e CAMPOS
    # -------------------------
    st.header("Seções e Elementos")
    # adicionar nova seção (form com clear_on_submit)
    with st.form("form_add_sec", clear_on_submit=True):
        nome_sec = st.text_input("Nome da nova seção", key="form_sec_nome")
        add_sec = st.form_submit_button("Criar seção")
        if add_sec:
            if not nome_sec or not nome_sec.strip():
                st.error("Informe um nome para a seção.")
            else:
                st.session_state.formulario["secoes"].append({"nome": nome_sec.strip(), "campos": []})
                st.success(f"Seção '{nome_sec.strip()}' criada.")

    # para cada seção: expander com formulário de adição de campo (cada um em seu próprio form para clear_on_submit)
    if st.session_state.formulario["secoes"]:
        for s_idx, sec in enumerate(st.session_state.formulario["secoes"]):
            with st.expander(f"Seção [{s_idx}] — {sec['nome']}", expanded=False):
                new_name_sec = st.text_input("Editar nome da seção", value=sec['nome'], key=f"sec_name_{s_idx}")
                if st.button("Salvar seção", key=f"save_sec_{s_idx}"):
                    sec['nome'] = new_name_sec.strip()
                    st.success("Seção atualizada.")

                st.markdown("**Adicionar campo/elemento**")
                # cada adição de campo é um form independente, para permitir clear_on_submit sem mexer no session_state global
                form_key = f"form_add_campo_{s_idx}"
                with st.form(form_key, clear_on_submit=True):
                    campo_nome = st.text_input("Nome do campo", key=f"campo_nome_{s_idx}")
                    campo_tipo = st.selectbox("Tipo do elemento", ELEMENTOS, index=0, key=f"campo_tipo_{s_idx}")
                    obrig = st.checkbox("Obrigatório", key=f"campo_obrig_{s_idx}")

                    # Dinâmica de campos por tipo (input simples aqui; complexos tratados abaixo)
                    metadados = {}

                    if campo_tipo == "FormularioElementoTexto":
                        metadados["valor"] = st.text_input("Valor padrão (texto)", key=f"val_text_{s_idx}")
                    elif campo_tipo == "FormularioElementoTextoArea":
                        metadados["valor"] = st.text_area("Valor padrão (texto longo)", key=f"val_textarea_{s_idx}")
                    elif campo_tipo == "FormularioElementoCNPJ":
                        v = st.text_input("CNPJ (14 dígitos - somente números)", key=f"val_cnpj_{s_idx}")
                        if v and not validar_cnpj(v):
                            st.error("CNPJ inválido (14 dígitos).")
                        metadados["valor"] = v
                    elif campo_tipo == "FormularioElementoCPF":
                        v = st.text_input("CPF (11 dígitos - somente números)", key=f"val_cpf_{s_idx}")
                        if v and not validar_cpf(v):
                            st.error("CPF inválido (11 dígitos).")
                        metadados["valor"] = v
                    elif campo_tipo == "FormularioElementoEmail":
                        v = st.text_input("E-mail", key=f"val_email_{s_idx}")
                        if v and not validar_email(v):
                            st.error("E-mail inválido.")
                        metadados["valor"] = v
                    elif campo_tipo == "FormularioElementoTelefone":
                        v = st.text_input("Telefone (apenas dígitos, opcional +)", key=f"val_tel_{s_idx}")
                        if v and v.strip() and not validar_telefone(v):
                            st.error("Telefone inválido.")
                        metadados["valor"] = v
                    elif campo_tipo == "FormularioElementoMoeda":
                        v = st.number_input("Valor monetário (use ponto para decimal)", format="%.2f", step=0.01, key=f"val_moeda_{s_idx}")
                        metadados["valor"] = f"{v:.2f}"
                    elif campo_tipo == "FormularioElementoData":
                        dflt = date.today()
                        v = st.date_input("Data padrão", value=dflt, key=f"val_date_{s_idx}")
                        metadados["valor"] = v.isoformat()
                    elif campo_tipo in ("FormularioElementoNumeroInteiro", "FormularioElementoNumerico"):
                        v = st.text_input("Valor numérico (digite apenas números)", key=f"val_num_{s_idx}")
                        if v and not re.fullmatch(r"^-?\d+(\.\d+)?$", v):
                            st.error("Valor numérico inválido.")
                        metadados["valor"] = v
                    elif campo_tipo in ("FormularioElementoSelecao", "FormularioElementoSelecaoComboBox",
                                        "FormularioElementoSelecaoComboFiltro", "FormularioElementoSelecaoGrupo",
                                        "FormularioElementoSelecaoGrupoCheck", "FormularioElementoSelecaoGrupoRadio"):
                        # opções interativas mantidas no session_state.temp por seção
                        temp_key = f"opcoes_{s_idx}"
                        if temp_key not in st.session_state.temp:
                            st.session_state.temp[temp_key] = []

                        cols = st.columns([3,3,2])
                        opt_label = cols[0].text_input("Label da opção", key=f"opt_label_{s_idx}")
                        opt_val = cols[1].text_input("Valor da opção", key=f"opt_val_{s_idx}")
                        opt_key = cols[2].text_input("Chave (opcional)", key=f"opt_key_{s_idx}")
                        if st.button("Adicionar opção", key=f"btn_add_opt_{s_idx}"):
                            if not opt_label and not opt_val:
                                st.error("Informe pelo menos label ou valor.")
                            else:
                                st.session_state.temp[temp_key].append({"label": opt_label, "valor": opt_val, "chave": opt_key})
                        st.write("Opções atuais:")
                        for oi, o in enumerate(st.session_state.temp[temp_key]):
                            c0, c1 = st.columns([6,1])
                            c0.write(f"- [{oi}] label='{o.get('label')}' valor='{o.get('valor')}' chave='{o.get('chave')}'")
                            if c1.button("Remover", key=f"btn_rmopt_{s_idx}_{oi}"):
                                st.session_state.temp[temp_key].pop(oi)
                                st.experimental_rerun()
                        metadados["opcoes"] = list(st.session_state.temp.get(temp_key, []))
                    elif campo_tipo == "FormularioElementoTabela":
                        # tabela temporária por seção
                        tab_key = f"tabela_{s_idx}"
                        if tab_key not in st.session_state.temp:
                            st.session_state.temp[tab_key] = {"colunas": [], "linhas": []}
                        # adicionar coluna
                        col_name = st.text_input("Nome da nova coluna (opcional)", key=f"colname_{s_idx}")
                        if st.button("Adicionar coluna", key=f"btn_add_col_{s_idx}") and col_name:
                            st.session_state.temp[tab_key]["colunas"].append(col_name)
                        st.write("Colunas:", st.session_state.temp[tab_key]["colunas"])
                        # adicionar linha (valores por coluna)
                        if st.session_state.temp[tab_key]["colunas"]:
                            values = []
                            for ccol in st.session_state.temp[tab_key]["colunas"]:
                                val = st.text_input(f"Valor coluna '{ccol}'", key=f"val_{s_idx}_{ccol}")
                                values.append({"col": ccol, "valor": val})
                            if st.button("Adicionar linha", key=f"btn_add_row_{s_idx}"):
                                st.session_state.temp[tab_key]["linhas"].append({"celulas": values})
                        st.write("Linhas atuais:")
                        for lr, l in enumerate(st.session_state.temp[tab_key]["linhas"]):
                            st.write(f"- linha {lr}: {[c['valor'] for c in l['celulas']]}")
                        metadados["linhas"] = list(st.session_state.temp[tab_key]["linhas"])
                    else:
                        metadados["valor"] = st.text_input("Valor padrão (genérico)", key=f"val_generic_{s_idx}")

                    add_campo = st.form_submit_button("Adicionar campo")
                    if add_campo:
                        # validação final antes de adicionar
                        valido, msg = validar_valor_por_tipo(campo_tipo, metadados.get("valor",""))
                        if not valido:
                            st.error(msg)
                        else:
                            campo = {"nome": campo_nome.strip(), "tipo": campo_tipo, "obrigatorio": bool(obrig)}
                            campo.update(metadados)
                            sec["campos"].append(campo)
                            st.success(f"Campo '{campo_nome}' adicionado à seção '{sec['nome']}'")
                            # limpar temporários
                            temp_key = f"opcoes_{s_idx}"
                            if temp_key in st.session_state.temp:
                                st.session_state.temp[temp_key] = []
                            tab_key = f"tabela_{s_idx}"
                            if tab_key in st.session_state.temp:
                                st.session_state.temp[tab_key] = {"colunas": [], "linhas": []}

                # listar campos com opções de remoção
                if sec.get("campos"):
                    st.markdown("**Campos desta seção**")
                    for c_idx, campo in enumerate(list(sec["campos"])):
                        st.write(f"- [{c_idx}] {campo['nome']} ({campo['tipo']}) obrigatorio={campo.get('obrigatorio', False)}")
                        if st.button("Remover campo", key=f"rmcampo_{s_idx}_{c_idx}"):
                            sec["campos"].pop(c_idx)
                            st.experimental_rerun()

with col_preview:
    # -------------------------
    # Painel de preview: exibe uma versão "interativa" resumida do formulário à direita
    # -------------------------
    st.subheader("Pré-visualização")
    st.caption("Visualização rápida do formulário — não é um formulário funcional completo, apenas um preview.")
    preview_box = st.container()
    def render_preview():
        preview_box.empty()
        with preview_box:
            st.markdown(f"**{st.session_state.formulario.get('nome','(sem nome)')}**  —  Versão {st.session_state.formulario.get('versao')}")
            st.markdown("**Domínios**")
            if not st.session_state.formulario["dominios"]:
                st.write("_Nenhum domínio definido._")
            else:
                for di, dom in enumerate(st.session_state.formulario["dominios"]):
                    st.write(f"- {dom['nome']} ({dom['tipo']}) — itens: {len(dom.get('itens',[]))}")
            st.markdown("---")
            st.markdown("**Seções**")
            if not st.session_state.formulario["secoes"]:
                st.write("_Nenhuma seção definida._")
            else:
                for si, sec in enumerate(st.session_state.formulario["secoes"]):
                    st.markdown(f"**{si}. {sec['nome']}**")
                    if not sec.get("campos"):
                        st.write("_sem campos_")
                    else:
                        for campo in sec.get("campos", []):
                            # representação simples por tipo
                            tipo = campo["tipo"]
                            nome = campo["nome"]
                            obrig = campo.get("obrigatorio", False)
                            if tipo in ("FormularioElementoTexto", "FormularioElementoTextoArea"):
                                st.text_input(f"{nome} {'*' if obrig else ''}", value=campo.get("valor",""), key=f"prev_{si}_{nome}", disabled=True)
                            elif tipo in ("FormularioElementoCNPJ", "FormularioElementoCPF", "FormularioElementoEmail", "FormularioElementoTelefone"):
                                st.text_input(f"{nome} {'*' if obrig else ''}", value=campo.get("valor",""), key=f"prev_{si}_{nome}", disabled=True)
                            elif tipo == "FormularioElementoMoeda":
                                try:
                                    val = float(campo.get("valor", 0))
                                except:
                                    val = 0.0
                                st.number_input(f"{nome} {'*' if obrig else ''}", value=val, step=0.01, key=f"prev_{si}_{nome}", disabled=True)
                            elif tipo == "FormularioElementoData":
                                try:
                                    val_date = campo.get("valor")
                                    if isinstance(val_date, str):
                                        val_date = datetime.fromisoformat(val_date).date()
                                    elif val_date is None:
                                        val_date = date.today()
                                except:
                                    val_date = date.today()
                                st.date_input(f"{nome} {'*' if obrig else ''}", value=val_date, key=f"prev_{si}_{nome}", disabled=True)
                            elif tipo in ("FormularioElementoSelecao", "FormularioElementoSelecaoComboBox",
                                          "FormularioElementoSelecaoComboFiltro", "FormularioElementoSelecaoGrupo",
                                          "FormularioElementoSelecaoGrupoCheck", "FormularioElementoSelecaoGrupoRadio"):
                                # mostrar opções
                                opts = campo.get("opcoes", [])
                                labels = [o.get("label") or o.get("valor") for o in opts]
                                if not labels:
                                    st.write(f"{nome}: _sem opções_")
                                else:
                                    # se é grupo radio -> show radio, else multiselect / selectbox depending on subtype
                                    if "Radio" in tipo:
                                        st.radio(f"{nome} {'*' if obrig else ''}", options=labels, key=f"prev_{si}_{nome}", disabled=True)
                                    elif "Check" in tipo:
                                        # check group -> mostrar checkboxes desabilitados
                                        for lb in labels:
                                            st.checkbox(lb, value=False, key=f"prev_{si}_{nome}_{lb}", disabled=True)
                                    else:
                                        st.selectbox(f"{nome} {'*' if obrig else ''}", options=labels, key=f"prev_{si}_{nome}", disabled=True)
                            elif tipo == "FormularioElementoTabela":
                                st.write(f"{nome} (tabela) — {len(campo.get('linhas',[]))} linhas")
                                # mostrar pequena tabela
                                linhas = campo.get("linhas", [])
                                if linhas:
                                    # montar tabela simples
                                    table_rows = []
                                    headers = [c['col'] for c in (linhas[0]['celulas'] if linhas[0].get('celulas') else [])]
                                    if headers:
                                        st.write(" | ".join(headers))
                                    for lr in linhas:
                                        vals = [str(c['valor']) for c in lr.get("celulas",[])]
                                        st.write(" | ".join(vals))
                            else:
                                # fallback textual
                                st.text_input(f"{nome} {'*' if obrig else ''}", value=str(campo.get("valor","")), key=f"prev_{si}_{nome}", disabled=True)

    # Render preview immediately once (and it will re-render each run)
    render_preview()

# =========================
# Exportação e download XML
# =========================
st.markdown("---")
st.header("Exportar / Visualizar XML")
if st.button("Gerar XML"):
    xml_out = exportar_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", xml_out, file_name="formulario.xml")

# Nota final
st.caption("Este editor respeita o catálogo extraído dos arquivos Java. Se quiser que o XML tenha nomes de tags idênticos aos @XmlType(name=...), posso gerar um mapeamento automático entre classes e tags.")
