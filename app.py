import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários 6.4", layout="wide")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "secoes": [],
        "dominios": []
    }

if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

TIPOS_ELEMENTOS = [
    "texto", "texto-area", "data", "moeda", "cpf", "cnpj", "email",
    "telefone", "check", "comboBox", "comboFiltro", "grupoRadio",
    "grupoCheck", "paragrafo", "rotulo"
]

def _prettify_xml(root: ET.Element) -> str:
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_bytes)
    return parsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

def gerar_xml(formulario: dict) -> str:
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome", ""),
        "versao": formulario.get("versao", "1.0")
    })

    elementos = ET.SubElement(root, "elementos")
    dominios_global = ET.Element("dominios")

    for sec in formulario.get("secoes", []):
        sec_el = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": sec.get("titulo", ""),
            "largura": str(sec.get("largura", 500))
        })
        subelems = ET.SubElement(sec_el, "elementos")

        tabela_aberta = None
        for campo in sec.get("campos", []):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")
            obrig = str(bool(campo.get("obrigatorio", False))).lower()
            largura = str(campo.get("largura", 450))

            if campo.get("in_tabela"):
                if tabela_aberta is None:
                    tabela_aberta = ET.SubElement(subelems, "elemento", {"gxsi:type": "tabela"})
                    linhas_tag = ET.SubElement(tabela_aberta, "linhas")
                    linha_tag = ET.SubElement(linhas_tag, "linha")
                    celulas_tag = ET.SubElement(linha_tag, "celulas")
                    celula_tag = ET.SubElement(celulas_tag, "celula", {"linhas": "1", "colunas": "1"})
                    elementos_destino = ET.SubElement(celula_tag, "elementos")
            else:
                tabela_aberta = None
                elementos_destino = subelems

            if tipo in ["paragrafo", "rotulo"]:
                ET.SubElement(elementos_destino, "elemento", {
                    "gxsi:type": tipo,
                    "valor": campo.get("valor", titulo),
                    "largura": largura
                })
                continue

            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] and campo.get("dominios"):
                chave_dom = titulo.replace(" ", "")[:20].upper()
                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "descricao": campo.get("descricao", titulo),
                    "obrigatorio": obrig,
                    "largura": largura,
                    "colunas": str(campo.get("colunas", 1)),
                    "dominio": chave_dom
                }
                ET.SubElement(elementos_destino, "elemento", attrs)

                dominio_el = ET.SubElement(dominios_global, "dominio", {
                    "gxsi:type": "dominioEstatico",
                    "chave": chave_dom
                })
                itens_el = ET.SubElement(dominio_el, "itens")
                for d in campo["dominios"]:
                    ET.SubElement(itens_el, "item", {
                        "gxsi:type": "dominioItemValor",
                        "descricao": d["descricao"],
                        "valor": d["valor"]
                    })
                continue

            attrs = {
                "gxsi:type": tipo,
                "titulo": titulo,
                "descricao": campo.get("descricao", titulo),
                "obrigatorio": obrig,
                "largura": largura
            }
            if tipo == "texto-area" and campo.get("altura"):
                attrs["altura"] = str(campo.get("altura"))
            el = ET.SubElement(elementos_destino, "elemento", attrs)
            ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    root.append(dominios_global)
    return _prettify_xml(root)

def renderizar_campo(campo, key):
    tipo = campo.get("tipo")
    if tipo == "texto":
        st.text_input(campo.get("titulo", ""), key=key)
    elif tipo == "texto-area":
        st.text_area(campo.get("titulo", ""), height=campo.get("altura", 100), key=key)
    elif tipo in ["comboBox", "comboFiltro", "grupoCheck"]:
        opcoes = [d["descricao"] for d in campo.get("dominios", [])]
        st.multiselect(campo.get("titulo", ""), opcoes, key=key)
    elif tipo == "grupoRadio":
        opcoes = [d["descricao"] for d in campo.get("dominios", [])]
        st.radio(campo.get("titulo", ""), opcoes, key=key)
    elif tipo == "check":
        st.checkbox(campo.get("titulo", ""), key=key)
    elif tipo in ["paragrafo", "rotulo"]:
        st.markdown(f"**{campo.get('titulo')}**")

col1, col2 = st.columns(2)

