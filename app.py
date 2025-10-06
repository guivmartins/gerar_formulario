import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "elementos": [],
    }

# -------------------------
# Função de formatação XML
# -------------------------
def prettify(elem):
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# -------------------------
# Geração do XML
# -------------------------
def gerar_xml():
    formulario = st.session_state.formulario
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    elementos_tag = ET.SubElement(root, "elementos")

    # Controle de tabela aberta
    tabela_aberta = None

    for el in formulario["elementos"]:
        if el["type"] == "seccao":
            sec = ET.SubElement(elementos_tag, "elemento", {
                "gxsi:type": "seccao",
                "titulo": el["titulo"],
                "largura": str(el["largura"])
            })
            sec_elems = ET.SubElement(sec, "elementos")
            tabela_aberta = None

        elif el["type"] == "tabela":
            tabela_aberta = ET.SubElement(sec_elems, "elemento", {"gxsi:type": "tabela"})
            linhas = ET.SubElement(tabela_aberta, "linhas")
            linha = ET.SubElement(linhas, "linha")
            celulas = ET.SubElement(linha, "celulas")
            celula = ET.SubElement(celulas, "celula", {"linhas": "1", "colunas": "1"})
            tabela_aberta = ET.SubElement(celula, "elementos")

        else:
            parent = tabela_aberta if tabela_aberta is not None else sec_elems
            attrs = {"gxsi:type": el["type"], "titulo": el["titulo"], "descricao": el["titulo"], "largura": str(el["largura"])}

            if el["type"] not in ["paragrafo", "rotulo"]:
                attrs["obrigatorio"] = "true" if el["obrigatorio"] else "false"

            if el["type"] in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                attrs["colunas"] = str(el["colunas"])
                attrs["dominio"] = el["dominio"]

            if el["type"] in ["paragrafo", "rotulo"]:
                attrs["valor"] = el["titulo"]

            elem_tag = ET.SubElement(parent, "elemento", attrs)

            if el["type"] not in ["paragrafo", "rotulo"]:
                conteudo = ET.SubElement(elem_tag, "conteudo", {"gxsi:type": "valor"})

    dominios_tag = ET.SubElement(root, "dominios")
    dominios_definidos = set(el["dominio"] for el in formulario["elementos"] if el.get("dominio"))
    for dom in dominios_definidos:
        dom_tag = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": dom})
        itens_tag = ET.SubElement(dom_tag, "itens")
        ET.SubElement(itens_tag, "item", {"gxsi:type": "dominioItemValor", "descricao": "Opção 1", "valor": "OPCAO1"})
        ET.SubElement(itens_tag, "item", {"gxsi:type": "dominioItemValor", "descricao": "Opção 2", "valor": "OPCAO2"})

    return prettify(root)

# -------------------------
# UI
# -------------------------
st.title("Construtor de Formulários 6.3beta")

st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

st.subheader("Adicionar Elemento")
col1, col2, col3 = st.columns(3)
with col1:
    tipo = st.selectbox("Tipo do elemento", [
        "seccao", "tabela", "texto", "texto-area", "data", "moeda",
        "cpf", "cnpj", "email", "telefone", "check",
        "comboBox", "comboFiltro", "grupoRadio", "grupoCheck",
        "paragrafo", "rotulo"
    ])
with col2:
    titulo = st.text_input("Título")
with col3:
    largura = st.number_input("Largura", value=450, step=25)

obrigatorio = False
colunas = 1
dominio = ""

if tipo not in ["paragrafo", "rotulo", "seccao", "tabela"]:
    obrigatorio = st.checkbox("Obrigatório", value=False)

if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
    colunas = st.number_input("Colunas", value=1, step=1)
    dominio = st.text_input("Domínio (chave)")

if st.button("Adicionar"):
    st.session_state.formulario["elementos"].append({
        "type": tipo,
        "titulo": titulo,
        "largura": largura,
        "obrigatorio": obrigatorio,
        "colunas": colunas,
        "dominio": dominio
    })

st.subheader("Pré-visualização do Formulário")
for el in st.session_state.formulario["elementos"]:
    st.write(f"📌 {el['type']} - {el['titulo']}")

st.subheader("Pré-visualização do XML")
st.code(gerar_xml(), language="xml")
