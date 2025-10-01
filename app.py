import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(layout="wide")

# Inicialização do estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "Formulário Sem Nome",
        "versao": "1.0",
        "secoes": [],
        "dominios": []
    }

if "nova_secao" not in st.session_state:
    # inicializa como string antes do widget ser criado — OK
    st.session_state.nova_secao = ""

if "novo_campo" not in st.session_state:
    st.session_state.novo_campo = {}

# Função para formatar XML
def prettify(elem):
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# Função para construir XML
def construir_xml():
    form = st.session_state.formulario
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": form["nome"],
        "versao": form["versao"]
    })

    elementos = ET.SubElement(root, "elementos")

    for secao in form["secoes"]:
        el_sec = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": "500"
        })
        el_sub = ET.SubElement(el_sec, "elementos")

        for campo in secao["campos"]:
            attrs = {
                "gxsi:type": campo["tipo"],
                "titulo": campo["titulo"],
                "obrigatorio": str(campo.get("obrigatorio", False)).lower(),
                "largura": "450"
            }
            if campo["tipo"] == "texto-area" and campo.get("altura"):
                attrs["altura"] = str(campo.get("altura"))
            if campo["tipo"] in ["grupoRadio", "grupoCheck"] and campo.get("dominio"):
                attrs["dominio"] = campo["dominio"]
                attrs["colunas"] = str(campo.get("colunas", 1))

            # Se for parágrafo, usamos a estrutura com atributo valor
            if campo["tipo"] == "paragrafo":
                ET.SubElement(el_sub, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo.get("valor", ""),
                    "largura": attrs["largura"]
                })
            else:
                ET.SubElement(el_sub, "elemento", attrs)

    if form["dominios"]:
        doms = ET.SubElement(root, "dominios")
        for dom in form["dominios"]:
            dom_el = ET.SubElement(doms, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": dom["chave"]
            })
            itens = ET.SubElement(dom_el, "itens")
            for item in dom["itens"]:
                ET.SubElement(itens, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": item["descricao"],
                    "valor": item["valor"]
                })

    return prettify(root)

# ================================
# Layout Principal
# ================================
col1, col2 = st.columns([1, 1])

# Coluna 1 - Construtor
with col1:
    st.title("Construtor de Formulários 2.0")

    # Mantive o input para o nome do formulário (esquerda)
    st.text_input("Nome do Formulário", key="form_nome", value=st.session_state.formulario["nome"])
    # atualiza modelo (mantive a lógica anterior)
    st.session_state.formulario["nome"] = st.session_state.form_nome

    st.subheader("Seções")
    for i, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {secao['titulo']}", expanded=False):
            novo_titulo = st.text_input("Título da Seção", value=secao["titulo"], key=f"sec_{i}")
            st.session_state.formulario["secoes"][i]["titulo"] = novo_titulo

            st.write("Campos:")
            for j, campo in enumerate(secao["campos"]):
                with st.expander(f"Campo: {campo['titulo'] or campo['tipo']}", expanded=False):
                    campo["titulo"] = st.text_input("Título", campo["titulo"], key=f"campo_tit_{i}_{j}")
                    campo["tipo"] = st.selectbox(
                        "Tipo",
                        ["texto", "texto-area", "grupoRadio", "grupoCheck", "paragrafo"],
                        index=["texto", "texto-area", "grupoRadio", "grupoCheck", "paragrafo"].index(campo["tipo"]),
                        key=f"campo_tipo_{i}_{j}"
                    )
                    campo["obrigatorio"] = st.checkbox("Obrigatório", campo.get("obrigatorio", False), key=f"campo_obr_{i}_{j}")
                    if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                        campo["dominio"] = st.text_input("Domínio", campo.get("dominio", ""), key=f"campo_dom_{i}_{j}")

            if st.button("Adicionar Campo", key=f"add_campo_{i}"):
                secao["campos"].append({
                    "titulo": "",
                    "tipo": "texto",
                    "obrigatorio": False
                })

    # Campo para nova seção (usando chave "nova_secao")
    nova_sec = st.text_input("Nova Seção", key="nova_secao")
    if st.button("Adicionar Seção"):
        if nova_sec.strip():
            st.session_state.formulario["secoes"].append({"titulo": nova_sec.strip(), "campos": []})
            # <-- NÃO redefinimos st.session_state.nova_secao aqui (removido para evitar StreamlitAPIException)

# Coluna 2 - Pré-visualização do Formulário
with col2:
    # Nome do formulário maior
    st.header(st.session_state.formulario["nome"])

    for secao in st.session_state.formulario["secoes"]:
        # Seção um pouco menor que o nome do formulário
        st.subheader(secao["titulo"])

        for campo in secao["campos"]:
            # bolinha preta como marcador
            st.markdown(f"• **{campo['titulo']}** ({campo['tipo']})")

# XML no fim da página
st.markdown("---")
st.subheader("Pré-visualização do XML")
xml_str = construir_xml()
st.code(xml_str, language="xml")
