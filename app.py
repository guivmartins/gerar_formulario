import streamlit as st
import xml.etree.ElementTree as ET

st.set_page_config(layout="wide")

# -------------------------
# Função para gerar XML
# -------------------------
def gerar_xml(formulario, dominios):
    root = ET.Element("formulario", attrib={"xmlns:gxsi": "http://www.gxsi.com.br"})

    elementos_tag = ET.SubElement(root, "elementos")
    for secao in formulario:
        secao_tag = ET.SubElement(elementos_tag, "secao", titulo=secao["titulo"])
        for campo in secao["campos"]:
            elem = ET.SubElement(
                secao_tag,
                "elemento",
                attrib={
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo.get("obrigatorio", False)).lower(),
                },
            )
            if campo.get("dominio"):
                elem.set("dominio", campo["dominio"])
            if campo.get("colunas"):
                elem.set("colunas", campo["colunas"])
            ET.SubElement(elem, "conteudo", attrib={"gxsi:type": "valor"})

    # Tag de domínios fora de <elementos>
    dominios_tag = ET.SubElement(root, "dominios")
    for nome, valores in dominios.items():
        dominio_tag = ET.SubElement(dominios_tag, "dominio", nome=nome)
        for v in valores:
            ET.SubElement(dominio_tag, "item").text = v

    return ET.tostring(root, encoding="unicode")

# -------------------------
# Função de pré-visualização do formulário
# -------------------------
def render_form_preview(formulario, dominios):
    for secao in formulario:
        st.subheader(secao["titulo"])
        for campo in secao["campos"]:
            tipo = campo["tipo"]
            titulo = campo["titulo"]
            dominio = campo.get("dominio")
            obrigatorio = campo.get("obrigatorio", False)

            # Identificar valores de domínio
            opcoes = []
            if dominio and dominio in dominios:
                opcoes = dominios[dominio]

            if tipo == "texto":
                st.text_input(titulo, placeholder="Digite aqui...")
            elif tipo == "combo":
                st.selectbox(titulo, opcoes if opcoes else ["Opção 1", "Opção 2"])
            elif tipo == "grupoCheck":
                st.multiselect(titulo, opcoes if opcoes else ["Item A", "Item B"])
            elif tipo == "grupoRadio":
                st.radio(titulo, opcoes if opcoes else ["Sim", "Não"])
            else:
                st.write(f"⚠️ Tipo não suportado: {tipo}")

# -------------------------
# Sessão principal
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = [
        {"titulo": "Dados do Cooperado", "campos": []}
    ]
if "dominios" not in st.session_state:
    st.session_state.dominios = {
        "empregadoSicoob": ["Sim", "Não"],
        "testeGed": ["Doc1", "Doc2"],
    }

col1, col2 = st.columns([1,1])

# -------------------------
# Coluna esquerda: Construtor
# -------------------------
with col1:
    st.header("Construtor de Formulários")

    for i, secao in enumerate(st.session_state.formulario):
        with st.expander(f"Seção: {secao['titulo']}", expanded=False):
            novo_titulo = st.text_input("Título da seção", value=secao["titulo"], key=f"sec_{i}")
            secao["titulo"] = novo_titulo

            if st.button("Adicionar campo", key=f"add_campo_{i}"):
                secao["campos"].append(
                    {"tipo": "texto", "titulo": "Novo Campo", "obrigatorio": False}
                )

            for j, campo in enumerate(secao["campos"]):
                with st.container():
                    campo["titulo"] = st.text_input("Título do campo", campo["titulo"], key=f"titulo_{i}_{j}")
                    campo["tipo"] = st.selectbox("Tipo", ["texto", "combo", "grupoCheck", "grupoRadio"], key=f"tipo_{i}_{j}", index=["texto", "combo", "grupoCheck", "grupoRadio"].index(campo["tipo"]))
                    campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo["obrigatorio"], key=f"obrig_{i}_{j}")
                    campo["dominio"] = st.text_input("Domínio (se aplicável)", value=campo.get("dominio",""), key=f"dom_{i}_{j}")
                    campo["colunas"] = st.text_input("Colunas (opcional)", value=campo.get("colunas",""), key=f"col_{i}_{j}")

    if st.button("Adicionar seção"):
        st.session_state.formulario.append({"titulo": "Nova Seção", "campos": []})

# -------------------------
# Coluna direita: Pré-visualização
# -------------------------
with col2:
    st.header("Pré-visualização")

    tab_xml, tab_form = st.tabs(["XML", "Formulário"])

    with tab_xml:
        xml_output = gerar_xml(st.session_state.formulario, st.session_state.dominios)
        st.code(xml_output, language="xml")

    with tab_form:
        render_form_preview(st.session_state.formulario, st.session_state.dominios)
