import streamlit as st
import xml.etree.ElementTree as ET

# =========================
# Funções auxiliares
# =========================
def gerar_chave_dominio(titulo, existentes):
    base = "".join(c for c in titulo.upper() if c.isalnum())[:20]
    chave = base
    i = 1
    while chave in existentes:
        chave = f"{base}{i}"
        i += 1
    return chave

def gerar_xml(formulario):
    root = ET.Element("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    dominios_elem = ET.SubElement(root, "dominios")
    chaves_dominios = set()

    elementos_elem = ET.SubElement(root, "elementos")

    for secao in formulario["secoes"]:
        secao_elem = ET.SubElement(elementos_elem, "elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": str(secao["largura"])
        })
        secao_elementos = ET.SubElement(secao_elem, "elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                ET.SubElement(secao_elementos, "elemento", {
                    "gxsi:type": "paragrafo",
                    "valor": campo["valor"],
                    "largura": str(campo["largura"])
                })
            elif campo["tipo"] in ["grupoRadio", "grupoCheck"]:
                chave = gerar_chave_dominio(campo["titulo"], chaves_dominios)
                chaves_dominios.add(chave)

                # Criar domínio
                dominio_elem = ET.SubElement(dominios_elem, "dominio", {
                    "gxsi:type": "dominioEstatico",
                    "chave": chave
                })
                for item in campo["dominios"]:
                    ET.SubElement(dominio_elem, "item", {
                        "gxsi:type": "dominioItemValor",
                        "descricao": item["descricao"],
                        "valor": item["valor"]
                    })

                # Criar campo referenciando o domínio
                ET.SubElement(secao_elementos, "elemento", {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "dominio": chave,
                    "colunas": "2" if campo["tipo"] == "grupoRadio" else "1",
                    "obrigatorio": str(campo["obrigatorio"]).lower()
                }).append(ET.Element("conteudo", {"gxsi:type": "valor"}))

            else:
                atributos = {
                    "gxsi:type": campo["tipo"],
                    "titulo": campo["titulo"],
                    "obrigatorio": str(campo["obrigatorio"]).lower(),
                    "largura": str(campo["largura"])
                }
                if campo["altura"]:
                    atributos["altura"] = str(campo["altura"])
                el = ET.SubElement(secao_elementos, "elemento", atributos)
                ET.SubElement(el, "conteudo", {"gxsi:type": "valor"})

    return ET.tostring(root, encoding="unicode")

# =========================
# Interface Streamlit
# =========================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "",
        "secoes": []
    }

st.title("📝 Construtor de Formulários GXSI")

# Nome e versão do formulário
st.session_state.formulario["nome"] = st.text_input("Nome do Formulário", st.session_state.formulario["nome"])
st.session_state.formulario["versao"] = st.text_input("Versão", st.session_state.formulario["versao"])

st.divider()

# Adicionar nova seção
with st.expander("➕ Adicionar Seção"):
    titulo_secao = st.text_input("Título da Seção")
    largura_secao = st.number_input("Largura da Seção", value=700)
    if st.button("Adicionar Seção"):
        if titulo_secao:
            st.session_state.formulario["secoes"].append({
                "titulo": titulo_secao,
                "largura": largura_secao,
                "campos": []
            })

# Listar seções e permitir adicionar campos
for i, secao in enumerate(st.session_state.formulario["secoes"]):
    st.subheader(f"📂 Seção: {secao['titulo']}")

    with st.expander(f"➕ Adicionar Campo em {secao['titulo']}"):
        tipo = st.selectbox("Tipo de Campo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"])
        titulo = st.text_input("Título do Campo (se aplicável)")
        obrigatorio = st.checkbox("Obrigatório?", value=False) if tipo != "paragrafo" else False
        largura = st.number_input("Largura", value=450)
        altura = st.number_input("Altura", value=100) if tipo == "texto-area" else None

        dominios = []
        if tipo in ["grupoRadio", "grupoCheck"]:
            st.markdown("### Domínios")
            qtd_dominios = st.number_input("Quantidade de Itens do Domínio", value=2, min_value=1, step=1)
            for d in range(qtd_dominios):
                desc = st.text_input(f"Descrição {d+1}", key=f"desc_{i}_{d}")
                val = st.text_input(f"Valor {d+1}", key=f"val_{i}_{d}")
                if desc and val:
                    dominios.append({"descricao": desc, "valor": val})

        valor_paragrafo = st.text_area("Texto do Parágrafo") if tipo == "paragrafo" else None

        if st.button(f"Adicionar Campo em {secao['titulo']}", key=f"btn_add_{i}"):
            campo = {
                "tipo": tipo,
                "titulo": titulo,
                "obrigatorio": obrigatorio,
                "largura": largura,
                "altura": altura,
                "valor": valor_paragrafo,
                "dominios": dominios
            }
            st.session_state.formulario["secoes"][i]["campos"].append(campo)

st.divider()
st.subheader("👀 Pré-visualização do Formulário")

if st.session_state.formulario["secoes"]:
    st.markdown(f"## 📄 {st.session_state.formulario['nome']} (v{st.session_state.formulario['versao']})")
    for secao in st.session_state.formulario["secoes"]:
        st.markdown(f"### 📂 {secao['titulo']}")
        for campo in secao["campos"]:
            if campo["tipo"] == "texto":
                st.text_input(campo["titulo"], placeholder="Digite aqui...")
            elif campo["tipo"] == "texto-area":
                st.text_area(campo["titulo"], placeholder="Digite aqui...", height=campo["altura"])
            elif campo["tipo"] == "paragrafo":
                st.markdown(campo["valor"])
            elif campo["tipo"] == "grupoRadio":
                opcoes = [item["descricao"] for item in campo["dominios"]]
                st.radio(campo["titulo"], opcoes)
            elif campo["tipo"] == "grupoCheck":
                opcoes = [item["descricao"] for item in campo["dominios"]]
                for opt in opcoes:
                    st.checkbox(opt)
else:
    st.info("Nenhuma seção adicionada ainda.")

st.divider()
st.subheader("⬇️ Exportar para XML")

if st.button("Gerar XML"):
    xml_str = gerar_xml(st.session_state.formulario)
    st.code(xml_str, language="xml")
