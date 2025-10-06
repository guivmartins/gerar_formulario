import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários 6.2Beta", layout="wide")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}

# -------------------------
# Funções auxiliares
# -------------------------
def xml_prettify(elem):
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="   ", encoding="UTF-8").decode("utf-8")

def gerar_xml():
    form = st.session_state.formulario
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": form["nome"],
        "versao": form["versao"],
    })
    elementos_tag = ET.SubElement(root, "elementos")

    for secao in form["secoes"]:
        secao_tag = ET.SubElement(elementos_tag, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao["largura"]),
        })
        elementos_secao = ET.SubElement(secao_tag, "elementos")

        # Agrupar elementos com base no uso de tabela
        tabela_aberta = None
        for el in secao["elementos"]:
            if el.get("in_tabela"):
                if tabela_aberta is None:
                    tabela_aberta = ET.SubElement(elementos_secao, "elemento", {"gxsi:type": "tabela"})
                    linhas_tag = ET.SubElement(tabela_aberta, "linhas")
                    linha_tag = ET.SubElement(linhas_tag, "linha")
                    celulas_tag = ET.SubElement(linha_tag, "celulas")
                    celula_tag = ET.SubElement(celulas_tag, "celula", {"linhas": "1", "colunas": "1"})
                    elementos_celula = ET.SubElement(celula_tag, "elementos")
                elementos_destino = elementos_celula
            else:
                tabela_aberta = None
                elementos_destino = elementos_secao

            atributos = {
                "gxsi:type": el["tipo"],
                "titulo": el["titulo"],
                "descricao": el["titulo"],
                "largura": str(el.get("largura", 250)),
                "obrigatorio": str(el.get("obrigatorio", False)).lower(),
            }
            if el["tipo"] in ["paragrafo", "rotulo"]:
                atributos["valor"] = el["titulo"]
            elem_tag = ET.SubElement(elementos_destino, "elemento", atributos)

            conteudo = ET.SubElement(elem_tag, "conteudo", {"gxsi:type": "valor"})
            if el.get("dominio"):
                ET.SubElement(conteudo, "dominio", {"nome": el["dominio"]})

    ET.SubElement(root, "dominios")  # placeholder

    return xml_prettify(root)

def render_preview():
    st.markdown("### 📋 Pré-visualização do Formulário")
    for secao in st.session_state.formulario["secoes"]:
        st.subheader(secao["titulo"])
        tabela_aberta = False
        for el in secao["elementos"]:
            if el.get("in_tabela") and not tabela_aberta:
                st.markdown("<table style='width:100%;border:1px solid #ccc'><tr><td>", unsafe_allow_html=True)
                tabela_aberta = True
            if not el.get("in_tabela") and tabela_aberta:
                st.markdown("</td></tr></table>", unsafe_allow_html=True)
                tabela_aberta = False
            st.text(f"{el['tipo'].upper()} - {el['titulo']}")
        if tabela_aberta:
            st.markdown("</td></tr></table>", unsafe_allow_html=True)

# -------------------------
# Layout principal
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.title("Construtor de Formulários 6.2Beta")

    st.session_state.formulario["nome"] = st.text_input("Nome do formulário", st.session_state.formulario["nome"])
    st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

    # Adicionar seção
    with st.expander("➕ Adicionar Seção"):
        titulo_secao = st.text_input("Título da seção", key="nova_secao_titulo")
        largura_secao = st.number_input("Largura", value=500, step=25, key="nova_secao_largura")
        if st.button("Adicionar seção"):
            st.session_state.formulario["secoes"].append({
                "titulo": titulo_secao,
                "largura": largura_secao,
                "elementos": []
            })
            st.rerun()

    # Exibir seções
    for i, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"📂 {secao['titulo']}"):
            titulo_elem = st.text_input("Título do elemento", key=f"titulo_elem_{i}")
            tipo_elem = st.selectbox("Tipo do elemento", [
                "texto", "numero", "data", "hora",
                "cpf", "cnpj", "telefone", "email",
                "paragrafo", "rotulo", "checkbox", "select"
            ], key=f"tipo_elem_{i}")
            largura_elem = st.number_input("Largura", value=250, step=25, key=f"largura_elem_{i}")
            obrig_elem = st.checkbox("Obrigatório", key=f"obrig_elem_{i}")
            in_tabela = st.checkbox("Dentro da tabela?", key=f"tabela_elem_{i}")

            if st.button("Adicionar elemento", key=f"add_elem_{i}"):
                secao["elementos"].append({
                    "titulo": titulo_elem,
                    "tipo": tipo_elem,
                    "largura": largura_elem,
                    "obrigatorio": obrig_elem,
                    "in_tabela": in_tabela
                })
                st.rerun()

with col2:
    render_preview()
    st.markdown("### 📄 Pré-visualização XML")
    st.code(gerar_xml(), language="xml")
