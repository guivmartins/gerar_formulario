# app.py - Construtor de Formulários com suporte a Tabela (versão 5.1)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}

# -------------------------
# Funções auxiliares
# -------------------------
def adicionar_secao(titulo, largura):
    st.session_state.formulario["secoes"].append(
        {"tipo": "seccao", "titulo": titulo, "largura": largura, "elementos": []}
    )

def adicionar_elemento(secao, tipo, titulo, descricao, obrigatorio, largura, opcoes=None):
    elemento = {
        "tipo": tipo,
        "titulo": titulo,
        "descricao": descricao,
        "obrigatorio": obrigatorio,
        "largura": largura,
        "opcoes": opcoes or [],
        "elementos": []  # suporte a filhos (no caso de tabela)
    }
    st.session_state.formulario["secoes"][secao]["elementos"].append(elemento)

def adicionar_tabela(secao):
    # tabela funciona como container
    tabela = {
        "tipo": "tabela",
        "elementos": []  # os elementos filhos vão aqui
    }
    st.session_state.formulario["secoes"][secao]["elementos"].append(tabela)

def gerar_xml():
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": st.session_state.formulario["nome"],
        "versao": st.session_state.formulario["versao"],
    })
    elementos_tag = ET.SubElement(root, "elementos")

    for secao in st.session_state.formulario["secoes"]:
        secao_tag = ET.SubElement(elementos_tag, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": secao["largura"],
        })
        secao_elementos_tag = ET.SubElement(secao_tag, "elementos")

        for elem in secao["elementos"]:
            if elem["tipo"] == "tabela":
                tabela_tag = ET.SubElement(secao_elementos_tag, "elemento", {"gxsi:type": "tabela"})
                linhas_tag = ET.SubElement(tabela_tag, "linhas")
                linha_tag = ET.SubElement(linhas_tag, "linha")
                celulas_tag = ET.SubElement(linha_tag, "celulas")
                celula_tag = ET.SubElement(celulas_tag, "celula", {"linhas": "1", "colunas": "1"})
                elementos_celula_tag = ET.SubElement(celula_tag, "elementos")

                # filhos dentro da tabela
                for filho in elem["elementos"]:
                    gerar_elemento_xml(filho, elementos_celula_tag)
            else:
                gerar_elemento_xml(elem, secao_elementos_tag)

    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="UTF-8")

def gerar_elemento_xml(elem, parent_tag):
    elem_tag = ET.SubElement(parent_tag, "elemento", {
        "gxsi:type": elem["tipo"],
        "titulo": elem["titulo"],
        "descricao": elem["descricao"],
        "obrigatorio": str(elem["obrigatorio"]).lower(),
        "largura": elem["largura"],
    })

    conteudo_tag = ET.SubElement(elem_tag, "conteudo", {"gxsi:type": "valor"})
    if elem["tipo"] == "lista" and elem["opcoes"]:
        for opc in elem["opcoes"]:
            ET.SubElement(conteudo_tag, "opcao").text = opc

# -------------------------
# Interface Streamlit
# -------------------------
st.title("Construtor de Formulários 5.1 (com Tabela)")

st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

if st.button("Adicionar Seção"):
    adicionar_secao("Nova Seção", "500")

for i, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"Seção: {secao['titulo']}", expanded=True):
        secao["titulo"] = st.text_input("Título da Seção", secao["titulo"], key=f"titulo_secao_{i}")
        secao["largura"] = st.text_input("Largura da Seção", secao["largura"], key=f"largura_secao_{i}")

        if st.button("Adicionar Tabela", key=f"add_tab_{i}"):
            adicionar_tabela(i)

        if st.button("Adicionar Elemento", key=f"add_elem_{i}"):
            adicionar_elemento(i, "texto", "Novo Campo", "descricao", False, "225")

        for j, elem in enumerate(secao["elementos"]):
            if elem["tipo"] == "tabela":
                st.markdown(f"📊 **Tabela** (contém {len(elem['elementos'])} elementos)")
                if st.button("Adicionar Campo na Tabela", key=f"add_elem_tab_{i}_{j}"):
                    elem["elementos"].append({
                        "tipo": "texto",
                        "titulo": "Campo Tabela",
                        "descricao": "descricao",
                        "obrigatorio": False,
                        "largura": "225",
                        "opcoes": []
                    })
            else:
                elem["titulo"] = st.text_input("Título", elem["titulo"], key=f"titulo_elem_{i}_{j}")
                elem["descricao"] = st.text_input("Descrição", elem["descricao"], key=f"desc_elem_{i}_{j}")

if st.button("Gerar XML"):
    xml_final = gerar_xml()
    st.download_button("Baixar XML", data=xml_final, file_name="formulario.xml", mime="application/xml")
    st.code(xml_final.decode("utf-8"), language="xml")
