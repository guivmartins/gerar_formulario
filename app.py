# app.py — Construtor de Formulários GXSI (v6.4 Estável)
# - Restaura regras de domínio (chave automática, edição inline de itens)
# - Agrupamento de elementos em <elemento gxsi:type="tabela"> quando in_table=True
# - Preview simplificado + export XML compatível com 4.0
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata
import streamlit.components.v1 as components

st.set_page_config(page_title="Construtor de Formulários GXSI - v6.4", layout="wide")

# ---------------------------
# Helpers / Estado inicial
# ---------------------------
ELEMENT_TYPES = [
    "texto", "texto-area", "data", "moeda",
    "cpf", "cnpj", "email", "telefone", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo"
]
DOMAIN_TYPES = {"comboBox", "comboFiltro", "grupoRadio", "grupoCheck"}

def pascalcase(s: str) -> str:
    if not s:
        return ""
    # remove accents
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    parts = re.split(r'\W+', s)
    parts = [p.capitalize() for p in parts if p.strip()]
    return "".join(parts)

def make_domain_key(title: str) -> str:
    if not title:
        return ""
    pc = pascalcase(title)
    if not pc:
        return ""
    return f"dom_{pc}"

def prettify_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

# Session state setup
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "Formulário Exemplo",
        "versao": "1.0",
        "secoes": []  # each section: {"titulo", "largura", "elementos": [ ... ]}
    }

# global domains store: key -> {"tipo":"estatico"|"dinamico", "itens":[{"descricao","valor"}, ...]}
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# temporary domain items while editing an element (key -> list of items)
if "temp_domain_items" not in st.session_state:
    st.session_state.temp_domain_items = {}

def add_section(title: str, largura: int = 500):
    st.session_state.formulario["secoes"].append({"titulo": title, "largura": largura, "elementos": []})

def add_element_to_section(sec_idx: int, element: dict):
    st.session_state.formulario["secoes"][sec_idx]["elementos"].append(element)

