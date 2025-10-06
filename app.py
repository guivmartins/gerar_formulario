# app.py - Construtor GXSI (v6.4 restauração UI de domínios da v5.0)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Construtor GXSI - v6.4 (domínios v5.0)", layout="wide")

# --------------------------
# Config / helpers
# --------------------------
ELEMENT_TYPES = [
    "texto", "texto-area", "data", "moeda",
    "cpf", "cnpj", "email", "telefone", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo"
]
DOMAIN_TYPES = {"comboBox", "comboFiltro", "grupoRadio", "grupoCheck"}

def normalize_domain_key_v5(title: str) -> str:
    """Regra v5.0: remove acentos/nao-alfa, junta e limita a 20 chars, uppercase"""
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r'[^0-9A-Za-z]+', '', s)
    return s[:20].upper()

def prettify_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

# --------------------------
# Session state init
# --------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "Formulário Exemplo", "versao": "1.0", "secoes": []}

# dominios globais: chave -> {"tipo": "estatico"|"dinamico", "itens":[{"descricao","valor"}]}
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# --------------------------
# XML generation (compatível v4.0)
# --------------------------
def create_element_xml(parent: ET.Element, el: dict):
    attrs = {"gxsi:type": el["tipo"]}
    if el["tipo"] != "tabela":
        if "titulo" in el:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo", ""))
        if "largura" in el:
            attrs["largura"] = str(el.get("largura"))
        if el["tipo"] not in ("paragrafo", "rotulo"):
            attrs["obrigatorio"] = str(bool(el.get("obrigatorio", False))).lower()
        if el.get("colunas") is not None:
            attrs["colunas"] = str(el.get("colunas"))
        if el["tipo"] == "texto-area" and el.get("altura") is not None:
            attrs["altura"] = str(el.get("altura"))
        if el.get("dominio"):
            attrs["dominio"] = el["dominio"]["chave"]
    node = ET.SubElement(parent, "elemento", attrs)
    if el["tipo"] in ("paragrafo", "rotulo"):
        node.set("valor", el.get("titulo", ""))
        return node
    if el["tipo"] != "tabela":
        ET.SubElement(node, "conteudo", {"gxsi:type": "valor"})
    return node

