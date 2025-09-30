# app.py
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata
import re

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -----------------------
# Helpers
# -----------------------
def normalize_key(s: str) -> str:
    """Remove acentos e caracteres não alfanuméricos, deixa em maiúsculas e trunca em 20 chars."""
    if not s:
        return ""
    nk = unicodedata.normalize("NFKD", s)
    nk = nk.encode("ASCII", "ignore").decode("ASCII")
    nk = re.sub(r"[^A-Za-z0-9]", "", nk).upper()
    return nk[:20]

def unique_domain_key(base: str, domains: dict) -> str:
    """Gera chave única a partir de base evitando colisões em domains dict."""
    key = normalize_key(base) or "DOM"
    candidate = key
    i = 1
    while candidate in domains:
        candidate = f"{key}{i}"
        i += 1
    return candidate

def make_item_value(desc: str) -> str:
    """Gera valor do item a partir da descrição (sem acentos, underscores, maiúsculas)."""
    if desc is None:
        return ""
    nk = unicodedata.normalize("NFKD", desc).encode("ASCII", "ignore").decode("ASCII")
    nk = re.sub(r"\s+", "_", nk.strip())
    nk = re.sub(r"[^A-Za-z0-9_]", "", nk).upper()
    return nk

def pretty_xml_from_et(root: ET.Element) -> bytes:
    xml_raw = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_raw)
    return parsed.toprettyxml(indent="   ", encoding="utf-8")

def remove_domain_if_unused(key: str, formulario: dict):
    """Remove domain 'key' from formulario['dominios'] se nenhuma campo referencia essa chave."""
    if not key or key not in formulario.get("dominios", {}):
        return
    used = False
    for sec in formulario.get("secoes", []):
        for campo in sec.get("campos", []):
            if campo.get("dominio") == key:
                used = True
                break
        if used:
            break
    if not used:
        formulario["dominios"].pop(key, None)

# -----------------------
# Initialize state
# -----------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "",
        "secoes": [],    # cada seção: {"titulo", "largura", "campos": [ ... ]}
        "dominios": {}   # chave -> [ {"descricao","valor"}, ... ]
    }

# Temp edit states
if "edit_section_index" not in st.session_state:
    st.session_state.edit_section_index = None
if "edit_field" not in st.session_state:
    st.session_state.edit_field = None  # dict: {"sec_idx": int, "field_idx": int}
if "tmp_section" not in st.session_state:
    st.session_state.tmp_section = {"titulo": "", "largura": 500}

st.title("Construtor de Formulários")

# -----------------------
# Form header: name/version
# -----------------------
form_data = st.session_state.formulario
form_data["nome"] = st.text_input("Nome do Formulário", value=form_data.get("nome", ""))
form_data["versao"] = st.text_input("Versão", value=form_data.get("versao", "") or "1.0")

st.markdown("---")

# -----------------------
# Add / Edit Section UI
# -----------------------
st.subheader("Seções")

col_a, col_b = st.columns([3,1])
with col_a:
    st.text("Criar nova seção")
    st.session_state.tmp_section["titulo"] = st.text_input("Título da Seção", value=st.session_state.tmp_section["titulo"])
    st.session_state.tmp_section["largura"] = st.number_input("Largura da Seção", min_value=100, value=st.session_state.tmp_section.get("largura",500), step=10)
with col_b:
    if st.button("Salvar Seção"):
        titulo = st.session_state.tmp_section["titulo"].strip()
        if titulo:
            st.session_state.formulario["secoes"].append({
                "titulo": titulo,
                "largura": st.session_state.tmp_section.get("largura", 500),
                "campos": []
            })
            st.session_state.tmp_section = {"titulo": "", "largura": 500}
            st.success(f"Seção '{titulo}' adicionada.")
    if st.button("Cancelar", key="cancel_new_section"):
        st.session_state.tmp_section = {"titulo": "", "largura": 500}

st.markdown("### Seções existentes")
if not form_data["secoes"]:
    st.info("Nenhuma seção criada ainda.")
