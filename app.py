import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# ----------------------------
# Helpers
# ----------------------------
def _normalize_domain_key(title: str) -> str:
    """Remove caracteres não alfanuméricos, converte para maiúsculas e limita a 20 chars."""
    base = re.sub(r'[^A-Za-z0-9]', '', (title or "")).upper()[:20]
    return base or "DOMINIO"

def gerar_xml(formulario):
    """Gera XML conforme o padrão solicitado (domínios fora de <elementos>)."""
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    elementos = ET.SubElement(root, "elementos")

    # para gerar chaves únicas de domínio
    used_keys = set()
    # mapeia index do campo (tupla sec_idx, campo_idx) para chave de domínio gerada
    domain_key_map = {}

    # Primeiro constrói os elementos (seções + campos)
    for s_idx, secao in enumerate(formulario["secoes"]):
        el_secao = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao.get("titulo", ""),
            "largura": str(secao.get("largura", 500))
        })
        subelementos = ET.SubElement(el_secao, "elementos")

        for c_idx, campo in enumerate(secao.get("campos", [])):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")

            if tipo == "paragrafo":
                ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo.get("valor", ""),
                    "largura": str(campo.get("largura", 450))
                })
            elif tipo in ["grupoRadio", "grupoCheck"]:
                # gerar chave única para domínio a partir do título
                base = _normalize_domain_key(titulo)
                key = base
                suffix = 1
                while key in used_keys:
                    key = f"{base}{suffix}"
                    suffix += 1
                used_keys.add(key)
                domain_key_map[(s_idx, c_idx)] = key

                # elemento com atributo dominio (sem conteudo interno, conforme exemplo)
                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "dominio": key,
                    "colunas": str(campo.get("colunas", 1)),
                    "obrigatorio": str(bool(campo.get("obrigatorio", False))).lower(),
                    "largura": str(campo.get("largura", 450))
                }
                # remover atributos vazios (precaução)
                attrs = {k: v for k, v in attrs.items() if v is not None and v != ""}
                ET.SubElement(subelementos, "elemento", attrs)
            else:
                # texto, texto-area, etc. -> contem <conteudo gxsi:type="valor"/>
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

    # Depois, bloco de dominios fora de <elementos>
    dominios_root = ET.SubElement(root, "dominios")
    # percorre novamente para preencher dominios na mesma ordem dos campos
    for s_idx, secao in enumerate(formulario["secoes"]):
        for c_idx, campo in enumerate(secao.get("campos", [])):
            if campo.get("tipo") in ["grupoRadio", "grupoCheck"]:
                key = domain_key_map.get((s_idx, c_idx))
                if not key:
                    # fallback: gerar chave
                    key = _normalize_domain_key(campo.get("titulo", ""))
                    suffix = 1
                    while key in used_keys:
                        key = f"{key}{suffix}"
                        suffix += 1
                    used_keys.add(key)

                dominio_el = ET.SubElement(dominios_root, "dominio", {
                    "gxsi:type": "dominioEstatico",
                    "chave": key
                })
                itens = ET.SubElement(dominio_el, "itens")
                for item in campo.get("dominios", []):
                    # item deve ter gxsi:type="dominioItemValor" e atributos descricao e valor
                    descricao = item.get("descricao", "")
                    valor = item.get("valor", descricao).upper()
                    ET.SubElement(itens, "item", {
                        "gxsi:type": "dominioItemValor",
                        "descricao": descricao,
                        "valor": valor
                    })

    # retornar string indentada
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_bytes)
    pretty = parsed.toprettyxml(indent="   ", encoding="utf-8")
    return pretty.decode("utf-8")

def render_form_preview(formulario):
    """Renderiza o formulário construído (visual) na coluna de preview."""
    for secao in formulario["secoes"]:
        st.markdown(f"### {secao.get('titulo','')}")
        for campo in secao.get("campos", []):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")
            obrig = campo.get("obrigatorio", False)

            if tipo == "texto":
                st.text_input(titulo + (" *" if obrig else ""), key=f"preview_{titulo}_{tipo}_{id(campo)}")
            elif tipo == "texto-area":
                altura = campo.get("altura", 100)
                # st.text_area supports height param (pixels); approximate: altura*? We'll use altura as pixels directly
                try:
                    h = int(altura)
                except:
                    h = 100
                st.text_area(titulo + (" *" if obrig else ""), height=h, key=f"preview_{titulo}_{tipo}_{id(campo)}")
            elif tipo == "paragrafo":
                st.markdown(campo.get("valor", ""))
            elif tipo == "grupoRadio":
                # obter opções
                opts = [it.get("descricao", "") for it in campo.get("dominios", [])] or ["Opção 1", "Opção 2"]
                st.radio(titulo + (" *" if obrig else ""), opts, key=f"preview_{titulo}_{tipo}_{id(campo)}")
            elif tipo == "grupoCheck":
                opts = [it.get("descricao", "") for it in campo.get("dominios", [])] or ["Opção 1", "Opção 2"]
                st.multiselect(titulo + (" *" if obrig else ""), opts, key=f"preview_{titulo}_{tipo}_{id(campo)}")
            else:
                # fallback
                st.text_input(titulo + (" *" if obrig else ""), key=f"preview_{titulo}_{tipo}_{id(campo)}")

