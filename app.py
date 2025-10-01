import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# Inicializar estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}
if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

st.title("Construtor de Formulários")

# Layout: duas colunas (Construtor e Pré-visualização)
col1, col2 = st.columns(2)

# ============================
# CONSTRUTOR (coluna esquerda)
# ============================
with col1:
    # Nome do formulário
    st.session_state.formulario["nome"] = st.text_input(
        "Nome do Formulário", st.session_state.formulario["nome"]
    )

    st.markdown("---")

    # Criar nova seção
    with st.expander("➕ Adicionar Seção", expanded=True):
        st.session_state.nova_secao["titulo"] = st.text_input(
            "Título da Seção", st.session_state.nova_secao["titulo"]
        )
        st.session_state.nova_secao["largura"] = st.number_input(
            "Largura da Seção", min_value=100, value=500, step=10
        )

        if st.button("Salvar Seção"):
            if st.session_state.nova_secao["titulo"]:
                st.session_state.formulario["secoes"].append(
                    st.session_state.nova_secao.copy()
                )
                st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}
                st.rerun()

    # Mostrar seções existentes com opção de excluir
    for idx_secao, secao in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {secao['titulo']}", expanded=False):
            st.write(f"**Largura:** {secao['largura']}")

            # Botão para excluir seção
            if st.button(f"🗑️ Excluir Seção {secao['titulo']}", key=f"del_secao_{idx_secao}"):
                del st.session_state.formulario["secoes"][idx_secao]
                st.rerun()

            st.markdown("### Campos")
            for idx_campo, campo in enumerate(secao["campos"]):
                with st.container():
                    st.write(f"**{campo['tipo']} - {campo.get('titulo','')}**")

                    # Botão para excluir campo
                    if st.button(
                        f"Excluir Campo {campo.get('titulo','') or campo['tipo']}",
                        key=f"del_campo_{idx_secao}_{idx_campo}",
                    ):
                        del st.session_state.formulario["secoes"][idx_secao]["campos"][idx_campo]
                        st.rerun()

    # Adicionar campos à última seção
    if st.session_state.formulario["secoes"]:
        secao_atual = st.session_state.formulario["secoes"][-1]

        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual['titulo']}", expanded=True):
            titulo = st.text_input("Título do Campo")
            tipo = st.selectbox(
                "Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"]
            )
            obrigatorio = False
            if tipo not in ["paragrafo"]:
                obrigatorio = st.checkbox("Obrigatório", value=False)

            largura = st.number_input("Largura", min_value=100, value=450, step=10)
            altura = None
            if tipo in ["texto-area"]:
                altura = st.number_input("Altura", min_value=50, value=100, step=10)

            valor_paragrafo = ""
            if tipo == "paragrafo":
                valor_paragrafo = st.text_area("Valor do Parágrafo")

            colunas = None
            dominios = []
            if tipo in ["grupoRadio", "grupoCheck"]:
                colunas = st.number_input(
                    "Quantidade de Colunas", min_value=1, max_value=5, value=2
                )
                qtd_dominios = st.number_input(
                    "Quantidade de Domínios", min_value=1, max_value=10, value=2
                )
                for i in range(qtd_dominios):
                    desc = st.text_input(f"Descrição Domínio {i+1}", key=f"dom_{i}")
                    if desc:
                        dominios.append(
                            {"descricao": desc, "valor": desc.replace(" ", "_").upper()}
                        )

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

# ============================
# PRÉ-VISUALIZAÇÃO (coluna direita)
# ============================
with col2:
    st.subheader("📋 Pré-visualização do Formulário")
    st.write(f"**Nome:** {st.session_state.formulario['nome']}")
    for secao in st.session_state.formulario["secoes"]:
        st.write(f"### • {secao['titulo']}") #antes markdown
        for campo in secao["campos"]:
            if campo["tipo"] == "texto":
                st.text_input(campo["titulo"], value="")
            elif campo["tipo"] == "texto-area":
                st.text_area(campo["titulo"], value="", height=campo.get("altura", 100))
            elif campo["tipo"] == "paragrafo":
                st.markdown(f"> {campo['valor']}")
            elif campo["tipo"] == "grupoRadio":
                st.radio(campo["titulo"], [d["descricao"] for d in campo["dominios"]])
            elif campo["tipo"] == "grupoCheck":
                st.multiselect(campo["titulo"], [d["descricao"] for d in campo["dominios"]])

# ============================
# FUNÇÃO DE EXPORTAÇÃO XML
# ============================
def gerar_xml():
    root = ET.Element(
        "gxsi:formulario",
        {
            "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
            "nome": st.session_state.formulario["nome"],
            "versao": st.session_state.formulario["versao"],
        },
    )

    elementos = ET.SubElement(root, "elementos")
    dominios_global = ET.Element("dominios")  # fora de <elementos>

    for secao in st.session_state.formulario["secoes"]:
        el_secao = ET.SubElement(
            elementos,
            "elemento",
            {
                "gxsi:type": "seccao",
                "titulo": secao["titulo"],
                "largura": str(secao["largura"]),
            },
        )
        subelementos = ET.SubElement(el_secao, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(
                    subelementos,
                    "elemento",
                    {
                        "gxsi:type": "paragrafo",
                        "valor": campo["valor"],
                        "largura": str(campo["largura"]),
                    },
                )
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                ET.SubElement(
                    subelementos,
                    "elemento",
                    {
                        "gxsi:type": campo["tipo"],
                        "titulo": campo["titulo"],
                        "obrigatorio": str(campo["obrigatorio"]).lower(),
                        "largura": str(campo["largura"]),
                        "colunas": str(campo["colunas"]),
                        "dominio": campo["titulo"].replace(" ", "")[:20].upper(),
                    },
                )
                chave = campo["titulo"].replace(" ", "")[:20].upper()
                dominio = ET.SubElement(
                    dominios_global,
                    "dominio",
                    {"gxsi:type": "dominioEstatico", "chave": chave},
                )
                itens = ET.SubElement(dominio, "itens")
                for d in campo["dominios"]:
                    ET.SubElement(
                        itens,
                        "item",
                        {
                            "gxsi:type": "dominioItemValor",
                            "descricao": d["descricao"],
                            "valor": d["valor"],
                        },
                    )
            else:
                el = ET.SubElement(
                    subelementos,
                    "elemento",
                    {
                        "gxsi:type": campo["tipo"],
                        "titulo": campo["titulo"],
                        "obrigatorio": str(campo["obrigatorio"]).lower(),
                        "largura": str(campo["largura"]),
                    },
                )
                if campo["altura"]:
                    el.set("altura", str(campo["altura"]))
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    # adicionar dominios no final do root
    root.append(dominios_global)

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# ============================
# PRÉ-VISUALIZAÇÃO DO XML
# ============================
st.markdown("---")
st.subheader("📑 Pré-visualização do XML")
st.code(gerar_xml(), language="xml")

