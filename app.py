# app.py - Construtor de Formulários (domínios embutidos por elemento, comportamento estilo v4.0)
import streamlit as st
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date, datetime

st.set_page_config(page_title="Construtor de Formulários", layout="wide")

# -----------------------
# Inicialização seguro do session_state
# -----------------------
if "formulario" not in st.session_state:
    st.session_state.formulario = {"nome": "", "versao": "1.0", "secoes": []}

# dominios: map dominio_key -> list of {"descricao","valor"}
# iniciado vazio; é atualizado exclusivamente a partir dos UIs dos elementos que usam dominio
if "dominios" not in st.session_state:
    st.session_state.dominios = {}  # ex: {"TESTEESTATICO": [{"descricao":"Opção 1","valor":"OP1"}, ...]}

# temporários por seção/elemento (para tabela etc.)
if "temp" not in st.session_state:
    st.session_state.temp = {}

# Tipos de elemento suportados
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
# Helpers XML
# -----------------------
def prettify_xml(elem):
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def export_to_gxsi_xml(formulario):
    root = ET.Element(
        "gxsi:formulario",
        {
            "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
            "nome": formulario.get("nome", "Formulario"),
            "versao": formulario.get("versao", "1.0"),
        },
    )

    elementos_tag = ET.SubElement(root, "elementos")

    # Build elements and collect domain keys referenced
    dominios_referenciados = set()

    for sec in formulario.get("secoes", []):
        sec_attrib = {
            "gxsi:type": "seccao",
            "titulo": sec.get("titulo", ""),
            "largura": str(sec.get("largura", 500)),
        }
        sec_el = ET.SubElement(elementos_tag, "elemento", sec_attrib)
        sec_elems = ET.SubElement(sec_el, "elementos")

        for el in sec.get("elementos", []):
            titulo = el.get("titulo", "")
            descricao = titulo  # regra: descricao == titulo (oculto na UI)
            attribs = {
                "gxsi:type": el.get("tipo"),
                "titulo": titulo,
                "descricao": descricao,
                "obrigatorio": str(el.get("obrigatorio", False)).lower(),
                "largura": str(el.get("largura", 450)),
            }
            if el.get("tipo") == "texto-area":
                attribs["altura"] = str(el.get("altura", 120))
            if el.get("tipo") in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck"):
                attribs["colunas"] = str(el.get("colunas", 1))
                dom_key = el.get("dominio_key", "")
                if dom_key:
                    attribs["dominio"] = dom_key
                    dominios_referenciados.add(dom_key)

            el_tag = ET.SubElement(sec_elems, "elemento", attribs)

            if el.get("tipo") in ("paragrafo", "rotulo"):
                if el.get("valor") is not None:
                    el_tag.set("valor", str(el.get("valor")))
            elif el.get("tipo") == "tabela":
                tabela_el = ET.SubElement(el_tag, "tabela")
                for linha in el.get("linhas", []):
                    linha_el = ET.SubElement(tabela_el, "linha")
                    for cel in linha:
                        ET.SubElement(linha_el, "celula", {"valor": str(cel)})
            else:
                # valor padrão no conteudo
                ET.SubElement(el_tag, "conteudo", {"gxsi:type": "valor"})

    # Top-level dominios: somente dominioEstatico com dominioItemValor
    if dominios_referenciados:
        dominios_tag = ET.SubElement(root, "dominios")
        for chave in sorted(dominios_referenciados):
            itens = st.session_state.dominios.get(chave, [])
            dom_el = ET.SubElement(dominios_tag, "dominio", {"gxsi:type": "dominioEstatico", "chave": chave})
            itens_el = ET.SubElement(dom_el, "itens")
            for it in itens:
                ET.SubElement(itens_el, "item", {"gxsi:type": "dominioItemValor", "descricao": it.get("descricao", ""), "valor": it.get("valor", "")})

    return prettify_xml(root)


# -----------------------
# UI helpers para adicionar seções / elementos
# -----------------------
def add_section(title, width):
    st.session_state.formulario["secoes"].append({"titulo": title, "largura": int(width), "elementos": []})


def add_element_to_section(sec_index, element):
    st.session_state.formulario["secoes"][sec_index]["elementos"].append(element)


# -----------------------
# Layout: controles (esquerda) e preview (direita)
# -----------------------
st.title("Construtor de Formulários (estável)")

col_controls, col_preview = st.columns([2.6, 1.4])