def gerar_gxsi_xml(form):
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": form.get("nome", ""),
        "versao": form.get("versao", "1.0")
    })
    elementos_tag = ET.SubElement(root, "elementos")
    referenced_domains = set()

    for sec in form.get("secoes", []):
        sec_attrs = {"gxsi:type":"seccao", "titulo": sec.get("titulo",""), "largura": str(sec.get("largura", 500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrs)
        sec_childs = ET.SubElement(sec_el, "elementos")

        elems = sec.get("elementos", [])
        i = 0
        L = len(elems)
        while i < L:
            e = elems[i]
            if e.get("in_table"):
                tabela_el = ET.SubElement(sec_childs, "elemento", {"gxsi:type": "tabela"})
                linhas_el = ET.SubElement(tabela_el, "linhas")
                linha_el = ET.SubElement(linhas_el, "linha")
                celulas_el = ET.SubElement(linha_el, "celulas")
                celula_el = ET.SubElement(celulas_el, "celula", {"linhas":"1", "colunas":"1"})
                elementos_in_cell = ET.SubElement(celula_el, "elementos")
                while i < L and elems[i].get("in_table"):
                    ch = elems[i]
                    if ch.get("dominio"):
                        referenced_domains.add(ch["dominio"]["chave"])
                    create_element_xml(elementos_in_cell, ch)
                    i += 1
            else:
                if e.get("dominio"):
                    referenced_domains.add(e["dominio"]["chave"])
                create_element_xml(sec_childs, e)
                i += 1

    dominios_tag = ET.SubElement(root, "dominios")
    for key in sorted(referenced_domains):
        dom_def = st.session_state.dominios.get(key)
        if not dom_def:
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")
            continue
        if dom_def.get("tipo","estatico") == "estatico":
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in dom_def.get("itens", []):
                ET.SubElement(itens_el, "item", {"gxsi:type":"dominioItemValor", "descricao": it.get("descricao",""), "valor": it.get("valor","")})
        else:
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")

    return prettify_xml(root)

# --------------------------
# UI layout
# --------------------------
CSS = """
<style>
.section-card { border:1px solid #e6eef8; padding:10px; border-radius:8px; background:#fff; margin-bottom:12px; }
.element-summary { padding:6px 8px; border:1px dashed #eef2f7; border-radius:6px; margin-bottom:6px; background:#fff; }
.preview-card { border:1px solid #e6eef8; padding:12px; border-radius:8px; background:#fff; height:80vh; overflow:auto; }
.preview-section { padding:8px; background:#f8fbff; border-radius:6px; margin-bottom:8px; font-weight:700; color:#0b5ed7; }
.small-muted { color:#6b7280; font-size:13px; }
.badge { display:inline-block; padding:3px 8px; background:#eef2ff; border-radius:999px; margin-right:6px; font-size:12px; color:#034; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

left, right = st.columns([1.6, 1.0])

# --------------------------
# Builder (left)
# --------------------------
with left:
    st.header("Construtor de Formulários (v6.4 - domínios v5.0)")
    # form meta
    c1, c2 = st.columns([3,1])
    st.session_state.formulario["nome"] = c1.text_input("Nome do formulário", value=st.session_state.formulario.get("nome",""), key="form_name_v64")
    st.session_state.formulario["versao"] = c2.text_input("Versão", value=st.session_state.formulario.get("versao","1.0"), key="form_ver_v64")

    st.markdown("---")
    # add section
    st.subheader("➕ Adicionar Seção")
    with st.form("form_add_section_v64", clear_on_submit=True):
        sec_title = st.text_input("Título da seção", key="sec_title_v64")
        sec_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="sec_width_v64")
        if st.form_submit_button("Adicionar seção"):
            if not sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                st.session_state.formulario["secoes"].append({"titulo": sec_title.strip(), "largura": int(sec_width), "elementos": []})
                st.success(f"Seção '{sec_title.strip()}' adicionada.")
                st.rerun()

    st.markdown("---")

    # each section: list elements and form to add
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"### {s_idx} — {sec.get('titulo','(sem título)')}")
        cols = st.columns([6,1,1])
        if cols[1].button("Editar", key=f"edit_sec_{s_idx}"):
            st.session_state[f"edit_section_title_{s_idx}"] = sec["titulo"]
            st.rerun()
        if cols[2].button("Remover", key=f"rm_sec_{s_idx}"):
            st.session_state.formulario["secoes"].pop(s_idx)
            st.rerun()

        # show elements
        if sec.get("elementos"):
            st.markdown("**Elementos:**")
            for e_idx, el in enumerate(sec["elementos"]):
                dom_marker = f" [dom={el.get('dominio').get('chave')}]" if el.get("dominio") else ""
                in_table = " (em tabela)" if el.get("in_table") else ""
                st.markdown(f'<div class="element-summary"><span class="badge">{el.get("tipo")}</span><strong>{el.get("titulo","(sem título)")}</strong>{in_table}{dom_marker}</div>', unsafe_allow_html=True)

        st.markdown("---")
        # add element form
        with st.form(f"form_add_elem_{s_idx}", clear_on_submit=True):
            tipo = st.selectbox("Tipo do elemento", ELEMENT_TYPES, key=f"tipo_{s_idx}")
            titulo = st.text_input("Título do elemento (descrição = título)", key=f"titulo_{s_idx}")
            largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=f"larg_{s_idx}")
            obrig = st.checkbox("Obrigatório", value=False, key=f"obrig_{s_idx}") if tipo not in ("paragrafo","rotulo") else False
            in_table = st.checkbox("Pertence à tabela", value=False, key=f"intable_{s_idx}")
            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=f"altura_{s_idx}")
            colunas = None

            # DOMAIN UI (restaurada do v5.0)
            domain_items_local = []
            if tipo in DOMAIN_TYPES:
                st.markdown("**Configuração do Domínio (v5.0 - restaurado)**")
                suggested_key = normalize_domain_key_v5(st.session_state.get(f"titulo_{s_idx}", "") or titulo or "")
                # show preview of domain key (readonly)
                st.text_input("Chave do domínio (gerada a partir do título)", value=suggested_key, key=f"dom_preview_{s_idx}", disabled=True)
                domain_tipo = st.selectbox("Tipo do domínio", ["estatico", "dinamico"], index=0, key=f"dom_tipo_{s_idx}")
                colunas = st.number_input("Colunas (para grupo/combo)", min_value=1, max_value=6, value=1, key=f"dom_cols_{s_idx}")

                if domain_tipo == "estatico":
                    qtd = st.number_input("Quantidade de opções do domínio", min_value=1, max_value=200, value=2, key=f"dom_qtd_{s_idx}")
                    # generate qtd text inputs (descrição + valor)
                    for i in range(int(qtd)):
                        desc = st.text_input(f"Opção {i+1} - Descrição", key=f"dom_{s_idx}_desc_{i}")
                        val = st.text_input(f"Opção {i+1} - Valor (opcional)", key=f"dom_{s_idx}_val_{i}")
                        # store local pair (values may be empty strings until submit)
                        domain_items_local.append({"descricao": desc.strip(), "valor": val.strip()})

            if st.form_submit_button("Adicionar elemento"):
                final_title = st.session_state.get(f"titulo_{s_idx}", "") or titulo or ""
                if tipo not in ("paragrafo", "rotulo") and not final_title.strip():
                    st.error("Informe o título do elemento.")
                else:
                    element = {
                        "tipo": tipo,
                        "titulo": final_title.strip() if final_title else "",
                        "descricao": final_title.strip() if final_title else "",
                        "largura": int(largura),
                        "obrigatorio": bool(obrig),
                        "in_table": bool(in_table)
                    }
                    if altura is not None:
                        element["altura"] = int(altura)
                    if colunas is not None:
                        element["colunas"] = int(colunas)

                    # Handle domain saving (v5.0 behaviour)
                    if tipo in DOMAIN_TYPES:
                        key = normalize_domain_key_v5(final_title)
                        element["dominio"] = {"chave": key}
                        # persist estatico items
                        dom_tipo_val = st.session_state.get(f"dom_tipo_{s_idx}", "estatico")
                        if dom_tipo_val == "estatico":
                            n_items_val = int(st.session_state.get(f"dom_qtd_{s_idx}", 0) or 0)
                            items = []
                            invalid = False
                            for i in range(n_items_val):
                                desc = st.session_state.get(f"dom_{s_idx}_desc_{i}", "").strip()
                                val = st.session_state.get(f"dom_{s_idx}_val_{i}", "").strip()
                                if not desc:
                                    st.error(f"Descrição da opção {i+1} é obrigatória.")
                                    invalid = True
                                else:
                                    if not val:
                                        # v5.0: if valor vazio, use descricao uppercase as valor
                                        val = desc.strip().upper()
                                    items.append({"descricao": desc, "valor": val})
                            if invalid:
                                st.stop()
                            # persist into global dominios without duplicating exact pairs
                            st.session_state.dominios.setdefault(key, {"tipo": "estatico", "itens": []})
                            existing = {(it["descricao"], it["valor"]) for it in st.session_state.dominios[key]["itens"]}
                            for it in items:
                                pair = (it["descricao"], it["valor"])
                                if pair not in existing:
                                    st.session_state.dominios[key]["itens"].append(it)
                                    existing.add(pair)
                        else:
                            # dinâmico: ensure placeholder
                            st.session_state.dominios.setdefault(key, {"tipo":"dinamico", "itens": []})

                    # append element to section
                    st.session_state.formulario["secoes"][s_idx]["elementos"].append(element)
                    st.success(f"Elemento '{element.get('titulo') or element.get('tipo')}' adicionado.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --------------------------
# Preview (right)
# --------------------------
with right:
    st.header("Pré-visualização")
    def build_preview_html(form):
        html = '<div style="font-family:Arial, sans-serif;">'
        html += f'<h2>{form.get("nome","")}</h2>'
        html += f'<div class="small-muted">Versão: {form.get("versao","")}</div><br/>'
        for sec in form.get("secoes", []):
            html += f'<div class="preview-section">{sec.get("titulo")}</div>'
            elems = sec.get("elementos", [])
            i = 0
            L = len(elems)
            while i < L:
                e = elems[i]
                if e.get("in_table"):
                    html += '<div style="border:1px solid #e6f0ff;padding:8px;border-radius:6px;margin-bottom:8px;">'
                    html += '<strong>Tabela</strong>'
                    j = i
                    while j < L and elems[j].get("in_table"):
                        ch = elems[j]
                        html += f'<div style="margin-top:8px;"><div style="font-weight:600;">{ch.get("titulo","")}'
                        if ch.get("obrigatorio"):
                            html += ' <span style="color:#c00">*</span>'
                        html += '</div>'
                        html += '<div style="height:30px;border:1px solid #e6eef8;border-radius:6px;background:#fff;margin-top:6px;"></div>'
                        if ch.get("dominio"):
                            dk = ch["dominio"]["chave"]
                            items = st.session_state.dominios.get(dk, {}).get("itens", [])
                            html += f'<div class="small-muted">domínio: <strong>{dk}</strong> — itens: {", ".join([it["descricao"] for it in items]) or "-"}</div>'
                        html += '</div>'
                        j += 1
                    html += '</div>'
                    i = j
                else:
                    if e.get("tipo") in ("paragrafo", "rotulo"):
                        if e.get("tipo") == "paragrafo":
                            html += f'<div style="padding:8px;background:#f8fafc;border-radius:6px;margin-bottom:6px;">{e.get("titulo","")}</div>'
                        else:
                            html += f'<div style="font-weight:600;margin-bottom:6px;">{e.get("titulo","")}</div>'
                    else:
                        html += f'<div style="margin-bottom:10px;"><div style="font-weight:600;">{e.get("titulo","")}'
                        if e.get("obrigatorio"):
                            html += ' <span style="color:#c00">*</span>'
                        html += '</div>'
                        html += '<div style="height:30px;border:1px solid #e2e8f0;border-radius:6px;background:#fff;margin-top:6px;"></div>'
                        if e.get("dominio"):
                            dk = e["dominio"]["chave"]
                            items = st.session_state.dominios.get(dk, {}).get("itens", [])
                            html += f'<div class="small-muted">domínio: <strong>{dk}</strong> — itens: {", ".join([it["descricao"] for it in items]) or "-"}</div>'
                        html += '</div>'
                    i += 1
        html += '</div>'
        return html

    preview_html = build_preview_html(st.session_state.formulario)
    components.html(preview_html, height=720, scrolling=True)

    st.markdown("---")
    st.subheader("XML gerado (preview)")
    xml_out = gerar_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario_v6.4_v5dom.xml", mime="application/xml")

st.caption("Versão v6.4 (UI de domínios restaurada da v5.0).")