else:
    for s_idx, sec in enumerate(form_data["secoes"]):
        cols = st.columns([6,1,1,1])
        cols[0].markdown(f"**{s_idx+1}. {sec['titulo']}** (largura: {sec.get('largura',500)})")
        if cols[1].button("✏️ Editar", key=f"edit_sec_{s_idx}"):
            st.session_state.edit_section_index = s_idx
            st.session_state.tmp_section = {"titulo": sec["titulo"], "largura": sec.get("largura",500)}
        if cols[2].button("❌ Excluir", key=f"del_sec_{s_idx}"):
            # remove domains created by fields in this section if no other field uses them
            for campo in sec.get("campos", []):
                dom = campo.get("dominio")
                if dom:
                    # tentatively remove domain; remove only if unused elsewhere
                    # but first remove field reference, then call remove_domain_if_unused
                    pass
            # perform deletion (but must remove domains after removing section)
            removed_sec = form_data["secoes"].pop(s_idx)
            # cleanup domains referenced only by removed fields
            for campo in removed_sec.get("campos", []):
                dom = campo.get("dominio")
                if dom:
                    remove_domain_if_unused(dom, form_data)
            st.experimental_rerun()
        if cols[3].button("🔽 Abrir", key=f"open_sec_{s_idx}"):
            # Scroll to section's add-field expander by setting temporary index
            st.session_state.edit_section_index = s_idx

# Section edit area
if st.session_state.edit_section_index is not None:
    idx = st.session_state.edit_section_index
    if 0 <= idx < len(form_data["secoes"]):
        st.markdown("---")
        st.subheader(f"Editar Seção: {form_data['secoes'][idx]['titulo']}")
        new_title = st.text_input("Título da Seção (editar)", value=st.session_state.tmp_section["titulo"], key=f"edit_sec_title_{idx}")
        new_width = st.number_input("Largura da Seção (editar)", min_value=100, value=st.session_state.tmp_section["largura"], step=10, key=f"edit_sec_w_{idx}")
        col_ok, col_cancel = st.columns(2)
        if col_ok.button("Salvar alterações", key=f"save_sec_{idx}"):
            old = form_data["secoes"][idx]
            old["titulo"] = new_title
            old["largura"] = new_width
            st.session_state.edit_section_index = None
            st.session_state.tmp_section = {"titulo": "", "largura": 500}
            st.success("Seção atualizada.")
            st.experimental_rerun()
        if col_cancel.button("Cancelar edição", key=f"cancel_sec_{idx}"):
            st.session_state.edit_section_index = None
            st.session_state.tmp_section = {"titulo": "", "largura": 500}
            st.experimental_rerun()

st.markdown("---")

# -----------------------
# Add Field to last section (maintain stable flow)
# -----------------------
st.subheader("Adicionar Campo (última seção)")

if form_data["secoes"]:
    last_idx = len(form_data["secoes"]) - 1
    secao_atual = form_data["secoes"][last_idx]
    st.markdown(f"**Seção atual para adição:** {secao_atual['titulo']}")

    with st.form(key="form_add_field"):
        f_tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
        f_titulo = st.text_input("Título do Campo (se aplicável)")
        f_obrig = st.checkbox("Obrigatório", value=False) if f_tipo != "paragrafo" else False
        f_largura = st.number_input("Largura", min_value=100, value=450, step=10)
        f_altura = None
        if f_tipo == "texto-area":
            f_altura = st.number_input("Altura (para texto-area)", min_value=50, value=100, step=10)
        f_valor_paragrafo = ""
        if f_tipo == "paragrafo":
            f_valor_paragrafo = st.text_area("Valor do parágrafo")

        # dominio options for group types: allow one-per-line input
        f_colunas = 1
        f_dom_text = ""
        if f_tipo in ["grupoRadio", "grupoCheck"]:
            f_colunas = st.number_input("Colunas", min_value=1, max_value=5, value=1)
            st.markdown("**Opções do domínio (uma por linha)**")
            f_dom_text = st.text_area("Opções", placeholder="Opção A\nOpção B\nOpção C")

        submitted = st.form_submit_button("Adicionar Campo")
        if submitted:
            campo = {
                "tipo": f_tipo,
                "titulo": f_titulo,
                "obrigatorio": f_obrig,
                "largura": f_largura,
                "altura": f_altura,
                "valor": f_valor_paragrafo,
                "colunas": f_colunas,
                "dominios": []
            }
            # handle domain creation if needed
            if f_tipo in ["grupoRadio", "grupoCheck"] and f_dom_text:
                lines = [ln.strip() for ln in f_dom_text.splitlines() if ln.strip()]
                # build items list
                itens = []
                for ln in lines:
                    itens.append({"descricao": ln, "valor": make_item_value(ln)})
                # generate unique key
                base_key = f_titulo or "DOM"
                chave = unique_domain_key(base_key, form_data["dominios"])
                form_data["dominios"][chave] = itens
                campo["dominio"] = chave
                campo["dominios"] = itens
            secao_atual["campos"].append(campo)
            st.success("Campo adicionado à seção.")
            st.experimental_rerun()
