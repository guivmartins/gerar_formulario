# app.py  — Construtor de Formulários 3.2 (estável)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

# ------------------------
# Config
# ------------------------
st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# ------------------------
# Helpers
# ------------------------
def safe_rerun():
    """Tenta forçar rerun de forma compatível com várias versões do Streamlit."""
    try:
        st.experimental_rerun()
    except Exception:
        try:
            st.rerun()
        except Exception:
            # fallback silencioso
            pass

def _normalize_domain_key(title: str) -> str:
    """Normaliza título para chave de domínio: remove não alfanuméricos, maiúsculas, 20 chars."""
    key = re.sub(r'[^A-Za-z0-9]', '', (title or "")).upper()[:20]
    return key or "DOMINIO"

def _prettify_xml_bytes(root: ET.Element) -> str:
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_bytes)
    pretty = parsed.toprettyxml(indent="   ", encoding="utf-8")
    return pretty.decode("utf-8")

def gerar_xml(formulario: dict) -> str:
    """
    Gera XML conforme padrão solicitado:
    - <gxsi:formulario xmlns:gxsi="...">
    - <elementos> ... <elemento gxsi:type="seccao"> ... </elementos>
    - <dominios> ... </dominios>  (fora de <elementos>)
    """
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome", ""),
        "versao": formulario.get("versao", "1.0")
    })

    elementos = ET.SubElement(root, "elementos")

    # para controle de chaves de dominio únicas
    used_keys = set()
    domain_map = {}  # map (s_idx, c_idx) -> chave

    # construir elementos (seções e seus campos)
    for s_idx, sec in enumerate(formulario.get("secoes", [])):
        el_secao = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": sec.get("titulo", ""),
            "largura": str(sec.get("largura", 500))
        })
        subelementos = ET.SubElement(el_secao, "elementos")

        for c_idx, campo in enumerate(sec.get("campos", [])):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")

            if tipo == "paragrafo":
                ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo.get("valor", ""),
                    "largura": str(campo.get("largura", 450))
                })
            elif tipo in ["grupoRadio", "grupoCheck"]:
                # gerar chave única
                base = _normalize_domain_key(titulo)
                key = base
                suffix = 1
                while key in used_keys:
                    key = f"{base}{suffix}"
                    suffix += 1
                used_keys.add(key)
                domain_map[(s_idx, c_idx)] = key

                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "dominio": key,
                    "colunas": str(campo.get("colunas", 1)),
                    "obrigatorio": str(bool(campo.get("obrigatorio", False))).lower(),
                    "largura": str(campo.get("largura", 450))
                }
                # remover atributos vazios
                attrs = {k: v for k, v in attrs.items() if v is not None and v != ""}
                ET.SubElement(subelementos, "elemento", attrs)
            else:
                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "obrigatorio": str(bool(campo.get("obrigatorio", False))).lower(),
                    "largura": str(campo.get("largura", 450))
                }
                if tipo == "texto-area" and campo.get("altura"):
                    attrs["altura"] = str(campo.get("altura"))
                el = ET.SubElement(subelementos, "elemento", attrs)
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    # bloco dominios fora de elementos (na ordem dos campos)
    dominios_root = ET.SubElement(root, "dominios")
    for s_idx, sec in enumerate(formulario.get("secoes", [])):
        for c_idx, campo in enumerate(sec.get("campos", [])):
            if campo.get("tipo") in ["grupoRadio", "grupoCheck"]:
                key = domain_map.get((s_idx, c_idx))
                # fallback (shouldn't happen)
                if not key:
                    key = _normalize_domain_key(campo.get("titulo", ""))
                    if key in used_keys:
                        # uniquify
                        suffix = 1
                        base = key
                        while key in used_keys:
                            key = f"{base}{suffix}"
                            suffix += 1
                    used_keys.add(key)

                dominio_el = ET.SubElement(dominios_root, "dominio", {
                    "gxsi:type": "dominioEstatico",
                    "chave": key
                })
                itens_el = ET.SubElement(dominio_el, "itens")
                for item in campo.get("dominios", []):
                    descricao = item.get("descricao", "")
                    valor = item.get("valor", descricao).upper()
                    ET.SubElement(itens_el, "item", {
                        "gxsi:type": "dominioItemValor",
                        "descricao": descricao,
                        "valor": valor
                    })

    return _prettify_xml_bytes(root)