# ----------------------------
# Estado inicial
# ----------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "Formulário Teste", "versao": "1.0", "secoes": []}

# ----------------------------
# Layout: duas colunas metade/metade
# ----------------------------
col1, col2 = st.columns([1, 1])

# ----------------------------
# Coluna ESQUERDA: Construtor
# ----------------------------
with col1:
    st.header("Construtor de Formulários")
    # Nome do formulário
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"], key="form_name")

    st.markdown("---")

    # Adicionar nova seção (expander)
    with st.expander("➕ Adicionar Seção", expanded=False):
        new_sec_title = st.text_input("Título da Seção", key="new_sec_title")
        new_sec_width = st.number_input("Largura da Seção", min_value=100, value=500, step=10, key="new_sec_width")
        if st.button("Salvar Seção", key="save_section"):
            if new_sec_title.strip():
                st.session_state.formulario["secoes"].append({
                    "titulo": new_sec_title.strip(),
                    "largura": new_sec_width,
                    "campos": []
                })
                # limpar campos temporários
                st.session_state.new_sec_title = ""
                st.session_state.new_sec_width = 500
                st.rerun()

    st.markdown("## Seções existentes")
    # listar seções
    for s_idx, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {secao.get('titulo','(sem título)')}", expanded=False):
            # editar título/largura
            t = st.text_input("Título da Seção", value=secao.get("titulo",""), key=f"sec_title_{s_idx}")
            secao["titulo"] = t
            w = st.number_input("Largura da Seção", min_value=100, value=secao.get("largura",500), step=10, key=f"sec_width_{s_idx}")
            secao["largura"] = w

            if st.button("🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                st.session_state.formulario["secoes"].pop(s_idx)
                st.rerun()

            st.markdown("**Campos desta seção**")

            # campos listados — sem usar expanders aninhados
            for c_idx, campo in enumerate(secao.get("campos", [])):
                st.markdown(f"---\n**Campo {c_idx+1}: {campo.get('titulo','(sem título)')} ({campo.get('tipo')})**")
                # checkbox para abrir edição do campo
                edit_toggle = st.checkbox("Editar este campo", key=f"edit_toggle_{s_idx}_{c_idx}", value=False)
                if edit_toggle:
                    # usar os valores retornados pelos widgets para auto-salvar
                    new_title = st.text_input("Título do Campo", value=campo.get("titulo",""), key=f"field_title_{s_idx}_{c_idx}")
                    campo["titulo"] = new_title

                    tipo_atual = campo.get("tipo", "texto")
                    tipos = ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"]
                    try:
                        idx_tipo = tipos.index(tipo_atual)
                    except ValueError:
                        idx_tipo = 0
                    novo_tipo = st.selectbox("Tipo do Campo", tipos, index=idx_tipo, key=f"field_type_{s_idx}_{c_idx}")
                    campo["tipo"] = novo_tipo

                    if campo["tipo"] != "paragrafo":
                        campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo.get("obrigatorio", False), key=f"field_req_{s_idx}_{c_idx}")

                    campo["largura"] = st.number_input("Largura", min_value=100, value=campo.get("largura",450), step=10, key=f"field_width_{s_idx}_{c_idx}")

                    if campo["tipo"] == "texto-area":
                        campo["altura"] = st.number_input("Altura", min_value=50, value=campo.get("altura",100), step=10, key=f"field_height_{s_idx}_{c_idx}")

                    if campo["tipo"] == "paragrafo":
                        campo["valor"] = st.text_area("Valor do Parágrafo", value=campo.get("valor",""), key=f"field_par_{s_idx}_{c_idx}")

                    if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                        campo["colunas"] = st.number_input("Quantidade de Colunas", min_value=1, max_value=5, value=campo.get("colunas",1), key=f"field_cols_{s_idx}_{c_idx}")
                        # número de domínios existentes
                        existing = len(campo.get("dominios", []))
                        qtd = st.number_input("Quantidade de Itens do domínio", min_value=1, max_value=50, value=existing or 2, key=f"field_qtd_dom_{s_idx}_{c_idx}")
                        new_dom_list = []
                        for d in range(qtd):
                            prev = campo.get("dominios", [])
                            prev_val = prev[d]["descricao"] if d < len(prev) else ""
                            desc = st.text_input(f"Descrição item {d+1}", value=prev_val, key=f"field_dom_{s_idx}_{c_idx}_{d}")
                            if desc is None:
                                desc = ""
                            # valor salvo: manter o que usuario digitar ou gerar padrão
                            # aqui vamos gravar descrição e valor (valor = uppercase sem alteração, per examples)
                            new_dom_list.append({"descricao": desc, "valor": desc.upper()})
                        campo["dominios"] = new_dom_list

                    if st.button("🗑️ Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                        secao["campos"].pop(c_idx)
                        st.rerun()

    # Separador antes do bloco de adicionar campo (final da coluna)
    st.markdown("---")
    st.subheader("➕ Adicionar novo campo (final da tela)")

    # selecionar seção alvo
    if st.session_state.formulario["secoes"]:
        secao_labels = [f"{idx+1} - {sec.get('titulo','(sem título)')}" for idx, sec in enumerate(st.session_state.formulario["secoes"])]
        target = st.selectbox("Adicionar campo à seção", options=list(range(len(secao_labels))), format_func=lambda i: secao_labels[i], key="new_field_section_idx")

        new_title = st.text_input("Título do Novo Campo", key="new_field_title")
        new_tipo = st.selectbox("Tipo do Novo Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], key="new_field_type")
        new_obrig = False
        if new_tipo != "paragrafo":
            new_obrig = st.checkbox("Obrigatório", value=False, key="new_field_obrig")
        new_larg = st.number_input("Largura do Novo Campo", min_value=100, value=450, step=10, key="new_field_larg")
        new_alt = None
        new_par_val = ""
        new_cols = None
        new_dom_list = []

        if new_tipo == "texto-area":
            new_alt = st.number_input("Altura do Novo Campo", min_value=50, value=100, step=10, key="new_field_alt")
        if new_tipo == "paragrafo":
            new_par_val = st.text_area("Valor do Parágrafo (novo)", key="new_field_par")
        if new_tipo in ["grupoRadio", "grupoCheck"]:
            new_cols = st.number_input("Colunas", min_value=1, max_value=5, value=1, key="new_field_cols")
            qtd_dom = st.number_input("Quantidade de itens do domínio", min_value=1, max_value=50, value=2, key="new_field_qtd_dom")
            for d in range(qtd_dom):
                desc = st.text_input(f"Descrição do item {d+1}", key=f"new_field_dom_{d}")
                if desc:
                    new_dom_list.append({"descricao": desc, "valor": desc.upper()})

        if st.button("Adicionar Campo", key="add_field_bottom"):
            campo = {
                "titulo": new_title or "",
                "tipo": new_tipo,
                "obrigatorio": new_obrig,
                "largura": new_larg,
                "altura": new_alt,
                "valor": new_par_val,
                "colunas": new_cols,
                "dominios": new_dom_list,
            }
            st.session_state.formulario["secoes"][st.session_state.get("new_field_section_idx", 0)]["campos"].append(campo)
            # limpar alguns campos
            st.session_state.new_field_title = ""
            st.session_state.new_field_type = "texto"
            st.session_state.new_field_obrig = False
            st.session_state.new_field_larg = 450
            st.rerun()
    else:
        st.info("Adicione ao menos uma seção para poder inserir campos.")

# ----------------------------
# Coluna DIREITA: Pré-visualização do formulário (meia tela)
# ----------------------------
with col2:
    st.header("Pré-visualização do Formulário")
    st.markdown("A pré-visualização abaixo mostra como ficará o formulário para o usuário final (interativa).")
    render_form_preview(st.session_state.formulario)

# ----------------------------
# Footer: Pré-visualização do XML (no final da página)
# ----------------------------
st.markdown("---")
st.subheader("Pré-visualização do XML")
xml_output = gerar_xml(st.session_state.formulario)
st.code(xml_output, language="xml")
