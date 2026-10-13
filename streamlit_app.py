import streamlit as st

st.set_page_config(
    page_title="Sistema de Calidad · María Almenara",
    page_icon="🍰",
    layout="centered",
)

# ── CSS personalizado ───────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Fondo general */
    .stApp { background-color: #FAF8F5; }

    /* Ocultar decoración del sidebar en portada */
    [data-testid="stSidebarNav"] { display: none; }

    /* Tarjetas de módulo */
    .modulo-card {
        background: #FFFFFF;
        border: 1px solid #E8E2DA;
        border-radius: 12px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 0.75rem;
        transition: box-shadow 0.15s ease;
    }
    .modulo-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .modulo-icon { font-size: 1.8rem; margin-bottom: 0.3rem; }
    .modulo-titulo {
        font-size: 1.05rem;
        font-weight: 700;
        color: #2D2926;
        margin: 0 0 0.2rem 0;
    }
    .modulo-desc {
        font-size: 0.85rem;
        color: #7A6E65;
        margin: 0;
    }
    /* Encabezado portada */
    .portada-header {
        text-align: center;
        padding: 2rem 0 1.5rem 0;
    }
    .portada-logo { font-size: 2.8rem; }
    .portada-titulo {
        font-size: 1.6rem;
        font-weight: 800;
        color: #2D2926;
        margin: 0.4rem 0 0.2rem 0;
        letter-spacing: -0.02em;
    }
    .portada-subtitulo {
        font-size: 0.9rem;
        color: #9C8F85;
        margin: 0;
    }
    .seccion-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #C4A882;
        margin: 1.4rem 0 0.6rem 0;
    }
    /* Botón de módulo — ancho completo */
    div[data-testid="stButton"] > button {
        width: 100%;
        background-color: #C4A882;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 0.45rem 1rem;
        font-size: 0.88rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        cursor: pointer;
        transition: background-color 0.15s ease;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #B0936D;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Encabezado ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="portada-header">
        <div class="portada-logo">🍰</div>
        <p class="portada-titulo">Sistema de Calidad</p>
        <p class="portada-subtitulo">María Almenara · Control de Procesos y Liberación</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Módulos de registro ─────────────────────────────────────────────────────
st.markdown('<p class="seccion-label">Registros de proceso</p>', unsafe_allow_html=True)

# Módulo 1 — Producto Terminado
col1, col2 = st.columns([3, 1], vertical_alignment="center")
with col1:
    st.markdown(
        """
        <div class="modulo-card">
            <div class="modulo-icon">📦</div>
            <p class="modulo-titulo">Producto Terminado (PT)</p>
            <p class="modulo-desc">Control de calidad y liberación de producto terminado</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    if st.button("Abrir →", key="btn_pt"):
        st.switch_page("pages/app-producto-terminado.py")

# Módulo 2 — Proceso Interno / B2B
col1, col2 = st.columns([3, 1], vertical_alignment="center")
with col1:
    st.markdown(
        """
        <div class="modulo-card">
            <div class="modulo-icon">🔬</div>
            <p class="modulo-titulo">Proceso Interno (PI / B2B)</p>
            <p class="modulo-desc">Control en proceso para líneas internas y B2B</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    if st.button("Abrir →", key="btn_pi"):
        st.switch_page("pages/app-procesos-b2b.py")

# Módulo 3 — Cocina Dulce
col1, col2 = st.columns([3, 1], vertical_alignment="center")
with col1:
    st.markdown(
        """
        <div class="modulo-card">
            <div class="modulo-icon">🥄</div>
            <p class="modulo-titulo">Cocina Dulce</p>
            <p class="modulo-desc">Registro de calidad para producción de cocina dulce</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    if st.button("Abrir →", key="btn_cocina"):
        st.switch_page("pages/app-cocina-dulce.py")

# ── Módulos de desinfección ─────────────────────────────────────────────────
st.markdown('<p class="seccion-label">Control de desinfección</p>', unsafe_allow_html=True)

# Módulo 4 — Desinfección Huevo
col1, col2 = st.columns([3, 1], vertical_alignment="center")
with col1:
    st.markdown(
        """
        <div class="modulo-card">
            <div class="modulo-icon">🥚</div>
            <p class="modulo-titulo">Desinfección de Huevo</p>
            <p class="modulo-desc">Registro de lavado, PPM de desinfectante y supervisión</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    if st.button("Abrir →", key="btn_huevo"):
        st.switch_page("pages/app-desinfeccion-huevo.py")

# Módulo 5 — Desinfección Naranja
col1, col2 = st.columns([3, 1], vertical_alignment="center")
with col1:
    st.markdown(
        """
        <div class="modulo-card">
            <div class="modulo-icon">🍊</div>
            <p class="modulo-titulo">Desinfección de Naranja</p>
            <p class="modulo-desc">Registro de lavado, PPM de desinfectante y supervisión</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    if st.button("Abrir →", key="btn_naranja"):
        st.switch_page("pages/app-desinfeccion-naranja.py")

# ── Pie ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("MA · Sistema Digital de Calidad · v1.0")
