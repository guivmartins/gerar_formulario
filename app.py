import streamlit as st
import xml.etree.ElementTree as ET
import re

# ==========================
# Funções auxiliares
# ==========================

def criar_elemento(tag, atributos=None, texto=None):
    elem = ET.Element(tag)
    if atributos:
        for k, v in atributos.items():
            elem.set(k, v)
    if texto:
        elem.text = texto
    return elem

def gerar_chave(titulo, chaves_usadas):
    chave_base = re.sub(r'\W+', '', titulo.strip().lower())[:20]
    chave = chave_base
    contador = 1
    while chave in chaves_usadas:
        chave = f"{chave_base}{contador}"
        contador += 1
    chaves_usadas.add(chave)
    return chave

def gerar_xml(formulario_nome, formulario_versao, secoes):
    root = criar_elemento("gxsi:formulario", {
        "xmlns:gxsi": "http://www.w3.org/2001/XMLSchema-instance",
        "nome": formulario_nome,
        "versao": formulario_versao
    })

    elementos_root = criar_elemento("elementos")
    dominios_root = criar_elemento("dominios")
    chaves_usadas = set()

    for secao in secoes:
        secao_elem = criar_elemento("elemento", {
            "gxsi:type": "seccao",
            "titulo": secao["titulo"],
            "largura": "500"
        })

        elementos_secao = criar_elemento("elementos")

        for campo in secao["campos"]:
            if campo["tipo"] == "paragrafo":
                # Caso especial: não tem título/obrigatório, mas tem valor
                atributos = {
                    "gxsi:type": "paragrafo",
                    "valor": campo["titulo"],  # usa o texto digitado
                    "largura": str(campo["largura"])
                }
                campo_elem = criar_elemento("elemento", atributos)

            else:
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

                # Domínios
                if campo["tipo"] in ["grupoRadio", "grupoCheck"] and campo["dominios"]:
                    chave = gerar_chave(campo["titulo"], chaves_usadas)
                    campo_elem.set("dominio", chave)

                    dominio_elem = criar_elemento("dominio", {
                        "gxsi:type": "dominioEstatico",
                        "chave": chave
                    })

                    for valor in campo["dominios"]:
                        valor_formatado = re.sub(r'\W+', '_', valor.strip().upper())
                        item_elem = criar_elemento("item", {
                            "gxsi:type": "dominioItemValor",
                            "descricao": valor.strip(),
                            "valor": valor_formatado
                        })
                        dominio_elem.append(item_elem)

                    dominios_root.append(dominio_elem)

            elementos_secao.append(campo_elem)

        secao_elem.append(elementos_secao)
        elementos_root.append(secao_elem)

    root.append(elementos_root)
    if list(dominios_root):
        root.append(dominios_root)

    return ET.tostring(root, encoding="unicode")

# ==========================
# Interface Streamlit
# ==========================

st.title("Gerador de Formulários GXSI XML")

formulario_nome = st.text_input("Nome do Formulário")
formulario_versao = st.text_input("Versão", "1.0")

secoes = []
num_secoes = st.number_input("Quantas seções deseja adicionar?", min_value=1, max_value=20, value=1)

for i in range(num_secoes):
    st.subheader(f"Seção {i+1}")
    secao_titulo = st.text_input(f"Título da Seção {i+1}", key=f"secao_titulo_{i}")
    campos = []
    num_campos = st.number_input(f"Quantos campos na seção {i+1}?", min_value=1, max_value=20, value=1, key=f"num_campos_{i}")

    for j in range(num_campos):
        st.markdown(f"**Campo {j+1}**")
        tipo = st.selectbox("Tipo", ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"],
                            key=f"tipo_{i}_{j}")
        titulo = st.text_input("Título", key=f"titulo_{i}_{j}")
        obrigatorio = st.checkbox("Obrigatório", value=False, key=f"obrigatorio_{i}_{j}")
        largura = st.number_input("Largura", min_value=100, max_value=1000, value=300, key=f"largura_{i}_{j}")
        altura = st.number_input("Altura", min_value=0, max_value=1000, value=0, key=f"altura_{i}_{j}")
        tamanhoMaximo = st.number_input("Tamanho Máximo", min_value=0, max_value=500, value=0, key=f"tamanhoMaximo_{i}_{j}")

        dominios = []
        if tipo in ["grupoRadio", "grupoCheck"]:
            num_dominios = st.number_input("Quantos itens no domínio?", min_value=1, max_value=20, value=2, key=f"num_dominios_{i}_{j}")
            for d in range(num_dominios):
                valor_dom = st.text_input(f"Item {d+1}", key=f"dominio_{i}_{j}_{d}")
                dominios.append(valor_dom)

        campos.append({
            "tipo": tipo,
            "titulo": titulo,
            "obrigatorio": obrigatorio,
            "largura": largura,
            "altura": altura,
            "tamanhoMaximo": tamanhoMaximo,
            "dominios": dominios
        })

    secoes.append({
        "titulo": secao_titulo,
        "campos": campos
    })

if st.button("Gerar XML"):
    xml_output = gerar_xml(formulario_nome, formulario_versao, secoes)
    st.code(xml_output, language="xml")
