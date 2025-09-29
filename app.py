import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata
import re

# =========================================
# Funções auxiliares
# =========================================
def normalizar_chave(titulo):
    """Normaliza string para gerar chave de domínio sem acentos e espaços."""
    chave = unicodedata.normalize("NFKD", titulo).encode("ASCII", "ignore").decode("ASCII")
    chave = re.sub(r"[^a-zA-Z0-9]", "", chave)
    return chave[:20]

def gerar_xml(formulario):
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    # Criar blocos de dominios
    if formulario["dominios"]:
        dominios_tag = ET.SubElement(root, "dominios")
        for chave, itens in formulario["dominios"].items():
            dominio_tag = ET.SubElement(dominios_tag, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": chave
            })
            itens_tag = ET.SubElement(dominio_tag, "itens")
            for item in itens:
                ET.SubElement(itens_tag, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": item["descricao"],
                    "valor": item["valor"]
                })

    # Criar blocos de elementos
    elementos_tag = ET.SubElement(root, "elementos")
    for secao in formulario["secoes"]:
        secao_tag = ET.SubElement(elementos_tag, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao.get("largura", 500))
        })
        elementos_secao = ET.SubElement(secao_tag, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(elementos_secao, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo["valor"],
                    "largura": str(campo.get("largura", 450))
                })
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                elem_attrib = {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "dominio": campo["dominio"],
                    "colunas": str(campo.get("colunas", 1)),
                    "obrigatorio": str(campo["obrigatorio"]).lower()
                }
                elemento_tag = ET.SubElement(elementos_secao, "elemento", elem_attrib)
                ET.SubElement(elemento_tag, "conteudo", {"gxsi:type": "valor"})
            elif campo["tipo"] == "texto-area":
                elem_attrib = {
                    "gxsi:type": "texto-area",
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo.get("largura", 450)),
                    "altura": str(campo.get("altura", 100)),
                    "maximo": str(campo.get("maximo", 0))
                }
                elemento_tag = ET.SubElement(elementos_secao, "elemento", elem_attrib)
                ET.SubElement(elemento_tag, "conteudo", {"gxsi:type": "valor"})
            else:  # texto
                elem_attrib = {
                    "gxsi:type": "texto",
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo.get("largura", 450)),
                    "tamanhoMaximo": str(campo.get("maximo", 0))
                }
                elemento_tag = ET.SubElement(elementos_secao, "elemento", elem_attrib)
                ET.SubElement(elemento_tag, "conteudo", {"gxsi:type": "valor"})

    xml_str = ET.tostring(root, encoding="utf-8")
    xml_pretty = minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="utf-8")
    return xml_pretty

# =========================================
# Interface Streamlit
# =========================================
st.set_page_config(page_title="Construtor de Formulários", layout="centered")
st.title("Construtor de Formulários")

if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "",
        "secoes": [],
        "dominios": {}
    }

formulario = st.session_state.formulario

# Nome e versão do formulário
st.subheader("Configuração do Formulário")
formulario["nome"] = st.text_input("Nome do formulário", formulario["nome"])
formulario["versao"] = st.text_input("Versão", formulario["versao"], value="1.0")

# Adicionar Seção
st.subheader("Adicionar Seção")
secao_titulo = st.text_input("Título da seção")
if st.button("Adicionar seção"):
    if secao_titulo:
        formulario["secoes"].append({"titulo": secao_titulo, "largura": 500, "campos": []})

# Listar seções
for i, secao in enumerate(formulario["secoes"]):
    st.markdown(f"### Seção: {secao['titulo']}")

    with st.expander("Adicionar campo"):
        tipo = st.selectbox("Tipo de campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
        if tipo == "paragrafo":
            valor = st.text_area("Valor do parágrafo")
            largura = st.number_input("Largura", value=450)
            if st.button(f"Adicionar parágrafo à {secao['titulo']}", key=f"p_{i}"):
                secao["campos"].append({
                    "tipo": "paragrafo",
                    "valor": valor,
                    "largura": largura
                })
        else:
            titulo = st.text_input("Título do campo", key=f"titulo_{i}_{tipo}")
            obrigatorio = st.checkbox("Obrigatório", value=True, key=f"obrig_{i}_{tipo}")
            largura = st.number_input("Largura", value=450, key=f"larg_{i}_{tipo}")

            if tipo in ["grupoRadio", "grupoCheck"]:
                colunas = st.number_input("Quantidade de colunas", min_value=1, max_value=5, value=2, key=f"col_{i}_{tipo}")
                descricoes = st.text_area("Opções (uma por linha)", key=f"opts_{i}_{tipo}").splitlines()
                if st.button(f"Adicionar {tipo} à {secao['titulo']}", key=f"btn_{i}_{tipo}"):
                    chave = normalizar_chave(titulo)
                    if chave in formulario["dominios"]:
                        chave += "1"
                    itens = [{"descricao": d, "valor": normalizar_chave(d)} for d in descricoes if d]
                    formulario["dominios"][chave] = itens
                    secao["campos"].append({
                        "tipo": tipo,
                        "titulo": titulo,
                        "obrigatorio": obrigatorio,
                        "dominio": chave,
                        "colunas": colunas
                    })
            elif tipo == "texto-area":
                altura = st.number_input("Altura", value=100, key=f"alt_{i}")
                maximo = st.number_input("Tamanho máximo", value=0, key=f"max_{i}")
                if st.button(f"Adicionar texto-area à {secao['titulo']}", key=f"btn_{i}_{tipo}"):
                    secao["campos"].append({
                        "tipo": "texto-area",
                        "titulo": titulo,
                        "obrigatorio": obrigatorio,
                        "largura": largura,
                        "altura": altura,
                        "maximo": maximo
                    })
            else:  # texto
                maximo = st.number_input("Tamanho máximo", value=0, key=f"max_{i}_{tipo}")
                if st.button(f"Adicionar texto à {secao['titulo']}", key=f"btn_{i}_{tipo}"):
                    secao["campos"].append({
                        "tipo": "texto",
                        "titulo": titulo,
                        "obrigatorio": obrigatorio,
                        "largura": largura,
                        "maximo": maximo
                    })

# Pré-visualização
st.subheader("Pré-visualização do formulário")
for secao in formulario["secoes"]:
    st.markdown(f"**{secao['titulo']}**")
    for campo in secao["campos"]:
        if campo["tipo"] == "paragrafo":
            st.markdown(f"> {campo['valor']}")
        elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
            st.markdown(f"{campo['titulo']} ({campo['tipo']}, colunas={campo['colunas']})")
            for item in formulario["dominios"].get(campo["dominio"], []):
                st.write(f"- {item['descricao']}")
        else:
            st.write(f"{campo['titulo']} ({campo['tipo']})")

# Exportar
st.subheader("Exportar Formulário")
xml_bytes = gerar_xml(formulario)
st.download_button("Exportar XML", data=xml_bytes, file_name="formulario.xml", mime="application/xml")
st.download_button("Exportar GFE", data=xml_bytes, file_name="formulario.gfe", mime="application/octet-stream")
