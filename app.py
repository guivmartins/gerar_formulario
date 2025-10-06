# app.py - Construtor de Formulários com Domínios completos (versão 5.0 funcionando)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "secoes": [],
        "dominios": []  # dominios globais
    }

if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

TIPOS_ELEMENTOS = [
    "texto", "texto-area", "data", "moeda", "cpf", "cnpj", "email", "telefone",
    "check", "comboBox", "comboFiltro", "grupoRadio", "grupoCheck", "paragrafo", "rotulo"
]

# -------------------------
# Função utilitária para XML
# -------------------------
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

        for campo in sec.get("campos", []):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")
            descricao = campo.get("descricao", titulo)
            obrig = str(bool(campo.get("obrigatorio", False))).lower()
            largura = str(campo.get("largura", 450))

            # paragrafo / rotulo -> valor direto
            if tipo in ["paragrafo", "rotulo"]:
                ET.SubElement(subelems, "elemento", {
                    "gxsi:type": tipo,
                    "valor": campo.get("valor", titulo),
                    "largura": largura
                })
                continue

            # campos com domínio
            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] and campo.get("dominios"):
                chave_dom = titulo.replace(" ", "")[:20].upper()
                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "descricao": descricao,
                    "obrigatorio": obrig,
                    "largura": largura,
                    "colunas": str(campo.get("colunas", 1)),
                    "dominio": chave_dom
                }
                ET.SubElement(subelems, "elemento", attrs)

                # criar domínio global
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

            # campos comuns (texto, data, moeda, etc.)
            attrs = {
                "gxsi:type": tipo,
                "titulo": titulo,
                "descricao": descricao,
                "obrigatorio": obrig,
                "largura": largura
            }
            if tipo == "texto-area" and campo.get("altura"):
                attrs["altura"] = str(campo.get("altura"))
            el = ET.SubElement(subelems, "elemento", attrs)
            ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    # adicionar dominios globais
    root.append(dominios_global)
    return _prettify_xml(root)

# -------------------------
# Layout: duas colunas
# -------------------------
col1, col2 = st.columns(2)

