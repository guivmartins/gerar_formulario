import streamlit as st 
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# Inicializar estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "", "secoes": []}

st.title("Construtor de Formulários")

# Nome e versão
st.session_state.formulario["nome"] = st.text_input(
    "Nome do Formulário", st.session_state.formulario["nome"]
)
st.session_state.formulario["versao"] = st.text_input(
    "Versão", st.session_state.formulario["versao"]
)

st.markdown("---")

# Criar nova seção
with st.expander("➕ Adicionar Seção", expanded=True):
    titulo_secao = st.text_input("Título da Seção")
    largura_secao = st.number_input("Largura da Seção", min_value=100, value=500, step=10)

    if st.button("Salvar Seção"):
        if titulo_secao.strip():
            nova_secao = {"titulo": titulo_secao, "largura": largura_secao, "campos": []}
            st.session_state.formulario["secoes"].append(nova_secao)
            st.rerun()

# Adicionar campos à última seção
if st.session_state.formulario["secoes"]:
    secao_atual = st.session_state.formulario["secoes"][-1]

    with st.expander(f"➕ Adicionar Campos à seção: {secao_atual['titulo']}", expanded=True):
        titulo = st.text_input("Título do Campo")
        tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
        obrigatorio = False
        if tipo != "paragrafo":
            obrigatorio = st.checkbox("Obrigatório", value=False)

        largura = st.number_input("Largura", min_value=100, value=450, step=10)
        altura = None
        if tipo == "texto-area":
            altura = st.number_input("Altura", min_value=50, value=100, step=10)

        valor_paragrafo = ""
        if tipo == "paragrafo":
            valor_paragrafo = st.text_area("Valor do Parágrafo")

        colunas = None
        dominios = []
        if tipo in ["grupoRadio", "grupoCheck"]:
            colunas = st.number_input("Quantidade de Colunas", min_value=1, max_value=5, value=1)
            qtd_dominios = st.number_input("Quantidade de Domínios", min_value=1, max_value=10, value=2)
            for i in range(qtd_dominios):
                desc = st.text_input(f"Descrição Domínio {i+1}", key=f"dom_{i}")
                if desc:
                    dominios.append({"descricao": desc, "valor": desc.replace(" ", "_").upper()})

        if st.button("Adicionar Campo"):
            campo = {
                "titulo": titulo,
                "tipo": tipo,
                "obrigatorio": obrigatorio,
                "largura": largura,
                "altura": altura,
                "valor": valor_paragrafo,
                "colunas": colunas,
                "dominios": dominios,
            }
            secao_atual["campos"].append(campo)
            st.rerun()

# Listar seções
for i, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"✏️ Seção: {secao['titulo']}", expanded=False):
        secao["titulo"] = st.text_input("Título da Seção", value=secao["titulo"], key=f"sec_titulo_{i}")
        secao["largura"] = st.number_input("Largura da Seção", min_value=100, value=secao["largura"], step=10, key=f"sec_largura_{i}")

        if st.button(f"🗑️ Excluir Seção {i+1}", key=f"del_secao_{i}"):
            st.session_state.formulario["secoes"].pop(i)
            st.rerun()

        st.markdown("**Campos desta seção:**")
        for j, campo in enumerate(secao["campos"]):
            st.markdown(f"- {campo['titulo']} ({campo['tipo']})")
            if st.button(f"🗑️ Excluir Campo {j+1}", key=f"del_campo_{i}_{j}"):
                secao["campos"].pop(j)
                st.rerun()

st.markdown("---")

# Função de geração do XML indentado
def gerar_xml():
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": st.session_state.formulario["nome"],
        "versao": st.session_state.formulario["versao"]
    })

    elementos = ET.SubElement(root, "elementos")

    for secao in st.session_state.formulario["secoes"]:
        el_secao = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao["largura"])
        })
        subelementos = ET.SubElement(el_secao, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo["valor"],
                    "largura": str(campo["largura"])
                })
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                el = ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"]),
                    "colunas": str(campo["colunas"])
                })
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
            else:
                el = ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"])
                })
                if campo["altura"]:
                    el.set("altura", str(campo["altura"]))
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# Pré-visualização
st.subheader("Pré-visualização do Formulário")
st.code(gerar_xml(), language="xml")

# Exportação
xml_str = gerar_xml()
st.download_button("⬇️ Exportar XML", xml_str, file_name="formulario.xml", mime="application/xml")
st.download_button("⬇️ Exportar GFE", xml_str, file_name="formulario.gfe", mime="application/xml")
