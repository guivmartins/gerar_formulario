import streamlit as st 
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# Inicializar estado
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "", "secoes": []}

st.title("Construtor de Formulários")

# Nome e versão
st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

st.markdown("---")

# Adicionar seção
with st.expander("➕ Adicionar Nova Seção", expanded=False):
    titulo_secao = st.text_input("Título da Nova Seção")
    largura_secao = st.number_input("Largura da Seção", min_value=100, value=500, step=10)
    if st.button("Salvar Seção"):
        if titulo_secao:
            st.session_state.formulario["secoes"].append({
                "titulo": titulo_secao,
                "largura": largura_secao,
                "campos": []
            })

# Listar e editar seções
for idx_secao, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"Seção: {secao['titulo']}", expanded=False):
        secao["titulo"] = st.text_input(f"Título da Seção {idx_secao+1}", secao["titulo"], key=f"sec_tit_{idx_secao}")
        secao["largura"] = st.number_input(f"Largura da Seção {idx_secao+1}", min_value=100, value=secao["largura"], step=10, key=f"sec_larg_{idx_secao}")

        if st.button(f"Excluir Seção {idx_secao+1}", key=f"del_sec_{idx_secao}"):
            st.session_state.formulario["secoes"].pop(idx_secao)
            st.rerun()

        st.markdown("**Adicionar Campo**")
        titulo = st.text_input("Título do Campo", key=f"tit_campo_{idx_secao}")
        tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], key=f"tipo_campo_{idx_secao}")
        obrigatorio = False
        if tipo != "paragrafo":
            obrigatorio = st.checkbox("Obrigatório", value=False, key=f"obrig_{idx_secao}")

        largura = st.number_input("Largura", min_value=100, value=450, step=10, key=f"larg_{idx_secao}")
        altura = None
        if tipo == "texto-area":
            altura = st.number_input("Altura", min_value=50, value=100, step=10, key=f"alt_{idx_secao}")

        valor_paragrafo = ""
        if tipo == "paragrafo":
            valor_paragrafo = st.text_area("Valor do Parágrafo", key=f"val_par_{idx_secao}")

        colunas = None
        dominios = []
        if tipo in ["grupoRadio", "grupoCheck"]:
            colunas = st.number_input("Quantidade de Colunas", min_value=1, max_value=5, value=1, key=f"col_{idx_secao}")
            qtd_dominios = st.number_input("Quantidade de Domínios", min_value=1, max_value=10, value=2, key=f"qtd_dom_{idx_secao}")
            for i in range(qtd_dominios):
                desc = st.text_input(f"Descrição Domínio {i+1}", key=f"dom_{idx_secao}_{i}")
                if desc:
                    dominios.append({"descricao": desc, "valor": desc.replace(" ", "_").upper()})

        if st.button("Adicionar Campo", key=f"add_campo_{idx_secao}"):
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
            secao["campos"].append(campo)

        # Listar campos existentes
        for idx_campo, campo in enumerate(secao["campos"]):
            with st.expander(f"Campo: {campo['titulo']}", expanded=False):
                campo["titulo"] = st.text_input("Título", campo["titulo"], key=f"edit_tit_{idx_secao}_{idx_campo}")
                campo["tipo"] = st.selectbox("Tipo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"], index=["texto","texto-area","paragrafo","grupoRadio","grupoCheck"].index(campo["tipo"]), key=f"edit_tipo_{idx_secao}_{idx_campo}")
                if campo["tipo"] != "paragrafo":
                    campo["obrigatorio"] = st.checkbox("Obrigatório", value=campo["obrigatorio"], key=f"edit_obr_{idx_secao}_{idx_campo}")
                campo["largura"] = st.number_input("Largura", min_value=100, value=campo["largura"], step=10, key=f"edit_larg_{idx_secao}_{idx_campo}")
                if campo["tipo"] == "texto-area":
                    campo["altura"] = st.number_input("Altura", min_value=50, value=campo["altura"] or 100, step=10, key=f"edit_alt_{idx_secao}_{idx_campo}")
                if campo["tipo"] == "paragrafo":
                    campo["valor"] = st.text_area("Valor", campo["valor"], key=f"edit_val_{idx_secao}_{idx_campo}")
                if campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                    campo["colunas"] = st.number_input("Colunas", min_value=1, max_value=5, value=campo["colunas"] or 1, key=f"edit_col_{idx_secao}_{idx_campo}")
                    for j, dom in enumerate(campo["dominios"]):
                        campo["dominios"][j]["descricao"] = st.text_input(f"Descrição Domínio {j+1}", dom["descricao"], key=f"edit_dom_{idx_secao}_{idx_campo}_{j}")

                if st.button("Excluir Campo", key=f"del_campo_{idx_secao}_{idx_campo}"):
                    secao["campos"].pop(idx_campo)
                    st.rerun()

# Função de geração do XML
def gerar_xml():
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": st.session_state.formulario["nome"],
        "versao": st.session_state.formulario["versao"]
    })

    # 🔹 Primeiro bloco de dominios fora de <elementos>
    dominios_root = ET.SubElement(root, "dominios")
    for secao in st.session_state.formulario["secoes"]:
        for campo in secao["campos"]:
            if campo["tipo"] in ["grupoRadio", "grupoCheck"] and campo.get("dominios"):
                dominio = ET.SubElement(dominios_root, "dominio", {
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
                el = ET.SubElement(subelementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"]),
                    "colunas": str(campo["colunas"])
                })
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
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
    return parsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# Pré-visualização
st.subheader("Pré-visualização do Formulário")
st.code(gerar_xml(), language="xml")

# Exportação
xml_str = gerar_xml()
st.download_button("⬇️ Exportar XML", xml_str, file_name="formulario.xml", mime="application/xml")
st.download_button("⬇️ Exportar GFE", xml_str, file_name="formulario.gfe", mime="application/xml")