with col_controls:
    st.header("Configuração do Formulário")
    st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", value=st.session_state.formulario.get("nome", ""))
    st.session_state.formulario["versao"] = st.text_input("Versão", value=st.session_state.formulario.get("versao", "1.0"))

    st.markdown("---")
    st.subheader("Seções")

    # adicionar seção (form para clear_on_submit evitar conflitos)
    with st.form("form_add_section", clear_on_submit=True):
        new_section_title = st.text_input("Título da nova seção")
        new_section_width = st.number_input("Largura da seção", min_value=100, max_value=1200, value=500)
        add_sec = st.form_submit_button("Adicionar Seção")
        if add_sec:
            if not new_section_title.strip():
                st.error("Informe o título da seção.")
            else:
                add_section(new_section_title.strip(), new_section_width)
                st.success(f"Seção '{new_section_title.strip()}' adicionada.")

    # para cada seção: expander com formulário próprio para adicionar elemento
    for s_idx, sec in enumerate(st.session_state.formulario["secoes"]):
        with st.expander(f"Seção [{s_idx}] — {sec['titulo']}", expanded=False):
            # editar título/largura
            sec_title = st.text_input("Editar título", value=sec["titulo"], key=f"sec_title_{s_idx}")
            sec_width = st.number_input("Editar largura", min_value=100, max_value=1200, value=sec.get("largura", 500), key=f"sec_width_{s_idx}")
            if st.button("Salvar seção", key=f"save_sec_{s_idx}"):
                sec["titulo"] = sec_title.strip()
                sec["largura"] = int(sec_width)
                st.success("Seção atualizada.")

            st.markdown("Adicionar elemento")
            form_key = f"form_add_elem_{s_idx}"
            with st.form(form_key, clear_on_submit=True):
                elem_type = st.selectbox("Tipo do elemento", ELEMENT_TYPES, index=0, key=f"elem_type_{s_idx}")
                titulo = st.text_input("Título (a descrição será igual ao título)", key=f"elem_title_{s_idx}")
                obrig = st.checkbox("Obrigatório", key=f"elem_obrig_{s_idx}")
                largura = st.number_input("Largura do elemento", min_value=50, max_value=1200, value=450, key=f"elem_larg_{s_idx}")

                altura = None
                valor = None
                colunas = None
                dominio_key = None

                if elem_type == "texto-area":
                    altura = st.number_input("Altura (px)", min_value=50, max_value=800, value=120, key=f"elem_alt_{s_idx}")
                if elem_type in ("paragrafo", "rotulo"):
                    valor = st.text_input("Valor do texto", key=f"elem_val_{s_idx}")
                if elem_type in ("comboBox", "comboFiltro", "grupoRadio", "grupoCheck"):
                    colunas = st.number_input("Colunas", min_value=1, max_value=6, value=1, key=f"elem_cols_{s_idx}")
                    dominio_key = st.text_input("Chave do domínio (ex: TESTEESTATICO)", key=f"elem_domkey_{s_idx}")
                    # Mostrar e manipular itens globais do domínio (comportamento v4.0)
                    if dominio_key and dominio_key.strip():
                        dk = dominio_key.strip()
                        if dk not in st.session_state.dominios:
                            st.session_state.dominios[dk] = []
                        st.markdown("**Itens do domínio (dominioItemValor)**")
                        # inputs para nova opção
                        col_a, col_b = st.columns([3, 2])
                        with col_a:
                            item_desc = st.text_input("Descrição da opção", key=f"dom_item_desc_{s_idx}")
                        with col_b:
                            item_val = st.text_input("Valor da opção", key=f"dom_item_val_{s_idx}")
                        if st.button("Adicionar opção ao domínio", key=f"btn_add_dom_item_{s_idx}"):
                            if not (item_desc.strip() or item_val.strip()):
                                st.error("Informe descrição ou valor para a opção.")
                            else:
                                st.session_state.dominios[dk].append({"descricao": item_desc.strip(), "valor": item_val.strip()})
                                st.success("Opção adicionada ao domínio.")
                                st.experimental_rerun()
                        # listar opções existentes no domínio
                        if st.session_state.dominios.get(dk):
                            st.write("Opções atuais do domínio:")
                            for oi, it in enumerate(list(st.session_state.dominios[dk])):
                                cols = st.columns([6,1])
                                cols[0].write(f"- [{oi}] desc='{it.get('descricao')}' valor='{it.get('valor')}'")
                                if cols[1].button("Remover", key=f"rm_dom_{s_idx}_{oi}_{dk}"):
                                    st.session_state.dominios[dk].pop(oi)
                                    st.experimental_rerun()

                # tabela builder
                if elem_type == "tabela":
                    tab_key = f"tab_{s_idx}"
                    if tab_key not in st.session_state.temp:
                        st.session_state.temp[tab_key] = {"colunas": [], "linhas": []}
                    st.write("Configurar tabela:")
                    new_col = st.text_input("Nome da nova coluna", key=f"tab_colname_{s_idx}")
                    if st.button("Adicionar coluna", key=f"btn_tab_col_{s_idx}") and new_col.strip():
                        st.session_state.temp[tab_key]["colunas"].append(new_col.strip())
                        st.experimental_rerun()
                    st.write("Colunas:", st.session_state.temp[tab_key]["colunas"])
                    if st.session_state.temp[tab_key]["colunas"]:
                        st.write("Adicionar linha (preencha cada campo)")
                        row_vals = []
                        for c_name in st.session_state.temp[tab_key]["colunas"]:
                            v = st.text_input(f"Valor - {c_name}", key=f"tab_val_{s_idx}_{c_name}")
                            row_vals.append(v)
                        if st.button("Adicionar linha", key=f"btn_tab_row_{s_idx}"):
                            st.session_state.temp[tab_key]["linhas"].append([rv for rv in row_vals])
                            st.experimental_rerun()
                        if st.session_state.temp[tab_key]["linhas"]:
                            st.write("Linhas atuais:")
                            for li, l in enumerate(st.session_state.temp[tab_key]["linhas"]):
                                st.write(f"- [{li}] " + " | ".join([str(x) for x in l]))

                submitted = st.form_submit_button("Adicionar Elemento")
                if submitted:
                    # validações básicas
                    if elem_type not in ("paragrafo", "rotulo") and not titulo.strip():
                        st.error("Informe o título do elemento.")
                    else:
                        element = {
                            "tipo": elem_type,
                            "titulo": titulo.strip() if titulo else "",
                            "descricao": titulo.strip() if titulo else "",
                            "obrigatorio": bool(obrig),
                            "largura": int(largura),
                        }
                        if altura:
                            element["altura"] = int(altura)
                        if valor:
                            element["valor"] = valor
                        if colunas:
                            element["colunas"] = int(colunas)
                        if dominio_key:
                            element["dominio_key"] = dominio_key.strip()
                        if elem_type == "tabela":
                            tk = f"tab_{s_idx}"
                            element["linhas"] = list(st.session_state.temp.get(tk, {}).get("linhas", []))
                            st.session_state.temp[tk] = {"colunas": [], "linhas": []}
                        add_element_to_section(s_idx, element)
                        st.success(f"Elemento '{element['titulo'] or element['tipo']}' adicionado.")

            # Mostrar elementos da seção
            if sec.get("elementos"):
                st.markdown("**Elementos desta seção**")
                for e_idx, el in enumerate(list(sec["elementos"])):
                    dominio_info = f" dominio={el.get('dominio_key')}" if el.get("dominio_key") else ""
                    st.write(f"- [{e_idx}] {el.get('titulo','(sem título)')} ({el.get('tipo')}) obrig={el.get('obrigatorio', False)}{dominio_info}")
                    cols = st.columns([1,1,1])
                    if cols[0].button("Remover", key=f"rm_elem_{s_idx}_{e_idx}"):
                        sec["elementos"].pop(e_idx)
                        st.experimental_rerun()
                    if cols[1].button("Editar", key=f"edit_elem_{s_idx}_{e_idx}"):
                        st.info("Edição inline não implementada — remova e recrie o elemento.")
                    if cols[2].button("Mover cima", key=f"up_elem_{s_idx}_{e_idx}"):
                        if e_idx > 0:
                            sec["elementos"][e_idx - 1], sec["elementos"][e_idx] = sec["elementos"][e_idx], sec["elementos"][e_idx - 1]
                            st.experimental_rerun()

with col_preview:
    st.header("Pré-visualização & Exportação")
    st.caption("Descrição é sempre igual ao título; domínios são gerenciados dentro dos elementos.")
    xml_out = export_to_gxsi_xml(st.session_state.formulario)
    st.code(xml_out, language="xml")
    st.download_button("Baixar XML", data=xml_out, file_name="formulario.xml", mime="application/xml")

# Rodapé com notas
st.markdown("---")
st.caption(
    "- Domínios (dominioEstatico) são criados/atualizados quando você adiciona opções a um elemento que usa domínio.\n"
    "- Apenas dominioItemValor é gerado (conforme solicitado).\n"
    "- Para editar opções de um domínio já existente, informe a mesma chave no elemento e remova/adicione opções diretamente ali."
)