with col1:
    st.title("Construtor de Formulários 6.4")

    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
    st.markdown("---")

    with st.expander("➕ Adicionar Seção", expanded=True):
        st.session_state.nova_secao["titulo"] = st.text_input("Título da Seção", st.session_state.nova_secao["titulo"])
        st.session_state.nova_secao["largura"] = st.number_input("Largura da Seção", min_value=100, value=st.session_state.nova_secao["largura"], step=10)
        if st.button("Salvar Seção"):
            if st.session_state.nova_secao["titulo"]:
                st.session_state.formulario["secoes"].append(st.session_state.nova_secao.copy())
                st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

    st.markdown("---")

    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        with st.expander(f"📁 Seção: {sec.get('titulo','(sem título)')}", expanded=False):
            st.write(f"**Largura:** {sec.get('largura', 500)}")

            if st.button(f"🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                st.session_state.formulario["secoes"].pop(s_idx)

            st.markdown("### Campos")
            for c_idx, campo in enumerate(sec.get("campos", [])):
                st.text(f"{campo.get('tipo')} - {campo.get('titulo')}")
                if st.button("Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                    st.session_state.formulario["secoes"][s_idx]["campos"].pop(c_idx)

    if st.session_state.formulario.get("secoes"):
        last_idx = len(st.session_state.formulario["secoes"]) - 1
        secao_atual = st.session_state.formulario["secoes"][last_idx]

        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual.get('titulo','')}", expanded=True):
            tipo = st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS, key=f"type_{last_idx}")
            titulo = st.text_input("Título do Campo", key=f"title_{last_idx}")
            obrig = st.checkbox("Obrigatório", key=f"obrig_{last_idx}")
            in_tabela = st.checkbox("Dentro da tabela?", key=f"tabela_{last_idx}")
            largura = st.number_input("Largura (px)", min_value=100, value=450, step=10, key=f"larg_{last_idx}")

            altura = None
            if tipo == "texto-area":
                altura = st.number_input("Altura", min_value=50, value=100, step=10, key=f"alt_{last_idx}")

            colunas = 1
            dominios_temp = []
            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                colunas = st.number_input("Colunas", min_value=1, max_value=5, value=1, key=f"colunas_{last_idx}")
                qtd_dom = st.number_input("Qtd. de Itens no Domínio", min_value=1, max_value=50, value=2, key=f"qtd_dom_{last_idx}")
                for i in range(int(qtd_dom)):
                    val = st.text_input(f"Descrição Item {i+1}", key=f"desc_{last_idx}_{i}")
                    if val:
                        dominios_temp.append({"descricao": val, "valor": val.upper()})

            if st.button("Adicionar Campo", key=f"add_field_{last_idx}"):
                campo = {
                    "titulo": titulo,
                    "descricao": titulo,
                    "tipo": tipo,
                    "obrigatorio": obrig,
                    "largura": largura,
                    "altura": altura,
                    "colunas": colunas,
                    "in_tabela": in_tabela,
                    "dominios": dominios_temp,
                    "valor": ""
                }
                secao_atual["campos"].append(campo)

with col2:
    st.header("📋 Pré-visualização do Formulário")
    st.subheader(st.session_state.formulario.get("nome", ""))
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        st.markdown(f"### {sec.get('titulo')}")
        tabela_aberta = False
        for campo in sec.get("campos", []):
            tipo = campo.get("tipo")
            key_prev = f"prev_{s_idx}_{campo.get('titulo')}"
            if campo.get("in_tabela") and not tabela_aberta:
                st.markdown("<div style='border:1px solid #ccc; padding:5px;'>", unsafe_allow_html=True)
                tabela_aberta = True
            if not campo.get("in_tabela") and tabela_aberta:
                st.markdown("</div>", unsafe_allow_html=True)
                tabela_aberta = False

            if tipo == "texto":
                st.text_input(campo.get("titulo", ""), key=key_prev)
            elif tipo == "texto-area":
                st.text_area(campo.get("titulo", ""), height=campo.get("altura", 100), key=key_prev)
            elif tipo in ["comboBox", "comboFiltro", "grupoCheck"]:
                st.multiselect(campo.get("titulo", ""), [d["descricao"] for d in campo.get("dominios", [])], key=key_prev)
            elif tipo == "grupoRadio":
                st.radio(campo.get("titulo", ""), [d["descricao"] for d in campo.get("dominios", [])], key=key_prev)
            elif tipo == "check":
                st.checkbox(campo.get("titulo", ""), key=key_prev)
            elif tipo in ["paragrafo", "rotulo"]:
                st.markdown(f"**{campo.get('titulo')}**")

        if tabela_aberta:
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.subheader("📑 Pré-visualização XML")
st.code(gerar_xml(st.session_state.formulario), language="xml")
