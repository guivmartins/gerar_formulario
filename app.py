# app.py - Construtor de Formulários 6.1 Beta (consolidado)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict

st.set_page_config(page_title="Construtor de Formulários 6.1 Beta", layout="wide")

# -----------------------
# Inicialização do estado
# -----------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "secoes": []  # each -> {"titulo", "largura", "elementos": [ element dicts ]}
    }

# dominios global: chave -> list of {"descricao","valor"}
# created/updated only from element UI when element is a domain type
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# helper for widget keys
def _k(*parts):
    return "::".join(str(p) for p in parts)

# -----------------------
# Supported element types
# -----------------------
ELEMENT_TYPES = [
    "texto", "texto-area", "numero", "numeroInteiro", "data", "moeda",
    "cpf", "cnpj", "telefone", "email", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo", "tabela"
]

# -----------------------
# XML helpers
# -----------------------
def _prettify_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def _create_elemento_xml(parent: ET.Element, el: dict):
    """
    Create <elemento ...> node for element dict el under parent.
    el keys: tipo, titulo, descricao, obrigatorio, largura, altura (opt), dominio_key (opt)
    """
    attrs = {"gxsi:type": el["tipo"]}
    # titulo/descricao for non-tabela and non-section elements
    if el["tipo"] != "tabela":
        if el.get("titulo") is not None:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo",""))
        attrs["obrigatorio"] = str(bool(el.get("obrigatorio", False))).lower()
        if el.get("largura") is not None:
            attrs["largura"] = str(el.get("largura"))
        if el["tipo"] == "texto-area" and el.get("altura"):
            attrs["altura"] = str(el.get("altura"))
        if el["tipo"] in ("comboBox","comboFiltro","grupoRadio","grupoCheck") and el.get("dominio_key"):
            attrs["dominio"] = el.get("dominio_key")
    node = ET.SubElement(parent, "elemento", attrs)
    # paragrafo/rotulo: set valor attribute (equal to titulo)
    if el["tipo"] in ("paragrafo","rotulo"):
        node.set("valor", el.get("titulo",""))
        return node
    # for non-tabela elements, add conteudo valor
    if el["tipo"] != "tabela":
        ET.SubElement(node, "conteudo", {"gxsi:type":"valor"})
    return node