# -------------------------
# Coluna esquerda: Construtor
# -------------------------
with col1:
    st.title("Construtor de Formulários")
    st.session_state.formulario["nome"] = st.text_input(
        "Nome do Formulário", st.session_state.formulario["nome"]
    )
    st.markdown("---")

    # Nova seção
    with st.expander("➕ Adicionar Seção", expanded=True):
        st.session_state.nova_secao["titulo"] = st.text_input(
            "Título da Seção", st.session_state.nova_secao["titulo"]
        )
        st.session_state.nova_secao["largura"] = st.number_input(
            "Largura da Seção", min_value=100, value=st.session_state.nova_secao["largura"], step=10
        )
        if st.button("Salvar Seção"):
            if st.session_state.nova_secao["titulo"]:
                st.session_state.formulario["secoes"].append(st.session_state.nova_secao.copy())
                st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}
                st.rerun()

    st.markdown("---")

    # Seções existentes
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        with st.expander(f"Seção: {sec.get('titulo','(sem título)')}", expanded=False):
            st.write(f"**Largura:** {sec.get('largura', 500)}")
            if st.button(f"🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                st.session_state.formulario["secoes"].pop(s_idx)
                st.rerun()

            st.markdown("### Campos")
            for c_idx, campo in enumerate(sec.get("campos", [])):
                with st.container():
                    st.write(f"**{campo.get('tipo','')} - {campo.get('titulo','(sem título)')}**")
                    if st.button("Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                        st.session_state.formulario["secoes"][s_idx]["campos"].pop(c_idx)
                        st.rerun()

    # Adicionar campos na última seção
    if st.session_state.formulario.get("secoes"):
        last_idx = len(st.session_state.formulario["secoes"]) - 1
        secao_atual = st.session_state.formulario["secoes"][last_idx]

        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual.get('titulo','(sem título)')}", expanded=True):
            key_title = f"add_title_{last_idx}"
            key_type = f"add_type_{last_idx}"
            key_obrig = f"add_obrig_{last_idx}"
            key_larg = f"add_larg_{last_idx}"
            key_alt = f"add_alt_{last_idx}"
            key_cols = f"add_cols_{last_idx}"
            key_qtd_dom = f"add_qtd_dom_{last_idx}"

            if key_title not in st.session_state:
                st.session_state[key_title] = ""
            st.text_input("Título do Campo", key=key_title)

            if key_type not in st.session_state:
                st.session_state[key_type] = "texto"
            st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS, key=key_type)

            st.checkbox("Obrigatório", key=key_obrig)
            st.number_input("Largura", min_value=100, value=450, step=10, key=key_larg)
            if st.session_state.get(key_type) == "texto-area":
                st.number_input("Altura", min_value=50, value=100, step=10, key=key_alt)

            colunas = None
            dominios_temp = []
            if st.session_state.get(key_type) in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                st.number_input("Colunas", min_value=1, max_value=5, value=1, key=key_cols)
                st.number_input("Quantidade de Itens", min_value=1, max_value=50, value=2, key=key_qtd_dom)
                qtd_dom = int(st.session_state.get(key_qtd_dom, 0) or 0)
                for i in range(qtd_dom):
                    key_dom_i = f"add_dom_{last_idx}_{i}"
                    if key_dom_i not in st.session_state:
                        st.session_state[key_dom_i] = ""
                    st.text_input(f"Descrição Item {i+1}", key=key_dom_i)
                    val = st.session_state.get(key_dom_i, "") or ""
                    if val:
                        dominios_temp.append({"descricao": val, "valor": val.upper()})

            if st.button("Adicionar Campo", key=f"btn_add_field_{last_idx}"):
                campo = {
                    "titulo": st.session_state.get(key_title, ""),
                    "descricao": st.session_state.get(key_title, ""),
                    "tipo": st.session_state.get(key_type, "texto"),
                    "obrigatorio": bool(st.session_state.get(key_obrig, False)),
                    "largura": int(st.session_state.get(key_larg, 450) or 450),
                    "altura": int(st.session_state.get(key_alt, 100) or 100) if st.session_state.get(key_type) == "texto-area" else None,
                    "colunas": int(st.session_state.get(key_cols, 1) or 1) if st.session_state.get(key_type) in ["comboBox","comboFiltro","grupoRadio","grupoCheck"] else None,
                    "dominios": dominios_temp,
                    "valor": ""  # paragrafo tratado no XML
                }
                secao_atual["campos"].append(campo)
                st.rerun()

# -------------------------
# Coluna direita: Pré-visualização
# -------------------------
with col2:
    st.subheader("📋 Pré-visualização do Formulário")
    st.header(st.session_state.formulario.get("nome", ""))
    for sec in st.session_state.formulario.get("secoes", []):
        st.subheader(f"• {sec.get('titulo','')}")
        for campo in sec.get("campos", []):
            tipo = campo.get("tipo", "texto")
            key_prev = f"prev_{campo.get('titulo','')}"
            if tipo == "texto":
                st.text_input(campo.get("titulo",""), key=key_prev)
            elif tipo == "texto-area":
                st.text_area(campo.get("titulo",""), height=campo.get("altura",100), key=key_prev)
            elif tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                opcoes = [d["descricao"] for d in campo.get("dominios",[])]
                if tipo in ["comboBox", "comboFiltro", "grupoCheck"]:
                    st.multiselect(campo.get("titulo",""), opcoes, key=key_prev)
                else:
                    st.radio(campo.get("titulo",""), opcoes, key=key_prev)

# -------------------------
# Pré-visualização do XML
# -------------------------
st.markdown("---")
st.subheader("📑 Pré-visualização do XML")
st.code(gerar_xml(st.session_state.formulario), language="xml")
