# app.py - Construtor de Formulários 6.4Beta (domínios automáticos restaurados)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit.components.v1 as components
import re

# Optional helper from streamlit-extras (fallback)
try:
    from streamlit_extras.add_vertical_space import add_vertical_space
except Exception:
    def add_vertical_space(n=1):
        for _ in range(n):
            st.write("")

st.set_page_config(page_title="Construtor de Formulários 6.4Beta", layout="wide")

# -----------------------
# Estado inicial
# -----------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "Formulário Exemplo",
        "versao": "6.4Beta",
        "secoes": []  # cada seção: {"titulo","largura","elementos":[...] }
    }

# dominios global: chave -> {"tipo":"estatico"|"dinamico", "itens":[{"codigo","descricao","valor"}, ...]}
# Esses domínios serão preenchidos automaticamente pelo fluxo de criação de elementos que usam domínio.
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# Temp storage for domain items being created in the form (by domain_key)
if "temp_domain_items" not in st.session_state:
    st.session_state.temp_domain_items = {}

# helper para chaves únicas de widget
def _k(*parts):
    return "__".join(str(p) for p in parts)

# helper: normalizar título para chave de domínio (maiúsculas, sem espaços, caracteres alfanuméricos e underscore)
def make_domain_key(title: str) -> str:
    if not title:
        return ""
    # remove accents, non-alnum -> replace with '', keep underscore
    # simplify: remove non-word chars and uppercase
    key = re.sub(r"\W+", "", title, flags=re.UNICODE).upper()
    return key or ""

# Tipos de elementos
ELEMENT_TYPES = [
    "texto", "texto-area", "data", "moeda",
    "cpf", "cnpj", "email", "telefone", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo", "tabela"
]
DOMAIN_TYPES = {"comboBox", "comboFiltro", "grupoRadio", "grupoCheck"}

