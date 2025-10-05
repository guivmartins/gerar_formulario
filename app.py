# app.py - Construtor de Formulários GXSI XML (versão 6.4Alpha)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata

st.set_page_config(page_title="Construtor de Formulários GXSI", layout="centered")

# ----------------------------------
# Inicialização do estado do app
# ----------------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"secoes": [], "dominios": []}

if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = ""
if "novo_elemento" not in st.session_state:
    st.session_state.novo_elemento = {}
if "preview_xml" not in st.session_state:
    st.session_state.preview_xml = ""
if "preview_form" not in st.session_state:
    st.session_state.preview_form = ""

# ----------------------------------
# Funções auxiliares
# ----------------------------------

def normalizar_nome(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return texto.upper().replace(" ", "").replace("-", "").replace("_", "")

def gerar_xml(formulario):
    root = ET.Element("formulario", {"xmlns:gxsi": "gxsi"})

    elementos_tag = ET.SubElement(root, "elementos")
    for secao in formulario["secoes"]:
        secao_tag = ET.SubElement(elementos_tag, "secao", {"titulo": secao["titulo"]})
        for elemento in secao["elementos"]:
            e_attrs = {
                "gxsi:type": elemento["tipo"],
                "titulo": elemento["titulo"],
                "obrigatorio": str(elemento["obrigatorio"]).lower(),
                "colunas": str(elemento.get("colunas", 1)),
            }
            e_tag = ET.SubElement(secao_tag, "elemento", e_attrs)

            # Se for tabela
            if elemento.get("tabela", False):
                ET.SubElement(e_tag, "celula", {"linhas": "1", "colunas": "1"})

    dominios_tag = ET.SubElement(root, "dominios")
    for dominio in formulario["dominios"]:
        d_tag = ET.SubElement(
            dominios_tag,
            "dominio",
            {"gxsi:type": "dominioEstatico", "chave": dominio["chave"]},
        )
        itens_tag = ET.SubElement(d_tag, "itens")
        for item in dominio["itens"]:
            ET.SubElement(
                itens_tag,
                "item",
                {
                    "gxsi:type": "dominioItemValor",
                    "descricao": item["descricao"],
                    "valor": item["valor"],
                },
            )

    xml_str = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# ----------------------------------
# Interface principal
# ----------------------------------

st.title("🧩 Construtor de Formulários GXSI XML")
st.markdown("---")

# Adicionar seção
with st.expander("➕ Adicionar Nova Seção"):
    nova_secao = st.text_input("Título da Seção", key="titulo_secao")
    if st.button("Adicionar Seção"):
        if nova_secao.strip():
            st.session_state.formulario["secoes"].append(
                {"titulo": nova_secao.strip(), "elementos": []}
            )
            st.success(f"✅ Seção '{nova_secao}' adicionada!")
            st.session_state.titulo_secao = ""

# Exibir e editar seções
for idx, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"📂 {secao['titulo']}", expanded=False):
        novo_titulo = st.text_input("Título do Elemento", key=f"titulo_{idx}")
        tipo = st.selectbox(
            "Tipo do Elemento",
            [
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
                "rotulo",
            ],
            key=f"tipo_{idx}",
        )
        obrigatorio = st.checkbox("Campo obrigatório?", key=f"obrigatorio_{idx}")
        tabela = st.checkbox("Elemento pertence a uma tabela?", key=f"tabela_{idx}")
        colunas = st.number_input("Colunas", min_value=1, max_value=12, value=1, key=f"colunas_{idx}")

        dominio_info = None
        if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
            dominio_chave = normalizar_nome(novo_titulo)
            st.markdown(f"**Nome do domínio gerado:** `{dominio_chave}`")

            if "dominios_temp" not in st.session_state:
                st.session_state.dominios_temp = {}
            if dominio_chave not in st.session_state.dominios_temp:
                st.session_state.dominios_temp[dominio_chave] = []

            st.subheader("🗂️ Itens do Domínio")
            cols = st.columns([3, 3, 1])
            if cols[2].button("Adicionar Item", key=f"additem_{idx}"):
                st.session_state.dominios_temp[dominio_chave].append(
                    {"descricao": "", "valor": ""}
                )

            for i, item in enumerate(st.session_state.dominios_temp[dominio_chave]):
                c1, c2, c3 = st.columns([3, 3, 1])
                item["descricao"] = c1.text_input("Descrição", item["descricao"], key=f"desc_{idx}_{i}")
                item["valor"] = c2.text_input("Valor", item["valor"], key=f"valor_{idx}_{i}")
                if c3.button("🗑️", key=f"del_{idx}_{i}"):
                    st.session_state.dominios_temp[dominio_chave].pop(i)
                    st.experimental_rerun()

            dominio_info = {
                "chave": dominio_chave,
                "itens": st.session_state.dominios_temp[dominio_chave],
            }

        if st.button("Adicionar Elemento", key=f"addelem_{idx}"):
            elemento = {
                "titulo": novo_titulo,
                "tipo": tipo,
                "obrigatorio": obrigatorio,
                "tabela": tabela,
                "colunas": colunas,
            }
            if dominio_info:
                elemento["dominio"] = dominio_info
                st.session_state.formulario["dominios"].append(dominio_info)
            st.session_state.formulario["secoes"][idx]["elementos"].append(elemento)
            st.success("✅ Elemento adicionado!")

# ----------------------------------
# Pré-visualizações
# ----------------------------------

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧾 Pré-visualização do Formulário")
    for secao in st.session_state.formulario["secoes"]:
        st.markdown(f"### {secao['titulo']}")
        for elem in secao["elementos"]:
            tipo = elem["tipo"]
            label = f"**{elem['titulo']}**"
            if tipo == "texto":
                st.text_input(label, key=f"prev_{label}")
            elif tipo == "texto-area":
                st.text_area(label, key=f"prev_{label}")
            elif tipo == "data":
                st.date_input(label, key=f"prev_{label}")
            elif tipo == "moeda":
                st.text_input(label, placeholder="0,00", key=f"prev_{label}")
            elif tipo == "cpf":
                st.text_input(label, placeholder="000.000.000-00", key=f"prev_{label}")
            elif tipo == "cnpj":
                st.text_input(label, placeholder="00.000.000/0000-00", key=f"prev_{label}")
            elif tipo == "email":
                st.text_input(label, placeholder="exemplo@email.com", key=f"prev_{label}")
            elif tipo == "telefone":
                st.text_input(label, placeholder="(00) 00000-0000", key=f"prev_{label}")
            elif tipo == "check":
                st.checkbox(label, key=f"prev_{label}")
            elif tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                opcoes = [i["descricao"] for i in elem.get("dominio", {}).get("itens", [])]
                if tipo in ["comboBox", "comboFiltro"]:
                    st.selectbox(label, options=opcoes, key=f"prev_{label}")
                elif tipo == "grupoRadio":
                    st.radio(label, options=opcoes, key=f"prev_{label}")
                elif tipo == "grupoCheck":
                    st.multiselect(label, options=opcoes, key=f"prev_{label}")
            elif tipo == "paragrafo":
                st.markdown(f"> {elem['titulo']}")
            elif tipo == "rotulo":
                st.caption(elem["titulo"])

with col2:
    st.subheader("🧩 Pré-visualização XML")
    if st.button("Gerar XML"):
        xml = gerar_xml(st.session_state.formulario)
        st.session_state.preview_xml = xml
    st.code(st.session_state.preview_xml, language="xml")