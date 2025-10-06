import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom

st.set_page_config(page_title="Construtor de Formulários 6.5", layout="wide")

# --- Inicialização do estado ---
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

# --- Função para formatar XML ---
def _prettify_xml(root: ET.Element) -> str:
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_bytes)
    return parsed.toprettyxml(indent="   ", encoding="utf-8").decode("utf-8")

# --- Função para gerar XML do formulário ---
def gerar_xml(formulario: dict) -> str:
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome", ""),
        "versao": formulario.get("versao", "1.0")
    })

    elementos = ET.SubElement(root, "elementos")
    dominios_global = ET.Element("dominios")

    for secao in formulario.get("secoes", []):
        sec_el = ET.SubElement(elementos, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao.get("titulo", ""),
            "largura": str(secao.get("largura", 500))
        })
        subelems = ET.SubElement(sec_el, "elementos")

        campos = secao.get("campos", [])
        i = 0
        while i < len(campos):
            campo = campos[i]
            if campo.get("in_tabela"):
                # Criar tabela e linha
                tabela_el = ET.SubElement(subelems, "elemento", {"gxsi:type": "tabela"})
                linhas_el = ET.SubElement(tabela_el, "linhas")
                linha_el = ET.SubElement(linhas_el, "linha")
                celulas_el = ET.SubElement(linha_el, "celulas")

                # Adicionar células enquanto campos consecutivos pertencem à tabela
                while i < len(campos) and campos[i].get("in_tabela"):
                    celula_el = ET.SubElement(celulas_el, "celula", {"linhas": "1", "colunas": "1"})
                    elementos_celula = ET.SubElement(celula_el, "elementos")

                    c = campos[i]
                    tipo = c.get("tipo", "texto")
                    titulo = c.get("titulo", "")
                    obrig = str(bool(c.get("obrigatorio", False))).lower()
                    largura = str(c.get("largura", 450))

                    # parágrafo / rótulo
                    if tipo in ["paragrafo", "rotulo"]:
                        ET.SubElement(elementos_celula, "elemento", {
                            "gxsi:type": tipo,
                            "valor": c.get("valor", titulo),
                            "largura": largura
                        })
                        i += 1
                        continue

                    # campos com domínio
                    if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"] and c.get("dominios"):
                        chave_dom = titulo.replace(" ", "")[:20].upper()
                        attrs = {
                            "gxsi:type": tipo,
                            "titulo": titulo,
                            "descricao": c.get("descricao", titulo),
                            "obrigatorio": obrig,
                            "largura": largura,
                            "colunas": str(c.get("colunas", 1)),
                            "dominio": chave_dom
                        }
                        ET.SubElement(elementos_celula, "elemento", attrs)

                        # domínio global
                        dominio_el = ET.SubElement(dominios_global, "dominio", {
                            "gxsi:type": "dominioEstatico",
                            "chave": chave_dom
                        })
                        itens_el = ET.SubElement(dominio_el, "itens")
                        for d in c["dominios"]:
                            ET.SubElement(itens_el, "item", {
                                "gxsi:type": "dominioItemValor",
                                "descricao": d["descricao"],
                                "valor": d["valor"]
                            })
                        i += 1
                        continue

                    # campos comuns
                    attrs = {
                        "gxsi:type": tipo,
                        "titulo": titulo,
                        "descricao": c.get("descricao", titulo),
                        "obrigatorio": obrig,
                        "largura": largura
                    }
                    if tipo == "texto-area" and c.get("altura"):
                        attrs["altura"] = str(c.get("altura"))
                    el = ET.SubElement(elementos_celula, "elemento", attrs)
                    ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
                    i += 1
            else:
                # Campo fora da tabela
                tipo = campo.get("tipo", "texto")
                titulo = campo.get("titulo", "")
                obrig = str(bool(campo.get("obrigatorio", False))).lower()
                largura = str(campo.get("largura", 450))

                # parágrafo / rótulo
                if tipo in ["paragrafo", "rotulo"]:
                    ET.SubElement(subelems, "elemento", {
                        "gxsi:type": tipo,
                        "valor": campo.get("valor", titulo),
                        "largura": largura
                    })
                    i += 1
                    continue

                # campos com domínio
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
                    ET.SubElement(subelems, "elemento", attrs)

                    # domínio global
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
                    i += 1
                    continue

                # campos comuns
                attrs = {
                    "gxsi:type": tipo,
                    "titulo": titulo,
                    "descricao": campo.get("descricao", titulo),
                    "obrigatorio": obrig,
                    "largura": largura
                }
                if tipo == "texto-area" and campo.get("altura"):
                    attrs["altura"] = str(campo.get("altura"))
                el = ET.SubElement(subelems, "elemento", attrs)
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

                i += 1

    root.append(dominios_global)
    return _prettify_xml(root)

# --- Função para renderizar campos na pré-visualização ---
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

# --- Layout da aplicação ---
col1, col2 = st.columns(2)

with col1:
    st.title("Construtor de Formulários 6.5")

    # Formulário para alterar nome e versão do formulário
    with st.form("formulario_info", clear_on_submit=False):
        st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
        st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario.get("versao", "1.0"))
        submitted = st.form_submit_button("Atualizar")

    st.markdown("---")

    # Adicionar nova seção
    with st.expander("➕ Adicionar Seção", expanded=True):
        titulo = st.text_input("Título da Seção", key="nova_secao_titulo")
        largura = st.number_input("Largura da Seção", min_value=100, value=500, step=10, key="nova_secao_largura")
        if st.button("Salvar Seção"):
            if titulo.strip():
                st.session_state.formulario["secoes"].append({
                    "titulo": titulo.strip(),
                    "largura": largura,
                    "campos": []
                })
                st.experimental_rerun()

    st.markdown("---")

    # Mostrar seções e campos existentes
    for s_idx, secao in enumerate(st.session_state.formulario.get("secoes", [])):
        with st.expander(f"📁 Seção: {secao.get('titulo','(sem título)')}", expanded=False):
            st.write(f"**Largura:** {secao.get('largura', 500)}")
            if st.button(f"🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                st.session_state.formulario["secoes"].pop(s_idx)
                st.experimental_rerun()

            st.markdown("### Campos")
            for c_idx, campo in enumerate(secao.get("campos", [])):
                st.text(f"{campo.get('tipo')} - {campo.get('titulo')}")
                if st.button("Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                    secao["campos"].pop(c_idx)
                    st.experimental_rerun()

    # Adicionar campos na última seção
    if st.session_state.formulario.get("secoes"):
        last_idx = len(st.session_state.formulario["secoes"]) - 1
        secao_atual = st.session_state.formulario["secoes"][last_idx]
        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual.get('titulo','')}", expanded=True):
            with st.form(f"form_add_campo_{last_idx}", clear_on_submit=True):
                titulo_campo = st.text_input("Título do Campo")
                tipo_campo = st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS)
                obrig_campo = st.checkbox("Obrigatório")
                largura_campo = st.number_input("Largura (px)", min_value=100, value=450, step=10)
                in_tabela_campo = st.checkbox("Dentro da tabela?")

                altura_campo = None
                if tipo_campo == "texto-area":
                    altura_campo = st.number_input("Altura", min_value=50, max_value=500, value=100, step=10)

                dominios_temp = []
                colunas_campo = 1
                if tipo_campo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                    colunas_campo = st.number_input("Colunas", min_value=1, max_value=5, value=1)
                    qtd_dom = st.number_input("Qtd. de Itens no Domínio", min_value=1, max_value=50, value=2)
                    for i in range(int(qtd_dom)):
                        val = st.text_input(f"Descrição Item
