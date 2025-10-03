import streamlit as st
import xml.etree.ElementTree as ET

# --------------------------
# Configuração inicial
# --------------------------
st.set_page_config(layout="wide")
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "Novo Formulário",
        "versao": "1.0",
        "secoes": [],
        "dominios": []
    }

# Tipos de elementos permitidos
TIPOS_ELEMENTOS = [
    "texto",
    "texto-area",
    "data",
    "moeda",
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
    "rotulo"
]

# --------------------------
# Funções auxiliares
# --------------------------
def gerar_xml(formulario):
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    elementos_tag = ET.SubElement(root, "elementos")

    for sec in formulario["secoes"]:
        sec_el = ET.SubElement(elementos_tag, "elemento", {
            "gxsi:type": "seccao",
            "titulo": sec["titulo"],
            "largura": "500"
        })
        sec_elementos_tag = ET.SubElement(sec_el, "elementos")

        for campo in sec["campos"]:
            attrs = {
                "gxsi:type": campo["tipo"],
                "titulo": campo.get("titulo", ""),
                "descricao": campo.get("descricao", campo.get("titulo", "")),
                "obrigatorio": str(campo.get("obrigatorio", "false")).lower(),
                "largura": "450"
            }
            if campo["tipo"] == "texto-area":
                attrs["altura"] = campo.get("altura", "100")
            if campo["tipo"] in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                attrs["colunas"] = campo.get("colunas", "1")
                if campo.get("dominio"):
                    attrs["dominio"] = campo["dominio"]
            if campo["tipo"] in ["paragrafo", "rotulo"]:
                attrs["valor"] = campo.get("valor", f"Texto {campo['tipo']}")

            el = ET.SubElement(sec_elementos_tag, "elemento", attrs)

            if campo["tipo"] not in ["paragrafo", "rotulo", "comboBox", "comboFiltro"]:
                conteudo = ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    # Domínios
    if formulario["dominios"]:
        doms_tag = ET.SubElement(root, "dominios")
        for dominio in formulario["dominios"]:
            dom_el = ET.SubElement(doms_tag, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": dominio["chave"]
            })
            itens_tag = ET.SubElement(dom_el, "itens")
            for item in dominio["itens"]:
                ET.SubElement(itens_tag, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": item["descricao"],
                    "valor": item["valor"]
                })

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def render_preview(formulario):
    st.markdown(f"<h2 style='margin-bottom: 10px;'>{formulario['nome']}</h2>", unsafe_allow_html=True)
    for sec in formulario["secoes"]:
        st.markdown(f"<h4 style='margin-top:20px;'>● {sec['titulo']}</h4>", unsafe_allow_html=True)
        for campo in sec["campos"]:
            label = f"{campo['titulo']} ({campo['tipo']})"
            if campo["tipo"] in ["texto", "cpf", "cnpj", "email", "telefone", "moeda", "data"]:
                st.text_input(label, key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] == "texto-area":
                st.text_area(label, key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] == "check":
                st.checkbox(label, key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] in ["comboBox", "comboFiltro"]:
                st.selectbox(label, ["Opção 1", "Opção 2"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] == "grupoRadio":
                st.radio(label, ["Opção 1", "Opção 2"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] == "grupoCheck":
                st.multiselect(label, ["Opção 1", "Opção 2"], key=f"preview_{sec['titulo']}_{campo['titulo']}")
            elif campo["tipo"] == "paragrafo":
                st.markdown(f"**{campo.get('valor','Parágrafo')}**")
            elif campo["tipo"] == "rotulo":
                st.markdown(f"*{campo.get('valor','Rótulo')}*")


# --------------------------
# Layout principal
# --------------------------
col1, col2 = st.columns([1, 1])

# Coluna esquerda: Construtor
with col1:
    st.subheader("Construtor de Formulários")

    st.text_input("Nome do Formulário", key="nome_formulario", value=st.session_state.formulario["nome"])
    st.session_state.formulario["nome"] = st.session_state.nome_formulario

    # Adicionar seção
    nova_secao = st.text_input("Nova Seção", key="nova_secao")
    if st.button("Adicionar Seção"):
        if nova_secao:
            st.session_state.formulario["secoes"].append({"titulo": nova_secao, "campos": []})
            st.session_state.nova_secao = ""

    # Editar seções e campos
    for i, sec in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção: {sec['titulo']}", expanded=False):
            novo_campo_titulo = st.text_input("Título do Campo", key=f"titulo_{i}")
            novo_campo_tipo = st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS, key=f"tipo_{i}")
            obrigatorio = st.checkbox("Obrigatório?", key=f"obrig_{i}")
            dominio = st.text_input("Domínio (se aplicável)", key=f"dom_{i}")

            if st.button("Adicionar Campo", key=f"addcampo_{i}"):
                sec["campos"].append({
                    "titulo": novo_campo_titulo,
                    "tipo": novo_campo_tipo,
                    "obrigatorio": obrigatorio,
                    "dominio": dominio
                })

# Coluna direita: Pré-visualização
with col2:
    st.subheader("Pré-visualização do Formulário")
    render_preview(st.session_state.formulario)

# Pré-visualização do XML
st.subheader("Pré-visualização do XML")
st.code(gerar_xml(st.session_state.formulario), language="xml")
