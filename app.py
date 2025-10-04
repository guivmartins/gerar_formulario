# app.py - Construtor de Formulários 6.4Beta (com regras completas de domínio)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit.components.v1 as components

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
        "secoes": []  # cada seção: {"titulo", "largura", "elementos": [ ... ]}
    }

# dominios global: chave -> {"tipo": "estatico"|"dinamico", "itens": [{"codigo","descricao","valor"}, ...]}
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# helper para chaves únicas
def _k(*parts):
    return "__".join(str(p) for p in parts)

# Tipos de elementos (conforme 6.3Final)
ELEMENT_TYPES = [
    "texto", "texto-area", "data", "moeda",
    "cpf", "cnpj", "email", "telefone", "check",
    "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
    "paragrafo", "rotulo", "tabela"
]
DOMAIN_TYPES = {"comboBox", "comboFiltro", "grupoRadio", "grupoCheck"}

# -----------------------
# CSS (tema claro, leve)
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
# XML helpers (GXSI) - with domain handling restored
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
    paragrafo/rotulo: set 'valor' attribute equal to titulo and no conteudo element.
    """
    attrs = {"gxsi:type": el["tipo"]}
    if el["tipo"] != "tabela":
        if el.get("titulo") is not None:
            attrs["titulo"] = el.get("titulo", "")
            attrs["descricao"] = el.get("descricao", el.get("titulo", ""))
        if el.get("largura") is not None:
            attrs["largura"] = str(el.get("largura"))
        if el["tipo"] not in ("paragrafo","rotulo"):
            attrs["obrigatorio"] = str(bool(el.get("obrigatorio", False))).lower()
        if el["tipo"] == "texto-area" and el.get("altura"):
            attrs["altura"] = str(el.get("altura"))
        if el["tipo"] in DOMAIN_TYPES and el.get("dominio_key"):
            attrs["dominio"] = el.get("dominio_key")
        if el["tipo"] in ("comboBox","comboFiltro","grupoRadio","grupoCheck") and el.get("colunas"):
            attrs["colunas"] = str(el.get("colunas"))
    node = ET.SubElement(parent, "elemento", attrs)
    # paragrafo/rotulo: attribute valor = titulo
    if el["tipo"] in ("paragrafo","rotulo"):
        node.set("valor", el.get("titulo",""))
        return node
    # tabela handled outside
    if el["tipo"] != "tabela":
        # content: dominio vs valor
        if el["tipo"] in DOMAIN_TYPES and el.get("dominio_key"):
            conteudo = ET.SubElement(node, "conteudo", {"gxsi:type":"dominio", "nome": el.get("dominio_key")})
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
            # referenced but no definition -> still create empty dominioEstatico
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            ET.SubElement(dom_el, "itens")
            continue
        # For now we only export dominioEstatico when tipo == "estatico"
        if dom_def.get("tipo","estatico") == "estatico":
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type":"dominioEstatico", "chave": key})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in dom_def.get("itens", []):
                # use dominioItemValor with descricao and valor
                ET.SubElement(itens_el, "item", {"gxsi:type":"dominioItemValor", "descricao": it.get("descricao",""), "valor": it.get("valor", it.get("codigo",""))})
        else:
            # dynamic domain: create empty dominio element with attribute tipo="dinamico"
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
    st.header("Construtor — 6.4Beta (Domínios restaurados)")
    st.markdown("</div>", unsafe_allow_html=True)

    # form meta
    c1, c2 = st.columns([3,1])
    st.session_state.formulario["nome"] = c1.text_input("Nome do formulário", value=st.session_state.formulario.get("nome",""), key="f_name_64_d")
    st.session_state.formulario["versao"] = c2.text_input("Versão", value=st.session_state.formulario.get("versao","6.4Beta"), key="f_ver_64_d")

    add_vertical_space(1)

    # add section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("➕ Nova Seção")
    with st.form("form_add_section_d", clear_on_submit=True):
        sec_title = st.text_input("Título da seção", key="sec_title_d")
        sec_width = st.number_input("Largura (px)", min_value=100, max_value=1200, value=500, key="sec_w_d")
        if st.form_submit_button("Adicionar seção"):
            if not sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                adicionar_secao(sec_title.strip(), int(sec_width))
                st.success(f"Seção '{sec_title.strip()}' adicionada.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    add_vertical_space(1)

    # sections list
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f"### {s_idx} — {sec.get('titulo','(sem título)')}")
        cols = st.columns([6,1,1])
        if cols[1].button("Editar", key=_k("edit_sec_d", s_idx)):
            st.session_state[_k("edit_sec_title_d", s_idx)] = sec["titulo"]
            st.session_state[_k("edit_sec_width_d", s_idx)] = sec.get("largura",500)
            st.rerun()
        if cols[2].button("Remover", key=_k("rm_sec_d", s_idx)):
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
        with st.form(_k("form_add_el_d", s_idx), clear_on_submit=True):
            tipo = st.selectbox("Tipo de elemento", ELEMENT_TYPES, key=_k("tipo_d", s_idx))
            titulo = st.text_input("Título (descrição = título)", key=_k("titulo_d", s_idx))
            largura = st.number_input("Largura (px)", min_value=50, max_value=1200, value=450, key=_k("larg_d", s_idx))
            obrig = st.checkbox("Obrigatório", value=False, key=_k("obrig_d", s_idx)) if tipo not in ("paragrafo","rotulo","tabela") else False
            in_table = st.checkbox("Pertence à tabela", value=False, key=_k("intable_d", s_idx))
            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=_k("altura_d", s_idx))

            dominio_key_text = ""
            dominio_tipo = "estatico"
            colunas = 1
            if tipo in DOMAIN_TYPES:
                st.markdown("**Domínio do elemento**")
                dominio_key_text = st.text_input("Nome/Chave do domínio", key=_k("domkey_d", s_idx))
                dominio_tipo = st.selectbox("Tipo do domínio", ["estatico", "dinamico"], index=0, key=_k("domtipo_d", s_idx))
                colunas = st.number_input("Colunas (para grupoRadio/grupoCheck/combo)", min_value=1, max_value=6, value=1, key=_k("domcols_d", s_idx))
                # If estatico, allow adding items (codigo, descricao, valor)
                if dominio_key_text and dominio_tipo == "estatico":
                    dk = dominio_key_text.strip()
                    if dk not in st.session_state.dominios:
                        st.session_state.dominios[dk] = {"tipo":"estatico", "itens":[]}
                    st.markdown("Adicionar item (código opcional, descrição obrigatório)")
                    c0, c1, c2 = st.columns([2,3,2])
                    dom_item_code = c0.text_input("Código (opcional)", key=_k("dom_item_code", s_idx))
                    dom_item_desc = c1.text_input("Descrição", key=_k("dom_item_desc", s_idx))
                    dom_item_val = c2.text_input("Valor (opcional)", key=_k("dom_item_val", s_idx))
                    if st.button("Adicionar item ao domínio", key=_k("add_dom_item_d", s_idx)):
                        if not dom_item_desc.strip():
                            st.error("Informe descrição para o item.")
                        else:
                            val = dom_item_val.strip() or dom_item_code.strip() or dom_item_desc.strip()
                            st.session_state.dominios[dk]["itens"].append({"codigo": dom_item_code.strip(), "descricao": dom_item_desc.strip(), "valor": val})
                            st.success("Item adicionado ao domínio.")
                            st.rerun()
                    # preview existing items
                    items_preview = st.session_state.dominios.get(dk, {}).get("itens", [])
                    if items_preview:
                        st.write("Itens do domínio:")
                        for oi, it in enumerate(items_preview):
                            rcol0, rcol1 = st.columns([6,1])
                            rcol0.write(f"- [{oi}] {it.get('descricao')} (valor: {it.get('valor','')}, código: {it.get('codigo','')})")
                            if rcol1.button("Remover", key=_k("rm_dom_item_d", s_idx, oi, dk)):
                                st.session_state.dominios[dk]["itens"].pop(oi)
                                st.rerun()

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
                        "in_table": bool(in_table)
                    }
                    if altura is not None:
                        el["altura"] = int(altura)
                    if tipo in DOMAIN_TYPES:
                        el["dominio_key"] = dominio_key_text.strip() if dominio_key_text else ""
                        el["dominio_tipo"] = dominio_tipo
                        el["colunas"] = int(colunas)
                        # ensure session_state.dominios has entry if user created items earlier
                        if dominio_key_text and dominio_tipo == "estatico" and dominio_key_text.strip() not in st.session_state.dominios:
                            st.session_state.dominios[dominio_key_text.strip()] = {"tipo":"estatico", "itens":[]}
                    # explicit tabela element insertion
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
    "6.4Beta — Domínios restaurados. "
    "Notas: adicionar domínios ao criar elementos (comboBox/comboFiltro/grupoRadio/grupoCheck). "
    "Itens estáticos são exportados em <dominios> como dominioEstatico + dominioItemValor."
)