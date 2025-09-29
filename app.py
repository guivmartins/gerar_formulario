import streamlit as st

# ==============================
# Inicialização do estado
# ==============================
if "formulario" not in st.session_state:
    st.session_state.formulario = {
        "nome": "",
        "versao": "",
        "secoes": []
    }

if "titulo_secao" not in st.session_state:
    st.session_state["titulo_secao"] = ""

# Funções utilitárias
def adicionar_secao(titulo):
    st.session_state.formulario["secoes"].append({
        "titulo": titulo,
        "campos": []
    })

def adicionar_campo(secao_idx, campo):
    st.session_state.formulario["secoes"][secao_idx]["campos"].append(campo)

# ==============================
# Layout
# ==============================
st.title("📝 Construtor de Formulários GXSI")

# Nome e versão do formulário
st.session_state.formulario["nome"] = st.text_input(
    "Nome do Formulário", st.session_state.formulario["nome"]
)
st.session_state.formulario["versao"] = st.text_input(
    "Versão", st.session_state.formulario["versao"]
)

st.divider()

# Adicionar nova seção
with st.expander("➕ Adicionar Seção"):
    titulo_secao = st.text_input("Título da Seção", key="titulo_secao")
    if st.button("Adicionar Seção"):
        if titulo_secao.strip():
            adicionar_secao(titulo_secao.strip())
            st.success(f"Seção '{titulo_secao}' adicionada com sucesso!")
            st.session_state["titulo_secao"] = ""  # limpa o campo

# Mostrar as seções existentes
for i, secao in enumerate(st.session_state.formulario["secoes"]):
    with st.expander(f"📂 {secao['titulo']}"):
        st.markdown(f"**Seção {i+1}: {secao['titulo']}**")

        # Adicionar campos nesta seção
        with st.form(key=f"form_add_campo_{i}"):
            tipo = st.selectbox(
                "Tipo do Campo",
                ["texto", "texto-area", "paragrafo", "grupoRadio", "grupoCheck"],
                key=f"tipo_{i}"
            )
            titulo = st.text_input("Título do Campo", key=f"titulo_{i}")
            obrigatorio = st.checkbox("Obrigatório", key=f"obrigatorio_{i}")
            largura = st.number_input(
                "Largura", min_value=100, max_value=1000, value=300, step=10, key=f"largura_{i}"
            )
            altura = st.number_input(
                "Altura", min_value=50, max_value=1000, value=100, step=10, key=f"altura_{i}"
            )
            tamanho_maximo = st.number_input(
                "Tamanho Máximo (opcional)", min_value=0, value=0, step=1, key=f"tammax_{i}"
            )

            dominios = []
            if tipo in ["grupoRadio", "grupoCheck"]:
                qtd_dom = st.number_input(
                    "Quantos domínios?", min_value=1, max_value=20, value=2, key=f"qtd_dom_{i}"
                )
                for d in range(qtd_dom):
                    desc = st.text_input(f"Descrição Domínio {d+1}", key=f"desc_{i}_{d}")
                    val = st.text_input(f"Valor Domínio {d+1}", key=f"val_{i}_{d}")
                    if desc and val:
                        dominios.append({"descricao": desc, "valor": val})

            submit_campo = st.form_submit_button("Adicionar Campo")
            if submit_campo:
                novo_campo = {
                    "tipo": tipo,
                    "titulo": titulo,
                    "obrigatorio": obrigatorio,
                    "largura": largura,
                    "altura": altura,
                    "tamanhoMaximo": tamanho_maximo if tamanho_maximo > 0 else None,
                    "dominios": dominios
                }
                adicionar_campo(i, novo_campo)
                st.success(f"Campo '{titulo}' adicionado à seção '{secao['titulo']}'")

        # Listar os campos da seção
        if secao["campos"]:
            st.write("📑 Campos desta seção:")
            for campo in secao["campos"]:
                st.markdown(f"- **{campo['titulo']}** ({campo['tipo']})")

# ==============================
# Pré-visualização dinâmica
# ==============================
st.divider()
st.subheader("👀 Pré-visualização do Formulário")

if st.session_state.formulario["secoes"]:
    st.markdown(f"## {st.session_state.formulario['nome']} (v{st.session_state.formulario['versao']})")
    for secao in st.session_state.formulario["secoes"]:
        st.markdown(f"### 📂 {secao['titulo']}")
        for campo in secao["campos"]:
            if campo["tipo"] == "texto":
                st.text_input(campo["titulo"], placeholder="Digite aqui...", key=f"pv_{campo['titulo']}")
            elif campo["tipo"] == "texto-area":
                st.text_area(campo["titulo"], placeholder="Digite aqui...", height=campo["altura"], key=f"pv_{campo['titulo']}")
            elif campo["tipo"] == "paragrafo":
                st.markdown(campo["titulo"])
            elif campo["tipo"] == "grupoRadio":
                opcoes = [item["descricao"] for item in campo["dominios"]]
                st.radio(campo["titulo"], opcoes, key=f"pv_{campo['titulo']}")
            elif campo["tipo"] == "grupoCheck":
                opcoes = [item["descricao"] for item in campo["dominios"]]
                for opt in opcoes:
                    st.checkbox(opt, key=f"pv_{campo['titulo']}_{opt}")
else:
    st.info("Nenhuma seção adicionada ainda.")

# Debug JSON
st.divider()
st.subheader("📋 Estrutura Atual do Formulário (JSON)")
st.json(st.session_state.formulario)