def gerar_gxsi_xml(formulario: dict) -> str:
    """
    Generate GXSI XML, grouping consecutive elements marked in_table into a single <elemento gxsi:type="tabela">.
    """
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome",""),
        "versao": formulario.get("versao","1.0")
    })
    elementos_tag = ET.SubElement(root, "elementos")
    referenced_domains = set()

    for sec in formulario.get("secoes", []):
        sec_attrs = {"gxsi:type":"seccao", "titulo": sec.get("titulo",""), "largura": str(sec.get("largura",500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrs)
        sec_childs = ET.SubElement(sec_el, "elementos")

        elems = sec.get("elementos", [])
        i = 0
        while i < len(elems):
            e = elems[i]
            if e.get("in_table"):
                # open tabela node
                tabela_node = ET.SubElement(sec_childs, "elemento", {"gxsi:type":"tabela"})
                linhas_node = ET.SubElement(tabela_node, "linhas")
                linha_node = ET.SubElement(linhas_node, "linha")
                celulas_node = ET.SubElement(linha_node, "celulas")
                celula_node = ET.SubElement(celulas_node, "celula", {"linhas":"1", "colunas":"1"})
                elementos_in_cell = ET.SubElement(celula_node, "elementos")
                # collect consecutive in_table elements
                while i < len(elems) and elems[i].get("in_table"):
                    child = elems[i]
                    if child["tipo"] in ("comboBox","comboFiltro","grupoRadio","grupoCheck"):
                        dk = child.get("dominio_key")
                        if dk:
                            referenced_domains.add(dk)
                    _create_elemento_xml(elementos_in_cell, child)
                    i += 1
            else:
                if e["tipo"] in ("comboBox","comboFiltro","grupoRadio","grupoCheck"):
                    dk = e.get("dominio_key")
                    if dk:
                        referenced_domains.add(dk)
                _create_elemento_xml(sec_childs, e)
                i += 1

    # build top-level dominios only for referenced keys
    dominios_tag = ET.SubElement(root, "dominios")
    for key in sorted(referenced_domains):
        items = st.session_state.dominios.get(key, [])
        dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
        itens_el = ET.SubElement(dom_el, "itens")
        for it in items:
            ET.SubElement(itens_el, "item", {"gxsi:type":"dominioItemValor", "descricao": it.get("descricao",""), "valor": it.get("valor","")})

    return _prettify_xml(root)

# -----------------------
# Mutators: add section / add element
# -----------------------
def adicionar_secao(titulo: str, largura: int = 500):
    st.session_state.formulario["secoes"].append({
        "titulo": titulo,
        "largura": largura,
        "elementos": []
    })

def adicionar_elemento(sec_idx: int, element: dict):
    st.session_state.formulario["secoes"][sec_idx]["elementos"].append(element)

# -----------------------
# UI (left = builder, right = preview + xml)
# -----------------------
col_builder, col_preview = st.columns([2.4, 1.6])

with col_builder:
    st.title("Construtor de Formulários 6.1 Beta")
    st.subheader("Configuração do formulário")
    st.session_state.formulario["nome"] = st.text_input("Nome do formulário", value=st.session_state.formulario.get("nome",""), key="f_nome")
    st.session_state.formulario["versao"] = st.text_input("Versão", value=st.session_state.formulario.get("versao","1.0"), key="f_versao")

    st.markdown("---")
    st.subheader("Seções")
    # add section
    with st.form("form_add_section", clear_on_submit=True):
        new_title = st.text_input("Título da nova seção", key="new_sec_title")
        new_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="new_sec_width")
        if st.form_submit_button("Adicionar seção"):
            if not new_title.strip():
                st.error("Informe o título da seção.")
            else:
                adicionar_secao(new_title.strip(), int(new_width))
                st.success(f"Seção '{new_title.strip()}' adicionada.")
                st.experimental_rerun()

    # each section expander
    for s_idx, sec in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção [{s_idx}] — {sec['titulo']}", expanded=False):
            # edit section
            sec_title_key = _k("sec_title", s_idx)
            sec_width_key = _k("sec_width", s_idx)
            if sec_title_key not in st.session_state:
                st.session_state[sec_title_key] = sec["titulo"]
            if sec_width_key not in st.session_state:
                st.session_state[sec_width_key] = sec["largura"]
            st.text_input("Título da seção", key=sec_title_key)
            st.number_input("Largura", min_value=100, max_value=1200, key=sec_width_key)
            if st.button("Salvar seção", key=_k("save_section", s_idx)):
                sec["titulo"] = st.session_state[sec_title_key].strip()
                sec["largura"] = int(st.session_state[sec_width_key])
                st.success("Seção atualizada.")

            # show existing elements
            st.markdown("**Elementos desta seção**")
            if sec.get("elementos"):
                for e_idx, el in enumerate(list(sec["elementos"])):
                    cols = st.columns([6,1,1])
                    cols[0].write(f"- [{e_idx}] {el.get('tipo')} — {el.get('titulo','(sem título)')} {'(em tabela)' if el.get('in_table') else ''}")
                    if cols[1].button("Remover", key=_k("rm_elem", s_idx, e_idx)):
                        sec["elementos"].pop(e_idx)
                        st.experimental_rerun()
                    if cols[2].button("Mover cima", key=_k("up_elem", s_idx, e_idx)):
                        if e_idx > 0:
                            sec["elementos"][e_idx-1], sec["elementos"][e_idx] = sec["elementos"][e_idx], sec["elementos"][e_idx-1]
                            st.experimental_rerun()

            st.markdown("---")
            st.markdown("Adicionar novo elemento")
            form_key = _k("form_add_el", s_idx)
            with st.form(form_key, clear_on_submit=True):
                tipo_key = _k("elem_type", s_idx)
                title_key = _k("elem_title", s_idx)
                req_key = _k("elem_req", s_idx)
                table_key = _k("elem_table", s_idx)
                width_key = _k("elem_width", s_idx)
                height_key = _k("elem_height", s_idx)
                domkey_key = _k("elem_domkey", s_idx)
                dom_desc_key = _k("elem_dom_desc", s_idx)
                dom_val_key = _k("elem_dom_val", s_idx)

                if tipo_key not in st.session_state:
                    st.session_state[tipo_key] = "texto"
                tipo = st.selectbox("Tipo de elemento", ELEMENT_TYPES, index=ELEMENT_TYPES.index(st.session_state[tipo_key]) if st.session_state[tipo_key] in ELEMENT_TYPES else 0, key=tipo_key)
                titulo = st.text_input("Título (descrição será igual ao título)", key=title_key)
                obrig = st.checkbox("Obrigatório", key=req_key) if tipo not in ("paragrafo","rotulo","tabela") else False
                in_table = st.checkbox("Pertence à tabela", key=table_key)
                largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=width_key)
                altura = None
                if tipo == "texto-area":
                    altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=height_key)

                dominio_key_text = ""
                # domain inline only for domain-driven types
                if tipo in ("comboBox","comboFiltro","grupoRadio","grupoCheck"):
                    st.markdown("**Configurar domínio do elemento**")
                    dominio_key_text = st.text_input("Chave do domínio (ex: TESTEESTATICO)", key=domkey_key)
                    if dominio_key_text:
                        dk = dominio_key_text.strip()
                        if dk not in st.session_state.dominios:
                            st.session_state.dominios[dk] = []
                        st.text("Adicione opções ao domínio (opcional).")
                        desc = st.text_input("Descrição da opção", key=dom_desc_key)
                        val = st.text_input("Valor da opção (opcional)", key=dom_val_key)
                        if st.button("Adicionar opção ao domínio", key=_k("add_dom_item", s_idx)):
                            if not (desc.strip() or val.strip()):
                                st.error("Informe descrição ou valor para a opção.")
                            else:
                                st.session_state.dominios[dk].append({"descricao": desc.strip(), "valor": (val.strip() or desc.strip())})
                                st.success("Opção adicionada ao domínio.")
                                st.experimental_rerun()
                        # show existing items for this dk
                        items_preview = st.session_state.dominios.get(dk, [])
                        if items_preview:
                            st.write("Itens do domínio:")
                            for oi, it in enumerate(items_preview):
                                c0, c1 = st.columns([6,1])
                                c0.write(f"- [{oi}] {it.get('descricao')} ({it.get('valor')})")
                                if c1.button("Remover", key=_k("rm_dom_item", s_idx, oi, dk)):
                                    st.session_state.dominios[dk].pop(oi)
                                    st.experimental_rerun()

                if st.form_submit_button("Adicionar elemento"):
                    if tipo not in ("paragrafo","rotulo","tabela") and not titulo.strip():
                        st.error("Informe o título do elemento.")
                    else:
                        el = {
                            "tipo": tipo,
                            "titulo": titulo.strip() if titulo else "",
                            "descricao": titulo.strip() if titulo else "",
                            "obrigatorio": bool(obrig),
                            "largura": int(largura),
                            "in_table": bool(in_table),
                        }
                        if altura is not None:
                            el["altura"] = int(altura)
                        if tipo in ("comboBox","comboFiltro","grupoRadio","grupoCheck"):
                            el["dominio_key"] = dominio_key_text.strip() if dominio_key_text else ""
                        # paragrafo/rotulo: valor handled in XML generator
                        adicionar_elemento(s_idx, el)
                        st.success(f"Elemento '{el['titulo'] or el['tipo']}' adicionado à seção '{sec['titulo']}'")
                        st.experimental_rerun()