# ------------------------
# session_state init (todas as chaves usadas nos widgets)
# ------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "Formulário Teste", "versao": "1.0", "secoes": []}

# keys usados por formulários temporários - inicializar para evitar sobrescrita depois
init_keys = [
    "new_sec_title", "new_sec_width",
    "new_field_section_idx", "new_field_title", "new_field_type", "new_field_obrig",
    "new_field_larg", "new_field_alt", "new_field_par", "new_field_cols", "new_field_qtd_dom"
]
for k in init_keys:
    if k not in st.session_state:
        st.session_state[k] = "" if "title" in k or "type" in k or "par" in k else 0

# ------------------------
# Callbacks (on_change)
# ------------------------
def on_change_field_attr(s_idx: int, c_idx: int, attr: str, widget_key: str):
    """
    Callback para salvar automaticamente o valor do widget (identificado por widget_key)
    no formulário em st.session_state.formulario.
    """
    val = st.session_state.get(widget_key)
    # safety checks
    try:
        sec = st.session_state.formulario["secoes"][s_idx]
        campo = sec["campos"][c_idx]
        # set attribute
        campo[attr] = val
    except Exception:
        # índices inválidos (por exemplo após deleção), ignorar silenciosamente
        pass

def on_add_section():
    title = st.session_state.get("new_sec_title", "").strip()
    width = st.session_state.get("new_sec_width", 500)
    if title:
        st.session_state.formulario["secoes"].append({
            "titulo": title,
            "largura": width,
            "campos": []
        })
    # safe rerun to refresh widgets (do not directly overwrite keys used by widgets)
    safe_rerun()

def on_add_field():
    # lê valores do st.session_state dos widgets dentro do form
    try:
        s_idx = int(st.session_state.get("new_field_section_idx", 0))
    except Exception:
        s_idx = 0
    title = st.session_state.get("new_field_title", "")
    tipo = st.session_state.get("new_field_type", "texto")
    obrig = bool(st.session_state.get("new_field_obrig", False))
    larg = st.session_state.get("new_field_larg", 450)
    alt = st.session_state.get("new_field_alt", None)
    par = st.session_state.get("new_field_par", "")
    cols = st.session_state.get("new_field_cols", 1)
    qtd_dom = int(st.session_state.get("new_field_qtd_dom", 0) or 0)

    dominios = []
    for d in range(qtd_dom):
        k = f"new_field_dom_{d}"
        desc = st.session_state.get(k, "") or ""
        if desc:
            dominios.append({"descricao": desc, "valor": desc.upper()})

    campo = {
        "titulo": title,
        "tipo": tipo,
        "obrigatorio": obrig,
        "largura": larg,
        "altura": alt,
        "valor": par,
        "colunas": cols,
        "dominios": dominios
    }

    # append to target section
    if st.session_state.formulario["secoes"]:
        idx = min(max(0, s_idx), len(st.session_state.formulario["secoes"]) - 1)
        st.session_state.formulario["secoes"][idx]["campos"].append(campo)
    else:
        # se não existir seção, cria uma nova automaticamente
        st.session_state.formulario["secoes"].append({
            "titulo": "Nova Seção",
            "largura": 500,
            "campos": [campo]
        })
    safe_rerun()

def on_delete_section(idx: int):
    try:
        st.session_state.formulario["secoes"].pop(idx)
    except Exception:
        pass
    safe_rerun()

