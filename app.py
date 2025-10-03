# app.py - Construtor de Formulários (correção: não sobrescrever nova_secao)
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
        "secoes": [],   # cada seção: {"titulo": str, "largura": int, "campos": [ {...} ]}
        "dominios": []  # lista de dominios: {"chave": str, "itens": [{"descricao":..., "valor":...}, ...]}
    }

# inicializar a chave usada pelo widget de nova seção ANTES de criar o widget
if "nova_secao" not in st.session_state:
    st.session_state.nova_secao = ""   # <- inicialização segura, NÃO reatribuir depois do widget

# Tipos suportados (conforme pedido; ignoramos cmc7/chave e dominioItemParametro)
TIPOS_ELEMENTOS = [
    "texto",
    "texto-area",
    "data",
    "moeda",
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
    "rotulo"
]

# -------------------------
# Funções utilitárias
# -------------------------
def _prettify_xml(root: ET.Element) -> str:
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    parsed = minidom.parseString(xml_bytes)
    pretty = parsed.toprettyxml(indent="   ", encoding="utf-8")
    return pretty.decode("utf-8")

def gerar_xml(formulario: dict) -> str:
    """Gera XML conforme estrutura solicitada (dominios fora de elementos)."""
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario.get("nome", ""),
        "versao": formulario.get("versao", "1.0")
    })

    elementos = ET.SubElement(root, "elementos")

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

            # paragrafo / rotulo -> atributo valor, sem <conteudo>
            if tipo == "paragrafo" or tipo == "rotulo":
                ET.SubElement(subelems, "elemento", {
                    "gxsi:type": tipo,
                    "valor": campo.get("valor", titulo),
                    "largura": largura
                })
                continue

            # atributos comuns
            attrs = {
                "gxsi:type": tipo,
                "titulo": titulo,
                "descricao": descricao,
                "obrigatorio": obrig,
                "largura": largura
            }

            # altura para texto-area
            if tipo == "texto-area" and campo.get("altura"):
                attrs["altura"] = str(campo.get("altura"))

            # colunas e dominio para combos / grupos
            if tipo in ["comboBox", "comboFiltro", "grupoRadio", "grupoCheck"]:
                attrs["colunas"] = str(campo.get("colunas", 1))
                if campo.get("dominio"):
                    attrs["dominio"] = campo.get("dominio")

            # cria elemento e, quando aplicável, o <conteudo>
            el = ET.SubElement(subelems, "elemento", attrs)
            # conforme seu exemplo, grupoRadio e grupoCheck apresentam <conteudo>, e a maioria dos inputs também
            if tipo in ["grupoRadio", "grupoCheck", "texto", "texto-area", "data", "moeda", "cpf", "cnpj", "email", "telefone", "check"]:
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})
            # comboBox / comboFiltro ficam sem <conteudo> (conforme exemplo)

    # dominios fora de <elementos>
    if formulario.get("dominios"):
        dominios_el = ET.SubElement(root, "dominios")
        for dom in formulario["dominios"]:
            dom_child = ET.SubElement(dominios_el, "dominio", {
                "gxsi:type": "dominioEstatico",
                "chave": dom.get("chave", "")
            })
            itens_el = ET.SubElement(dom_child, "itens")
            for it in dom.get("itens", []):
                # somente dominioItemValor conforme solicitado
                ET.SubElement(itens_el, "item", {
                    "gxsi:type": "dominioItemValor",
                    "descricao": it.get("descricao", ""),
                    "valor": it.get("valor", "")
                })

    return _prettify_xml(root)

# -------------------------
# Layout (duas colunas)
# -------------------------
col1, col2 = st.columns(2)

