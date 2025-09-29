import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Funções utilitárias
def criar_formulario(nome, versao="1.0"):
    formulario = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": nome,
        "versao": versao
    })
    dominios = ET.SubElement(formulario, "dominios")
    elementos = ET.SubElement(formulario, "elementos")
    return formulario, dominios, elementos

def adicionar_dominio(dominios, chave, itens):
    dominio = ET.SubElement(dominios, "dominio", {"gxsi:type": "dominioEstatico", "chave": chave})
    for desc, val in itens:
        ET.SubElement(dominio, "item", {
            "gxsi:type": "dominioItemValor",
            "descricao": desc,
            "valor": val
        })

def adicionar_secao(elementos, titulo, largura=500):
    secao = ET.SubElement(elementos, "elemento", {
        "gxsi:type": "seccao",
        "titulo": titulo,
        "largura": str(largura)
    })
    ET.SubElement(secao, "elementos")
    return secao

def adicionar_texto(secao, titulo, largura=450, obrigatorio="false"):
    conteudos = secao.find("elementos")
    elemento = ET.SubElement(conteudos, "elemento", {
        "gxsi:type": "texto",
        "titulo": titulo,
        "largura": str(largura),
        "obrigatorio": obrigatorio
    })
    ET.SubElement(elemento, "conteudo", {"gxsi:type": "valor"})

def salvar_xml(formulario):
    return minidom.parseString(ET.tostring(formulario)).toprettyxml(indent="   ", encoding="UTF-8")


# ================== INTERFACE STREAMLIT ==================
st.title("📝 Gerador de Formulários GXSI XML")

nome_formulario = st.text_input("Nome do Formulário", "Formulário Teste")
versao_formulario = st.text_input("Versão", "1.0")

formulario, dominios, elementos = criar_formulario(nome_formulario, versao_formulario)

st.subheader("➕ Adicionar Domínios")
chave = st.text_input("Chave do domínio", "simNao")
itens_input = st.text_area("Itens (um por linha, no formato Descrição=Valor)", "Sim=SIM\nNão=NAO")
if st.button("Adicionar Domínio"):
    itens = [tuple(linha.split("=")) for linha in itens_input.splitlines() if "=" in linha]
    adicionar_dominio(dominios, chave, itens)
    st.success(f"Domínio {chave} adicionado!")

st.subheader("➕ Adicionar Seções e Campos")
titulo_secao = st.text_input("Título da Seção", "Dados Destinatário")
if st.button("Adicionar Seção"):
    secao = adicionar_secao(elementos, titulo_secao)
    st.session_state["ultima_secao"] = secao
    st.success(f"Seção '{titulo_secao}' criada!")

if "ultima_secao" in st.session_state:
    titulo_campo = st.text_input("Título do Campo", "Nome")
    obrigatorio = st.checkbox("Obrigatório?", value=True)
    if st.button("Adicionar Campo Texto"):
        adicionar_texto(st.session_state["ultima_secao"], titulo_campo, obrigatorio=str(obrigatorio).lower())
        st.success(f"Campo '{titulo_campo}' adicionado!")

st.subheader("📥 Gerar XML")
if st.button("Gerar XML"):
    xml_str = salvar_xml(formulario)
    st.code(xml_str.decode("utf-8"), language="xml")
    st.download_button("⬇️ Baixar XML", data=xml_str, file_name="formulario.xml", mime="application/xml")
