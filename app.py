import streamlit as st
import xml.etree.ElementTree as ET

# Inicializar sessão
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
        obrigatorio = st.checkbox("Obrigatório?", value=False)
        largura = st.number_input("Largura", value=450)
        altura = st.number_input("Altura (para texto-area)", value=100) if tipo == "texto-area" else None

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