# -------------------------
# Coluna esquerda: construtor
# -------------------------
with col1:
    st.title("Construtor de Formulários")

    # Nome do formulário (campo simples)
    name_key = "form_name_input"
    # usar value do estado existente como padrão
    if name_key not in st.session_state:
        st.session_state[name_key] = st.session_state.formulario.get("nome", "")
    st.text_input("Nome do Formulário", key=name_key)
    # gravar no modelo
    st.session_state.formulario["nome"] = st.session_state.get(name_key, "")

    st.markdown("---")

    # Adicionar nova seção (expander)
    with st.expander("➕ Adicionar Seção", expanded=True):
        # usamos a chave 'nova_secao' (inicializada no topo). NÃO reatribuir essa chave em nenhum momento.
        st.text_input("Título da Seção", key="nova_secao")
        if "nova_secao_width" not in st.session_state:
            st.session_state.nova_secao_width = 500
        st.number_input("Largura da Seção", min_value=100, value=st.session_state.nova_secao_width, step=10, key="nova_secao_width")

        if st.button("Salvar Seção", key="btn_save_section"):
            title = (st.session_state.get("nova_secao") or "").strip()
            width = int(st.session_state.get("nova_secao_width", 500) or 500)
            if title:
                st.session_state.formulario["secoes"].append({
                    "titulo": title,
                    "largura": width,
                    "campos": []
                })
                # NÃO sobrescrever st.session_state.nova_secao (isso gerou o erro)
                # Apenas rerun para atualizar a interface
                try:
                    st.rerun()
                except Exception:
                    pass

    st.markdown("---")

    # Mostrar seções existentes com opção de excluir e listar campos
    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        with st.expander(f"Seção: {sec.get('titulo','(sem título)')}", expanded=False):
            st.write(f"**Largura:** {sec.get('largura', 500)}")

            # Excluir seção
            if st.button(f"🗑️ Excluir Seção", key=f"del_sec_{s_idx}"):
                try:
                    st.session_state.formulario["secoes"].pop(s_idx)
                except Exception:
                    pass
                try:
                    st.rerun()
                except Exception:
                    pass

            st.markdown("### Campos")
            # listar campos com container (sem expanders aninhados)
            for c_idx, campo in enumerate(sec.get("campos", [])):
                with st.container():
                    st.write(f"**{campo.get('tipo','')} - {campo.get('titulo','(sem título)')}**")
                    # Excluir campo
                    if st.button("Excluir Campo", key=f"del_field_{s_idx}_{c_idx}"):
                        try:
                            st.session_state.formulario["secoes"][s_idx]["campos"].pop(c_idx)
                        except Exception:
                            pass
                        try:
                            st.rerun()
                        except Exception:
                            pass

    st.markdown("---")

    # Adicionar campos à ÚLTIMA seção (com chaves que incluem o índice da seção)
    if st.session_state.formulario.get("secoes"):
        last_idx = len(st.session_state.formulario["secoes"]) - 1
        secao_atual = st.session_state.formulario["secoes"][last_idx]

        with st.expander(f"➕ Adicionar Campos à seção: {secao_atual.get('titulo','(sem título)')}", expanded=True):
            # keys únicos para este formulário de adição
            key_title = f"add_title_{last_idx}"
            key_type = f"add_type_{last_idx}"
            key_obrig = f"add_obrig_{last_idx}"
            key_larg = f"add_larg_{last_idx}"
            key_alt = f"add_alt_{last_idx}"
            key_cols = f"add_cols_{last_idx}"
            key_qtd_dom = f"add_qtd_dom_{last_idx}"

            # widgets
            if key_title not in st.session_state:
                st.session_state[key_title] = ""
            st.text_input("Título do Campo", key=key_title)

            if key_type not in st.session_state:
                st.session_state[key_type] = "texto"
            st.selectbox("Tipo do Campo", TIPOS_ELEMENTOS, key=key_type)

            # Obrigatório (não aplicável a paragrafo/rotulo logically but we leave visible)
            st.checkbox("Obrigatório", key=key_obrig)

            st.number_input("Largura", min_value=100, value=450, step=10, key=key_larg)

            if st.session_state.get(key_type) == "texto-area":
                st.number_input("Altura", min_value=50, value=100, step=10, key=key_alt)

            valor_paragrafo = ""
            if st.session_state.get(key_type) == "paragrafo":
                st.text_area("Valor do Parágrafo", key=f"add_par_{last_idx}")

            colunas = None
            dominios_temp = []
            if st.session_state.get(key_type) in ["grupoRadio", "grupoCheck", "comboBox", "comboFiltro"]:
                st.number_input("Colunas", min_value=1, max_value=5, value=1, key=key_cols)
                st.number_input("Quantidade de Domínios (itens)", min_value=1, max_value=50, value=2, key=key_qtd_dom)
                qtd_dom = int(st.session_state.get(key_qtd_dom, 0) or 0)
                for i in range(qtd_dom):
                    key_dom_i = f"add_dom_{last_idx}_{i}"
                    if key_dom_i not in st.session_state:
                        st.session_state[key_dom_i] = ""
                    st.text_input(f"Descrição Domínio {i+1}", key=key_dom_i)
                    val = st.session_state.get(key_dom_i, "") or ""
                    if val:
                        dominios_temp.append({"descricao": val, "valor": val.upper()})

            if st.button("Adicionar Campo", key=f"btn_add_field_{last_idx}"):
                campo = {
                    "titulo": st.session_state.get(key_title, "") or "",
                    "descricao": st.session_state.get(key_title, "") or "",
                    "tipo": st.session_state.get(key_type, "texto"),
                    "obrigatorio": bool(st.session_state.get(key_obrig, False)),
                    "largura": int(st.session_state.get(key_larg, 450) or 450),
                    "altura": int(st.session_state.get(key_alt, 100) or 100) if st.session_state.get(key_type) == "texto-area" else None,
                    "colunas": int(st.session_state.get(key_cols, 1) or 1) if st.session_state.get(key_type) in ["grupoRadio", "grupoCheck", "comboBox", "comboFiltro"] else None,
                    "dominios": dominios_temp,
                    "valor": st.session_state.get(f"add_par_{last_idx}", "") if st.session_state.get(key_type) == "paragrafo" else ""
                }
                st.session_state.formulario["secoes"][last_idx]["campos"].append(campo)
                try:
                    st.rerun()
                except Exception:
                    pass

