import streamlit as st
import xml.etree.ElementTree as ET
import re

# ===============================
# Funções auxiliares
# ===============================

def gerar_chave(titulo, usadas):
    """Gera chave única para domínio baseado no título (máx 20 chars)."""
    base = re.sub(r'\W+', '', titulo)[:20]
    chave = base
    contador = 1
    while chave in usadas:
        chave = f"{base}{contador}"
        contador += 1
    usadas.add(chave)
    return chave

def criar_elemento(tag, atributos=None, conteudo=None):
    """Cria elemento XML com atributos e conteúdo opcional."""
    elem = ET.Element(tag)
    if atributos:
        for k, v in atributos.items():
            elem.set(k, str(v))
    if conteudo is not None:
        elem.text = conteudo
    return elem

def gerar_xml(formulario):
    """Gera XML GXSI a partir do dicionário do formulário."""
    ns = {"gxsi": "http://www.w3.org/2001/XMLSchema-instance"}
    ET.register_namespace("gxsi", ns["gxsi"])

    root = criar_elemento("gxsi:formulario", {
        "xmlns:gxsi": ns["gxsi"],
        "nome": formulario["nome"],
        "versao": formulario["versao"]
    })

    elementos_root = criar_elemento("elementos")
    root.append(elementos_root)

    # armazenar chaves de domínios
    chaves_usadas = set()
    dominios_root = criar_elemento("dominios")

    for secao in formulario["secoes"]:
        secao_elem = criar_elemento("elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": "500"
        })

        elementos_secao = criar_elemento("elementos")

        for campo in secao["campos"]:
            atributos = {
                "gxsi:type": campo["tipo"],
                "titulo": campo["titulo"],
                "obrigatorio": str(campo["obrigatorio"]).lower(),
                "largura": str(campo["largura"])
            }

            if campo["altura"]:
                atributos["altura"] = str(campo["altura"])
            if campo["tamanhoMaximo"]:
                atributos["tamanhoMaximo"] = str(campo["tamanhoMaximo"])

            campo_elem = criar_elemento("elemento", atributos)
            conteudo_elem = criar_elemento("conteudo", {"gxsi:type": "valor"})
            campo_elem.append(conteudo_elem)

            # grupoRadio e grupoCheck -> associar domínio
            if campo["tipo"] in ["grupoRadio", "grupoCheck"] and campo["dominios"]:
                chave = gerar_chave(campo["titulo"], chaves_usadas)
                campo_elem.set("dominio", chave)

                dominio_elem = criar_elemento("dominio", {"chave": chave})
                for valor in campo["dominios"]:
                    valor_elem = criar_elemento("valor", None, valor)
                    dominio_elem.append(valor_elem)
                dominios_root.append(dominio_elem)

            elementos_secao.append(campo_elem)

        secao_elem.append(elementos_secao)
        elementos_root.append(secao_elem)

    # adicionar dominios apenas se existirem
    if list(dominios_root):
        root.append(dominios_root)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

# ===============================
# Interface Streamlit
# ===============================

st.title("📝 Construtor de Formulários GXSI")

# Dados do formulário
st.subheader("📄 Informações do Formulário")
form_nome = st.text_input("Nome do Formulário", "Formulário Teste")
form_versao = st.text_input("Versão", "1.0")

if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": form_nome,
        "versao": form_versao,
        "secoes": []
    }

# Adicionar seções
st.subheader("➕ Adicionar Seções")
secao_titulo = st.text_input("Título da Seção")
if st.button("Adicionar Seção") and secao_titulo:
    st.session_state.formulario["secoes"].append({"titulo": secao_titulo, "campos": []})

# Listar seções e campos
for i, secao in enumerate(st.session_state.formulario["secoes"]):
    st.markdown(f"### 📌 Seção: {secao['titulo']}")

    # Adicionar campos
    with st.expander("➕ Adicionar Campo"):
        campo_titulo = st.text_input(f"Título do Campo (Seção {i+1})", key=f"titulo_{i}")
        campo_tipo = st.selectbox(
            "Tipo do Campo",
            ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"],
            key=f"tipo_{i}"
        )
        obrigatorio = st.checkbox("Obrigatório", value=False, key=f"obrigatorio_{i}")
        largura = st.number_input("Largura", value=450, key=f"largura_{i}")
        altura = st.number_input("Altura (se aplicável)", value=0, key=f"altura_{i}")
        tamanho_max = st.number_input("Tamanho Máximo (se aplicável)", value=0, key=f"tamanho_{i}")

        dominios = []
        if campo_tipo in ["grupoRadio", "grupoCheck"]:
            dominios = st.text_area("Domínios (um por linha)", key=f"dominios_{i}")
            dominios = [d.strip() for d in dominios.split("\n") if d.strip()]

        if st.button("Salvar Campo", key=f"salvar_{i}") and campo_titulo:
            secao["campos"].append({
                "titulo": campo_titulo,
                "tipo": campo_tipo,
                "obrigatorio": obrigatorio,
                "largura": largura,
                "altura": altura if altura > 0 else None,
                "tamanhoMaximo": tamanho_max if tamanho_max > 0 else None,
                "dominios": dominios
            })

    # Listar campos já adicionados
    for campo in secao["campos"]:
        st.write(f"- {campo['titulo']} ({campo['tipo']})")

# Exportar XML
if st.button("📤 Gerar XML"):
    st.session_state.formulario["nome"] = form_nome
    st.session_state.formulario["versao"] = form_versao
    xml_saida = gerar_xml(st.session_state.formulario)
    st.code(xml_saida, language="xml")
