import streamlit as st
import xml.etree.ElementTree as ET

st.set_page_config(layout="wide")

# ============================
# Inicialização do session_state
# ============================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "Novo Formulário",
        "versao": "1.0",
        "secoes": []
    }

if "secoes_expandidas" not in st.session_state:
    st.session_state.secoes_expandidas = {}

# ============================
# Funções auxiliares
# ============================

def gerar_xml(formulario):
    root = ET.Element("formulario", {
        "xmlns:gxsi": "http://www.sicoob.com.br/gxsi",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    elementos = ET.SubElement(root, "elementos")
    dominios = ET.SubElement(root, "dominios")

    for sec in formulario["secoes"]:
        sec_el = ET.SubElement(elementos, "secao", {"titulo": sec["titulo"]})
        for campo in sec["campos"]:
            attrs = {
                "gxsi:type": campo["tipo"],
                "titulo": campo["titulo"],
            }
            if campo.get("dominio"):
                attrs["dominio"] = campo["dominio"]
            if campo.get("colunas"):
                attrs["colunas"] = campo["colunas"]
            if campo.get("obrigatorio"):
                attrs["obrigatorio"] = "true"

            campo_el = ET.SubElement(sec_el, "elemento", attrs)
            ET.SubElement(campo_el, "conteudo", {"gxsi:type": "valor"})

        # exporta domínio se houver
        for campo in sec["campos"]:
            if campo.get("dominio"):
                dom_el = ET.SubElement(dominios, "dominio", {"nome": campo["dominio"]})
                ET.SubElement(dom_el, "valor").text = "Exemplo 1"
                ET.SubElement(dom_el, "valor").text = "Exemplo 2"

    return ET.tostring(root, encoding="unicode")

def renderizar_formulario(formulario):
    """Renderiza pré-visualização do formulário (lado direito)"""
    st.subheader("📋 Pré-visualização do Formulário")
    for sec in formulario["secoes"]:
        with st.container():
            st.markdown(f"### {sec['titulo']}")
            for campo in sec["campos"]:
                if campo["tipo"] == "texto":
                    st.text_input(campo["titulo"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
                elif campo["tipo"] == "numero":
                    st.number_input(campo["titulo"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
                elif campo["tipo"] == "data":
                    st.date_input(campo["titulo"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
                elif campo["tipo"] == "grupoRadio":
                    st.radio(campo["titulo"], ["Exemplo 1", "Exemplo 2"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
                elif campo["tipo"] == "grupoCheck":
                    st.multiselect(campo["titulo"], ["Exemplo 1", "Exemplo 2"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
                else:
                    st.text(f"(Campo não suportado na pré-visualização: {campo['tipo']})")

# ============================
# Layout em duas colunas
# ============================
col1, col2 = st.columns([2, 2])

with col1:
    st.title("🛠 Construtor de Formulários 3.1")

    # Nome do formulário (sem descrição extra)
    st.text_input("Nome do Formulário", key="form_nome")
    st.session_state.formulario["nome"] = st.session_state.form_nome

    # Versão oculta
    st.session_state.formulario["versao"] = "1.0"

    # Construção das seções
    for idx, sec in enumerate(st.session_state.formulario["secoes"]):
        expanded = st.session_state.secoes_expandidas.get(idx, False)
        with st.expander(f"Seção: {sec['titulo']}", expanded=expanded):
            new_title = st.text_input("Título da seção", sec["titulo"], key=f"sec_title_{idx}")
            if new_title != sec["titulo"]:
                sec["titulo"] = new_title

            # Campos
            for i, campo in enumerate(sec["campos"]):
                with st.expander(f"Campo: {campo['titulo'] or campo['tipo']}", expanded=False):
                    campo["titulo"] = st.text_input("Título", campo["titulo"], key=f"campo_titulo_{i}_{idx}")
                    campo["tipo"] = st.selectbox("Tipo", ["texto", "numero", "data", "grupoRadio", "grupoCheck"],
                                                 index=["texto", "numero", "data", "grupoRadio", "grupoCheck"].index(campo["tipo"]),
                                                 key=f"campo_tipo_{i}_{idx}")
                    campo["dominio"] = st.text_input("Domínio (opcional)", campo.get("dominio", ""), key=f"campo_dom_{i}_{idx}")
                    campo["colunas"] = st.text_input("Colunas (opcional)", campo.get("colunas", ""), key=f"campo_col_{i}_{idx}")
                    campo["obrigatorio"] = st.checkbox("Obrigatório", campo.get("obrigatorio", False), key=f"campo_obr_{i}_{idx}")

            # Botão para adicionar campo
            if st.button("➕ Adicionar campo", key=f"add_field_{idx}"):
                sec["campos"].append({"titulo": "", "tipo": "texto"})

    # Botão para adicionar seção
    if st.button("➕ Adicionar seção"):
        st.session_state.formulario["secoes"].append({"titulo": "Nova Seção", "campos": []})
        st.session_state.secoes_expandidas[len(st.session_state.formulario["secoes"]) - 1] = True
        st.rerun()

with col2:
    renderizar_formulario(st.session_state.formulario)

# ============================
# Pré-visualização do XML no fim
# ============================
st.markdown("---")
st.subheader("📄 Pré-visualização do XML")
xml_code = gerar_xml(st.session_state.formulario)
st.code(xml_code, language="xml")