# ---------------------------
# XML generation (GXSI-compatible to v4.0)
# ---------------------------
def create_element_xml(parent: ET.Element, el: dict):
    attrs = {"gxsi:type": el["tipo"]}
    if el["tipo"] != "tabela":
        # Put titulo/descricao/largura/obrigatorio/colunas where applicable
        if "titulo" in el:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo", ""))
        if "largura" in el:
            attrs["largura"] = str(el.get("largura"))
        if el["tipo"] not in ("paragrafo", "rotulo"):
            attrs["obrigatorio"] = str(bool(el.get("obrigatorio", False))).lower()
        if el["tipo"] in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck") and el.get("colunas"):
            attrs["colunas"] = str(el.get("colunas"))
        if el["tipo"] == "texto-area" and el.get("altura"):
            attrs["altura"] = str(el.get("altura"))
        if el.get("dominio"):
            attrs["dominio"] = el["dominio"].get("chave")
    node = ET.SubElement(parent, "elemento", attrs)
    # paragrafo / rotulo: set valor attribute and return
    if el["tipo"] in ("paragrafo", "rotulo"):
        node.set("valor", el.get("titulo", ""))
        return node
    if el["tipo"] != "tabela":
        # content is always gxsi:type="valor" for elements (v4.0 style),
        # while domain is referenced via attribute dominio="KEY" and domain block is exported separately.
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
        sec_attrs = {"gxsi:type": "seccao", "titulo": sec.get("titulo", ""), "largura": str(sec.get("largura", 500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrs)
        sec_childs = ET.SubElement(sec_el, "elementos")

        elems = sec.get("elementos", [])
        i = 0
        L = len(elems)
        while i < L:
            e = elems[i]
            # group consecutive in_table into a tabela element
            if e.get("in_table"):
                tabela_el = ET.SubElement(sec_childs, "elemento", {"gxsi:type": "tabela"})
                linhas_el = ET.SubElement(tabela_el, "linhas")
                linha_el = ET.SubElement(linhas_el, "linha")
                celulas_el = ET.SubElement(linha_el, "celulas")
                celula_el = ET.SubElement(celulas_el, "celula", {"linhas": "1", "colunas": "1"})
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

    # Export domains block only for referenced domains
    dominios_tag = ET.SubElement(root, "dominios")
    for key in sorted(referenced_domains):
        dom_def = st.session_state.dominios.get(key)
        if not dom_def:
            # create empty dominioEstatico to preserve ref
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")
            continue
        if dom_def.get("tipo", "estatico") == "estatico":
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": key})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in dom_def.get("itens", []):
                ET.SubElement(itens_el, "item", {"gxsi:type": "dominioItemValor", "descricao": it.get("descricao", ""), "valor": it.get("valor", "")})
        else:
            # dynamic: export empty structure (placeholder)
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")

    return prettify_xml(root)

# ---------------------------
# UI - layout: builder (left) / preview (right)
# ---------------------------
_CUSTOM_CSS = """
<style>
.section-card { border:1px solid #e6eef8; padding:10px; border-radius:8px; background:#ffffff; margin-bottom:12px;}
.element-summary { padding:6px 8px; border:1px dashed #eef2f7; border-radius:6px; margin-bottom:6px; background:#fff; }
.preview-card { border:1px solid #e6eef8; padding:12px; border-radius:8px; background:#fff; height:80vh; overflow:auto;}
.preview-section { padding:8px; background:#f8fbff; border-radius:6px; margin-bottom:8px; font-weight:700; color:#0b5ed7;}
.small-muted { color:#6b7280; font-size:13px; }
.badge { display:inline-block; padding:3px 8px; background:#eef2ff; border-radius:999px; margin-right:6px; font-size:12px; color:#034; }
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

col_builder, col_preview = st.columns([1.6, 1.0])

with col_builder:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.header("Construtor de Formulários GXSI — v6.4 Estável")
    st.markdown("</div>", unsafe_allow_html=True)

    # Form meta
    c1, c2 = st.columns([3,1])
    st.session_state.formulario["nome"] = c1.text_input("Nome do formulário", value=st.session_state.formulario.get("nome", ""), key="form_name_64")
    st.session_state.formulario["versao"] = c2.text_input("Versão", value=st.session_state.formulario.get("versao", "1.0"), key="form_ver_64")

    st.markdown("---")

    # Add section
    st.subheader("➕ Adicionar Seção")
    with st.form("form_add_section_64", clear_on_submit=True):
        sec_title = st.text_input("Título da seção", key="sec_title_64")
        sec_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="sec_width_64")
        if st.form_submit_button("Adicionar seção"):
            if not sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                add_section(sec_title.strip(), int(sec_width))
                st.success(f"Seção '{sec_title.strip()}' adicionada.")
                st.rerun()

    st.markdown("---")

    # Existing sections and element builder per section
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"### {s_idx} — {sec.get('titulo','(sem título)')}")
        cA, cB, cC = st.columns([6,1,1])
        if cB.button("Editar", key=f"edit_sec_{s_idx}"):
            st.session_state[f"edit_sec_title_{s_idx}"] = sec["titulo"]
            st.rerun()
        if cC.button("Remover", key=f"rm_sec_{s_idx}"):
            st.session_state.formulario["secoes"].pop(s_idx)
            st.rerun()

        # show elements summary
        if sec.get("elementos"):
            st.markdown("**Elementos:**")
            for e_idx, el in enumerate(sec["elementos"]):
                dom_marker = f" [dom={el.get('dominio').get('chave')}]" if el.get("dominio") else ""
                in_table = " (em tabela)" if el.get("in_table") else ""
                st.markdown(f'<div class="element-summary"><span class="badge">{el.get("tipo")}</span><strong>{el.get("titulo","(sem título)")}</strong>{in_table}{dom_marker}</div>', unsafe_allow_html=True)

        st.markdown("---")
        # add element form for this section
        with st.form(f"form_add_elem_{s_idx}", clear_on_submit=True):
            tipo = st.selectbox("Tipo do elemento", ELEMENT_TYPES, key=f"tipo_{s_idx}")
            titulo = st.text_input("Título do elemento (descrição = título)", key=f"titulo_{s_idx}")
            largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=f"larg_{s_idx}")
            obrig = st.checkbox("Obrigatório", value=False, key=f"obrig_{s_idx}") if tipo not in ("paragrafo","rotulo") else False
            in_table = st.checkbox("Pertence à tabela", value=False, key=f"intable_{s_idx}")
            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=f"altura_{s_idx}")
            colunas = 1
            # domain-specific UI
            domain_key_preview = ""
            domain_items_local = []
            domain_tipo = "estatico"
            if tipo in DOMAIN_TYPES:
                st.markdown("**Configuração do Domínio**")
                # generate key from title
                suggested_key = make_domain_key(st.session_state.get(f"titulo_{s_idx}", "") or titulo or "")
                domain_key_preview = suggested_key
                st.text_input("Chave do domínio (gerada automaticamente a partir do título)", value=suggested_key, key=f"dom_preview_{s_idx}", disabled=True)
                domain_tipo = st.selectbox("Tipo do domínio", ["estatico", "dinamico"], index=0, key=f"dom_tipo_{s_idx}")
                colunas = st.number_input("Colunas (para grupo/combo)", min_value=1, max_value=6, value=1, key=f"dom_cols_{s_idx}")
                # prepare temp store
                dk = suggested_key
                if dk and dk not in st.session_state.temp_domain_items:
                    # preload from existing global domain if present
                    existing = st.session_state.dominios.get(dk, {}).get("itens", []) if st.session_state.dominios.get(dk) else []
                    st.session_state.temp_domain_items[dk] = list(existing) if existing else []
                if dk and domain_tipo == "estatico":
                    st.markdown("Itens do domínio (descrição obrigatório)")
                    c1, c2 = st.columns([3,3])
                    new_desc = c1.text_input("Descrição", key=f"dom_new_desc_{s_idx}")
                    new_val = c2.text_input("Valor (opcional)", key=f"dom_new_val_{s_idx}")
                    if st.button("Adicionar item do domínio", key=f"add_dom_item_{s_idx}"):
                        if not new_desc.strip():
                            st.error("Informe a descrição do item.")
                        else:
                            val = new_val.strip() or new_desc.strip()
                            st.session_state.temp_domain_items.setdefault(dk, []).append({"descricao": new_desc.strip(), "valor": val})
                            st.success("Item adicionado (temporário).")
                            st.rerun()
                    # list temp items with remove
                    items_preview = st.session_state.temp_domain_items.get(dk, [])
                    if items_preview:
                        st.markdown("Itens (temporários / atuais):")
                        for oi, it in enumerate(items_preview):
                            r0, r1 = st.columns([6,1])
                            r0.write(f"- [{oi}] {it.get('descricao')} (valor: {it.get('valor')})")
                            if r1.button("Remover", key=f"rm_dom_item_{s_idx}_{oi}"):
                                st.session_state.temp_domain_items[dk].pop(oi)
                                st.rerun()
                    domain_items_local = st.session_state.temp_domain_items.get(dk, [])
            # submit element
            if st.form_submit_button("Adicionar elemento"):
                final_title = st.session_state.get(f"titulo_{s_idx}", "") or titulo or ""
                if tipo not in ("paragrafo","rotulo") and not final_title.strip():
                    st.error("Informe o título do elemento.")
                else:
                    el = {
                        "tipo": tipo,
                        "titulo": final_title.strip() if final_title else "",
                        "descricao": final_title.strip() if final_title else "",
                        "largura": int(largura),
                        "obrigatorio": bool(obrig),
                        "in_table": bool(in_table)
                    }
                    if altura is not None:
                        el["altura"] = int(altura)
                    if tipo in DOMAIN_TYPES:
                        dk = make_domain_key(final_title)
                        el["dominio"] = {"chave": dk}
                        el["colunas"] = int(colunas)
                        # persist domain items if estatico
                        if domain_tipo == "estatico":
                            temp_items = st.session_state.temp_domain_items.get(dk, [])
                            st.session_state.dominios.setdefault(dk, {"tipo":"estatico", "itens":[]})
                            # append non-duplicate items
                            existing_pairs = {(it["descricao"], it["valor"]) for it in st.session_state.dominios[dk]["itens"]}
                            for it in temp_items:
                                pair = (it["descricao"], it["valor"])
                                if pair not in existing_pairs:
                                    st.session_state.dominios[dk]["itens"].append(it)
                                    existing_pairs.add(pair)
                            # clear temp store for that key
                            st.session_state.temp_domain_items[dk] = []
                    # append element
                    add_element_to_section(s_idx, el)
                    st.success(f"Elemento '{el.get('titulo') or el.get('tipo')}' adicionado.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

with col_preview:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.header("Pré-visualização (simplificada)")
    # simplified HTML preview using components.html for nicer scroll area
    def build_preview_html(form):
        html = '<div style="font-family: Arial, sans-serif;">'
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
                        html += '<div style="height:30px;border:1px solid #e6eef8;border-radius:6px;background:#fff;margin-top:6px;"></div>'
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
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("XML gerado (preview)")
    xml_out = gerar_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario_v6.4.xml", mime="application/xml")

st.caption("Versão 6.4 Estável — Domínios automáticos (chave gerada a partir do título).")