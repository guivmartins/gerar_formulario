import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

# ========================
# Funções auxiliares
# ========================

def normalizar_chave(titulo):
    chave = re.sub(r'[^a-zA-Z0-9]', '', titulo)[:20]
    return chave or "dominio"

def exportar_xml():
    root = ET.Element("formulario", xmlns_gxsi="gxsi")

    # Atributos fixos
    ET.SubElement(root, "nome").text = st.session_state["formulario"]["nome"]
    ET.SubElement(root, "versao").text = st.session_state["formulario"]["versao"]

    elementos_tag = ET.SubElement(root, "elementos")
    dominios_tag = ET.Element("dominios")  # fora de elementos

    dominios_existentes = {}

    for secao in st.session_state["formulario"]["secoes"]:
        secao_el = ET.SubElement(elementos_tag, "secao", titulo=secao["titulo"])
        for campo in secao["campos"]:
            atributos = {"gxsi:type": campo["tipo"], "titulo": campo["titulo"]}
            if campo.get("obrigatorio"):
                atributos["obrigatorio"] = "true"

            # Se for grupo, gera domínio
            if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                chave = normalizar_chave(campo["titulo"])
                if chave in dominios_existentes:
                    count = dominios_existentes[chave] + 1
                    chave = f"{chave}{count}"
                    dominios_existentes[chave] = count
                else:
                    dominios_existentes[chave] = 1
                atributos["dominio"] = chave

                dominio_el = ET.SubElement(dominios_tag, "dominio", chave=chave)
                for i, item in enumerate(campo.get("opcoes", []), start=1):
                    ET.SubElement(
                        dominio_el,
                        "item",
                        descricao=item,
                        valor=f"VALOR_{i}"
                    )

            elemento_el = ET.SubElement(secao_el, "elemento", atributos)
            ET.SubElement(elemento_el, "conteudo", {"gxsi:type": "valor"})

    root.append(dominios_tag)

    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="utf-8")


# ========================
# Estado inicial
# ========================

if "formulario" not in st.session_state:
    st.session_state["formulario"] = {
        "nome": "",
        "versao": "1.0",
        "secoes": []
    }

# ========================
# Interface Streamlit
# ========================

st.title("Construtor de Formulários 2.0")

st.text_input("Nome do Formulário", key="formulario_nome", value=st.session_state["formulario"]["nome"])
st.session_state["formulario"]["nome"] = st.session_state["formulario_nome"]

# Listagem de seções
for i, secao in enumerate(st.session_state["formulario"]["secoes"]):
    with st.container():
        st.text_input("Título da Seção", key=f"secao_{i}_titulo", value=secao["titulo"])
        secao["titulo"] = st.session_state[f"secao_{i}_titulo"]

        # Listagem de campos
        for j, campo in enumerate(secao["campos"]):
            with st.expander(f"Campo: {campo['titulo'] or campo['tipo']}", expanded=False):
                st.text_input("Título do Campo", key=f"campo_{i}_{j}_titulo", value=campo["titulo"])
                campo["titulo"] = st.session_state[f"campo_{i}_{j}_titulo"]

                tipo = st.selectbox(
                    "Tipo de Campo",
                    ["texto", "numero", "data", "grupoRadio", "grupoCheck"],
                    key=f"campo_{i}_{j}_tipo",
                    index=["texto", "numero", "data", "grupoRadio", "grupoCheck"].index(campo["tipo"])
                )
                campo["tipo"] = tipo

                campo["obrigatorio"] = st.checkbox("Obrigatório", key=f"campo_{i}_{j}_obrig", value=campo["obrigatorio"])

                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    st.text_area(
                        "Opções (uma por linha)",
                        key=f"campo_{i}_{j}_opcoes",
                        value="\n".join(campo.get("opcoes", []))
                    )
                    campo["opcoes"] = st.session_state[f"campo_{i}_{j}_opcoes"].split("\n")

                if st.button("Excluir Campo", key=f"excluir_campo_{i}_{j}"):
                    secao["campos"].pop(j)
                    st.rerun()

        # Botão adicionar campo dentro da seção
        if st.button("Adicionar Campo", key=f"add_campo_{i}"):
            secao["campos"].append({
                "titulo": "",
                "tipo": "texto",
                "obrigatorio": False,
                "opcoes": []
            })
            st.rerun()

        # Botão excluir seção
        if st.button("Excluir Seção", key=f"excluir_secao_{i}"):
            st.session_state["formulario"]["secoes"].pop(i)
            st.rerun()

# Botão adicionar seção (fim da página)
if st.button("Adicionar Seção", key="add_secao_final"):
    st.session_state["formulario"]["secoes"].append({"titulo": "", "campos": []})
    st.rerun()

# Pré-visualização XML
st.subheader("Pré-visualização XML")
st.code(exportar_xml().decode("utf-8"))