# -----------------------
# Styling (claro, leve)
# -----------------------
_CSS = """
<style>
.section-card {
  border: 1px solid #e6eef8;
  background: #ffffff;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.element-row {
  border: 1px dashed #eef2f7;
  padding: 8px;
  margin: 6px 0;
  border-radius: 6px;
  background: #fff;
}
.preview-card {
  border: 1px solid #e6eef8;
  background: #ffffff;
  padding: 12px;
  border-radius: 8px;
  height: 78vh;
  overflow: auto;
}
.preview-section {
  padding: 8px;
  background: #f8fbff;
  border-radius: 6px;
  margin-bottom: 8px;
  font-weight:700;
  color: #0b5ed7;
}
.preview-table {
  border: 1px solid #dbeafe;
  background: #fbfdff;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 10px;
}
.preview-field {
  margin: 6px 0;
}
.preview-label {
  font-weight:600;
  font-size:13px;
}
.small-muted { color:#6b7280; font-size:13px; }
.badge { display:inline-block; padding:3px 8px; background:#eef2ff; border-radius:999px; margin-right:6px; font-size:12px; color:#034; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# -----------------------
# XML helpers (GXSI) - domains restored exactly per rules
# -----------------------
def _prettify_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def _create_element_xml(parent: ET.Element, el: dict):
    """
    Create <elemento ...> under parent from el dict.
    For domain-bearing elements, conteudo will be gxsi:type="dominio" nome="..."
    For others, conteudo gxsi:type="valor"
    paragrafo/rotulo: attribute valor = titulo
    """
    attrs = {"gxsi:type": el["tipo"]}
    if el["tipo"] != "tabela":
        if el.get("titulo") is not None:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo", ""))
        if el.get("largura") is not None:
            attrs["largura"] = str(el.get("largura"))
        if el["tipo"] not in ("paragrafo", "rotulo"):
            attrs["obrigatorio"] = str(bool(el.get("obrigatorio", False))).lower()
        if el["tipo"] == "texto-area" and el.get("altura"):
            attrs["altura"] = str(el.get("altura"))
        if el["tipo"] in DOMAIN_TYPES and el.get("dominio_key"):
            attrs["dominio"] = el.get("dominio_key")
        if el["tipo"] in ("comboBox","comboFiltro","grupoRadio","grupoCheck") and el.get("colunas"):
            attrs["colunas"] = str(el.get("colunas"))
    node = ET.SubElement(parent, "elemento", attrs)
    # paragrafo/rotulo: valor attribute = titulo
    if el["tipo"] in ("paragrafo", "rotulo"):
        node.set("valor", el.get("titulo",""))
        return node
    # tabela handled separately outside
    if el["tipo"] != "tabela":
        # content: dominio vs valor
        if el["tipo"] in DOMAIN_TYPES and el.get("dominio_key"):
            ET.SubElement(node, "conteudo", {"gxsi:type":"dominio", "nome": el.get("dominio_key")})
        else:
            ET.SubElement(node, "conteudo", {"gxsi:type":"valor"})
    return node

def gerar_gxsi_xml(form):
    """
    Generate GXSI XML:
    - Groups consecutive elements with in_table=True into a single <elemento gxsi:type="tabela">
    - Exports top-level <dominios> for all referenced domain keys that exist in st.session_state.dominios
    """
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": form.get("nome",""),
        "versao": form.get("versao","1.0")
    })
    elementos_tag = ET.SubElement(root, "elementos")
    referenced_domains = set()

    for sec in form.get("secoes", []):
        sec_attrs = {"gxsi:type":"seccao", "titulo": sec.get("titulo",""), "largura": str(sec.get("largura",500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrs)
        sec_childs = ET.SubElement(sec_el, "elementos")

        elems = sec.get("elementos", [])
        i = 0
        L = len(elems)
        while i < L:
            e = elems[i]
            if e.get("in_table"):
                tabela_el = ET.SubElement(sec_childs, "elemento", {"gxsi:type":"tabela"})
                linhas_el = ET.SubElement(tabela_el, "linhas")
                linha_el = ET.SubElement(linhas_el, "linha")
                celulas_el = ET.SubElement(linha_el, "celulas")
                celula_el = ET.SubElement(celulas_el, "celula", {"linhas":"1","colunas":"1"})
                elementos_in_cell = ET.SubElement(celula_el, "elementos")
                while i < L and elems[i].get("in_table"):
                    ch = elems[i]
                    if ch["tipo"] in DOMAIN_TYPES:
                        dk = ch.get("dominio_key")
                        if dk:
                            referenced_domains.add(dk)
                    _create_element_xml(elementos_in_cell, ch)
                    i += 1
            else:
                if e["tipo"] in DOMAIN_TYPES:
                    dk = e.get("dominio_key")
                    if dk:
                        referenced_domains.add(dk)
                _create_element_xml(sec_childs, e)
                i += 1

    # Build top-level <dominios> only for referenced domain keys
    dominios_tag = ET.SubElement(root, "dominios")
    for key in sorted(referenced_domains):
        dom_def = st.session_state.dominios.get(key)
        if not dom_def:
            # referenced but no definition -> create empty dominioEstatico
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")
            continue
        # export dominioEstatico when tipo == "estatico"
        if dom_def.get("tipo","estatico") == "estatico":
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in dom_def.get("itens", []):
                ET.SubElement(itens_el, "item", {"gxsi:type":"dominioItemValor", "descricao": it.get("descricao",""), "valor": it.get("valor", it.get("codigo",""))})
        else:
            # dynamic domain - export empty structure to preserve reference
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")

    return _prettify_xml(root)

# -----------------------
# Mutators
# -----------------------
def adicionar_secao(titulo: str, largura: int = 500):
    st.session_state.formulario["secoes"].append({"titulo": titulo, "largura": largura, "elementos": []})

def adicionar_elemento(sec_index: int, elemento: dict):
    st.session_state.formulario["secoes"][sec_index]["elementos"].append(elemento)

# -----------------------
# UI: Builder (left) / Preview (right) simplified preview
# -----------------------
col_builder, col_preview = st.columns([1.6, 1.0])

with col_builder:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.header("Construtor — 6.4Beta (domínios automáticos)")
    st.markdown("</div>", unsafe_allow_html=True)

    # form meta
    c1, c2 = st.columns([3,1])
    st.session_state.formulario["nome"] = c1.text_input("Nome do formulário", value=st.session_state.formulario.get("nome",""), key="f_name_64_dom")
    st.session_state.formulario["versao"] = c2.text_input("Versão", value=st.session_state.formulario.get("versao","6.4Beta"), key="f_ver_64_dom")

    add_vertical_space(1)

    # add section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("➕ Nova Seção")
    with st.form("form_add_section_dom", clear_on_submit=True):
        sec_title = st.text_input("Título da seção", key="sec_title_dom")
        sec_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="sec_w_dom")
        if st.form_submit_button("Adicionar seção"):
            if not sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                adicionar_secao(sec_title.strip(), int(sec_width))
                st.success(f"Seção '{sec_title.strip()}' adicionada.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    add_vertical_space(1)

    # sections list and element builder per section
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"### {s_idx} — {sec.get('titulo','(sem título)')}")
        cols = st.columns([6,1,1])
        if cols[1].button("Editar", key=_k("edit_sec_dom", s_idx)):
            st.session_state[_k("edit_sec_title_dom", s_idx)] = sec["titulo"]
            st.session_state[_k("edit_sec_width_dom", s_idx)] = sec.get("largura",500)
            st.rerun()
        if cols[2].button("Remover", key=_k("rm_sec_dom", s_idx)):
            st.session_state.formulario["secoes"].pop(s_idx)
            st.rerun()

        # Show elements summary
        if sec.get("elementos"):
            st.markdown("**Elementos**")
            for e_idx, el in enumerate(list(sec["elementos"])):
                in_table_marker = " (em tabela)" if el.get("in_table") else ""
                dom_marker = f" [domínio={el.get('dominio_key','-')}]" if el.get("dominio_key") else ""
                st.markdown(f'- <span class="badge">{el.get("tipo")}</span> **{el.get("titulo","(sem título)")}**{in_table_marker}{dom_marker}', unsafe_allow_html=True)

        st.markdown("---")
        # add element form
        with st.form(_k("form_add_el_dom", s_idx), clear_on_submit=True):
            tipo = st.selectbox("Tipo de elemento", ELEMENT_TYPES, key=_k("tipo_dom", s_idx))
            titulo = st.text_input("Título (descrição = título)", key=_k("titulo_dom", s_idx))
            largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=_k("larg_dom", s_idx))
            obrig = st.checkbox("Obrigatório", value=False, key=_k("obrig_dom", s_idx)) if tipo not in ("paragrafo","rotulo","tabela") else False
            in_table = st.checkbox("Pertence à tabela", value=False, key=_k("intable_dom", s_idx))
            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=_k("altura_dom", s_idx))

            # domain handling - automatic key based on title
            dominio_key_text = ""
            dominio_tipo = "estatico"
            colunas = 1
            if tipo in DOMAIN_TYPES:
                st.markdown("**Domínio (automaticamente vinculado ao título)**")
                # auto-generate domain key from the entered title
                suggested_key = make_domain_key(st.session_state.get(_k("titulo_dom", s_idx), "") or titulo or "")
                if not suggested_key:
                    st.info("Digite o título do elemento para gerar a chave do domínio automaticamente.")
                st.text_input("Chave do domínio (gerada automaticamente a partir do título)", value=suggested_key, key=_k("domkey_preview_dom", s_idx), disabled=True)
                dominio_key_text = suggested_key
                dominio_tipo = st.selectbox("Tipo do domínio", ["estatico", "dinamico"], index=0, key=_k("domtipo_dom", s_idx))
                colunas = st.number_input("Colunas (para grupos/combos)", min_value=1, max_value=6, value=1, key=_k("domcols_dom", s_idx))
                # If estatico, allow adding items to a temporary domain store tied to the key
                if dominio_key_text and dominio_tipo == "estatico":
                    dk = dominio_key_text
                    # ensure temp store exists
                    if dk not in st.session_state.temp_domain_items:
                        # initialize from existing global domain if present
                        existing = st.session_state.dominios.get(dk, {}).get("itens") if st.session_state.dominios.get(dk) else []
                        st.session_state.temp_domain_items[dk] = list(existing) if existing else []
                    st.markdown("Adicionar item ao domínio (descrição obrigatório)")
                    c0, c1 = st.columns([2,3])
                    dom_item_desc = c0.text_input("Descrição", key=_k("dom_item_desc_dom", s_idx))
                    dom_item_val = c1.text_input("Valor (opcional)", key=_k("dom_item_val_dom", s_idx))
                    if st.button("Adicionar item ao domínio (temporário)", key=_k("add_dom_item_dom", s_idx)):
                        if not dom_item_desc.strip():
                            st.error("Informe a descrição do item.")
                        else:
                            val = dom_item_val.strip() or dom_item_desc.strip()
                            st.session_state.temp_domain_items[dk].append({"codigo": "", "descricao": dom_item_desc.strip(), "valor": val})
                            st.success("Item adicionado (temporário).")
                            st.rerun()
                    # preview and allow removal from temp
                    items_preview = st.session_state.temp_domain_items.get(dk, [])
                    if items_preview:
                        st.markdown("Itens temporários do domínio:")
                        for oi, it in enumerate(items_preview):
                            rcol0, rcol1 = st.columns([6,1])
                            rcol0.write(f"- [{oi}] {it.get('descricao')} (valor: {it.get('valor','')})")
                            if rcol1.button("Remover", key=_k("rm_dom_item_dom", s_idx, oi, dk)):
                                st.session_state.temp_domain_items[dk].pop(oi)
                                st.rerun()

            if st.form_submit_button("Adicionar elemento"):
                # Determine domain key again at submit (in case title was typed just now)
                final_title = st.session_state.get(_k("titulo_dom", s_idx), "") or titulo or ""
                final_key = make_domain_key(final_title)
                if tipo in DOMAIN_TYPES:
                    dominio_key_text = final_key
                if tipo not in ("paragrafo","rotulo","tabela") and not final_title.strip():
                    st.error("Informe o título do elemento.")
                else:
                    el = {
                        "tipo": tipo,
                        "titulo": final_title.strip() if final_title else "",
                        "descricao": final_title.strip() if final_title else "",
                        "obrigatorio": bool(obrig),
                        "largura": int(largura),
                        "in_table": bool(in_table)
                    }
                    if altura is not None:
                        el["altura"] = int(altura)
                    if tipo in DOMAIN_TYPES:
                        el["dominio_key"] = dominio_key_text or ""
                        el["dominio_tipo"] = dominio_tipo
                        el["colunas"] = int(colunas)
                        # If estatico and temp items exist, persist them into global st.session_state.dominios[domain_key]
                        if dominio_key_text and dominio_tipo == "estatico":
                            tk = dominio_key_text
                            temp_items = st.session_state.temp_domain_items.get(tk, [])
                            # ensure domain global exists
                            st.session_state.dominios.setdefault(tk, {"tipo":"estatico", "itens":[]})
                            # append new items only if not duplicates (by descricao+valor)
                            existing_vals = {(it.get("descricao"), it.get("valor")) for it in st.session_state.dominios[tk].get("itens", [])}
                            for it in temp_items:
                                pair = (it.get("descricao"), it.get("valor"))
                                if pair not in existing_vals:
                                    st.session_state.dominios[tk]["itens"].append(it)
                                    existing_vals.add(pair)
                            # clear temp store for that key (keeps UI clean)
                            st.session_state.temp_domain_items[tk] = []
                    # If explicit tabela element chosen, append a tabela marker element
                    if tipo == "tabela":
                        sec["elementos"].append({"tipo":"tabela", "titulo":"", "in_table": False})
                    else:
                        sec["elementos"].append(el)
                    st.success(f"Elemento '{el.get('titulo') or el.get('tipo')}' adicionado.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        add_vertical_space(1)

with col_preview:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.header("Pré-visualização (simplificada)")

    # Build simplified preview HTML
    def build_simplified_preview(form):
        html = '<div style="font-family: Arial, sans-serif;">'
        html += f'<h2 style="margin-bottom:6px;">{form.get("nome","")}</h2>'
        html += f'<div class="small-muted">Versão: {form.get("versao","")}</div><br/>'
        for sec in form.get("secoes", []):
            html += f'<div class="preview-section">{sec.get("titulo","")}</div>'
            elems = sec.get("elementos", [])
            i = 0
            L = len(elems)
            while i < L:
                e = elems[i]
                if e.get("in_table"):
                    html += '<div class="preview-table">'
                    html += '<div style="font-weight:600;margin-bottom:6px;">Tabela</div>'
                    j = i
                    while j < L and elems[j].get("in_table"):
                        ch = elems[j]
                        html += '<div style="margin-bottom:8px;">'
                        html += f'<div class="preview-label">{ch.get("titulo","")}'
                        if ch.get("obrigatorio"):
                            html += ' <span style="color:#c00">*</span>'
                        html += '</div>'
                        html += f'<div style="height:32px;width:100%;border-radius:6px;border:1px solid #e2e8f0;background:#fff;margin-top:6px;"></div>'
                        if ch.get("tipo") in DOMAIN_TYPES:
                            dk = ch.get("dominio_key","")
                            items = st.session_state.dominios.get(dk, {}).get("itens", [])
                            html += f'<div class="small-muted" style="margin-top:6px;">domínio: <strong>{dk or "-"}</strong> — itens: {", ".join([it["descricao"] for it in items]) or "-"}</div>'
                        html += '</div>'
                        j += 1
                    html += '</div>'  # end preview-table
                    i = j
                else:
                    if e.get("tipo") in ("paragrafo","rotulo"):
                        if e.get("tipo") == "paragrafo":
                            html += f'<div style="padding:8px;background:#f8fafc;border-radius:6px;margin-bottom:6px;">{e.get("titulo","")}</div>'
                        else:
                            html += f'<div style="font-weight:600;margin-bottom:6px;">{e.get("titulo","")}</div>'
                    else:
                        html += '<div style="margin-bottom:10px;">'
                        html += f'<div class="preview-label">{e.get("titulo","")}'
                        if e.get("obrigatorio"):
                            html += ' <span style="color:#c00">*</span>'
                        html += '</div>'
                        html += f'<div style="height:32px;width:100%;border-radius:6px;border:1px solid #e2e8f0;background:#fff;margin-top:6px;"></div>'
                        if e.get("tipo") in DOMAIN_TYPES:
                            dk = e.get("dominio_key","")
                            items = st.session_state.dominios.get(dk, {}).get("itens", [])
                            html += f'<div class="small-muted" style="margin-top:6px;">domínio: <strong>{dk or "-"}</strong> — itens: {", ".join([it["descricao"] for it in items]) or "-"}</div>'
                        html += '</div>'
                    i += 1
        html += '</div>'
        return html

    preview_html = build_simplified_preview(st.session_state.formulario)
    components.html(preview_html, height=720, scrolling=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("XML gerado (preview)")
    xml_out = gerar_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario_6.4beta.xml", mime="application/xml")

st.caption(
    "6.4Beta — Domínios automáticos: a chave do domínio é gerada automaticamente a partir do título do elemento (sem espaços, maiúsculas). "
    "Ao criar um elemento que usa domínio, adicione opções (descrição + valor opcional) no painel de criação antes de submeter o elemento; elas serão persistidas ao salvar o elemento."
)