import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# ===============================
# Sessão de estado
# ===============================
if "form_name" not in st.session_state:
    st.session_state.form_name = ""
if "form_version" not in st.session_state:
    st.session_state.form_version = ""
if "sections" not in st.session_state:
    st.session_state.sections = []
if "domains" not in st.session_state:
    st.session_state.domains = {}

# ===============================
# Funções auxiliares
# ===============================
def generate_key(base, existing_keys):
    key = base[:20].replace(" ", "").replace("ç", "c").replace("ã", "a").replace("õ", "o")
    candidate = key
    i = 1
    while candidate in existing_keys:
        candidate = f"{key}{i}"
        i += 1
    return candidate

def export_xml_gfe():
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": st.session_state.form_name,
        "versao": st.session_state.form_version
    })

    # Domínios
    if st.session_state.domains:
        dominios_tag = ET.SubElement(root, "dominios")
        for chave, itens in st.session_state.domains.items():
            dominio_tag = ET.SubElement(dominios_tag, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": chave
            })
            itens_tag = ET.SubElement(dominio_tag, "itens")
            for desc, val in itens:
                ET.SubElement(itens_tag, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": desc,
                    "valor": val
                })

    # Elementos
    elementos_tag = ET.SubElement(root, "elementos")
    for section in st.session_state.sections:
        sec_tag = ET.SubElement(elementos_tag, "elemento", {
            "gxsi:type": "seccao",
            "titulo": section["titulo"],
            "largura": str(section.get("largura", 800))
        })
        elems_tag = ET.SubElement(sec_tag, "elementos")

        for field in section["campos"]:
            if field["tipo"] == "paragrafo":
                ET.SubElement(elems_tag, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": field["valor"],
                    "largura": str(field.get("largura", 450))
                })
            else:
                attribs = {
                    "gxsi:type": field["tipo"],
                    "titulo": field["titulo"],
                    "largura": str(field.get("largura", 450))
                }
                if field["tipo"] in ["grupoRadio", "grupoCheck"]:
                    attribs["dominio"] = field["dominio"]
                    attribs["colunas"] = str(field.get("colunas", 1))
                if "obrigatorio" in field:
                    attribs["obrigatorio"] = str(field["obrigatorio"]).lower()
                if "tamanhoMaximo" in field:
                    attribs["tamanhoMaximo"] = str(field["tamanhoMaximo"])
                if "altura" in field:
                    attribs["altura"] = str(field["altura"])

                el = ET.SubElement(elems_tag, "elemento", attribs)
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    xml_str = ET.tostring(root, encoding="utf-8")
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="   ", encoding="utf-8")

    return pretty_xml

# ===============================
# Interface Streamlit
# ===============================
st.title("Construtor de Formulários")

st.subheader("Informações do Formulário")
st.session_state.form_name = st.text_input("Nome do Formulário", st.session_state.form_name)
st.session_state.form_version = st.text_input("Versão", st.session_state.form_version)

# Gerenciar seções
st.subheader("Adicionar Seção")
sec_title = st.text_input("Título da Seção")
sec_width = st.number_input("Largura da Seção", value=800)
if st.button("Adicionar Seção"):
    st.session_state.sections.append({
        "titulo": sec_title,
        "largura": sec_width,
        "campos": []
    })

# Escolher seção para inserir campos
if st.session_state.sections:
    st.subheader("Adicionar Campos")
    sec_names = [s["titulo"] for s in st.session_state.sections]
    chosen_sec = st.selectbox("Selecione a Seção", sec_names)
    current_section = next(s for s in st.session_state.sections if s["titulo"] == chosen_sec)

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo do Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
    with col2:
        obrig = st.checkbox("Obrigatório", value=True, disabled=(tipo == "paragrafo"))

    titulo = ""
    valor = ""
    if tipo == "paragrafo":
        valor = st.text_area("Valor do Parágrafo")
    else:
        titulo = st.text_input("Título do Campo")

    largura = st.number_input("Largura do Campo", value=450)
    altura = None
    if tipo == "texto-area":
        altura = st.number_input("Altura do Campo", value=100)

    tamanho_max = None
    if tipo in ["texto", "texto-area"]:
        tamanho_max = st.number_input("Tamanho Máximo", value=0)

    dominio_key = None
    colunas = 1
    if tipo in ["grupoRadio", "grupoCheck"]:
        colunas = st.number_input("Número de Colunas", value=1, min_value=1)
        if titulo:
            dominio_key = generate_key(titulo, st.session_state.domains.keys())
            if dominio_key not in st.session_state.domains:
                st.session_state.domains[dominio_key] = []
            with st.expander(f"Gerenciar Domínio ({dominio_key})"):
                desc = st.text_input("Descrição do item de domínio")
                if st.button("Adicionar Item de Domínio"):
                    st.session_state.domains[dominio_key].append((desc, desc))
                st.write("Itens atuais:", st.session_state.domains[dominio_key])

    if st.button("Adicionar Campo"):
        campo = {"tipo": tipo, "largura": largura}
        if tipo == "paragrafo":
            campo["valor"] = valor
        else:
            campo["titulo"] = titulo
            campo["obrigatorio"] = obrig
            if tamanho_max:
                campo["tamanhoMaximo"] = tamanho_max
            if altura:
                campo["altura"] = altura
            if dominio_key:
                campo["dominio"] = dominio_key
                campo["colunas"] = colunas
        current_section["campos"].append(campo)

# Pré-visualização
if st.session_state.sections:
    st.subheader("Pré-visualização do Formulário")
    st.write(f"📄 **{st.session_state.form_name}** (versão {st.session_state.form_version})")
    for sec in st.session_state.sections:
        st.markdown(f"### {sec['titulo']}")
        for campo in sec["campos"]:
            if campo["tipo"] == "paragrafo":
                st.markdown(f"*{campo['valor']}*")
            else:
                st.text(f"{campo['tipo'].upper()}: {campo['titulo']}")

# Exportação
st.subheader("Exportar")
xml_bytes = export_xml_gfe()
st.download_button("⬇️ Exportar como XML", xml_bytes, file_name="formulario.xml")
st.download_button("⬇️ Exportar como GFE", xml_bytes, file_name="formulario.gfe")
