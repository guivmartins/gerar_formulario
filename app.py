# app.py - Construtor de Formulários com Domínios completos (versão 6.4 - restaurado 5.0)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
import unicodedata
import re

st.set_page_config(page_title="Construtor de Formulários", layout="centered")

# -------------------------
# Inicialização do estado
# -------------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "1.0",
        "secoes": [],     # cada seção terá: {"titulo","largura","campos":[...]}
        # obs: 'dominios' aqui era global na v5.0 - no v5.0 original dominios eram apenas construídos no XML
        # e não apresentados separadamente para edição fora do elemento. Mantemos o mesmo comportamento.
    }

# estado temporário para nova seção (preenchimento antes de salvar)
if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}

# Tipos de elementos conforme versão 4.0 / solicitado
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

def _normalize_key_from_title(title: str) -> str:
    # regra v5.0: remover acentos/caracteres não alfanuméricos, limitar 20 chars, uppercase
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r'[^0-9A-Za-z]+', '', s)
    return s[:20].upper()

def gerar_xml(formulario: dict) -> str:
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome", ""),
        "versao": formulario.get("versao", "1.0")
    })

    elementos = ET.SubElement(root, "elementos")
    dominios_global = ET.Element("dominios")

    # percorre seções e campos (v5.0 style: sec["campos"])
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

            # campos com domínio: gerar elemento + domínio global
            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] and campo.get("dominios"):
                # chave = título sem espaços e maiúscula limitado a 20 chars (v5.0)
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

                # criar domínio global (dominioEstatico)
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

    # adicionar dominios globais (sempre fora de <elementos>)
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
    # Nome do formulário (usar retorno do widget para atualizar o estado)
    nome_form = st.text_input("Nome do Formulário", value=st.session_state.formulario.get("nome", ""))
    st.session_state.formulario["nome"] = nome_form

    st.markdown("---")

    # Nova seção (expander)
    with st.expander("➕ Adicionar Seção", expanded=True):
        sec_title = st.text_input("Título da Seção", value=st.session_state.nova_secao.get("titulo", ""), key="input_nova_secao_titulo")
        sec_width = st.number_input("Largura da Seção", min_value=100, value=st.session_state.nova_secao.get("largura", 500), step=10, key="input_nova_secao_largura")
        if st.button("Salvar Seção"):
            if sec_title:
                # salvar nova seção com campos vazios
                st.session_state.formulario["secoes"].append({
                    "titulo": sec_title,
                    "largura": int(sec_width),
                    "campos": []
                })
                # reset temporário
                st.session_state.nova_secao = {"titulo": "", "largura": 500, "campos": []}
                st.experimental_rerun()

    st.markdown("---")

    # Seções existentes
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        with st.expander(f"Seção: {sec.get('titulo','(sem título)')}", expanded=False):
            st.write(f"**Largura:** {sec.get('largura', 500)}")
            if st.button(f"🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                st.session_state.formulario["secoes"].pop(s_idx)
                st.experimental_rerun()

            st.markdown("### Campos")
            for c_idx, campo in enumerate(sec.get("campos", [])):
                with st.container():
                    st.write(f"**{campo.get('tipo','')} - {campo.get('titulo','(sem título)')}**")
                    if st.button("Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                        st.session_state.formulario["secoes"][s_idx]["campos"].pop(c_idx)
                        st.experimental_rerun()

    # Adicionar campos na última seção (mesma lógica da v5.0)
    if st.session_state.formulario.get("secoes"):
        last_idx = len(st.session_state.formulario["secoes"]) - 1
        secao_atual = st.session_state.formulario["secoes"][last_idx]

        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual.get('titulo','(sem título)')}", expanded=True):
            # keys dinâmicas por seção
            key_title = f"add_title_{last_idx}"
            key_type = f"add_type_{last_idx}"
            key_obrig = f"add_obrig_{last_idx}"
            key_larg = f"add_larg_{last_idx}"
            key_alt = f"add_alt_{last_idx}"
            key_cols = f"add_cols_{last_idx}"
            key_qtd_dom = f"add_qtd_dom_{last_idx}"

            # inicializar chaves no session_state se não existirem (mantém valor entre reruns)
            if key_title not in st.session_state:
                st.session_state[key_title] = ""
            if key_type not in st.session_state:
                st.session_state[key_type] = "texto"
            if key_obrig not in st.session_state:
                st.session_state[key_obrig] = False
            if key_larg not in st.session_state:
                st.session_state[key_larg] = 450
            if key_alt not in st.session_state:
                st.session_state[key_alt] = 100
            if key_cols not in st.session_state:
                st.session_state[key_cols] = 1
            if key_qtd_dom not in st.session_state:
                st.session_state[key_qtd_dom] = 2

            # widgets (usar chaves para persistência)
            st.text_input("Título do Campo", key=key_title)
            st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS, key=key_type)
            st.checkbox("Obrigatório", key=key_obrig)
            st.number_input("Largura", min_value=100, value=st.session_state[key_larg], step=10, key=key_larg)

            if st.session_state.get(key_type) == "texto-area":
                st.number_input("Altura", min_value=50, value=st.session_state[key_alt], step=10, key=key_alt)

            dominios_temp = []
            # se o tipo usa domínio, mostrar colunas + quantidade de itens e inputs para cada item
            if st.session_state.get(key_type) in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                st.number_input("Colunas", min_value=1, max_value=5, value=st.session_state[key_cols], key=key_cols)
                st.number_input("Quantidade de Itens", min_value=1, max_value=50, value=st.session_state[key_qtd_dom], key=key_qtd_dom)
                qtd_dom = int(st.session_state.get(key_qtd_dom, 0) or 0)
                for i in range(qtd_dom):
                    key_dom_i = f"add_dom_{last_idx}_{i}"
                    if key_dom_i not in st.session_state:
                        st.session_state[key_dom_i] = ""
                    st.text_input(f"Descrição Item {i+1}", key=key_dom_i)
                    val = st.session_state.get(key_dom_i, "") or ""
                    if val:
                        # valor automático = descrição.upper()
                        dominios_temp.append({"descricao": val, "valor": val.upper()})

            # botão para adicionar campo
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
                # limpar os inputs de domínio temporários
                if st.session_state.get(key_type) in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                    qtd_dom = int(st.session_state.get(key_qtd_dom, 0) or 0)
                    for i in range(qtd_dom):
                        key_dom_i = f"add_dom_{last_idx}_{i}"
                        if key_dom_i in st.session_state:
                            st.session_state[key_dom_i] = ""
                # limpar título do campo para facilitar inclusão sequencial
                st.session_state[key_title] = ""
                st.experimental_rerun()

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
            key_prev = f"prev_{campo.get('titulo','')}_{tipo}"
            if tipo == "texto":
                st.text_input(campo.get("titulo",""), key=key_prev)
            elif tipo == "texto-area":
                st.text_area(campo.get("titulo",""), height=campo.get("altura",100), key=key_prev)
            elif tipo == "data":
                st.date_input(campo.get("titulo",""), key=key_prev)
            elif tipo == "moeda":
                st.text_input(campo.get("titulo",""), placeholder="0,00", key=key_prev)
            elif tipo == "cpf":
                st.text_input(campo.get("titulo",""), placeholder="000.000.000-00", key=key_prev)
            elif tipo == "cnpj":
                st.text_input(campo.get("titulo",""), placeholder="00.000.000/0000-00", key=key_prev)
            elif tipo == "email":
                st.text_input(campo.get("titulo",""), placeholder="exemplo@dominio.com", key=key_prev)
            elif tipo == "telefone":
                st.text_input(campo.get("titulo",""), placeholder="(00) 00000-0000", key=key_prev)
            elif tipo == "check":
                st.checkbox(campo.get("titulo",""), key=key_prev)
            elif tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                opcoes = [d["descricao"] for d in campo.get("dominios",[])]
                if tipo in ["comboBox", "comboFiltro", "grupoCheck"]:
                    st.multiselect(campo.get("titulo",""), opcoes, key=key_prev)
                else:
                    st.radio(campo.get("titulo",""), opcoes, key=key_prev)
            elif tipo == "paragrafo":
                st.markdown(campo.get("titulo",""))
            elif tipo == "rotulo":
                st.caption(campo.get("titulo",""))

# -------------------------
# Pré-visualização do XML
# -------------------------
st.markdown("---")
st.subheader("📑 Pré-visualização do XML")
st.code(gerar_xml(st.session_state.formulario), language="xml")
