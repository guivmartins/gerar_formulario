import xml.etree.ElementTree as ET
import streamlit as st

# ================================================================
# Funções auxiliares
# ================================================================
def parse_dominios(root):
    dominios = {}
    for dominio in root.find("dominios"):
        chave = dominio.attrib["chave"]
        itens = []
        for item in dominio.find("itens"):
            itens.append({"descricao": item.attrib["descricao"], "valor": item.attrib["valor"]})
        dominios[chave] = itens
    return dominios

def render_elemento(elemento, dominios, respostas):
    tipo = elemento.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type")
    titulo = elemento.attrib.get("titulo", "")
    largura = elemento.attrib.get("largura", "750")
    obrigatorio = elemento.attrib.get("obrigatorio", "false") == "true"
    dominio_ref = elemento.attrib.get("dominio")

    if tipo == "texto":
        respostas[titulo] = st.text_input(
            titulo, value=respostas.get(titulo, "")
        )
    elif tipo == "texto-area":
        respostas[titulo] = st.text_area(
            titulo, value=respostas.get(titulo, ""), height=int(elemento.attrib.get("altura", "200"))
        )
    elif tipo == "grupoRadio" and dominio_ref in dominios:
        opcoes = [item["descricao"] for item in dominios[dominio_ref]]
        respostas[titulo] = st.radio(
            titulo, options=opcoes, index=opcoes.index(respostas[titulo]) if respostas.get(titulo) in opcoes else 0
        )
    elif tipo == "grupoCheck" and dominio_ref in dominios:
        opcoes = [item["descricao"] for item in dominios[dominio_ref]]
        valores_atuais = respostas.get(titulo, [])
        if not isinstance(valores_atuais, list):
            valores_atuais = []
        respostas[titulo] = []
        st.write(titulo)
        for opcao in opcoes:
            checked = opcao in valores_atuais
            if st.checkbox(opcao, value=checked, key=f"{titulo}_{opcao}"):
                respostas[titulo].append(opcao)
    elif tipo == "paragrafo":
        st.markdown(f"**{elemento.attrib.get('valor','')}**")
    elif tipo == "seccao":
        st.subheader(titulo)
        for subelemento in elemento.find("elementos"):
            render_elemento(subelemento, dominios, respostas)

# ================================================================
# Leitura do XML
# ================================================================
xml_file = "formulario.xml"

tree = ET.parse(xml_file)
root = tree.getroot()

formulario = {
    "nome": root.attrib.get("nome", ""),
    "versao": root.attrib.get("versao", "1.0"),
}

dominios = parse_dominios(root)

# ================================================================
# Interface Streamlit
# ================================================================
st.title("Formulário GXSI")

formulario["nome"] = st.text_input("Nome do Formulário", value=formulario["nome"])
formulario["versao"] = st.text_input("Versão", value=formulario["versao"] or "1.0")

respostas = {}

elementos = root.find("elementos")
for elemento in elementos:
    render_elemento(elemento, dominios, respostas)

# ================================================================
# Debug/Export
# ================================================================
if st.button("Salvar Respostas"):
    st.json(respostas)
