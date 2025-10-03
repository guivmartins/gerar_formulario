import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# ------------------------
# Estado inicial
# ------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}
if "dominios" not in st.session_state:
    st.session_state.dominios = []

# ------------------------
# Funções auxiliares
# ------------------------
def gerar_xml():
    formulario = st.session_state.formulario
    dominios = st.session_state.dominios

    root = ET.Element(
        "gxsi:formulario",
        {
            "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
            "nome": formulario["nome"] or "Formulario",
            "versao": formulario["versao"],
        },
    )

    elementos_tag = ET.SubElement(root, "elementos")

    # Seções e elementos
    for secao in formulario["secoes"]:
        secao_el = ET.SubElement(
            elementos_tag,
            "elemento",
            {"gxsi:type": "seccao", "titulo": secao["titulo"], "largura": str(secao["largura"])},
        )
        secao_elementos = ET.SubElement(secao_el, "elementos")

        for elem in secao["elementos"]:
            atributos = {
                "gxsi:type": elem["tipo"],
                "titulo": elem["titulo"],
                "descricao": elem.get("descricao", ""),
                "obrigatorio": str(elem.get("obrigatorio", False)).lower(),
                "largura": str(elem.get("largura", 450)),
            }
            if elem["tipo"] in ["texto-area"]:
                atributos["altura"] = str(elem.get("altura", 120))
            if elem["tipo"] in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                atributos["colunas"] = str(elem.get("colunas", 1))
                atributos["dominio"] = elem.get("dominio", "")

            el = ET.SubElement(secao_elementos, "elemento", atributos)

            # Conteúdo para tipos de valor
            if elem["tipo"] not in ["paragrafo", "rotulo", "comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                conteudo = ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
            elif elem["tipo"] in ["paragrafo", "rotulo"]:
                el.set("valor", elem.get("valor", ""))

    # Domínios
    if dominios:
        dominios_tag = ET.SubElement(root, "dominios")
        for dom in dominios:
            dom_el = ET.SubElement(
                dominios_tag,
                "dominio",
                {"gxsi:type": "dominioEstatico", "chave": dom["chave"]},
            )
            itens_el = ET.SubElement(dom_el, "itens")
            for item in dom["itens"]:
                ET.SubElement(
                    itens_el,
                    "item",
                    {
                        "gxsi:type": "dominioItemValor",
                        "descricao": item["descricao"],
                        "valor": item["valor"],
                    },
                )

    xml_str = ET.tostring(root, encoding="utf-8")
    xml_pretty = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")
    return xml_pretty.decode("utf-8")


def adicionar_secao(titulo, largura):
    st.session_state.formulario["secoes"].append({"titulo": titulo, "largura": largura, "elementos": []})


def adicionar_elemento(secao_idx, elem):
    st.session_state.formulario["secoes"][secao_idx]["elementos"].append(elem)


def adicionar_dominio(chave):
    st.session_state.dominios.append({"chave": chave, "itens": []})


def adicionar_item_dominio(dominio_idx, descricao, valor):
    st.session_state.dominios[dominio_idx]["itens"].append({"descricao": descricao, "valor": valor})


# ------------------------
# Interface
# ------------------------
st.title("Construtor de Formulários 4.1 (Estável)")

col1, col2 = st.columns([2, 2])

with col1:
    st.header("Configuração do Formulário")
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
    st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

    st.subheader("Seções")
    nova_secao_titulo = st.text_input("Título da nova seção")
    nova_secao_largura = st.number_input("Largura da seção", 100, 1000, 500)
    if st.button("Adicionar Seção") and nova_secao_titulo:
        adicionar_secao(nova_secao_titulo, nova_secao_largura)

    for i, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {secao['titulo']}"):
            st.write(f"Largura: {secao['largura']}")

            tipo = st.selectbox(
                "Tipo de elemento",
                [
                    "data",
                    "moeda",
                    "texto-area",
                    "texto",
                    "cpf",
                    "cnpj",
                    "email",
                    "telefone",
                    "check",
                    "comboBox",
                    "comboFiltro",
                    "grupoRadio",
                    "grupoCheck",
                    "paragrafo",
                    "rotulo",
                ],
                key=f"tipo_{i}",
            )
            titulo = st.text_input("Título", key=f"titulo_{i}")
            descricao = st.text_input("Descrição", key=f"desc_{i}")
            obrigatorio = st.checkbox("Obrigatório", key=f"obrig_{i}")
            largura = st.number_input("Largura", 100, 1000, 450, key=f"largura_{i}")
            altura = None
            valor = None
            colunas = None
            dominio = None

            if tipo == "texto-area":
                altura = st.number_input("Altura", 50, 500, 120, key=f"altura_{i}")
            if tipo in ["paragrafo", "rotulo"]:
                valor = st.text_input("Valor", key=f"valor_{i}")
            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                colunas = st.number_input("Colunas", 1, 5, 1, key=f"col_{i}")
                if st.session_state.dominios:
                    dominio = st.selectbox(
                        "Domínio",
                        [d["chave"] for d in st.session_state.dominios],
                        key=f"dom_{i}",
                    )

            if st.button("Adicionar Elemento", key=f"add_{i}"):
                elem = {
                    "tipo": tipo,
                    "titulo": titulo,
                    "descricao": descricao,
                    "obrigatorio": obrigatorio,
                    "largura": largura,
                }
                if altura:
                    elem["altura"] = altura
                if valor:
                    elem["valor"] = valor
                if colunas:
                    elem["colunas"] = colunas
                if dominio:
                    elem["dominio"] = dominio
                adicionar_elemento(i, elem)

    st.subheader("Domínios")
    novo_dom = st.text_input("Chave do novo domínio")
    if st.button("Adicionar Domínio") and novo_dom:
        adicionar_dominio(novo_dom)

    for i, dom in enumerate(st.session_state.dominios):
        with st.expander(f"Domínio: {dom['chave']}"):
            desc = st.text_input("Descrição do item", key=f"desc_dom_{i}")
            val = st.text_input("Valor do item", key=f"val_dom_{i}")
            if st.button("Adicionar Item", key=f"add_item_dom_{i}"):
                adicionar_item_dominio(i, desc, val)

with col2:
    st.header("Pré-visualização do XML")
    xml = gerar_xml()
    st.code(xml, language="xml")

    st.download_button("Baixar XML", data=xml, file_name="formulario.xml", mime="application/xml")
