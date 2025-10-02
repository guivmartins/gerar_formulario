import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# Inicializar estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}
if "novo_dominio_nome" not in st.session_state:
    st.session_state["novo_dominio_nome"] = ""
if "novo_dominio_tipo" not in st.session_state:
    st.session_state["novo_dominio_tipo"] = "dominioEstatico"
if "dominios" not in st.session_state:
    st.session_state["dominios"] = []

# Função para gerar XML
def gerar_xml():
    form = st.session_state.formulario
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": form["nome"],
        "versao": form["versao"]
    })

    elementos = ET.SubElement(root, "elementos")
    for secao in form["secoes"]:
        secao_el = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao.get("largura", 500))
        })
        secao_elementos = ET.SubElement(secao_el, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "tabela":
                campo_el = ET.SubElement(secao_elementos, "elemento", {
                    "gxsi:type": "tabela",
                    "titulo": campo["titulo"],
                    "largura": str(campo.get("largura", 500)),
                    "colunas": str(campo.get("colunas", 1))
                })
                tabela_el = ET.SubElement(campo_el, "tabela")
                for linha in campo.get("linhas", []):
                    linha_el = ET.SubElement(tabela_el, "linha")
                    for celula in linha:
                        ET.SubElement(linha_el, "celula", {"valor": celula})
            else:
                campo_el = ET.SubElement(secao_elementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "descricao": campo.get("descricao", ""),
                    "obrigatorio": str(campo.get("obrigatorio", False)).lower(),
                    "largura": str(campo.get("largura", 500))
                })
                if campo["tipo"] in ["texto-area"]:
                    campo_el.set("altura", str(campo.get("altura", 120)))
                if campo["tipo"] in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                    campo_el.set("colunas", str(campo.get("colunas", 1)))
                    if campo.get("dominio"):
                        campo_el.set("dominio", campo["dominio"])
                if campo["tipo"] not in ["paragrafo", "rotulo", "tabela"]:
                    ET.SubElement(campo_el, "conteudo", {"gxsi:type": "valor"})

    if st.session_state.dominios:
        dominios_el = ET.SubElement(root, "dominios")
        for dominio in st.session_state.dominios:
            dom_el = ET.SubElement(dominios_el, "dominio", {
                "gxsi:type": dominio["tipo"],
                "chave": dominio["nome"]
            })
            itens_el = ET.SubElement(dom_el, "itens")
            for item in dominio["itens"]:
                ET.SubElement(itens_el, "item", {
                    "gxsi:type": item["tipo"],
                    "descricao": item["descricao"],
                    "valor": item["valor"],
                    **({"chave": item["chave"]} if item["tipo"] == "dominioItemParametro" else {})
                })

    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="utf-8")

# Interface
st.title("Construtor de Formulários 4.1")

col1, col2 = st.columns([2, 2])

with col1:
    st.header("Configuração do Formulário")
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
    st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

    st.subheader("Seções")
    for i, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {secao['titulo']}", expanded=False):
            secao["titulo"] = st.text_input("Título da Seção", secao["titulo"], key=f"secao_titulo_{i}")
            secao["largura"] = st.number_input("Largura", value=secao.get("largura", 500), key=f"secao_largura_{i}")

            st.markdown("**Campos da Seção**")
            for j, campo in enumerate(secao["campos"]):
                with st.expander(f"Campo: {campo['titulo']} ({campo['tipo']})", expanded=False):
                    campo["titulo"] = st.text_input("Título", campo["titulo"], key=f"campo_titulo_{i}_{j}")
                    campo["descricao"] = st.text_input("Descrição", campo.get("descricao", ""), key=f"campo_desc_{i}_{j}")
                    campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo.get("obrigatorio", False), key=f"campo_obrig_{i}_{j}")
                    campo["largura"] = st.number_input("Largura", value=campo.get("largura", 500), key=f"campo_largura_{i}_{j}")

                    if campo["tipo"] == "texto-area":
                        campo["altura"] = st.number_input("Altura", value=campo.get("altura", 120), key=f"campo_altura_{i}_{j}")
                    if campo["tipo"] in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                        campo["colunas"] = st.number_input("Colunas", value=campo.get("colunas", 1), key=f"campo_colunas_{i}_{j}")
                        campo["dominio"] = st.text_input("Domínio (chave)", campo.get("dominio", ""), key=f"campo_dom_{i}_{j}")
                    if campo["tipo"] == "tabela":
                        campo["colunas"] = st.number_input("Colunas", value=campo.get("colunas", 1), key=f"campo_colunas_{i}_{j}")
                        if "linhas" not in campo:
                            campo["linhas"] = []
                        nova_linha = st.text_area("Adicionar linha (valores separados por vírgula)", key=f"campo_linha_{i}_{j}")
                        if st.button("Adicionar Linha", key=f"add_linha_{i}_{j}"):
                            if nova_linha:
                                campo["linhas"].append([v.strip() for v in nova_linha.split(",")])

            if st.button("Adicionar Campo", key=f"add_campo_{i}"):
                secao["campos"].append({"tipo": "texto", "titulo": "Novo Campo"})

    if st.button("Adicionar Seção"):
        st.session_state.formulario["secoes"].append({"titulo": "Nova Seção", "largura": 500, "campos": []})

    st.subheader("Domínios")
    st.session_state["novo_dominio_nome"] = st.text_input("Nome do Domínio", st.session_state["novo_dominio_nome"], key="dom_nome")
    st.session_state["novo_dominio_tipo"] = st.selectbox("Tipo de Domínio", ["dominioEstatico", "dominioDinamico"], key="dom_tipo")

    if st.button("Adicionar Domínio"):
        st.session_state.dominios.append({"nome": st.session_state["novo_dominio_nome"], "tipo": st.session_state["novo_dominio_tipo"], "itens": []})

    for d, dominio in enumerate(st.session_state.dominios):
        with st.expander(f"Domínio: {dominio['nome']} ({dominio['tipo']})", expanded=False):
            for k, item in enumerate(dominio["itens"]):
                st.text_input("Descrição", item["descricao"], key=f"dom_desc_{d}_{k}")
                st.text_input("Valor", item["valor"], key=f"dom_val_{d}_{k}")
            desc = st.text_input("Nova Descrição", key=f"new_desc_{d}")
            val = st.text_input("Novo Valor", key=f"new_val_{d}")
            if st.button("Adicionar Item", key=f"add_item_{d}"):
                dominio["itens"].append({"tipo": "dominioItemValor", "descricao": desc, "valor": val})

with col2:
    st.header("Pré-visualização (XML)")
    if st.button("Gerar XML"):
        xml_bytes = gerar_xml()
        st.download_button("Baixar XML", data=xml_bytes, file_name="formulario.xml", mime="application/xml")
        st.code(xml_bytes.decode("utf-8"), language="xml")
