# app.py - Construtor de Formulários 4.2 (estável)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date, datetime

st.set_page_config(page_title="Construtor de Formulários 4.2", layout="wide")

# -----------------------
# Configuração inicial
# -----------------------
# Estrutura do formulário em session_state:
# formulario: { nome, versao, secoes: [ {titulo, largura, elementos: [...] } ] }
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}

# Estruturas temporárias para opções/tabelas por seção (evitar sobrescrever widgets)
if "temp" not in st.session_state:
    st.session_state.temp = {}

# Elementos suportados (gxsi:type)
ELEMENT_TYPES = [
    "data",
    "moeda",
    "texto-area",
    "texto",
    "cpf",
    "cnpj",
    "email",
    "telefone",
    "check",
    "comboBox",
    "comboFiltro",
    "grupoRadio",
    "grupoCheck",
    "paragrafo",
    "rotulo",
    "tabela",
]

# -----------------------
# Funções utilitárias
# -----------------------
def prettify_xml(elem):
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def export_to_gxsi_xml(formulario):
    """Exporta o estado do formulário para o XML GXSI no formato solicitado."""
    root = ET.Element(
        "gxsi:formulario",
        {
            "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
            "nome": formulario.get("nome", "Formulario"),
            "versao": formulario.get("versao", "1.0"),
        },
    )

    elementos_tag = ET.SubElement(root, "elementos")

    # Coletar domínios usados para criar <dominios> no final
    # mapa: dominio_key -> list of {descricao, valor}
    dominios_map = {}

    for sec in formulario.get("secoes", []):
        sec_attrib = {"gxsi:type": "seccao", "titulo": sec.get("titulo", ""), "largura": str(sec.get("largura", 500))}
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrib)
        sec_elems = ET.SubElement(sec_el, "elementos")

        for elem in sec.get("elementos", []):
            # descricao deve sempre ser igual ao titulo (oculto na UI)
            titulo = elem.get("titulo", "")
            descricao = titulo

            attribs = {
                "gxsi:type": elem.get("tipo"),
                "titulo": titulo,
                "descricao": descricao,
                "obrigatorio": str(elem.get("obrigatorio", False)).lower(),
                "largura": str(elem.get("largura", 450)),
            }

            # atributos específicos
            if elem.get("tipo") == "texto-area":
                attribs["altura"] = str(elem.get("altura", 120))
            if elem.get("tipo") in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck"):
                attribs["colunas"] = str(elem.get("colunas", 1))
                # dominio key if present
                dominio_key = elem.get("dominio_key", "")
                if dominio_key:
                    attribs["dominio"] = dominio_key
                # Register domain items in dominios_map (if provided)
                itens = elem.get("dominio_itens", [])
                if dominio_key:
                    if dominio_key not in dominios_map:
                        dominios_map[dominio_key] = []
                    # only dominioItemValor allowed in this version
                    for it in itens:
                        # it is dict with descricao and valor
                        dominios_map[dominio_key].append({"descricao": it.get("descricao", ""), "valor": it.get("valor", "")})

            # tabela is a top-level element with child <tabela> in this implementation
            el = ET.SubElement(sec_elems, "elemento", attribs)

            if elem.get("tipo") in ("paragrafo", "rotulo"):
                # set 'valor' attribute for these types if provided
                if elem.get("valor"):
                    el.set("valor", str(elem.get("valor")))
            elif elem.get("tipo") == "tabela":
                # tabela as own node (not inside conteudo)
                tabela_el = ET.SubElement(el, "tabela")
                for linha in elem.get("linhas", []):
                    linha_el = ET.SubElement(tabela_el, "linha")
                    for cel in linha:
                        ET.SubElement(linha_el, "celula", {"valor": str(cel)})
            else:
                # default: add conteudo gxsi:type="valor"
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    # adicionar top-level dominios (somente dominioEstatico com dominioItemValor)
    if dominios_map:
        dominios_tag = ET.SubElement(root, "dominios")
        for chave, itens in dominios_map.items():
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": chave})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in itens:
                # dominioItemValor only
                ET.SubElement(itens_el, "item", {"gxsi:type": "dominioItemValor", "descricao": it.get("descricao", ""), "valor": it.get("valor", "")})

    return prettify_xml(root)


# -----------------------
# UI helpers: adicionar seção, elemento
# -----------------------
def add_section(titulo, largura):
    st.session_state.formulario["secoes"].append({"titulo": titulo, "largura": int(largura), "elementos": []})


def add_element_to_section(sec_index, element):
    st.session_state.formulario["secoes"][sec_index]["elementos"].append(element)


# -----------------------
# Layout: controles (esquerda) e preview (direita)
# -----------------------
st.title("Construtor de Formulários 4.2")

col_controls, col_preview = st.columns([2.6, 1.4])