else:
    st.info("Crie ao menos uma seção para poder adicionar campos.")

st.markdown("---")

# -----------------------
# List fields per section with edit/delete
# -----------------------
st.subheader("Campos por Seção (editar / excluir)")
for s_idx, sec in enumerate(form_data["secoes"]):
    st.markdown(f"### {s_idx+1}. {sec['titulo']}")
    if not sec.get("campos"):
        st.write("_Nenhum campo nessa seção_")
        continue
    for f_idx, campo in enumerate(sec["campos"]):
        cols = st.columns([6,1,1])
        # Title display
        display_title = campo.get("titulo") if campo.get("titulo") else f"({campo['tipo']})"
        cols[0].write(f"**{display_title}** — tipo: {campo['tipo']}")
        if cols[1].button("✏️", key=f"edit_field_{s_idx}_{f_idx}"):
            st.session_state.edit_field = {"sec_idx": s_idx, "field_idx": f_idx}
        if cols[2].button("❌", key=f"del_field_{s_idx}_{f_idx}"):
            # remove field and possibly domain
            removed = sec["campos"].pop(f_idx)
            dom = removed.get("dominio")
            if dom:
                remove_domain_if_unused(dom, form_data)
            st.success("Campo removido.")
            st.experimental_rerun()

# -----------------------
# Edit field modal / area
# -----------------------
if st.session_state.edit_field:
    ef = st.session_state.edit_field
    s_idx = ef["sec_idx"]
    f_idx = ef["field_idx"]
    if 0 <= s_idx < len(form_data["secoes"]) and 0 <= f_idx < len(form_data["secoes"][s_idx]["campos"]):
        campo = form_data["secoes"][s_idx]["campos"][f_idx]
        st.markdown("---")
        st.subheader(f"Editar campo - Seção: {form_data['secoes'][s_idx]['titulo']}")
        with st.form(key=f"form_edit_field_{s_idx}_{f_idx}"):
            e_tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], index=["texto","texto-area","paragrafo","grupoRadio","grupoCheck"].index(campo["tipo"]))
            e_titulo = st.text_input("Título do Campo", value=campo.get("titulo",""))
            e_obrig = st.checkbox("Obrigatório", value=campo.get("obrigatorio", False)) if e_tipo != "paragrafo" else False
            e_larg = st.number_input("Largura", min_value=100, value=campo.get("largura",450), step=10)
            e_alt = None
            if e_tipo == "texto-area":
                e_alt = st.number_input("Altura", min_value=50, value=campo.get("altura",100), step=10)
            e_val_par = ""
            if e_tipo == "paragrafo":
                e_val_par = st.text_area("Valor do parágrafo", value=campo.get("valor",""))
            e_col = 1
            e_dom_text = ""
            if e_tipo in ["grupoRadio", "grupoCheck"]:
                e_col = st.number_input("Colunas", min_value=1, max_value=5, value=campo.get("colunas",1))
                # load existing domain lines if exists
                existing_lines = []
                domain_key = campo.get("dominio")
                if domain_key and domain_key in form_data["dominios"]:
                    existing_lines = [it["descricao"] for it in form_data["dominios"][domain_key]]
                e_dom_text = st.text_area("Opções do domínio (uma por linha)", value="\n".join(existing_lines))

            save = st.form_submit_button("Salvar campo")
            cancel = st.form_submit_button("Cancelar edição", on_click=lambda: st.session_state.update({"edit_field": None}))
            if save:
                # Update domain handling:
                old_dom = campo.get("dominio")
                # If changing to a group type, create/update domain
                if e_tipo in ["grupoRadio","grupoCheck"]:
                    lines = [ln.strip() for ln in e_dom_text.splitlines() if ln.strip()]
                    itens = [{"descricao": ln, "valor": make_item_value(ln)} for ln in lines]
                    # Determine new domain key from title
                    new_base = e_titulo or "DOM"
                    new_key = unique_domain_key(new_base, form_data["dominios"]) if (old_dom is None or normalize_key(new_base) != normalize_key(campo.get("titulo",""))) else old_dom
                    # If old_dom is None or key changed, create/move
                    if new_key != old_dom:
                        # If new_key collides, unique_domain_key already handled
                        form_data["dominios"][new_key] = itens
                        # remove old dom if unused
                        if old_dom:
                            remove_domain_if_unused(old_dom, form_data)
                    else:
                        # overwrite items
                        form_data["dominios"][new_key] = itens
                    campo["dominio"] = new_key
                    campo["dominios"] = itens
                else:
                    # If previously had a domain but now no longer group type, remove old domain if unused
                    if old_dom:
                        remove_domain_if_unused(old_dom, form_data)
                    campo.pop("dominio", None)
                    campo.pop("dominios", None)

                # Update other attributes
                campo["tipo"] = e_tipo
                campo["titulo"] = e_titulo
                if e_tipo != "paragrafo":
                    campo["obrigatorio"] = e_obrig
                else:
                    campo.pop("obrigatorio", None)
                campo["largura"] = e_larg
                if e_alt is not None:
                    campo["altura"] = e_alt
                elif "altura" in campo and e_tipo != "texto-area":
                    campo.pop("altura", None)
                if e_tipo == "paragrafo":
                    campo["valor"] = e_val_par
                else:
                    campo.pop("valor", None)
                if e_tipo in ["grupoRadio","grupoCheck"]:
                    campo["colunas"] = e_col
                else:
                    campo.pop("colunas", None)

                st.session_state.edit_field = None
                st.success("Campo atualizado.")
                st.experimental_rerun()
    else:
        st.session_state.edit_field = None

