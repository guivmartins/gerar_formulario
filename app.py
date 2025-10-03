# app.py - Construtor de Formulários com Domínios (versão 6.0 corrigida)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}
if "dominios" not in st.session_state:
    st.session_state.dominios = {}

# -------------------------
# Funções auxiliares
# -------------------------
def adicionar_secao(nome):
    st.session_state.formulario["secoes"].append({"nome": nome, "campos": []})

def adicionar_campo(secao_nome, nome, tipo, obrigatorio, dominio):
    for secao in st.session_state.formulario["secoes"]:
        if secao["nome"] == secao_nome:
            secao["campos"].append(
                {"nome": nome, "tipo": tipo, "obrigatorio": obrigatorio, "dominio": dominio}
            )

def gerar_xml(formulario):
    root = ET.Element("formulario", xmlns="http://www.gxsi.com.br/formulario")
    ET.SubElement(root, "nome").text = formulario["nome"]
    ET.SubElement(root, "versao").text = formulario["versao"]

    elementos = ET.SubElement(root, "elementos")
    for secao in formulario["secoes"]:
        secao_el = ET.SubElement(elementos, "secao", nome=secao["nome"])
        for campo in secao["campos"]:
            campo_el = ET.SubElement(secao_el, "campo")
            ET.SubElement(campo_el, "nome").text = campo["nome"]
            ET.SubElement(campo_el, "tipo").text = campo["tipo"]
            ET.SubElement(campo_el, "obrigatorio").text = str(campo["obrigatorio"]).lower()
            if campo["dominio"]:
                ET.SubElement(campo_el, "dominio").text = campo["dominio"]

    dominios_el = ET.SubElement(root, "dominios")
    for nome_dom, valores in st.session_state.dominios.items():
        dom_el = ET.SubElement(dominios_el, "dominio", nome=nome_dom)
        for valor in valores:
            ET.SubElement(dom_el, "valor").text = valor

    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

def gerar_preview_formulario(formulario):
    st.subheader("📋 Pré-visualização do Formulário")

    st.markdown(f"**Nome:** {formulario['nome']}")
    st.markdown(f"**Versão:** {formulario['versao']}")

    for secao in formulario["secoes"]:
        st.markdown(f"### {secao['nome']}")
        if len(secao["campos"]) > 0:
            tabela_md = "| Nome | Tipo | Obrigatório | Domínio |\n"
            tabela_md += "|------|------|-------------|---------|\n"
            for campo in secao["campos"]:
                obrig = "✅" if campo["obrigatorio"] else "❌"
                dominio = campo["dominio"] if campo["dominio"] else "-"
                tabela_md += f"| {campo['nome']} | {campo['tipo']} | {obrig} | {dominio} |\n"
            st.markdown(tabela_md)
        else:
            st.markdown("_(Sem campos nesta seção)_")

    # Pré-visualização do XML
    st.subheader("📄 Pré-visualização XML")
    xml_str = gerar_xml(formulario)
    st.code(xml_str, language="xml")

# -------------------------
# Interface Streamlit
# -------------------------
st.title("🛠️ Construtor de Formulários GXSI")

# Dados principais
st.header("📑 Dados do Formulário")
st.session_state.formulario["nome"] = st.text_input("Nome do formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

# Seções
st.header("📂 Seções")
nome_secao = st.text_input("Nome da nova seção")
if st.button("Adicionar Seção"):
    if nome_secao.strip():
        adicionar_secao(nome_secao.strip())

for secao in st.session_state.formulario["secoes"]:
    with st.expander(f"Seção: {secao['nome']}"):
        nome_campo = st.text_input(f"Nome do campo ({secao['nome']})", key=f"campo_nome_{secao['nome']}")
        tipo_campo = st.selectbox(f"Tipo do campo ({secao['nome']})",
                                  ["texto", "numero", "data", "booleano", "dominio"],
                                  key=f"campo_tipo_{secao['nome']}")
        obrigatorio = st.checkbox(f"Obrigatório ({secao['nome']})", key=f"campo_obr_{secao['nome']}")
        dominio = ""
        if tipo_campo == "dominio":
            dominio = st.selectbox(f"Domínio ({secao['nome']})", list(st.session_state.dominios.keys()) or [""])

        if st.button(f"Adicionar Campo ({secao['nome']})", key=f"addcampo_{secao['nome']}"):
            if nome_campo.strip():
                adicionar_campo(secao["nome"], nome_campo.strip(), tipo_campo, obrigatorio, dominio)

# Domínios
st.header("📚 Domínios")
nome_dominio = st.text_input("Nome do domínio")
valores_dominio = st.text_area("Valores (um por linha)")
if st.button("Adicionar Domínio"):
    if nome_dominio.strip():
        st.session_state.dominios[nome_dominio.strip()] = [v.strip() for v in valores_dominio.splitlines() if v.strip()]

if st.session_state.dominios:
    for dom, vals in st.session_state.dominios.items():
        st.markdown(f"**{dom}:** {', '.join(vals)}")

# Preview
gerar_preview_formulario(st.session_state.formulario)

# Exportação
st.header("💾 Exportar")
xml_str = gerar_xml(st.session_state.formulario)
st.download_button("Baixar XML", xml_str, file_name="formulario.xml", mime="application/xml")
