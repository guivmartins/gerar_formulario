import streamlit as st 
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# Inicializar estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "", "secoes": [], "dominios": {}}
if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

st.title("Construtor de Formulários")

# Nome e versão
st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

st.markdown("---")

# Criar nova seção
with st.expander("➕ Adicionar Seção", expanded=True):
    st.session_state.nova_secao["titulo"] = st.text_input("Título da Seção", st.session_state.nova_secao["titulo"])
    st.session_state.nova_secao["largura"] = st.number_input(
        "Largura da Seção", min_value=100, value=500, step=10
    )

    if st.button("Salvar Seção"):
        if st.session_state.nova_secao["titulo"]:
            st.session_state.formulario["secoes"].append(st.session_state.nova_secao.copy())
            st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

# Adicionar campos à última seção
if st.session_state.formulario["secoes"]:
    secao_atual = st.session_state.formulario["secoes"][-1]

    with st.expander(f"➕ Adicionar Campos à seção: {secao_atual['titulo']}", expanded=True):
        titulo = st.text_input("Título do Campo")
        tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
        obrigatorio = False
