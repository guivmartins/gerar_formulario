# app.py - Construtor de Formulários com Tabela corrigida (versão 5.1 teste)

import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "elementos": [], "dominios": {}}
if "novo_elemento" not in st.session_state:
    st.session_state.novo_elemento = {}
if "xml_preview" not in st.session_state:
    st.session_state.xml_preview = ""

# -------------------------
# Funções auxiliares
# -------------------------
def adicionar_elemento(tipo, titulo="", obrigatorio=False, largura="450", dominio=None):
    elem = {"type": tipo, "titulo": titulo, "obrigatorio": obrigatorio, "largura": largura, "children": []}
    
    # descrição sempre igual ao título
    if titulo:
        elem["descricao"] = titulo

    # tipos especiais
    if tipo in ["paragrafo", "rotulo"]:
        elem["valor"] = titulo
    if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] and dominio:
        elem["dominio"] = dominio
        if dominio not in st.session_state.formulario["dominios"]:
            st.session_state.formulario["dominios"][dominio] = [
                {"descricao": "Opção 1", "valor": "OPCAO1"},
                {"descricao": "Opção 2", "valor": "OPCAO2"},
            ]
    st.session_state.formulario["elementos"].append(elem)


def build_xml():
    formulario = st.session_state.formulario
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })
    elementos_tag = ET.SubElement(root, "elementos")

    def add_element(parent, elem):
        attrib = {"gxsi:type": elem["type"]}
        if "titulo" in elem and elem["type"] not in ["tabela"]:
            attrib["titulo"] = elem["titulo"]
            attrib["descricao"] = elem["descricao"]
        if "obrigatorio" in elem:
            attrib["obrigatorio"] = str(elem["obrigatorio"]).lower()
        if "largura" in elem and elem["type"] not in ["tabela"]:
            attrib["largura"] = elem["largura"]
        if "valor" in elem:
            attrib["valor"] = elem["valor"]
        if "dominio" in elem:
            attrib["dominio"] = elem["dominio"]

        el = ET.SubElement(parent, "elemento", attrib)

        # Conteúdo
        if elem["type"] not in ["seccao", "tabela"]:
            ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

        # Seção
        if elem["type"] == "seccao":
            filhos_tag = ET.SubElement(el, "elementos")
            for filho in elem["children"]:
                add_element(filhos_tag, filho)

        # Tabela
        if elem["type"] == "tabela":
            linhas_tag = ET.SubElement(el, "linhas")
            linha_tag = ET.SubElement(linhas_tag, "linha")
            celulas_tag = ET.SubElement(linha_tag, "celulas")
            celula_tag = ET.SubElement(celulas_tag, "celula", {"linhas": "1", "colunas": "1"})
            elementos_celula_tag = ET.SubElement(celula_tag, "elementos")
            for filho in elem["children"]:
                add_element(elementos_celula_tag, filho)

    # Montar elementos
    for e in formulario["elementos"]:
        add_element(elementos_tag, e)

    # Montar domínios
    dominios_tag = ET.SubElement(root, "dominios")
    for chave, itens in formulario["dominios"].items():
        dominio_tag = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": chave})
        itens_tag = ET.SubElement(dominio_tag, "itens")
        for item in itens:
            ET.SubElement(itens_tag, "item", {
                "gxsi:type": "dominioItemValor",
                "descricao": item["descricao"],
                "valor": item["valor"]
            })

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ", encoding="utf-8")
    st.session_state.xml_preview = xml_str.decode("utf-8")

# -------------------------
# Interface Streamlit
# -------------------------
col1, col2 = st.columns([2, 2])

with col1:
    st.header("Construtor de Formulários 5.1")

    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
    st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

    st.subheader("Adicionar Elemento")
    tipo = st.selectbox("Tipo de Elemento", [
        "seccao", "tabela", "texto", "texto-area", "data", "moeda", "cpf", "cnpj",
        "email", "telefone", "check", "comboBox", "comboFiltro", "grupoRadio",
        "grupoCheck", "paragrafo", "rotulo"
    ])
    titulo = st.text_input("Título")
    obrigatorio = st.checkbox("Obrigatório", value=False) if tipo not in ["seccao", "tabela", "paragrafo", "rotulo"] else False
    largura = st.text_input("Largura", "450") if tipo not in ["tabela"] else None
    dominio = st.text_input("Chave do Domínio") if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] else None

    if st.button("Adicionar Elemento"):
        adicionar_elemento(tipo, titulo, obrigatorio, largura, dominio)
        build_xml()

    st.subheader("Estrutura Atual")
    st.json(st.session_state.formulario)

with col2:
    st.header("Pré-visualização XML")
    if st.session_state.xml_preview:
        st.code(st.session_state.xml_preview, language="xml")
    else:
        st.info("O XML será exibido aqui quando você adicionar elementos.")