with col_preview:
    st.header("Pré-visualização & Exportação")
    st.subheader(st.session_state.formulario.get("nome",""))

    # preview of sections and elements with table simulation
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f"### {sec.get('titulo','')}")
        elems = sec.get("elementos", [])
        i = 0
        while i < len(elems):
            el = elems[i]
            if el.get("in_table"):
                # start table block
                html = '<div style="border:1px solid #999;padding:8px;margin-bottom:10px;border-radius:6px;background:#fbfbfb;">'
                html += '<div style="font-weight:600;margin-bottom:6px;">Tabela</div>'
                j = i
                while j < len(elems) and elems[j].get("in_table"):
                    child = elems[j]
                    html += f'<div style="padding:6px 4px;border-top:1px dashed #ddd;">'
                    html += f'<strong>{child.get("titulo","")}</strong> <em>({child.get("tipo")})</em>'
                    if child.get("obrigatorio"):
                        html += ' <span style="color:#c00">(*)</span>'
                    # domain preview
                    if child.get("tipo") in ("comboBox","comboFiltro","grupoRadio","grupoCheck"):
                        dk = child.get("dominio_key","")
                        items = st.session_state.dominios.get(dk, [])
                        html += f'<div style="font-size:12px;color:#444;margin-top:4px;">domínio: <strong>{dk or "-"}</strong> — itens: {", ".join([it["descricao"] for it in items]) or "-"}</div>'
                    html += '</div>'
                    j += 1
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
                i = j
            else:
                t = el.get("tipo")
                title = el.get("titulo","")
                # use deterministic keys using section index and element index
                key_base = _k("pv", s_idx, i)
                if t == "texto":
                    st.text_input(title, key=_k(key_base, "texto"))
                elif t == "texto-area":
                    st.text_area(title, height=el.get("altura",120), key=_k(key_base, "texto-area"))
                elif t == "numero":
                    st.number_input(title, key=_k(key_base, "numero"))
                elif t == "numeroInteiro":
                    st.number_input(title, step=1, key=_k(key_base, "numeroInteiro"))
                elif t == "data":
                    st.date_input(title, key=_k(key_base, "data"))
                elif t == "moeda":
                    st.text_input(f"{title} (moeda)", key=_k(key_base, "moeda"))
                elif t == "cpf":
                    st.text_input(f"{title} (CPF)", key=_k(key_base, "cpf"))
                elif t == "cnpj":
                    st.text_input(f"{title} (CNPJ)", key=_k(key_base, "cnpj"))
                elif t == "telefone":
                    st.text_input(f"{title} (Telefone)", key=_k(key_base, "telefone"))
                elif t == "email":
                    st.text_input(f"{title} (E-mail)", key=_k(key_base, "email"))
                elif t == "check":
                    st.checkbox(title, key=_k(key_base, "check"))
                elif t in ("comboBox","comboFiltro","grupoCheck"):
                    dk = el.get("dominio_key","")
                    opts = [it["descricao"] for it in st.session_state.dominios.get(dk,[])]
                    st.multiselect(title, options=opts, key=_k(key_base, "multiselect"))
                elif t == "grupoRadio":
                    dk = el.get("dominio_key","")
                    opts = [it["descricao"] for it in st.session_state.dominios.get(dk,[])]
                    if opts:
                        st.radio(title, options=opts, key=_k(key_base, "radio"))
                    else:
                        st.write(f"{title} (sem opções no domínio '{el.get('dominio_key','')}')")
                elif t in ("paragrafo","rotulo"):
                    if t == "paragrafo":
                        st.markdown(f"📄 **{title}**")
                    else:
                        st.markdown(f"🏷️ {title}")
                else:
                    st.write(f"{t} - {title}")
                i += 1

    st.markdown("---")
    st.subheader("Pré-visualização do XML")
    xml_out = gerar_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario.xml", mime="application/xml")

# footer notes
st.caption(
    "Notas:\n"
    "- Domínios são definidos no próprio elemento (comboBox/comboFiltro/grupoRadio/grupoCheck). Ao informar uma chave e adicionar opções, essas opções são salvas globalmente por chave e reutilizadas por outros elementos que usarem a mesma chave.\n"
    "- Marque 'Pertence à tabela' em elementos para agrupá-los na mesma tabela. Elementos consecutivos com esse checkbox marcado participam da mesma tabela; quando aparece um elemento sem o checkbox, a tabela fecha.\n"
    "- paragrafo e rotulo gravam 'valor' igual ao 'titulo' automaticamente.\n"
    "- Se quiser, informe pontos adicionais que ajustamos e eu aplico um patch rápido."
)
