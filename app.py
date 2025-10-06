import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# ========================
# Inicialização de Estado
# ========================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "secoes": [],
        "dominios": {}
    }

if "editando_secao" not in st.session_state:
    st.session_state.editando_secao = None

if "editando_campo" not in st.session_state:
    st.session_state.editando_campo = None

form = st.session_state.formulario

# ========================
# Funções Auxiliares
# ========================
def salvar_xml():
    root = ET.Element("formulario", {
        "nome": form["nome"],
        "versao": form["versao"],
        "xmlns:gxsi": "http://www.sicoob.com.br/gxsi"
    })

    # Elementos
    elementos = ET.SubElement(root, "elementos")
    for secao in form["secoes"]:
        el_secao = ET.SubElement(elementos, "secao", {"titulo": secao["titulo"]})
        for campo in secao["campos"]:
            el_campo = ET.SubElement(el_secao, "campo", {
                "nome": campo["nome"],
                "tipo": campo["tipo"]
            })
            if campo.get("titulo"):
                el_campo.set("titulo", campo["titulo"])
            if campo.get("dominio"):
                el_campo.set("dominio", campo["dominio"])
            if campo["tipo"] == "tabela":
                for col in campo.get("colunas", []):
                    ET.SubElement(el_campo, "coluna", col)

    # Domínios
    dominios = ET.SubElement(root, "dominios")
    for nome, valores in form["dominios"].items():
        el_dom = ET.SubElement(dominios, "dominio", {"nome": nome})
        for val in valores:
            ET.SubElement(el_dom, "valor").text = val

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    st.download_button("⬇️ Baixar XML", xml_str, file_name=f"{form['nome']}.xml", mime="application/xml")

def carregar_xml(arquivo):
    tree = ET.parse(arquivo)
    root = tree.getroot()

    st.session_state.formulario = {
        "nome": root.attrib.get("nome", ""),
        "versao": root.attrib.get("versao", ""),
        "secoes": [],
        "dominios": {}
    }
    form = st.session_state.formulario

    # Ler seções
    for el_secao in root.find("elementos"):
        secao = {"titulo": el_secao.attrib.get("titulo", ""), "campos": []}
        for el_campo in el_secao.findall("campo"):
            campo = {
                "nome": el_campo.attrib.get("nome", ""),
                "titulo": el_campo.attrib.get("titulo", ""),
                "tipo": el_campo.attrib.get("tipo", ""),
                "dominio": el_campo.attrib.get("dominio", "")
            }
            if campo["tipo"] == "tabela":
                campo["colunas"] = [col.attrib for col in el_campo.findall("coluna")]
            secao["campos"].append(campo)
        form["secoes"].append(secao)

    # Ler domínios
    for el_dom in root.find("dominios"):
        form["dominios"][el_dom.attrib["nome"]] = [v.text for v in el_dom.findall("valor")]

    st.rerun()

# ========================
# Interface Principal
# ========================
st.title("🧱 Construtor de Formulários GXSI")

st.text_input("Nome do formulário", key="nome_form", value=form["nome"], on_change=lambda: form.update({"nome": st.session_state.nome_form}))
st.text_input("Versão", key="versao_form", value=form["versao"], on_change=lambda: form.update({"versao": st.session_state.versao_form}))

st.divider()

# ------------------------
# Gerenciamento de Domínios
# ------------------------
st.subheader("🌐 Domínios Estáticos")

nome_dom = st.text_input("Nome do domínio")
valor_dom = st.text_input("Adicionar valor ao domínio")

col1, col2 = st.columns([1, 1])
if col1.button("➕ Adicionar domínio"):
    if nome_dom:
        form["dominios"].setdefault(nome_dom, [])
        st.rerun()

if col2.button("➕ Adicionar valor"):
    if nome_dom and valor_dom:
        form["dominios"].setdefault(nome_dom, []).append(valor_dom)
        st.rerun()

for dom, vals in form["dominios"].items():
    st.markdown(f"**{dom}**: {', '.join(vals)}")

st.divider()

# ------------------------
# Gerenciamento de Seções
# ------------------------
st.subheader("📄 Seções do Formulário")

nova_secao = st.text_input("Título da nova seção")
if st.button("➕ Adicionar seção"):
    if nova_secao:
        form["secoes"].append({"titulo": nova_secao, "campos": []})
        st.rerun()

for i, secao in enumerate(form["secoes"]):
    with st.expander(f"📦 {secao['titulo']}", expanded=False):
        novo_campo_nome = st.text_input(f"Nome do campo ({secao['titulo']})", key=f"nome_campo_{i}_{uuid.uuid4().hex[:6]}")
        novo_campo_titulo = st.text_input(f"Título do campo ({secao['titulo']})", key=f"titulo_campo_{i}_{uuid.uuid4().hex[:6]}")
        novo_campo_tipo = st.selectbox(f"Tipo do campo ({secao['titulo']})",
                                       ["texto", "numero", "data", "radio", "tabela"],
                                       key=f"tipo_campo_{i}_{uuid.uuid4().hex[:6]}")
        novo_campo_dominio = st.selectbox(f"Domínio (opcional) ({secao['titulo']})",
                                          [""] + list(form["dominios"].keys()),
                                          key=f"dom_campo_{i}_{uuid.uuid4().hex[:6]}")

        if novo_campo_tipo == "tabela":
            st.markdown("**Colunas da tabela:**")
            colunas = []
            num_cols = st.number_input(f"Nº de colunas - {secao['titulo']}", min_value=1, step=1,
                                       key=f"numcols_{i}_{uuid.uuid4().hex[:6]}")
            for c in range(num_cols):
                col_nome = st.text_input(f"Nome da coluna {c+1}", key=f"col_nome_{i}_{c}_{uuid.uuid4().hex[:6]}")
                col_titulo = st.text_input(f"Título da coluna {c+1}", key=f"col_titulo_{i}_{c}_{uuid.uuid4().hex[:6]}")
                col_tipo = st.selectbox(f"Tipo da coluna {c+1}", ["texto", "numero", "data"],
                                        key=f"col_tipo_{i}_{c}_{uuid.uuid4().hex[:6]}")
                colunas.append({"nome": col_nome, "titulo": col_titulo, "tipo": col_tipo})
        else:
            colunas = []

        if st.button(f"✅ Adicionar campo à seção {secao['titulo']}", key=f"addcampo_{i}_{uuid.uuid4().hex[:6]}"):
            secao["campos"].append({
                "nome": novo_campo_nome,
                "titulo": novo_campo_titulo,
                "tipo": novo_campo_tipo,
                "dominio": novo_campo_dominio,
                "colunas": colunas
            })
            st.rerun()

        for j, campo in enumerate(secao["campos"]):
            st.write(f"- **{campo['titulo']}** ({campo['tipo']})")
            if campo["tipo"] == "tabela":
                st.table([{col['titulo']: '' for col in campo.get('colunas', [])}])

        if st.button(f"🗑️ Excluir seção {secao['titulo']}", key=f"delsecao_{i}_{uuid.uuid4().hex[:6]}"):
            del form["secoes"][i]
            st.rerun()

st.divider()

# ------------------------
# Exportar / Importar
# ------------------------
st.subheader("💾 Exportar / Importar XML")

colA, colB = st.columns([1, 1])
with colA:
    salvar_xml()

with colB:
    arquivo_xml = st.file_uploader("Carregar XML existente", type=["xml"])
    if arquivo_xml:
        carregar_xml(arquivo_xml)
