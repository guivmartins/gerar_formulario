# app.py — Construtor GXSI (v6.4 finalizado: domínios restaurados como v5.0)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Construtor GXSI - v6.4", layout="wide")

# ---------------------
# Config & helpers
# ---------------------
ELEMENT_TYPES = [
    "texto", "texto-area", "data", "moeda",
    "cpf", "cnpj", "email", "telefone", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo"
]
DOMAIN_TYPES = {"comboBox", "comboFiltro", "grupoRadio", "grupoCheck"}

def normalize_domain_key(title: str) -> str:
    """Concatena o título em CHAVE: remove acentos, não-alfa, maiúsculas, sem espaços."""
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r'[^0-9A-Za-z]+', '', s)
    return s.upper()

def value_from_description(desc: str) -> str:
    """Gera o valor a partir da descrição: remove acentos/non-alnum e uppercase (concat)."""
    if not desc:
        return ""
    s = unicodedata.normalize("NFKD", desc).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r'[^0-9A-Za-z]+', '', s)
    return s.upper()

def prettify_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

# ---------------------
# Session state init
# ---------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "Formulário Exemplo", "versao": "1.0", "secoes": []}

# Domínios globais (persistidos automaticamente quando criados por elementos)
# estrutura: chave -> {"tipo":"estatico", "itens":[{"descricao","valor"}, ...]}
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# ---------------------
# XML generation (v4.0 / v5.0 style)
# ---------------------
def create_element_xml(parent: ET.Element, el: dict):
    attrs = {"gxsi:type": el["tipo"]}
    if el["tipo"] != "tabela":
        if el.get("titulo") is not None:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo", ""))
        if el.get("largura") is not None:
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
        # set valor attribute equal to titulo
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
        sec_attrs = {"gxsi:type": "seccao", "titulo": sec.get("titulo", ""), "largura": str(sec.get("largura", 500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrs)
        sec_childs = ET.SubElement(sec_el, "elementos")

        elems = sec.get("elementos", [])
        i = 0
        L = len(elems)
        while i < L:
            e = elems[i]
            if e.get("in_table"):
                # create tabela grouping consecutive in_table elements
                tabela_el = ET.SubElement(sec_childs, "elemento", {"gxsi:type": "tabela"})
                linhas_el = ET.SubElement(tabela_el, "linhas")
                linha_el = ET.SubElement(linhas_el, "linha")
                celulas_el = ET.SubElement(linha_el, "celulas")
                # fixed cell attributes linhas="1" colunas="1"
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

    # Export only referenced domains
    dominios_tag = ET.SubElement(root, "dominios")
    for key in sorted(referenced_domains):
        dom_def = st.session_state.dominios.get(key)
        if not dom_def:
            # referenced but not defined: keep placeholder
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")
            continue
        dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": key})
        itens_el = ET.SubElement(dom_el, "itens")
        for it in dom_def.get("itens", []):
            ET.SubElement(itens_el, "item", {"gxsi:type": "dominioItemValor", "descricao": it.get("descricao",""), "valor": it.get("valor","")})

    return prettify_xml(root)

# ---------------------
# UI layout (builder left / preview right)
# ---------------------
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

col_builder, col_preview = st.columns([1.6, 1.0])

with col_builder:
    st.header("Construtor de Formulários GXSI — v6.4 (domínios restaurados)")
    # Form metadata
    c1, c2 = st.columns([3,1])
    st.session_state.formulario["nome"] = c1.text_input("Nome do formulário", value=st.session_state.formulario.get("nome",""), key="form_name")
    st.session_state.formulario["versao"] = c2.text_input("Versão", value=st.session_state.formulario.get("versao","1.0"), key="form_ver")
    st.markdown("---")

    # Add section form
    st.subheader("➕ Adicionar Seção")
    with st.form("form_add_section", clear_on_submit=True):
        sec_title = st.text_input("Título da seção", key="sec_title")
        sec_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="sec_width")
        if st.form_submit_button("Adicionar seção"):
            if not sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                st.session_state.formulario["secoes"].append({"titulo": sec_title.strip(), "largura": int(sec_width), "elementos": []})
                st.success(f"Seção '{sec_title.strip()}' adicionada.")
                st.rerun()

    st.markdown("---")

    # Sections loop: show elements + add element form per section
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"### {s_idx} — {sec.get('titulo','(sem título)')}")
        btns = st.columns([6,1,1])
        if btns[1].button("Editar", key=f"edit_{s_idx}"):
            st.session_state[f"edit_sec_title_{s_idx}"] = sec["titulo"]
            st.rerun()
        if btns[2].button("Remover", key=f"rm_{s_idx}"):
            st.session_state.formulario["secoes"].pop(s_idx)
            st.rerun()

        # list elements
        if sec.get("elementos"):
            st.markdown("**Elementos:**")
            for e_idx, el in enumerate(sec["elementos"]):
                dom_marker = f" [dom={el.get('dominio').get('chave')}]" if el.get("dominio") else ""
                in_table = " (em tabela)" if el.get("in_table") else ""
                st.markdown(f'<div class="element-summary"><span class="badge">{el.get("tipo")}</span><strong>{el.get("titulo","(sem título)")}</strong>{in_table}{dom_marker}</div>', unsafe_allow_html=True)

        st.markdown("---")
        # Add element form for this section (single form)
        with st.form(f"form_add_elem_{s_idx}", clear_on_submit=True):
            tipo = st.selectbox("Tipo do elemento", ELEMENT_TYPES, key=f"tipo_{s_idx}")
            titulo = st.text_input("Título do elemento (descrição = título)", key=f"titulo_{s_idx}")
            largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=f"larg_{s_idx}")
            obrig = st.checkbox("Obrigatório", value=False, key=f"obrig_{s_idx}") if tipo not in ("paragrafo","rotulo") else False
            in_table = st.checkbox("Pertence à tabela", value=False, key=f"in_table_{s_idx}")
            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=f"altura_{s_idx}")
            colunas = None

            # Domain UI (exact spec)
            domain_items_local = []
            domain_key = ""
            if tipo in DOMAIN_TYPES:
                st.markdown("**Configuração do Domínio (estático)**")
                # domain key generated from title concatenated
                suggested_title = st.session_state.get(f"titulo_{s_idx}", "") or titulo or ""
                domain_key = normalize_domain_key(suggested_title)
                st.text_input("Chave do domínio (gerada a partir do título)", value=domain_key, key=f"dom_key_preview_{s_idx}", disabled=True)
                st.info("Tipo do domínio: estatico (fixo).")
                colunas = st.number_input("Colunas (para grupo/combo)", min_value=1, max_value=6, value=1, key=f"dom_cols_{s_idx}")

                # Number of options
                n_items = st.number_input("Quantidade de opções do domínio", min_value=1, max_value=200, value=2, key=f"dom_n_{s_idx}")
                # For each option show Description input only; value auto-generated from description
                for i in range(int(n_items)):
                    desc_key = f"dom_{s_idx}_{i}_desc"
                    desc_val = st.text_input(f"Opção {i+1} - Descrição", key=desc_key)
                    # derive valor from description automatically (show as info)
                    computed_val = value_from_description(desc_val or "")
                    st.caption(f"Valor gerado (automático): {computed_val or '(vazio enquanto descrição não informada)'}")
                    domain_items_local.append({"descricao_key": desc_key, "descricao": desc_val, "valor": computed_val})

            if st.form_submit_button("Adicionar elemento"):
                final_title = st.session_state.get(f"titulo_{s_idx}", "") or titulo or ""
                if tipo not in ("paragrafo","rotulo") and not final_title.strip():
                    st.error("Informe o título do elemento.")
                else:
                    # build element dict
                    el = {
                        "tipo": tipo,
                        "titulo": final_title.strip() if final_title else "",
                        # description always equal to title
                        "descricao": final_title.strip() if final_title else "",
                        "largura": int(largura),
                        "obrigatorio": bool(obrig),
                        "in_table": bool(in_table)
                    }
                    if altura is not None:
                        el["altura"] = int(altura)
                    if colunas is not None:
                        el["colunas"] = int(colunas)

                    # handle domain: always estatico per spec
                    if tipo in DOMAIN_TYPES:
                        key = normalize_domain_key(final_title)
                        el["dominio"] = {"chave": key}
                        # collect items from st.session_state keys and persist
                        n_items_val = int(st.session_state.get(f"dom_n_{s_idx}", 0) or 0)
                        items = []
                        invalid = False
                        for i in range(n_items_val):
                            desc = st.session_state.get(f"dom_{s_idx}_{i}_desc", "").strip()
                            if not desc:
                                st.error(f"Descrição da opção {i+1} é obrigatória.")
                                invalid = True
                            else:
                                val = value_from_description(desc)
                                items.append({"descricao": desc, "valor": val})
                        if invalid:
                            st.stop()
                        # persist (replace existing domain definition for this key)
                        st.session_state.dominios[key] = {"tipo": "estatico", "itens": items}

                    # append element to section
                    st.session_state.formulario["secoes"][s_idx]["elementos"].append(el)
                    st.success(f"Elemento '{el.get('titulo') or el.get('tipo')}' adicionado.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

with col_preview:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.header("Pré-visualização (simulação)")
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
                    html += '<div style="border:1px solid #e6f0ff;padding:8px;border-radius:6px;margin-bottom:8px;"><strong>Tabela</strong>'
                    j = i
                    while j < L and elems[j].get("in_table"):
                        ch = elems[j]
                        html += f'<div style="margin-top:8px;"><div style="font-weight:600;">{ch.get("titulo","")}'
                        if ch.get("obrigatorio"):
                            html += ' <span style="color:#c00">*</span>'
                        html += '</div><div style="height:30px;border:1px solid #e6eef8;border-radius:6px;background:#fff;margin-top:6px;"></div>'
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
                        html += '</div><div style="height:30px;border:1px solid #e6eef8;border-radius:6px;background:#fff;margin-top:6px;"></div>'
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

st.caption("v6.4 — inclusão de elementos com domínio restaurada (chave = título concatenado, domínio estatico, valor = descrição concatenada).")
