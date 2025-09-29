import streamlit as st
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# Estado inicial
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "",
        "secoes": [],
        "dominios": {}
    }

st.title("Construtor de Formulários")

with st.container():
    # Nome e versão
    st.session_state.formulario["nome"] = st.text_input("Nome do formulário", value=st.session_state.formulario["nome"])
    st.session_state.formulario["versao"] = st.text_input("Versão", value=st.session_state.formulario["versao"])

    st.divider()
    st.subheader("Adicionar Seções")

    # Criar nova seção
    with st.expander("➕ Nova Seção"):
        titulo_secao = st.text_input("Título da Seção")
        largura_secao = st.number_input("Largura da Seção", value=500, step=10)
        if st.button("Adicionar Seção"):
            if titulo_secao:
                st.session_state.formulario["secoes"].append({
                    "titulo": titulo_secao,
                    "largura": largura_secao,
                    "campos": []
                })

    # Selecionar seção para adicionar campos
    if st.session_state.formulario["secoes"]:
        st.divider()
        st.subheader("Adicionar Campos")
        secao_idx = st.selectbox("Selecione a seção", range(len(st.session_state.formulario["secoes"])),
                                 format_func=lambda i: st.session_state.formulario["secoes"][i]["titulo"])

        with st.expander("➕ Novo Campo"):
            tipo = st.selectbox("Tipo do campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
            largura = st.number_input("Largura do campo", value=450, step=10)
            altura = None
            obrigatorio = False
            titulo = ""
            valor_paragrafo = ""
            colunas = 1
            dominios = []

            if tipo != "paragrafo":
                titulo = st.text_input("Título do campo")
                obrigatorio = st.checkbox("Obrigatório?", value=False)
            else:
                valor_paragrafo = st.text_area("Valor do parágrafo")

            if tipo == "texto-area":
                altura = st.number_input("Altura do campo", value=100, step=10)

            if tipo in ["grupoRadio", "grupoCheck"]:
                colunas = st.number_input("Quantidade de colunas", min_value=1, max_value=5, value=1)
                qtd_itens = st.number_input("Quantidade de opções", min_value=1, value=2)
                dominios = []
                for i in range(qtd_itens):
                    descricao = st.text_input(f"Descrição da opção {i+1}")
                    if descricao:
                        valor = descricao.upper().replace(" ", "_")
                        dominios.append({"descricao": descricao, "valor": valor})

            if st.button("Adicionar Campo"):
                campo = {
                    "tipo": tipo,
                    "largura": largura,
                }
                if tipo != "paragrafo":
                    campo["titulo"] = titulo
                    campo["obrigatorio"] = obrigatorio
                else:
                    campo["valor"] = valor_paragrafo
                if tipo == "texto-area":
                    campo["altura"] = altura
                if tipo in ["grupoRadio", "grupoCheck"]:
                    chave = titulo.replace(" ", "")[:20].upper()
                    if chave in st.session_state.formulario["dominios"]:
                        chave += "1"
                    st.session_state.formulario["dominios"][chave] = dominios
                    campo["colunas"] = colunas
                    campo["dominio"] = chave

                st.session_state.formulario["secoes"][secao_idx]["campos"].append(campo)

# -------- Gerar XML --------
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
        els = ET.SubElement(el_secao, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                el = ET.SubElement(els, "elemento", {
                    "gxsi:type": "paragrafo",
                    "largura": str(campo["largura"])
                })
                conteudo = ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
                conteudo.text = campo.get("valor", "")
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                el = ET.SubElement(els, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"]),
                    "colunas": str(campo["colunas"])
                })
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor", "dominio": campo["dominio"]})
            else:
                attrs = {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"])
                }
                if campo["tipo"] == "texto-area":
                    attrs["altura"] = str(campo["altura"])
                el = ET.SubElement(els, "elemento", attrs)
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    if st.session_state.formulario["dominios"]:
        dominios = ET.SubElement(root, "dominios")
        for chave, itens in st.session_state.formulario["dominios"].items():
            dom = ET.SubElement(dominios, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": chave
            })
            itens_tag = ET.SubElement(dom, "itens")
            for item in itens:
                ET.SubElement(itens_tag, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": item["descricao"],
                    "valor": item["valor"]
                })

    return ET.tostring(root, encoding="unicode")

# -------- Pré-visualização --------
st.divider()
st.subheader("Pré-visualização do Formulário")

if st.session_state.formulario["secoes"]:
    for secao in st.session_state.formulario["secoes"]:
        st.markdown(f"### {secao['titulo']}")
        for campo in secao["campos"]:
            if campo["tipo"] == "texto":
                st.text_input(campo["titulo"], placeholder="Digite aqui...")
            elif campo["tipo"] == "texto-area":
                st.text_area(campo["titulo"], placeholder="Digite aqui...", height=campo["altura"])
            elif campo["tipo"] == "paragrafo":
                st.markdown(campo["valor"])
            elif campo["tipo"] == "grupoRadio":
                opcoes = [item["descricao"] for item in st.session_state.formulario["dominios"][campo["dominio"]]]
                st.radio(campo["titulo"], opcoes, horizontal=True)
            elif campo["tipo"] == "grupoCheck":
                st.markdown(f"**{campo['titulo']}**")
                opcoes = [item["descricao"] for item in st.session_state.formulario["dominios"][campo["dominio"]]]
                for opt in opcoes:
                    st.checkbox(opt)
else:
    st.info("Nenhuma seção adicionada ainda.")

# -------- Exportação --------
st.divider()
st.subheader("Exportar Formulário")

xml_string = gerar_xml()
st.download_button("📥 Exportar XML", xml_string, file_name="formulario.xml", mime="application/xml")
st.download_button("📥 Exportar GFE", xml_string, file_name="formulario.gfe", mime="application/xml")