with col_controls:
    st.header("Configuração do Formulário")
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", value=st.session_state.formulario.get("nome", ""))
    st.session_state.formulario["versao"] = st.text_input("Versão", value=st.session_state.formulario.get("versao", "1.0"))

    st.markdown("---")
    st.subheader("Seções")
    # Adicionar seção (form para clear_on_submit)
    with st.form("form_add_sec", clear_on_submit=True):
        new_sec_title = st.text_input("Título da nova seção")
        new_sec_width = st.number_input("Largura da seção", min_value=100, max_value=1200, value=500)
        add_sec_btn = st.form_submit_button("Adicionar Seção")
        if add_sec_btn:
            if not new_sec_title.strip():
                st.error("Informe o título da seção.")
            else:
                add_section(new_sec_title.strip(), new_sec_width)
                st.success(f"Seção '{new_sec_title.strip()}' criada.")

    # Para cada seção: expander com formulário para adicionar elementos
    for s_idx, sec in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção [{s_idx}] — {sec['titulo']}", expanded=False):
            # permitir editar título/largura da seção
            new_title = st.text_input("Editar título da seção", value=sec["titulo"], key=f"sec_title_{s_idx}")
            new_width = st.number_input("Editar largura", min_value=100, max_value=1200, value=sec.get("largura", 500), key=f"sec_width_{s_idx}")
            if st.button("Salvar seção", key=f"save_sec_{s_idx}"):
                sec["titulo"] = new_title.strip()
                sec["largura"] = int(new_width)
                st.success("Seção atualizada.")

            st.markdown("Adicionar elemento")
            # form separado para cada seção (clear_on_submit)
            form_key = f"form_add_elem_{s_idx}"
            with st.form(form_key, clear_on_submit=True):
                elem_type = st.selectbox("Tipo do elemento", ELEMENT_TYPES, index=0, key=f"elem_type_{s_idx}")
                titulo = st.text_input("Título", key=f"elem_title_{s_idx}")
                # descricao oculto: será igual ao título automaticamente
                obrig = st.checkbox("Obrigatório", key=f"elem_obrig_{s_idx}")
                largura = st.number_input("Largura do elemento", min_value=50, max_value=1200, value=450, key=f"elem_larg_{s_idx}")

                # campos dinâmicos por tipo
                altura = None
                valor = None
                colunas = None
                dominio_key = None
                dominio_items = []

                if elem_type == "texto-area":
                    altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=f"elem_alt_{s_idx}")
                if elem_type in ("paragrafo", "rotulo"):
                    valor = st.text_input("Valor (texto mostrado)", key=f"elem_val_{s_idx}")
                if elem_type in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck"):
                    colunas = st.number_input("Colunas", min_value=1, max_value=6, value=1, key=f"elem_cols_{s_idx}")
                    dominio_key = st.text_input("Chave do domínio (ex: TESTEESTATICO)", key=f"elem_domkey_{s_idx}")
                    # usar temp storage para itens do domínio por seção/elemento
                    temp_key = f"dom_items_{s_idx}"
                    if temp_key not in st.session_state.temp:
                        st.session_state.temp[temp_key] = []
                    st.markdown("**Itens do domínio (apenas dominioItemValor)**")
                    col_a, col_b = st.columns([3,2])
                    with col_a:
                        item_desc = st.text_input("Descrição da opção", key=f"dom_item_desc_{s_idx}")
                    with col_b:
                        item_val = st.text_input("Valor da opção", key=f"dom_item_val_{s_idx}")
                    if st.button("Adicionar opção", key=f"btn_add_dom_item_{s_idx}"):
                        if not (item_desc.strip() or item_val.strip()):
                            st.error("Informe descrição ou valor para a opção.")
                        else:
                            st.session_state.temp[temp_key].append({"descricao": item_desc.strip(), "valor": item_val.strip()})
                    # mostrar opções atuais
                    if st.session_state.temp[temp_key]:
                        st.write("Opções atuais:")
                        for oi, it in enumerate(list(st.session_state.temp[temp_key])):
                            cols = st.columns([6,1])
                            cols[0].write(f"- [{oi}] desc='{it.get('descricao')}' valor='{it.get('valor')}'")
                            if cols[1].button("Remover", key=f"rm_opt_{s_idx}_{oi}"):
                                st.session_state.temp[temp_key].pop(oi)
                                st.experimental_rerun()
                    dominio_items = list(st.session_state.temp.get(temp_key, []))

                if elem_type == "tabela":
                    # Tabela: colunas definidas por usuário e linhas adicionadas
                    temp_tab_key = f"tab_{s_idx}"
                    if temp_tab_key not in st.session_state.temp:
                        st.session_state.temp[temp_tab_key] = {"colunas": [], "linhas": []}
                    st.write("**Configurar tabela (colunas e linhas)**")
                    new_col_name = st.text_input("Nome da nova coluna", key=f"tab_col_name_{s_idx}")
                    if st.button("Adicionar coluna", key=f"btn_tab_add_col_{s_idx}") and new_col_name.strip():
                        st.session_state.temp[temp_tab_key]["colunas"].append(new_col_name.strip())
                    st.write("Colunas atuais:", st.session_state.temp[temp_tab_key]["colunas"])
                    if st.session_state.temp[temp_tab_key]["colunas"]:
                        # inputs para adicionar uma linha (um input por coluna)
                        st.write("Adicionar linha:")
                        row_vals = []
                        for c_name in st.session_state.temp[temp_tab_key]["colunas"]:
                            v = st.text_input(f"Valor - {c_name}", key=f"tab_val_{s_idx}_{c_name}")
                            row_vals.append(v)
                        if st.button("Adicionar linha", key=f"btn_tab_add_row_{s_idx}"):
                            # strip and append
                            st.session_state.temp[temp_tab_key]["linhas"].append([rv for rv in row_vals])
                    # mostrar linhas
                    if st.session_state.temp[temp_tab_key]["linhas"]:
                        st.write("Linhas atuais:")
                        for li, l in enumerate(st.session_state.temp[temp_tab_key]["linhas"]):
                            st.write(f"- [{li}] " + " | ".join([str(x) for x in l]))
                    # ao submeter o form, vamos pegar colunas e linhas
                    # (dominio_items not used)
                # Submissão do elemento
                submitted = st.form_submit_button("Adicionar Elemento")
                if submitted:
                    if not titulo.strip() and elem_type not in ("paragrafo", "rotulo"):
                        st.error("Informe o título do elemento.")
                    else:
                        element = {
                            "tipo": elem_type,
                            "titulo": titulo.strip() if titulo else "",
                            # descricao não editável, igual ao titulo
                            "descricao": (titulo.strip() if titulo else ""),
                            "obrigatorio": bool(obrig),
                            "largura": int(largura),
                        }
                        if altura:
                            element["altura"] = int(altura)
                        if valor:
                            element["valor"] = valor
                        if colunas:
                            element["colunas"] = int(colunas)
                        if elem_type in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck"):
                            # dominio key mandatory to export domain later; but accept empty
                            element["dominio_key"] = dominio_key.strip() if dominio_key else ""
                            element["dominio_itens"] = dominio_items
                            # clear temp for this section
                            temp_key = f"dom_items_{s_idx}"
                            st.session_state.temp[temp_key] = []
                        if elem_type == "tabela":
                            tab_key = f"tab_{s_idx}"
                            element["linhas"] = list(st.session_state.temp.get(tab_key, {}).get("linhas", []))
                            # clear temp table
                            st.session_state.temp[tab_key] = {"colunas": [], "linhas": []}

                        add_element_to_section(s_idx, element)
                        st.success(f"Elemento '{element['titulo'] or element['tipo']}' adicionado à seção '{sec['titulo']}'")

            # Exibir elementos já adicionados nessa seção
            if sec.get("elementos"):
                st.markdown("**Elementos desta seção**")
                for e_idx, el in enumerate(list(sec["elementos"])):
                    st.write(f"- [{e_idx}] {el.get('titulo','(sem título)')} ({el.get('tipo')}) obrigatorio={el.get('obrigatorio', False)}")
                    cols = st.columns([1,1,1])
                    if cols[0].button("Remover", key=f"rm_elem_{s_idx}_{e_idx}"):
                        sec["elementos"].pop(e_idx)
                        st.experimental_rerun()
                    if cols[1].button("Editar", key=f"edit_elem_{s_idx}_{e_idx}"):
                        st.info("Edite o elemento removendo e recriando (edição inline não implementada).")
                    # preview small
                    if cols[2].button("Mover cima", key=f"up_elem_{s_idx}_{e_idx}"):
                        if e_idx > 0:
                            sec["elementos"][e_idx - 1], sec["elementos"][e_idx] = sec["elementos"][e_idx], sec["elementos"][e_idx - 1]
                            st.experimental_rerun()

with col_preview:
    st.header("Pré-visualização & Exportação")
    st.caption("Preview do XML (automático) — descrição sempre igual ao título.")
    xml_out = export_to_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario.xml", mime="application/xml")

# -----------------------
# Nota: dicas rápidas
# -----------------------
st.markdown("---")
st.caption("Observações: \n"
           "- Domínios (dominioEstatico) são declarados automaticamente no XML quando você adicionar opções a um elemento que usa domínio.\n"
           "- Apenas dominioItemValor é gerado (conforme solicitado).\n"
           "- Descrições são sempre iguais ao título (campo de descrição oculto).")