def on_delete_field(s_idx: int, c_idx: int):
    try:
        st.session_state.formulario["secoes"][s_idx]["campos"].pop(c_idx)
    except Exception:
        pass
    safe_rerun()

# ------------------------
# Layout: duas colunas (esquerda: construtor / direita: preview do formulário)
# ------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.title("🛠 Construtor de Formulários (v3.2)")

    # Nome do formulário (simples input)
    form_name_key = "form_name"
    if form_name_key not in st.session_state:
        st.session_state[form_name_key] = st.session_state.formulario.get("nome", "")
    st.text_input("Nome do Formulário", key=form_name_key, on_change=lambda: st.session_state.formulario.update({"nome": st.session_state[form_name_key]}))

    st.markdown("---")

    # Adicionar nova seção com st.form (evita sobrescrita de keys após widget)
    with st.form("form_add_section", clear_on_submit=False):
        st.subheader("➕ Adicionar Seção")
        st.text_input("Título da Seção", key="new_sec_title")
        st.number_input("Largura da Seção", min_value=100, value=500, step=10, key="new_sec_width")
        submitted = st.form_submit_button("Salvar Seção")
        if submitted:
            on_add_section()

    st.markdown("---")
    st.subheader("Seções existentes")

    # listar seções
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        # cada seção em um expander (não aninhamos expanders para campos)
        with st.expander(f"Seção {s_idx+1}: {sec.get('titulo','(sem título)')}", expanded=False):
            # editar título e largura — usando keys únicas
            key_title = f"sec_{s_idx}_title"
            key_width = f"sec_{s_idx}_width"
            if key_title not in st.session_state:
                st.session_state[key_title] = sec.get("titulo", "")
            if key_width not in st.session_state:
                st.session_state[key_width] = sec.get("largura", 500)

            # text_input with on_change to write back to formulario
            def _on_change_section_title(sidx=s_idx, k=key_title):
                try:
                    st.session_state.formulario["secoes"][sidx]["titulo"] = st.session_state[k]
                except Exception:
                    pass
            def _on_change_section_width(sidx=s_idx, k=key_width):
                try:
                    st.session_state.formulario["secoes"][sidx]["largura"] = int(st.session_state[k] or 500)
                except Exception:
                    pass

            st.text_input("Título da Seção", key=key_title, on_change=_on_change_section_title)
            st.number_input("Largura da Seção", min_value=100, key=key_width, on_change=_on_change_section_width)

            # botão excluir seção
            if st.button("🗑️ Excluir Seção", key=f"del_section_{s_idx}"):
                on_delete_section(s_idx)

            st.markdown("**Campos desta seção**")

            # listar campos (sem expanders aninhados)
            for c_idx, campo in enumerate(sec.get("campos", [])):
                st.markdown(f"---\n**Campo {c_idx+1}: {campo.get('titulo','(sem título)')} ({campo.get('tipo')})**")

                # toggle para editar o campo
                edit_key = f"edit_toggle_{s_idx}_{c_idx}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False
                edit_toggle = st.checkbox("Editar este campo", key=edit_key)

                if edit_toggle:
                    # título
                    w_title = f"field_{s_idx}_{c_idx}_title"
                    if w_title not in st.session_state:
                        st.session_state[w_title] = campo.get("titulo", "")
                    st.text_input("Título do Campo", key=w_title, on_change=on_change_field_attr, args=(s_idx, c_idx, "titulo", w_title))

                    # tipo
                    w_type = f"field_{s_idx}_{c_idx}_type"
                    tipos = ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"]
                    if w_type not in st.session_state:
                        st.session_state[w_type] = campo.get("tipo", "texto")
                    st.selectbox("Tipo do Campo", tipos, key=w_type, on_change=on_change_field_attr, args=(s_idx, c_idx, "tipo", w_type))

                    # obrigatorio
                    if campo.get("tipo") != "paragrafo":
                        w_req = f"field_{s_idx}_{c_idx}_req"
                        if w_req not in st.session_state:
                            st.session_state[w_req] = bool(campo.get("obrigatorio", False))
                        st.checkbox("Obrigatório", key=w_req, on_change=on_change_field_attr, args=(s_idx, c_idx, "obrigatorio", w_req))

                    # largura
                    w_larg = f"field_{s_idx}_{c_idx}_larg"
                    if w_larg not in st.session_state:
                        st.session_state[w_larg] = campo.get("largura", 450)
                    st.number_input("Largura", min_value=100, key=w_larg, on_change=on_change_field_attr, args=(s_idx, c_idx, "largura", w_larg))

                    # altura (texto-area)
                    if st.session_state.get(w_type, campo.get("tipo")) == "texto-area":
                        w_alt = f"field_{s_idx}_{c_idx}_alt"
                        if w_alt not in st.session_state:
                            st.session_state[w_alt] = campo.get("altura", 100)
                        st.number_input("Altura", min_value=50, key=w_alt, on_change=on_change_field_attr, args=(s_idx, c_idx, "altura", w_alt))

                    # paragrafo valor
                    if st.session_state.get(w_type, campo.get("tipo")) == "paragrafo":
                        w_par = f"field_{s_idx}_{c_idx}_par"
                        if w_par not in st.session_state:
                            st.session_state[w_par] = campo.get("valor", "")
                        st.text_area("Valor do Parágrafo", key=w_par, on_change=on_change_field_attr, args=(s_idx, c_idx, "valor", w_par))

                    # dominio items (grupoRadio / grupoCheck)
                    if st.session_state.get(w_type, campo.get("tipo")) in ["grupoRadio", "grupoCheck"]:
                        w_cols = f"field_{s_idx}_{c_idx}_cols"
                        if w_cols not in st.session_state:
                            st.session_state[w_cols] = campo.get("colunas", 1)
                        st.number_input("Colunas", min_value=1, max_value=5, key=w_cols, on_change=on_change_field_attr, args=(s_idx, c_idx, "colunas", w_cols))

                        # qtd items
                        existing = len(campo.get("dominios", []))
                        w_qtd = f"field_{s_idx}_{c_idx}_qtd"
                        if w_qtd not in st.session_state:
                            st.session_state[w_qtd] = existing or 2
                        qtd = st.number_input("Quantidade de itens do domínio", min_value=1, max_value=50, key=w_qtd)

                        # cada item
                        new_dom_list = []
                        for d in range(qtd):
                            w_dom = f"field_{s_idx}_{c_idx}_dom_{d}"
                            prev = ""
                            if d < len(campo.get("dominios", [])):
                                prev = campo.get("dominios", [])[d].get("descricao", "")
                            if w_dom not in st.session_state:
                                st.session_state[w_dom] = prev
                            st.text_input(f"Item {d+1}", key=w_dom, on_change=on_change_field_attr, args=(s_idx, c_idx, "dominios", w_dom))
                            # Note: on_change handler will set the whole 'dominios' field; we accumulate after changes via reading session_state keys
                        # After possible edits, reconstruct dominios from session_state keys:
                        for d in range(int(st.session_state.get(w_qtd, 0) or 0)):
                            key_dom = f"field_{s_idx}_{c_idx}_dom_{d}"
                            desc = st.session_state.get(key_dom, "") or ""
                            new_dom_list.append({"descricao": desc, "valor": desc.upper()})
                        # write directly to model (safe)
                        try:
                            st.session_state.formulario["secoes"][s_idx]["campos"][c_idx]["dominios"] = new_dom_list
                        except Exception:
                            pass

                    # excluir campo
                    if st.button("🗑️ Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                        on_delete_field(s_idx, c_idx)

    # separar e formulário para adicionar novo campo no final (usando st.form)
    st.markdown("---")
    st.subheader("➕ Adicionar novo campo (final da página)")
    if st.session_state.formulario["secoes"]:
        section_options = [f"{i+1} - {s.get('titulo','(sem título)')}" for i, s in enumerate(st.session_state.formulario["secoes"])]
        # ensure index key exists
        if "new_field_section_idx" not in st.session_state:
            st.session_state["new_field_section_idx"] = 0

        with st.form("form_add_field", clear_on_submit=False):
            st.selectbox("Seção", options=list(range(len(section_options))), format_func=lambda i: section_options[i], key="new_field_section_idx")
            st.text_input("Título do Novo Campo", key="new_field_title")
            st.selectbox("Tipo do Novo Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], key="new_field_type")
            # obrigatorio (não aparece para paragrafo in logic when adding)
            st.checkbox("Obrigatório", key="new_field_obrig")
            st.number_input("Largura do Novo Campo", min_value=100, value=450, step=10, key="new_field_larg")
            if st.session_state.get("new_field_type", "texto") == "texto-area":
                st.number_input("Altura do Novo Campo", min_value=50, value=100, step=10, key="new_field_alt")
            if st.session_state.get("new_field_type", "texto") == "paragrafo":
                st.text_area("Valor do Parágrafo", key="new_field_par")
            if st.session_state.get("new_field_type", "texto") in ["grupoRadio", "grupoCheck"]:
                st.number_input("Colunas", min_value=1, max_value=5, value=1, key="new_field_cols")
                st.number_input("Quantidade de itens do domínio", min_value=1, max_value=50, value=2, key="new_field_qtd_dom")
                # domain item fields (dynamically name keys)
                qtd_new = int(st.session_state.get("new_field_qtd_dom", 0) or 0)
                for d in range(qtd_new):
                    key_dom_new = f"new_field_dom_{d}"
                    if key_dom_new not in st.session_state:
                        st.session_state[key_dom_new] = ""
                    st.text_input(f"Item {d+1}", key=key_dom_new)

            submitted_field = st.form_submit_button("Adicionar Campo")
            if submitted_field:
                on_add_field()
    else:
        st.info("Adicione ao menos uma seção para inserir campos.")

with col_right:
    st.header("📋 Pré-visualização do Formulário")
    st.markdown("Esta pré-visualização mostra como o formulário aparecerá para o usuário final. Alterações são salvas automaticamente.")
    # render interactive preview
    for sec in st.session_state.formulario.get("secoes", []):
        st.markdown(f"### {sec.get('titulo','')}")
        for campo in sec.get("campos", []):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")
            obrig = campo.get("obrigatorio", False)
            label = titulo + (" *" if obrig else "")

            if tipo == "texto":
                st.text_input(label, key=f"preview_{id(campo)}")
            elif tipo == "texto-area":
                h = int(campo.get("altura", 100) or 100)
                st.text_area(label, height=h, key=f"preview_{id(campo)}")
            elif tipo == "paragrafo":
                st.markdown(campo.get("valor", ""))
            elif tipo == "grupoRadio":
                options = [it.get("descricao","") for it in campo.get("dominios",[])] or ["Opção 1","Opção 2"]
                st.radio(label, options, key=f"preview_{id(campo)}")
            elif tipo == "grupoCheck":
                options = [it.get("descricao","") for it in campo.get("dominios",[])] or ["Opção 1","Opção 2"]
                st.multiselect(label, options, key=f"preview_{id(campo)}")
            else:
                st.text(f"(Tipo não suportado na pré-visualização: {tipo})")

# ------------------------
# Footer: pré-visualização do XML (no fim da página)
# ------------------------
st.markdown("---")
st.subheader("📄 Pré-visualização do XML")
xml_str = gerar_xml(st.session_state.formulario)
st.code(xml_str, language="xml")

# Opcional: botão de download do XML (se desejar descomentar)
# st.download_button("⬇️ Baixar XML", xml_str, file_name="formulario.xml", mime="application/xml")