st.markdown("---")

# -----------------------
# Preview (stable behavior) - show form name/version + elements structure
# -----------------------
st.subheader("Pré-visualização (XML gerado)")

def build_xml_from_formulario(formulario: dict) -> bytes:
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome",""),
        "versao": formulario.get("versao","")
    })

    # dominios (out of elementos)
    if formulario.get("dominios"):
        doms = ET.SubElement(root, "dominios")
        for chave, itens in formulario["dominios"].items():
            dom = ET.SubElement(doms, "dominio", {"gxsi:type": "dominioEstatico", "chave": chave})
            itens_tag = ET.SubElement(dom, "itens")
            for it in itens:
                ET.SubElement(itens_tag, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": it["descricao"],
                    "valor": it["valor"]
                })

    elementos = ET.SubElement(root, "elementos")
    for sec in formulario.get("secoes", []):
        sec_el = ET.SubElement(elementos, "elemento", {"gxsi:type":"seccao", "titulo": sec.get("titulo",""), "largura": str(sec.get("largura",500))})
        els = ET.SubElement(sec_el, "elementos")
        for campo in sec.get("campos", []):
            if campo["tipo"] == "paragrafo":
                ET.SubElement(els, "elemento", {"gxsi:type":"paragrafo", "valor": campo.get("valor",""), "largura": str(campo.get("largura",450))})
            else:
                attribs = {"gxsi:type": campo["tipo"], "titulo": campo.get("titulo",""), "largura": str(campo.get("largura",450))}
                if "obrigatorio" in campo:
                    attribs["obrigatorio"] = str(campo.get("obrigatorio")).lower()
                if campo["tipo"] in ["grupoRadio","grupoCheck"]:
                    attribs["dominio"] = campo.get("dominio","")
                    attribs["colunas"] = str(campo.get("colunas",1))
                if campo["tipo"] == "texto-area" and "altura" in campo:
                    attribs["altura"] = str(campo.get("altura"))
                if campo["tipo"] == "texto" and "tamanhoMaximo" in campo:
                    attribs["tamanhoMaximo"] = str(campo.get("tamanhoMaximo"))
                elc = ET.SubElement(els, "elemento", attribs)
                # only non-paragraphs have <conteudo>
                ET.SubElement(elc, "conteudo", {"gxsi:type":"valor"})

    return pretty_xml_from_et(root)

xml_bytes = build_xml_from_formulario(form_data)
st.code(xml_bytes.decode("utf-8"), language="xml")

# -----------------------
# Export buttons
# -----------------------
st.markdown("---")
st.subheader("Exportar")
st.download_button("⬇️ Exportar XML", data=xml_bytes, file_name="formulario.xml", mime="application/xml")
st.download_button("⬇️ Exportar GFE", data=xml_bytes, file_name="formulario.gfe", mime="application/octet-stream")
