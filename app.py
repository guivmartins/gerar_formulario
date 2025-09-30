import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ==============================
# Inicialização do estado
# ==============================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "descricao": "",
        "versao": "1.0",
        "secoes": []
    }

formulario = st.session_state.formulario

# ==============================
# Função para exportar XML
# ==============================
def exportar_xml():
    root = ET.Element("formulario", {
        "nome": formulario["nome"],
        "descricao": formulario["descricao"],
        "versao": formulario["versao"]
    })

    elementos = ET.SubElement(root, "elementos")

    dominios_global = ET.Element("dominios")

    for secao in formulario["secoes"]:
        secao_el = ET.SubElement(elementos, "grupo", {"titulo": secao["titulo"]})
        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(secao_el, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo["valor"],
                    "largura": str(campo["largura"])
                })
            else:
                atributos = {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "largura": str(campo["largura"])
                }
                if campo["tipo"] != "paragrafo":
                    atributos["obrigatorio"] = str(campo["obrigatorio"]).lower()
                if campo["tipo"] == "texto-area":
                    atributos["altura"] = str(campo["altura"])
                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    atributos["colunas"] = str(campo["colunas"])

                el = ET.SubElement(secao_el, "elemento", atributos)

                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    dominio_el = ET.SubElement(dominios_global, "dominio", {
                        "gxsi:type": "dominioEstatico",
                        "chave": campo["titulo"].upper().replace(" ", "_")
                    })
                    itens_el = ET.SubElement(dominio_el, "itens")
                    for dom in campo["dominios"]:
                        ET.SubElement(itens_el, "item", {
                            "gxsi:type": "dominioItemValor",
                            "descricao": dom["descricao"],
                            "valor": dom["descricao"]
                        })
                    el.set("dominio", campo["titulo"].upper().replace(" ", "_"))

    # Adiciona <dominios> fora de <elementos>
    root.append(dominios_global)

    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="utf-8")

# ==============================
# UI - Formulário principal
# ==============================
st.title("Construtor de Formulários 1.0")

formulario["nome"] = st.text_input("Nome do Formulário", formulario["nome"])
formulario["descricao"] = st.text_area("Descrição", formulario["descricao"])
formulario["versao"] = st.text_input("Versão", value=formulario["versao"])

# ==============================
# Gerenciar Seções
# ==============================
st.subheader("Seções")

if st.button("Adicionar Seção"):
    formulario["secoes"].append({"titulo": "Nova Seção", "campos": []})

for idx_secao, secao in enumerate(formulario["secoes"]):
    with st.expander(f"Seção: {secao['titulo']}", expanded=False):
        secao["titulo"] = st.text_input("Título da Seção", secao["titulo"], key=f"sec_{idx_secao}")

        if st.button("Excluir Seção", key=f"del_sec_{idx_secao}"):
            formulario["secoes"].pop(idx_secao)
            st.rerun()

        st.markdown("### Campos")
        if st.button("Adicionar Campo", key=f"add_field_{idx_secao}"):
            secao["campos"].append({
                "titulo": "Novo Campo",
                "tipo": "texto",
                "obrigatorio": False,
                "largura": 300,
                "altura": None,
                "valor": "",
                "colunas": None,
                "dominios": []
            })

        # ==============================
        # Listar e Editar Campos
        # ==============================
        for idx_campo, campo in enumerate(secao["campos"]):
            with st.container():
                st.markdown(f"**Campo: {campo['titulo']}**")

                campo["titulo"] = st.text_input("Título", campo["titulo"], key=f"edit_tit_{idx_secao}_{idx_campo}")
                campo["tipo"] = st.selectbox(
                    "Tipo",
                    ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"],
                    index=["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"].index(campo["tipo"]),
                    key=f"edit_tipo_{idx_secao}_{idx_campo}"
                )

                if campo["tipo"] != "paragrafo":
                    campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo["obrigatorio"], key=f"edit_obr_{idx_secao}_{idx_campo}")

                campo["largura"] = st.number_input("Largura", min_value=100, value=campo["largura"], step=10, key=f"edit_larg_{idx_secao}_{idx_campo}")

                if campo["tipo"] == "texto-area":
                    campo["altura"] = st.number_input("Altura", min_value=50, value=campo["altura"] or 100, step=10, key=f"edit_alt_{idx_secao}_{idx_campo}")

                if campo["tipo"] == "paragrafo":
                    campo["valor"] = st.text_area("Valor", campo["valor"], key=f"edit_val_{idx_secao}_{idx_campo}")

                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    campo["colunas"] = st.number_input("Colunas", min_value=1, max_value=5, value=campo["colunas"] or 1, key=f"edit_col_{idx_secao}_{idx_campo}")
                    if st.button("Adicionar Domínio", key=f"add_dom_{idx_secao}_{idx_campo}"):
                        campo["dominios"].append({"descricao": ""})
                    for j, dom in enumerate(campo["dominios"]):
                        campo["dominios"][j]["descricao"] = st.text_input(
                            f"Descrição Domínio {j+1}", dom["descricao"], key=f"edit_dom_{idx_secao}_{idx_campo}_{j}"
                        )
                        if st.button("Excluir Domínio", key=f"del_dom_{idx_secao}_{idx_campo}_{j}"):
                            campo["dominios"].pop(j)
                            st.rerun()

                if st.button("Excluir Campo", key=f"del_campo_{idx_secao}_{idx_campo}"):
                    secao["campos"].pop(idx_campo)
                    st.rerun()

                st.markdown("---")

# ==============================
# Exportar XML
# ==============================
if st.button("Exportar XML"):
    xml_content = exportar_xml()
    st.download_button("Baixar XML", data=xml_content, file_name="formulario.xml", mime="application/xml")

# ==============================
# Pré-visualização
# ==============================
st.subheader("Pré-visualização do XML")
st.code(exportar_xml().decode("utf-8"))