# -------------------------
# Coluna direita: Pré-visualização (formulário renderizado)
# -------------------------
with col2:
    st.subheader("📋 Pré-visualização do Formulário")
    st.header(st.session_state.formulario.get("nome", ""))

    for s_idx, sec in enumerate(st.session_state.formulario.get("secoes", [])):
        # seções com bolinha preta e tamanho um pouco menor
        st.subheader(f"• {sec.get('titulo','')}")
        for c_idx, campo in enumerate(sec.get("campos", [])):
            tipo = campo.get("tipo", "texto")
            titulo = campo.get("titulo", "")
            label = f"{titulo} ({tipo})"
            preview_key = f"preview_{s_idx}_{c_idx}"

            # mapear tipos para widgets de preview
            if tipo == "texto":
                st.text_input(label, key=preview_key)
            elif tipo == "texto-area":
                h = int(campo.get("altura", 100) or 100)
                st.text_area(label, height=h, key=preview_key)
            elif tipo == "data":
                # data input; se preferir formatar default, ajustar
                try:
                    st.date_input(label, key=preview_key)
                except Exception:
                    st.text_input(label, key=preview_key)
            elif tipo == "moeda":
                st.text_input(label, key=preview_key)
            elif tipo in ["cpf", "cnpj", "email", "telefone"]:
                st.text_input(label, key=preview_key)
            elif tipo == "check":
                st.checkbox(label, key=preview_key)
            elif tipo in ["comboBox", "comboFiltro"]:
                st.selectbox(label, ["Opção 1", "Opção 2"], key=preview_key)
            elif tipo == "grupoRadio":
                st.radio(label, [it.get("descricao","") for it in campo.get("dominios",[]) or ["Opção 1","Opção 2"]], key=preview_key)
            elif tipo == "grupoCheck":
                st.multiselect(label, [it.get("descricao","") for it in campo.get("dominios",[]) or ["Opção 1","Opção 2"]], key=preview_key)
            elif tipo == "paragrafo":
                st.markdown(f"> {campo.get('valor','')}")
            elif tipo == "rotulo":
                st.markdown(f"*{campo.get('valor','')}*")
            else:
                st.text_input(label, key=preview_key)

# -------------------------
# Pré-visualização do XML no final
# -------------------------
st.markdown("---")
st.subheader("📑 Pré-visualização do XML")
xml_text = gerar_xml(st.session_state.formulario)
st.code(xml_text, language="xml")
