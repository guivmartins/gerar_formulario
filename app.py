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

# Nome do formulário
st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])

st.markdown("---")

# Criar nova seção
with st.expander("➕ Adicionar Seção", expanded=True):
    st.session_state.nova_secao["titulo"] = st.text_input("Título da Seção", st.session_state.nova_secao["titulo"], key="titulo_secao")
    st.session_state.nova_secao["largura"] = st.number_input(
        "Largura da Seção", min_value=100, value=500, step=10, key="largura_secao"
    )

    if st.button("Salvar Seção"):
        if st.session_state.nova_secao["titulo"]:
            st.session_state.formulario["secoes"].append(st.session_state.nova_secao.copy())
            st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}
            st.rerun()

# Listagem de seções e campos
for i, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"Seção: {secao['titulo']}", expanded=False):
        # Editar seção
        secao["titulo"] = st.text_input(f"Título da Seção {i+1}", secao["titulo"], key=f"titulo_secao_{i}")
        secao["largura"] = st.number_input(f"Largura da Seção {i+1}", min_value=100, value=secao["largura"], step=10, key=f"largura_secao_{i}")

        # Listagem dos campos
        for j, campo in enumerate(secao["campos"]):
            with st.expander(f"Campo: {campo['titulo'] or campo['tipo']}", expanded=False):
                campo["titulo"] = st.text_input("Título do Campo", campo["titulo"], key=f"titulo_{i}_{j}")
                campo["tipo"] = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"],
                                             index=["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"].index(campo["tipo"]),
                                             key=f"tipo_{i}_{j}")
                if campo["tipo"] != "paragrafo":
                    campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo["obrigatorio"], key=f"obrigatorio_{i}_{j}")

                campo["largura"] = st.number_input("Largura", min_value=100, value=campo["largura"], step=10, key=f"largura_{i}_{j}")

                if campo["tipo"] == "texto-area":
                    campo["altura"] = st.number_input("Altura", min_value=50, value=campo.get("altura", 100), step=10, key=f"altura_{i}_{j}")

                if campo["tipo"] == "paragrafo":
                    campo["valor"] = st.text_area("Valor do Parágrafo", campo.get("valor", ""), key=f"valor_{i}_{j}")

                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    campo["colunas"] = st.number_input("Quantidade de Colunas", min_value=1, max_value=5,
                                                       value=campo.get("colunas", 1), key=f"colunas_{i}_{j}")
                    qtd_dominios = st.number_input("Quantidade de Domínios", min_value=1, max_value=10,
                                                   value=len(campo.get("dominios", [])) or 2, key=f"qtd_dominios_{i}_{j}")
                    dominios = []
                    for d in range(qtd_dominios):
                        desc = st.text_input(f"Descrição Domínio {d+1}", value=(campo.get("dominios", [{}]*qtd_dominios)[d].get("descricao", "") if d < len(campo.get("dominios", [])) else ""),
                                             key=f"dom_{i}_{j}_{d}")
                        if desc:
                            dominios.append({"descricao": desc, "valor": desc.replace(" ", "_").upper()})
                    campo["dominios"] = dominios

# Adicionar campos (botão no final da tela)
if st.session_state.formulario["secoes"]:
    secao_atual = st.session_state.formulario["secoes"][-1]
    st.markdown("---")
    st.subheader(f"➕ Adicionar Campos à seção: {secao_atual['titulo']}")

    titulo = st.text_input("Título do Novo Campo", key="novo_titulo")
    tipo = st.selectbox("Tipo do Novo Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], key="novo_tipo")
    obrigatorio = tipo != "paragrafo" and st.checkbox("Obrigatório", value=False, key="novo_obrigatorio")
    largura = st.number_input("Largura do Novo Campo", min_value=100, value=450, step=10, key="novo_largura")

    altura = None
    valor_paragrafo = ""
    colunas = None
    dominios = []

    if tipo == "texto-area":
        altura = st.number_input("Altura do Novo Campo", min_value=50, value=100, step=10, key="novo_altura")
    if tipo == "paragrafo":
        valor_paragrafo = st.text_area("Valor do Novo Parágrafo", key="novo_valor")
    if tipo in ["grupoRadio", "grupoCheck"]:
        colunas = st.number_input("Quantidade de Colunas", min_value=1, max_value=5, value=1, key="novo_colunas")
        qtd_dominios = st.number_input("Quantidade de Domínios", min_value=1, max_value=10, value=2, key="novo_qtd_dominios")
        for d in range(qtd_dominios):
            desc = st.text_input(f"Descrição Domínio {d+1}", key=f"novo_dom_{d}")
            if desc:
                dominios.append({"descricao": desc, "valor": desc.replace(" ", "_").upper()})

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

st.markdown("---")

# Função de geração do XML indentado
def exportar_xml():
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": st.session_state.formulario["nome"],
        "versao": st.session_state.formulario["versao"]
    })

    # bloco de dominios fora de elementos
    dominios_global = ET.SubElement(root, "dominios")
    for secao in st.session_state.formulario["secoes"]:
        for campo in secao["campos"]:
            if campo["tipo"] in ["grupoRadio", "grupoCheck"] and campo["dominios"]:
                dominio = ET.SubElement(dominios_global, "dominio", {
                    "gxsi:type": "dominioEstatico",
                    "chave": campo["titulo"].replace(" ", "")[:20].upper()
                })
                itens = ET.SubElement(dominio, "itens")
                for d in campo["dominios"]:
                    ET.SubElement(itens, "item", {
                        "gxsi:type": "dominioItemValor",
                        "descricao": d["descricao"],
                        "valor": d["valor"]
                    })

    elementos = ET.SubElement(root, "elementos")

    for secao in st.session_state.formulario["secoes"]:
        el_secao = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao["largura"])
        })
        subelementos = ET.SubElement(el_secao, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo["valor"],
                    "largura": str(campo["largura"])
                })
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"]),
                    "colunas": str(campo["colunas"]),
                    "dominio": campo["titulo"].replace(" ", "")[:20].upper()
                })
            else:
                el = ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"])
                })
                if campo["altura"]:
                    el.set("altura", str(campo["altura"]))
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="   ", encoding="utf-8")

# Pré-visualização
st.subheader("Pré-visualização do Formulário")
st.code(exportar_xml().decode("utf-8"), language="xml")
