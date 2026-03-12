"""
NBR 6118:2023 — Calculadora de Estruturas de Concreto Armado
Aplicação Streamlit com base na norma ABNT NBR 6118:2023
"""

import streamlit as st
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json as _json
import os as _os

# ─── IMPORTAÇÃO DO MÓDULO SKETCHUP (opcional) ─────────────────────────────────
try:
    from report_generator import gerar_relatorio_pdf as _gerar_pdf
    _HAS_REPORT = True
except ImportError:
    _HAS_REPORT = False

try:
    from json_importer import JSONImporter as _JSONImporter
    _HAS_IMPORTER = True
except ImportError:
    _HAS_IMPORTER = False

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NBR 6118:2023 | Concreto Armado",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

/* Main background */
.stApp {
    background: #0f1117;
    color: #e8eaf0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #161b27;
    border-right: 1px solid #2a3040;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #1a2235 0%, #0d1520 100%);
    border: 1px solid #2a3a5c;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(45deg, transparent 60%, rgba(59, 130, 246, 0.05) 100%);
}
.main-header h1 {
    color: #60a5fa;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: #7a8ba8;
    font-size: 0.9rem;
    margin: 0;
}
.badge {
    display: inline-block;
    background: #1d3461;
    color: #60a5fa;
    border: 1px solid #2a4a7f;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.6rem;
}

/* Result cards */
.result-card {
    background: #161b27;
    border: 1px solid #2a3a5c;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin: 0.5rem 0;
}
.result-card.success {
    border-left: 4px solid #22c55e;
    background: #0f1e15;
}
.result-card.warning {
    border-left: 4px solid #f59e0b;
    background: #1c1508;
}
.result-card.error {
    border-left: 4px solid #ef4444;
    background: #1c0a0a;
}
.result-card.info {
    border-left: 4px solid #3b82f6;
    background: #0a1222;
}

.result-title {
    font-size: 0.78rem;
    color: #7a8ba8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.3rem;
}
.result-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #e8eaf0;
    font-family: 'JetBrains Mono', monospace;
}
.result-unit {
    font-size: 0.85rem;
    color: #7a8ba8;
    margin-left: 4px;
}
.result-status {
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 0.3rem;
}

/* Formula box */
.formula-box {
    background: #0d111a;
    border: 1px solid #2a3040;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #7dd3fc;
    margin: 0.6rem 0;
    line-height: 1.7;
}

/* Section divider */
.section-tag {
    background: #1a2235;
    border: 1px solid #2a3a5c;
    color: #60a5fa;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    display: inline-block;
    margin-bottom: 0.8rem;
}

/* Streamlit overrides */
.stSelectbox > label, .stNumberInput > label, .stSlider > label {
    color: #9aaec8 !important;
    font-size: 0.85rem !important;
}
.stButton > button {
    background: linear-gradient(135deg, #1e40af, #1d4ed8);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* Tabs */
[data-baseweb="tab-list"] {
    background: #161b27;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
[data-baseweb="tab"] {
    border-radius: 7px;
    color: #7a8ba8;
    font-weight: 500;
}
[aria-selected="true"] {
    background: #1e40af !important;
    color: white !important;
}

/* Warning / success messages */
.stSuccess { background: #0f2318 !important; border: 1px solid #22c55e !important; }
.stError { background: #1c0a0a !important; border: 1px solid #ef4444 !important; }
.stWarning { background: #1c1508 !important; border: 1px solid #f59e0b !important; }
.stInfo { background: #0a1222 !important; border: 1px solid #3b82f6 !important; }

hr { border-color: #2a3040; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTES E DADOS DA NORMA ─────────────────────────────────────────────

CONCRETOS = {
    "C20": {"fck": 20, "fctm": 2.21, "Eci": 25.0, "Ecs": 21.3},
    "C25": {"fck": 25, "fctm": 2.56, "Eci": 28.0, "Ecs": 23.8},
    "C30": {"fck": 30, "fctm": 2.90, "Eci": 30.7, "Ecs": 26.1},
    "C35": {"fck": 35, "fctm": 3.21, "Eci": 33.0, "Ecs": 28.1},
    "C40": {"fck": 40, "fctm": 3.51, "Eci": 35.5, "Ecs": 30.2},
    "C45": {"fck": 45, "fctm": 3.80, "Eci": 37.7, "Ecs": 32.1},
    "C50": {"fck": 50, "fctm": 4.07, "Eci": 39.8, "Ecs": 33.8},
    "C55": {"fck": 55, "fctm": 4.21, "Eci": 41.7, "Ecs": 35.4},
    "C60": {"fck": 60, "fctm": 4.35, "Eci": 43.6, "Ecs": 37.0},
    "C70": {"fck": 70, "fctm": 4.61, "Eci": 47.2, "Ecs": 40.1},
    "C80": {"fck": 80, "fctm": 4.86, "Eci": 50.7, "Ecs": 43.1},
    "C90": {"fck": 90, "fctm": 5.10, "Eci": 54.1, "Ecs": 46.0},
}

ACOS = {
    "CA-25": {"fyk": 250, "Es": 210000},
    "CA-50": {"fyk": 500, "Es": 210000},
    "CA-60": {"fyk": 600, "Es": 210000},
}

BARRAS_MM = [6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 22.0, 25.0, 32.0, 40.0]

# Tabela 7.3 — Cobrimento nominal mínimo (mm) por classe de agressividade e tipo
COBRIMENTO = {
    "I":   {"laje": 20, "viga_pilar": 25, "fundacao": 30},
    "II":  {"laje": 25, "viga_pilar": 30, "fundacao": 40},
    "III": {"laje": 35, "viga_pilar": 40, "fundacao": 50},
    "IV":  {"laje": 45, "viga_pilar": 50, "fundacao": 65},
}

# Tabela 6.1 — Classes de agressividade ambiental
AGRESSIVIDADE = {
    "I — Fraca":   {"classe": "I",  "risco": "Insignificante", "ambiente": "Rural seco, submerso"},
    "II — Moderada":  {"classe": "II", "risco": "Pequeno",      "ambiente": "Urbano, submerso não poluído"},
    "III — Forte": {"classe": "III","risco": "Grande",         "ambiente": "Marinha, industrial, respingos"},
    "IV — Muito Forte":{"classe": "IV", "risco": "Elevado",    "ambiente": "Industrial especial, imersão em esgoto"},
}

# Coeficientes de ponderação (Tab. 12.1)
GAMMA = {
    "gc_normal": 1.4,
    "gs_normal": 1.15,
    "gc_especial": 1.2,
    "gs_especial": 1.15,
    "gc_excepcional": 1.2,
    "gs_excepcional": 1.0,
    "gf_normal_perm": 1.4,
    "gf_normal_var": 1.4,
    "gf_especial": 1.3,
}

# ─── FUNÇÕES AUXILIARES ───────────────────────────────────────────────────────

def alpha_c_val(fck_mpa: float) -> float:
    """Parâmetro αc de redução da resistência do concreto (§ 17.2.2e)"""
    if fck_mpa <= 50:
        return 0.85
    else:
        return 0.85 * (1.0 - (fck_mpa - 50) / 200)

def fcd(fck_mpa: float, combinacao: str = "normal") -> float:
    """Resistência de cálculo do concreto à compressão (Seção 12.3.3)"""
    gc = GAMMA[f"gc_{combinacao}"]
    return alpha_c_val(fck_mpa) * fck_mpa / gc

def fctk_inf(fck_mpa: float) -> float:
    """Resistência característica inferior à tração (Seção 8.2.5)"""
    if fck_mpa <= 50:
        fctm = 0.3 * fck_mpa ** (2/3)
    else:
        fctm = 2.12 * math.log(1 + 0.1 * (fck_mpa + 8))
    return 0.7 * fctm

def fctd_val(fck_mpa: float, combinacao: str = "normal") -> float:
    """Resistência de cálculo à tração"""
    gc = GAMMA[f"gc_{combinacao}"]
    return fctk_inf(fck_mpa) / gc

def fyd_val(fyk_mpa: float, combinacao: str = "normal") -> float:
    """Resistência de cálculo do aço"""
    gs = GAMMA[f"gs_{combinacao}"]
    return fyk_mpa / gs

def area_barra(phi_mm: float) -> float:
    """Área da seção transversal de uma barra (cm²)"""
    return math.pi * (phi_mm / 10) ** 2 / 4

def Ecs_calc(fck_mpa: float, alpha_g: float = 1.0) -> float:
    """Módulo de elasticidade secante do concreto (Seção 8.2.8)
    αg: 1.2 basalto/diabásio | 1.0 granito/gnaisse | 0.9 calcário | 0.7 arenito
    """
    if fck_mpa <= 50:
        Eci = alpha_g * 5600 * math.sqrt(fck_mpa)
    else:
        Eci = alpha_g * 21.5e3 * (fck_mpa / 10 + 1.25) ** (1/3)
    alpha_i = min(0.8 + 0.2 * fck_mpa / 80, 1.0)
    return alpha_i * Eci

def epsilon_c2(fck_mpa: float) -> float:
    """Deformação máxima do concreto (diagrama parábola-retângulo)"""
    return 2.0 + 0.085 * (fck_mpa - 50) ** 0.53 if fck_mpa > 50 else 2.0  # ‰

def epsilon_cu(fck_mpa: float) -> float:
    """Deformação última do concreto"""
    return 2.6 + 35 * ((90 - fck_mpa) / 100) ** 4 if fck_mpa > 50 else 3.5  # ‰


# ─── SESSION STATE ─────────────────────────────────────────────────────────────
_SK_INIT = {
    "sk_data": None, "sk_elements": [], "sk_sel_idx": 0, "sk_applied": False,
    "v_bw": 25.0, "v_h": 60.0, "v_cnom": 30.0,
    "v_phi_long_idx": 5, "v_phi_est_idx": 1, "v_Md": 150.0,
    "c_bw": 25.0, "c_d": 55.0, "c_Vd": 120.0, "c_As": 8.04, "c_ramos_idx": 0,
    "p_b": 30.0, "p_h": 40.0, "p_Le": 3.6,
    "p_Nd": 800.0, "p_Mdx": 60.0, "p_Mdy": 30.0,
    "d_bw": 25.0, "d_h": 60.0, "d_d": 55.0,
    "d_L": 6.0, "d_As": 8.04, "d_Asl": 0.0, "d_Mk": 80.0,
    "f_bw": 25.0, "f_h": 60.0, "f_d": 55.0,
    "f_As": 8.04, "f_n": 4, "f_Ms": 80.0,
    "sk_concreto": None, "sk_aco": None, "sk_combinacao": None, "sk_agress_key": None,
    # Solver 3D (F6)
    "solver_results": None, "solver_floors": None, "solver_load_totals": None,
    "solver_json_data": None, "solver_ran": False, "solver_error": None,
}
for _k, _v in _SK_INIT.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

_BARRAS_MM_ALL = [6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 22.0, 25.0, 32.0, 40.0]

def _phi_idx(phi_mm: float) -> int:
    return next((i for i, x in enumerate(_BARRAS_MM_ALL) if abs(x - phi_mm) < 0.5), 5)

def _apply_element(el: dict):
    g = el.get("geometria", {})
    p = el.get("parametros_calculo", {})
    tipo = el.get("tipo", "")
    c_nom = float(p.get("cobrimento_nominal", 30.0))
    if tipo == "viga":
        bw  = float(g.get("largura", 25.0))
        h   = float(g.get("altura",  60.0))
        phi_e = float(p.get("phi_estribo", 8.0))
        phi_l = float(p.get("phi_longitudinal", 20.0))
        d = max(h - c_nom/10 - phi_e/10 - phi_l/20, 10.0)
        Md = float(p.get("momento_fletor_Md", 0.0))
        Vd = float(p.get("forca_cortante_Vd", 0.0))
        As = float(p.get("as_tracao_els", 0.0)) or float(p.get("as_fornecida_flexao", 0.0))
        Mk = float(p.get("momento_caracteristico_Mk", 0.0))
        Ms = float(p.get("momento_servico_Ms", 0.0))
        n_b = int(p.get("num_barras_fissuras", 4))
        ramos = int(p.get("num_ramos_estribo", 2))
        st.session_state.update({
            "v_bw": bw, "v_h": h, "v_cnom": c_nom,
            "v_phi_long_idx": _phi_idx(phi_l), "v_phi_est_idx": _phi_idx(phi_e), "v_Md": Md,
            "c_bw": bw, "c_d": d, "c_Vd": Vd, "c_As": max(As, 0.5),
            "c_ramos_idx": max(ramos - 2, 0),
            "d_bw": bw, "d_h": h, "d_d": d, "d_As": max(As, 0.5), "d_Mk": Mk,
            "f_bw": bw, "f_h": h, "f_d": d, "f_As": max(As, 0.5), "f_n": n_b, "f_Ms": Ms,
        })
    elif tipo == "pilar":
        b  = float(g.get("largura",     30.0))
        h  = float(g.get("altura",      40.0))
        Le = float(g.get("comprimento", 3.6))
        st.session_state.update({
            "p_b": b, "p_h": h, "p_Le": Le,
            "p_Nd": float(p.get("forca_normal_Nd", 0.0)),
            "p_Mdx": float(p.get("momento_Mdx", 0.0)),
            "p_Mdy": float(p.get("momento_Mdy", 0.0)),
        })
    st.session_state["sk_applied"] = True

def _batch_calc(el, fck_v, fyd_loc, fcd_loc, fctd_loc):
    g = el.get("geometria", {}); p = el.get("parametros_calculo", {})
    tipo = el.get("tipo", ""); checks = []; nome = el.get("nome","?")
    try:
        if tipo == "viga":
            bw = float(g.get("largura",25.0)); h = float(g.get("altura",60.0))
            c  = float(p.get("cobrimento_nominal",30.0))
            pe = float(p.get("phi_estribo",8.0)); pl = float(p.get("phi_longitudinal",20.0))
            d  = max(h - c/10 - pe/10 - pl/20, 10.0)
            Md = float(p.get("momento_fletor_Md",0.0)); Vd = float(p.get("forca_cortante_Vd",0.0))
            if Md > 0:
                b_m = bw/100; d_m = d/100
                mu = Md*1e3/(b_m*d_m**2*fcd_loc*1e6)
                xi_lim = 0.45 if fck_v<=50 else 0.35
                disc = 0.85**2 - 4*0.34*mu
                if disc >= 0:
                    xd = (0.85 - math.sqrt(disc))/(2*0.34)
                    z  = d_m*(1-0.4*xd)
                    fctm_v = 0.3*fck_v**(2/3) if fck_v<=50 else 2.12*math.log(1+0.1*(fck_v+8))
                    As_req = max(Md*1e3/(z*fyd_loc*1e6)*1e4, max(0.26*fctm_v/500,0.0013)*bw*d)
                    checks.append({"V": "ELU Flexão", "R": f"As≥{As_req:.2f}cm² | x/d={xd:.3f}", "L": f"x/d≤{xi_lim}", "ok": xd<=xi_lim})
                else:
                    checks.append({"V": "ELU Flexão", "R": "μ inválido (disc<0)", "L":"—","ok":False})
            if Vd > 0:
                av2 = 1 - fck_v/250
                Vrd2 = 0.27*av2*fcd_loc*bw*d*1e4/1e6
                Vc   = 0.6*fctd_loc*bw*d*1e4/1e6
                checks.append({"V":"ELU Cisalh.","R":f"Vd={Vd:.1f}kN Vc={Vc:.1f}kN","L":f"Vrd2={Vrd2:.1f}kN","ok":Vd<=Vrd2})
        elif tipo == "pilar":
            b=float(g.get("largura",30)); h=float(g.get("altura",40)); Le=float(g.get("comprimento",3.6))
            Ac=b*h; ix=b/math.sqrt(12); iy=h/math.sqrt(12)
            lmax=max(Le*100/ix, Le*100/iy)
            Nd=float(p.get("forca_normal_Nd",0.0)); Nrd=0.85*fcd_loc*Ac/10
            checks.append({"V":"Esbeltez λ","R":f"λ={lmax:.1f}","L":"λ≤90","ok":lmax<=90})
            checks.append({"V":"Compressão","R":f"Nd={Nd:.0f}kN Nrd={Nrd:.0f}kN","L":"Nd≤Nrd","ok":Nd<=Nrd})
    except Exception as exc:
        checks.append({"V":"Erro","R":str(exc),"L":"—","ok":False})
    status = "❌" if any(not c["ok"] for c in checks) else "✅"
    return {"nome": nome, "tipo": tipo.upper(), "status": status, "checks": checks}

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding:1rem 0 0.5rem 0'>
        <span style='color:#60a5fa;font-size:1.1rem;font-weight:700'>🏗️ NBR 6118:2023</span><br>
        <span style='color:#7a8ba8;font-size:0.78rem'>Calculadora Estrutural</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**⚙️ Parâmetros Globais**")

    _conc_keys = list(CONCRETOS.keys())
    _aco_keys  = list(ACOS.keys())
    _agress_keys = list(AGRESSIVIDADE.keys())
    _ci = _conc_keys.index(st.session_state["sk_concreto"]) if st.session_state.get("sk_concreto") in _conc_keys else 2
    _ai = _aco_keys.index(st.session_state["sk_aco"]) if st.session_state.get("sk_aco") in _aco_keys else 1
    _ki = _agress_keys.index(st.session_state["sk_agress_key"]) if st.session_state.get("sk_agress_key") in _agress_keys else 1
    classe_concreto = st.selectbox("Classe do Concreto", _conc_keys, index=_ci)
    tipo_aco = st.selectbox("Tipo de Aço", _aco_keys, index=_ai)
    tipo_combinacao = st.selectbox("Combinação de Ações", ["normal", "especial", "excepcional"], index=0)
    classe_agress_key = st.selectbox("Agressividade Ambiental", _agress_keys, index=_ki)
    
    st.markdown("---")
    
    fck = CONCRETOS[classe_concreto]["fck"]
    fyk = ACOS[tipo_aco]["fyk"]
    Es  = ACOS[tipo_aco]["Es"]
    fcd_val = fcd(fck, tipo_combinacao)
    fyd_v   = fyd_val(fyk, tipo_combinacao)
    Ecs     = Ecs_calc(fck)
    
    st.markdown("**📊 Resistências de Cálculo**")
    st.markdown(f"""
    <div style='background:#0d111a;border-radius:8px;padding:0.8rem;font-family:JetBrains Mono,monospace;font-size:0.8rem;line-height:1.8'>
        <span style='color:#7a8ba8'>fck  = </span><span style='color:#60a5fa'>{fck} MPa</span><br>
        <span style='color:#7a8ba8'>fcd  = </span><span style='color:#34d399'>{fcd_val:.2f} MPa</span><br>
        <span style='color:#7a8ba8'>fyk  = </span><span style='color:#60a5fa'>{fyk} MPa</span><br>
        <span style='color:#7a8ba8'>fyd  = </span><span style='color:#34d399'>{fyd_v:.2f} MPa</span><br>
        <span style='color:#7a8ba8'>Ecs  = </span><span style='color:#f9a8d4'>{Ecs/1000:.2f} GPa</span><br>
        <span style='color:#7a8ba8'>αe   = </span><span style='color:#fbbf24'>{Es/Ecs:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    classe_agress = AGRESSIVIDADE[classe_agress_key]["classe"]
    st.markdown("---")
    st.markdown(f"<span style='color:#7a8ba8;font-size:0.78rem'>Norma: ABNT NBR 6118:2023</span>", unsafe_allow_html=True)

    # ── Seção SketchUp ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**📥 Importar do SketchUp**")
    sk_file = st.file_uploader(
        "JSON exportado pela extensão",
        type=["json"],
        key="sk_uploader",
        help="Use a extensão SketchUp v2.0 para exportar o modelo.",
    )
    if sk_file is not None:
        try:
            _raw = _json.load(sk_file)
            _els = _raw.get("elementos_estruturais", [])
            st.session_state["sk_data"]     = _raw
            st.session_state["sk_elements"] = _els
            # Aplica parâmetros globais do JSON automaticamente
            _gp = _raw.get("global_parameters", {})
            if _gp.get("classe_concreto") in list(CONCRETOS.keys()):
                st.session_state["sk_concreto"] = _gp["classe_concreto"]
            if _gp.get("tipo_aco") in list(ACOS.keys()):
                st.session_state["sk_aco"] = _gp["tipo_aco"]
            _agress_map = {"I": "I — Fraca", "II": "II — Moderada",
                           "III": "III — Forte", "IV": "IV — Muito Forte"}
            _ag = _gp.get("classe_agressividade", "")
            if _ag in _agress_map:
                st.session_state["sk_agress_key"] = _agress_map[_ag]
            st.success(f"✅ {len(_els)} elemento(s) carregado(s)")
        except Exception as _e:
            st.error(f"Erro ao ler JSON: {_e}")

    _elements_loaded = st.session_state.get("sk_elements", [])
    if _elements_loaded:
        _labels = [f"[{e.get('tipo','?').upper()}] {e.get('nome','?')}" for e in _elements_loaded]
        _sel = st.selectbox("Elemento ativo", range(len(_labels)),
                            format_func=lambda i: _labels[i],
                            key="sk_sel_idx_widget")
        st.session_state["sk_sel_idx"] = _sel
        if st.button("⚡ Aplicar nos formulários", use_container_width=True):
            _apply_element(_elements_loaded[_sel])
            st.rerun()
        _sel_el = _elements_loaded[_sel]
        _g = _sel_el.get("geometria", {})
        st.markdown(f"""<div style='background:#0d111a;border-radius:6px;padding:0.6rem;
            font-size:0.75rem;color:#7a8ba8;font-family:monospace;line-height:1.7'>
            L={_g.get("comprimento","?")}m | bw={_g.get("largura","?")}cm | h={_g.get("altura","?")}cm
            </div>""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class='main-header'>
    <h1>🏗️ NBR 6118:2023 — Estruturas de Concreto Armado</h1>
    <p>Verificação e dimensionamento segundo a norma ABNT NBR 6118 — Quarta Edição — Agosto 2023</p>
    <span class='badge'>ABNT NBR 6118:2023</span>
    <span class='badge' style='margin-left:8px'>ELU + ELS</span>
    <span class='badge' style='margin-left:8px'>Beams · Pilares · Lajes</span>
</div>
""", unsafe_allow_html=True)

# ─── TABS PRINCIPAIS ──────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🧱 Materiais",
    "🔩 Flexão (Viga)",
    "✂️ Cisalhamento",
    "🏛️ Pilar",
    "↔️ ELS — Deformação",
    "🔎 ELS — Fissuras",
    "⚖️ Ações (NBR 6120)",
    "📊 Lote SketchUp",
    "🏗️ Análise Estrutural",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: MATERIAIS
# ═════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("<div class='section-tag'>§ 8 — Propriedades dos Materiais</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Concreto")
        
        df_conc = pd.DataFrame([
            {
                "Classe": k,
                "fck (MPa)": v["fck"],
                "fctm (MPa)": round(0.3*v["fck"]**(2/3) if v["fck"]<=50 else 2.12*math.log(1+0.1*(v["fck"]+8)), 2),
                "Eci (GPa)": round(5600*v["fck"]**0.5/1000, 2),
                "Ecs (GPa)": round(Ecs_calc(v["fck"])/1000, 2),
                "εc2 (‰)": round(epsilon_c2(v["fck"]), 2),
                "εcu (‰)": round(epsilon_cu(v["fck"]), 2),
            }
            for k, v in CONCRETOS.items()
        ])
        st.dataframe(df_conc.set_index("Classe"), use_container_width=True)
        
        st.markdown("<div class='formula-box'>fctm = 0,30·fck^(2/3)  →  fck ≤ 50 MPa<br>fctm = 2,12·ln[1+0,1·(fck+8)]  →  fck > 50 MPa<br>fctk,inf = 0,70·fctm<br>Eci = 5600·√fck  (MPa)</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Aço de Armadura Passiva")
        
        df_aco = pd.DataFrame([
            {
                "Tipo": k,
                "fyk (MPa)": v["fyk"],
                "fyd (MPa)": round(v["fyk"]/1.15, 1),
                "Es (GPa)": 210,
                "εyd (‰)": round(v["fyk"]/1.15/210000*1000, 2),
                "Ductilidade": "A" if k=="CA-25" else ("B" if k=="CA-50" else "B"),
            }
            for k, v in ACOS.items()
        ])
        st.dataframe(df_aco.set_index("Tipo"), use_container_width=True)
        
        st.markdown("### Bitolas Disponíveis")
        df_bitolas = pd.DataFrame([
            {"φ (mm)": phi, "As (cm²)": round(area_barra(phi), 4), 
             "Peso (kg/m)": round(math.pi*(phi/1000)**2/4*7850, 3)}
            for phi in BARRAS_MM
        ])
        st.dataframe(df_bitolas.set_index("φ (mm)"), use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Cobrimento Nominal Mínimo (Tabela 7.3)")
    col_cob1, col_cob2 = st.columns([2, 1])
    
    with col_cob1:
        df_cob = pd.DataFrame([
            {
                "Classe": f"CAA {c}",
                "Laje (mm)": v["laje"],
                "Viga/Pilar (mm)": v["viga_pilar"],
                "Fundação (mm)": v["fundacao"],
                "fck mín. (MPa)": {
                    "I": 20, "II": 25, "III": 30, "IV": 40
                }[c]
            }
            for c, v in COBRIMENTO.items()
        ])
        st.dataframe(df_cob.set_index("Classe"), use_container_width=True)
    
    with col_cob2:
        st.markdown("<div class='result-card info'>", unsafe_allow_html=True)
        st.markdown(f"**Classe selecionada:** CAA {classe_agress}")
        st.markdown(f"**Ambiente:** {AGRESSIVIDADE[classe_agress_key]['ambiente']}")
        st.markdown(f"**Risco de deterioração:** {AGRESSIVIDADE[classe_agress_key]['risco']}")
        c_nom_laje = COBRIMENTO[classe_agress]["laje"]
        c_nom_vp   = COBRIMENTO[classe_agress]["viga_pilar"]
        c_nom_fund = COBRIMENTO[classe_agress]["fundacao"]
        st.markdown(f"**Cnom laje:** {c_nom_laje} mm  \n**Cnom viga/pilar:** {c_nom_vp} mm  \n**Cnom fundação:** {c_nom_fund} mm")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Diagrama tensão × deformação do concreto
    st.markdown("### Diagrama Tensão–Deformação do Concreto Selecionado")
    
    ec2 = epsilon_c2(fck)
    ecu = epsilon_cu(fck)
    fcd_diag = fcd_val
    n_param = 2 if fck <= 50 else 1.4 + 23.4 * ((90 - fck) / 100) ** 4
    
    eps_range = np.linspace(0, ecu, 300)
    sigma = []
    for e in eps_range:
        if e <= ec2:
            s = 0.85 * fcd_diag * (1 - (1 - e/ec2)**n_param)
        else:
            s = 0.85 * fcd_diag
        sigma.append(s)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eps_range, y=sigma,
        mode='lines', name='σ_c',
        line=dict(color='#60a5fa', width=2.5),
        fill='tozeroy', fillcolor='rgba(96,165,250,0.1)'
    ))
    fig.add_vline(x=ec2, line_dash="dash", line_color="#fbbf24", 
                  annotation_text=f"εc2={ec2:.1f}‰", annotation_font_color="#fbbf24")
    fig.add_vline(x=ecu, line_dash="dash", line_color="#f87171",
                  annotation_text=f"εcu={ecu:.1f}‰", annotation_font_color="#f87171")
    fig.update_layout(
        plot_bgcolor='#0d111a', paper_bgcolor='#0d111a',
        font_color='#9aaec8',
        xaxis_title="Deformação εc (‰)",
        yaxis_title="Tensão σc (MPa)",
        title=f"Diagrama Parábola-Retângulo — {classe_concreto} | fcd = {fcd_diag:.2f} MPa",
        title_font_color='#e8eaf0',
        xaxis=dict(gridcolor='#1e2535'),
        yaxis=dict(gridcolor='#1e2535'),
        height=320,
        margin=dict(t=45, b=40, l=60, r=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: FLEXÃO SIMPLES / COMPOSTA — VIGA
# ═════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<div class='section-tag'>§ 17.3 — Elementos Lineares Sujeitos à Flexão — ELU</div>", unsafe_allow_html=True)
    st.markdown("### Dimensionamento à Flexão Simples — Seção Retangular")
    
    col_in, col_out = st.columns([1, 1])
    
    with col_in:
        st.markdown("**Geometria da Seção**")
        b_w   = st.number_input("Largura bw (cm)", min_value=10.0, max_value=200.0, value=float(st.session_state.get("v_bw",25.0)), step=1.0)
        h_tot = st.number_input("Altura total h (cm)", min_value=10.0, max_value=300.0, value=float(st.session_state.get("v_h",60.0)), step=1.0)
        c_nom = st.number_input("Cobrimento nominal c (mm)", min_value=20, max_value=80, 
                                value=int(st.session_state.get("v_cnom", COBRIMENTO[classe_agress]["viga_pilar"])), step=5)
        phi_estribo = st.selectbox("Bitola do estribo φest (mm)", [6.3, 8.0, 10.0], index=min(int(st.session_state.get("v_phi_est_idx",1)),2))
        phi_long    = st.selectbox("Bitola longitudinal φ (mm)", BARRAS_MM, index=min(int(st.session_state.get("v_phi_long_idx",5)),len(BARRAS_MM)-1))
        
        d_calc = h_tot - c_nom/10 - phi_estribo/10 - phi_long/20
        st.markdown(f"<div class='formula-box'>d (altura útil) = h - c - φest - φlong/2<br>d = {h_tot:.1f} - {c_nom/10:.1f} - {phi_estribo/10:.1f} - {phi_long/20:.2f} = <b style='color:#34d399'>{d_calc:.2f} cm</b></div>", unsafe_allow_html=True)
        
        st.markdown("**Esforços Solicitantes**")
        Md_kNm = st.number_input("Momento fletor de cálculo Md (kN·m)", min_value=0.0, value=float(st.session_state.get("v_Md",150.0)), step=5.0)
        
        st.markdown("**Tipo de Dimensionamento**")
        modo_flex = st.radio("Modo", ["Calcular As", "Verificar seção"], horizontal=True)
        
        if modo_flex == "Verificar seção":
            n_barras  = st.number_input("Nº de barras", min_value=1, max_value=20, value=4)
            As_user   = n_barras * area_barra(phi_long)
            st.info(f"As fornecida = {As_user:.2f} cm²")
    
    with col_out:
        st.markdown("**Resultados**")
        
        # Cálculo
        b  = b_w / 100       # m
        d  = d_calc / 100    # m
        Md = Md_kNm * 1e3    # N·m → kN·m

        # μ = Md / (b·d²·fcd)  — adimensional
        fcd_Pa = fcd_val * 1e6   # Pa
        mu = Md_kNm * 1e3 / (b * d**2 * fcd_Pa)
        
        # Limites de x/d (seção 17.3.3)
        if fck <= 50:
            xi_lim_a = 0.45   # domínio 3
            xi_lim_b = 0.45
        else:
            xi_lim_a = 0.35
            xi_lim_b = 0.35
        
        mu_lim = 0.85 * xi_lim_a * (1 - 0.4 * xi_lim_a)
        
        # Resolução: mu = 0.85·(x/d)·[1 - 0.4·(x/d)]
        # 0.34·(x/d)² - 0.85·(x/d) + mu = 0
        A_coef = 0.34
        B_coef = -0.85
        C_coef = mu
        disc = B_coef**2 - 4*A_coef*C_coef
        
        if disc < 0:
            st.error("❌ Momento muito elevado — revise a seção transversal.")
        else:
            xi = (-B_coef - math.sqrt(disc)) / (2 * A_coef)
            x_d = xi
            
            dupla_armadura = x_d > xi_lim_a
            
            if not dupla_armadura:
                # Armadura simples
                fyd_Pa = fyd_v * 1e6
                z = d * (1 - 0.4 * x_d)  # braço de alavanca (m)
                As_calc = Md_kNm * 1e3 / (z * fyd_Pa) * 1e4  # cm²
                
                # Armadura mínima (seção 17.3.5.2)
                fctm_v = 0.3*fck**(2/3) if fck<=50 else 2.12*math.log(1+0.1*(fck+8))
                rho_min = 0.26 * fctm_v / fyk
                As_min  = rho_min * b_w * d_calc  # cm²
                As_min  = max(As_min, 0.0013 * b_w * d_calc)
                
                # Armadura máxima (seção 17.3.5.2)
                As_max = 0.04 * b_w * h_tot  # cm²
                
                As_final = max(As_calc, As_min)
                
                # Número mínimo de barras
                n_barras_calc = math.ceil(As_final / area_barra(phi_long))
                As_adotada = n_barras_calc * area_barra(phi_long)
                
                # Verificação
                if modo_flex == "Verificar seção":
                    As_final = As_user
                    As_adotada = As_user
                
                # ── Domínios de Deformação (NBR 6118 §17.2.2) ──────────────
                ecu_v  = epsilon_cu(fck)
                eyd_v  = fyd_v / Es * 1000         # ‰
                xi_D34 = ecu_v / (ecu_v + eyd_v)   # limite teórico D3/D4
                eps_s  = ecu_v * (1 - x_d) / x_d if x_d > 0 else 999.0

                if eps_s >= eyd_v and x_d <= xi_lim_a:
                    dominio = 2; dom_cor = "#34d399"
                    dom_txt = f"D2/3 — Flexão subarmada (εs={eps_s:.2f}‰ ≥ εyd={eyd_v:.2f}‰) ✓"
                elif eps_s >= eyd_v:
                    dominio = 3; dom_cor = "#f59e0b"
                    dom_txt = f"D3 — Armadura dupla necessária (x/d={x_d:.3f} > ξlim={xi_lim_a})"
                elif x_d <= xi_D34:
                    dominio = 4; dom_cor = "#ef4444"
                    dom_txt = f"D4 — SUPERAR-ARMADO (εs={eps_s:.2f}‰ < εyd={eyd_v:.2f}‰) ✗"
                else:
                    dominio = 5; dom_cor = "#ef4444"
                    dom_txt = "D5 — Compressão dominante"

                # ── Detalhamento: espaçamento (§18.3.1) ─────────────────────
                a_min_mm = max(phi_long, 20.0, 1.2 * 20.0)  # agregado 20mm
                a_min_cm = a_min_mm / 10
                bw_int_cm = b_w - 2 * (c_nom/10 + phi_estribo/10)
                n_max_fit = max(1, int((bw_int_cm + a_min_cm) / (phi_long/10 + a_min_cm)))
                if n_barras_calc > 1:
                    a_ef_cm = (bw_int_cm - n_barras_calc * phi_long/10) / (n_barras_calc - 1)
                else:
                    a_ef_cm = bw_int_cm - phi_long/10
                espacamento_ok = a_ef_cm >= a_min_cm

                # ── Ancoragem (§9.4) ─────────────────────────────────────────
                fbd   = 2.25 * fctd_val(fck, tipo_combinacao)   # η1=2.25, barras nervuradas boa posição
                lb_bas = (phi_long / 10) * (fyd_v / (4 * fbd))  # cm
                lb_nec = max(lb_bas * max(As_calc, 0.001) / max(As_adotada, 0.001),
                             0.3 * lb_bas, 10 * phi_long/10, 10.0)

                # ── DISPLAY ───────────────────────────────────────────────────
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"""
                    <div class='result-card {{"success" if As_adotada >= As_final else "error"}}'>
                        <div class='result-title'>As calculada</div>
                        <div class='result-value'>{As_calc:.2f}<span class='result-unit'>cm²</span></div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class='result-card info'>
                        <div class='result-title'>As mínima (ρmin={rho_min*100:.3f}%)</div>
                        <div class='result-value'>{As_min:.2f}<span class='result-unit'>cm²</span></div>
                    </div>""", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"""
                    <div class='result-card success'>
                        <div class='result-title'>As adotada ({n_barras_calc}φ{phi_long:.0f})</div>
                        <div class='result-value'>{As_adotada:.2f}<span class='result-unit'>cm²</span></div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class='result-card {{"success" if As_adotada <= As_max else "error"}}'>
                        <div class='result-title'>As máxima (ρmax=4,0%)</div>
                        <div class='result-value'>{As_max:.2f}<span class='result-unit'>cm²</span></div>
                    </div>""", unsafe_allow_html=True)

                # Domínio
                st.markdown(f"""<div style='background:#0d111a;border:1px solid {dom_cor}44;
                    border-left:4px solid {dom_cor};border-radius:6px;padding:0.7rem 1rem;margin:0.5rem 0'>
                    <span style='color:{dom_cor};font-weight:700'>Domínio {dominio}</span>
                    <span style='color:#9aaec8;margin-left:8px;font-size:0.82rem'>{dom_txt}</span><br>
                    <span style='color:#6b7fa0;font-size:0.75rem'>
                    εcu={ecu_v:.2f}‰ | εyd={eyd_v:.2f}‰ | εs={eps_s:.2f}‰ | x/d={x_d:.4f} | ξD34={xi_D34:.3f}
                    </span></div>""", unsafe_allow_html=True)

                if dominio == 4:
                    fck_sug = next((f for f in [35,40,45,50,55,60] if f > fck), fck+5)
                    st.error(f"⛔ **Domínio 4 — Ruptura Frágil.** O concreto rompe antes do aço escoar. "
                             f"Aumente bw/h, use fck={fck_sug} MPa ou adicione armadura de compressão.")
                elif dominio == 3:
                    st.warning(f"⚠️ **Domínio 3 estendido** — x/d={x_d:.3f} > ξlim={xi_lim_a}. Armadura dupla necessária.")

                # Detalhamento
                st.markdown("**Detalhamento — Espaçamento (§18.3.1)**")
                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    st.markdown(f"""<div class='result-card {"success" if espacamento_ok else "error"}'>
                        <div class='result-title'>Espaçamento efetivo</div>
                        <div class='result-value'>{a_ef_cm:.1f}<span class='result-unit'>cm</span></div>
                        <div class='result-status' style='color:{"#22c55e" if espacamento_ok else "#ef4444"}'>
                        {"✓ ≥ amin" if espacamento_ok else f"✗ < amin={a_min_cm:.1f}cm"}</div>
                    </div>""", unsafe_allow_html=True)
                with col_d2:
                    st.markdown(f"""<div class='result-card info'>
                        <div class='result-title'>Espaçamento mínimo</div>
                        <div class='result-value'>{a_min_cm:.1f}<span class='result-unit'>cm</span></div>
                        <div class='result-status' style='color:#7a8ba8'>max(φ; 2cm; 1,2·φag)</div>
                    </div>""", unsafe_allow_html=True)
                with col_d3:
                    st.markdown(f"""<div class='result-card {"success" if n_barras_calc <= n_max_fit else "warning"}'>
                        <div class='result-title'>Barras em 1 camada</div>
                        <div class='result-value'>{n_barras_calc}<span class='result-unit'> / {n_max_fit} max</span></div>
                        <div class='result-status' style='color:{"#22c55e" if n_barras_calc<=n_max_fit else "#f59e0b"}'>
                        {"✓ Cabe" if n_barras_calc<=n_max_fit else "⚠ 2 camadas"}</div>
                    </div>""", unsafe_allow_html=True)
                if not espacamento_ok:
                    st.error(f"❌ Espaçamento {a_ef_cm:.1f} cm < mínimo {a_min_cm:.1f} cm. Reduza bitola, aumente bw ou use 2 camadas.")

                # Ancoragem
                st.markdown("**Ancoragem (§9.4)**")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.markdown(f"""<div class='result-card info'>
                        <div class='result-title'>lb,nec — Comprimento necessário</div>
                        <div class='result-value'>{lb_nec:.1f}<span class='result-unit'>cm</span></div>
                        <div class='result-status' style='color:#7a8ba8'>
                        fbd={fbd:.3f} MPa | lb,bas={lb_bas:.1f} cm</div>
                    </div>""", unsafe_allow_html=True)
                with col_a2:
                    apoio_cm = st.number_input("Comprimento de apoio disponível (cm)",
                        min_value=0.0, value=round(lb_nec*1.15, 0), step=1.0, key="apoio_cm",
                        help="Largura do pilar/viga de apoio onde esta viga se assenta.")
                    ancoragem_ok = apoio_cm >= lb_nec
                    st.markdown(f"""<div class='result-card {"success" if ancoragem_ok else "error"}'>
                        <div class='result-title'>Apoio disponível</div>
                        <div class='result-value'>{apoio_cm:.1f}<span class='result-unit'>cm</span></div>
                        <div class='result-status' style='color:{"#22c55e" if ancoragem_ok else "#ef4444"}'>
                        {"✓ Apoio ≥ lb,nec" if ancoragem_ok else f"✗ Insuficiente (falta {lb_nec-apoio_cm:.1f}cm)"}</div>
                    </div>""", unsafe_allow_html=True)
                if not ancoragem_ok:
                    st.error(f"❌ **Apoio insuficiente** para ancoragem reta. Disponível: {apoio_cm:.1f} cm | Necessário: {lb_nec:.1f} cm. "
                             f"Solução: gancho padrão (~30% redução) ou aumentar apoio.")

                # Fórmulas
                st.markdown(f"""
                <div class='formula-box'>
                μd={mu:.4f} | μlim={mu_lim:.4f} | x/d={x_d:.4f} | ξlim={xi_lim_a} | ξD34={xi_D34:.3f}<br>
                z = d·(1−0,4·x/d) = {z*100:.2f} cm | As={As_calc:.2f} cm²<br>
                ρ={As_adotada/(b_w*d_calc)*100:.3f}% | ρmin={rho_min*100:.3f}% | ρmax=4,0%<br>
                aef={a_ef_cm:.1f} cm | amin={a_min_cm:.1f} cm | nmax={n_max_fit} barras/camada<br>
                fbd=η1·fctd={fbd:.3f} MPa | lb,bas={lb_bas:.1f} cm | lb,nec={lb_nec:.1f} cm
                </div>""", unsafe_allow_html=True)

                # Diagrama da seção
                fig_sec = go.Figure()
                bw_m = b_w / 100; h_m = h_tot / 100; d_m = d_calc / 100
                fig_sec.add_shape(type="rect", x0=0, y0=0, x1=bw_m, y1=h_m,
                    fillcolor="#1e40af", line_color="#60a5fa", line_width=2, opacity=0.7)
                y_as = (c_nom/10 + phi_estribo/10 + phi_long/20) / 100
                fig_sec.add_shape(type="line", x0=0.02, y0=y_as, x1=bw_m-0.02, y1=y_as,
                    line_color="#fbbf24", line_dash="dot", line_width=1.5)
                spacing = (bw_m - 0.04) / max(n_barras_calc-1, 1)
                for i in range(n_barras_calc):
                    xi_bar = 0.02 + i * spacing
                    fig_sec.add_shape(type="circle",
                        x0=xi_bar-phi_long/2000, y0=y_as-phi_long/2000,
                        x1=xi_bar+phi_long/2000, y1=y_as+phi_long/2000,
                        fillcolor="#fbbf24", line_color="#f59e0b", line_width=1)
                y_x = h_m - x_d * d_m
                fig_sec.add_shape(type="line", x0=0, y0=y_x, x1=bw_m, y1=y_x,
                    line_color="#f87171", line_dash="dashdot", line_width=1.5)
                fig_sec.add_annotation(x=bw_m+0.01, y=(h_m+y_x)/2,
                    text=f"x={x_d*d_calc:.1f}cm", font=dict(color="#f87171", size=9), showarrow=False, xanchor="left")
                fig_sec.add_shape(type="line", x0=-0.03, y0=d_m, x1=0, y1=d_m,
                    line_color="#34d399", line_width=1.5)
                fig_sec.add_annotation(x=-0.06, y=d_m/2, text=f"d={d_calc:.1f}cm",
                    font=dict(color="#34d399", size=10), showarrow=False)
                fig_sec.update_layout(
                    plot_bgcolor='#0d111a', paper_bgcolor='#0d111a', font_color='#9aaec8', height=280,
                    xaxis=dict(visible=False, range=[-0.1, bw_m+0.12]),
                    yaxis=dict(visible=False, range=[-0.05, h_m+0.05], scaleanchor="x", scaleratio=1),
                    margin=dict(t=10, b=10, l=60, r=20), title="Seção Transversal", title_font_color='#e8eaf0')
                st.plotly_chart(fig_sec, use_container_width=True)

            else:
                ecu_v = epsilon_cu(fck); eyd_v = fyd_v / Es * 1000; xi_D34 = ecu_v / (ecu_v + eyd_v)
                eps_s_else = ecu_v * (1 - x_d) / x_d if x_d > 0 else 0.0
                fck_sug = next((f for f in [35,40,45,50,55,60] if f > fck), fck+5)
                st.error(f"⛔ **Domínio 4 — Ruptura Frágil.** x/d={x_d:.3f} > ξlim={xi_lim_a} | ξD34={xi_D34:.3f}. "
                         f"εs≈{eps_s_else:.2f}‰ < εyd={eyd_v:.2f}‰. Aço não escoa antes do concreto romper.")
                st.markdown(f"""<div style='background:#1a1010;border:1px solid #ef444430;border-radius:8px;padding:1rem;margin-top:0.5rem'>
                <p style='color:#fca5a5;font-weight:600;margin-bottom:0.4rem'>Opções para resolver:</p>
                <ul style='color:#9aaec8;line-height:2;margin:0'>
                <li>Aumentar largura bw (atual: {b_w:.0f} cm)</li>
                <li>Aumentar altura h (atual: {h_tot:.0f} cm)</li>
                <li>Usar concreto {fck_sug} MPa em vez de {fck} MPa</li>
                <li>Adicionar armadura de compressão (armadura dupla)</li>
                </ul></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class='formula-box'>
                μd={mu:.4f} &gt; μlim={mu_lim:.4f}<br>x/d={x_d:.4f} &gt; ξlim={xi_lim_a} | ξD34={xi_D34:.3f}<br>
                → Domínio 4 — revisar seção</div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: CISALHAMENTO
# ═════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<div class='section-tag'>§ 17.4 — Força Cortante — ELU — Modelo I</div>", unsafe_allow_html=True)
    st.markdown("### Dimensionamento à Força Cortante")
    
    col_c1, col_c2 = st.columns([1, 1])
    
    with col_c1:
        st.markdown("**Geometria**")
        bw_c  = st.number_input("Largura da alma bw (cm)", min_value=10.0, max_value=200.0, value=float(st.session_state.get("c_bw",25.0)), step=1.0, key="bw_c")
        d_c   = st.number_input("Altura útil d (cm)", min_value=10.0, max_value=300.0, value=float(st.session_state.get("c_d",55.0)), step=1.0, key="d_c")
        
        st.markdown("**Esforços**")
        Vd_kN = st.number_input("Força cortante de cálculo Vd (kN)", min_value=0.0, value=float(st.session_state.get("c_Vd",120.0)), step=5.0)
        
        st.markdown("**Armadura Longitudinal**")
        As_c  = st.number_input("As longitudinal (cm²)", min_value=0.1, value=float(st.session_state.get("c_As",8.04)), step=0.5)
        
        st.markdown("**Parâmetros do Modelo**")
        modelo = st.radio("Modelo de cálculo", ["Modelo I — Treliça 45°", "Modelo II — Treliça variável"], 
                          horizontal=False)
        if modelo == "Modelo II — Treliça variável":
            theta_deg = st.slider("Ângulo θ (graus)", min_value=30, max_value=45, value=38)
        else:
            theta_deg = 45
        
        phi_est = st.selectbox("Bitola do estribo φ (mm)", BARRAS_MM, index=2, key="phi_est_c")
        ramos   = st.selectbox("Nº de ramos", [2, 3, 4], index=min(int(st.session_state.get("c_ramos_idx",0)),2))
    
    with col_c2:
        st.markdown("**Verificações e Resultados**")
        
        bw = bw_c / 100   # m
        d  = d_c  / 100   # m
        Vd = Vd_kN * 1e3  # N
        fcd_Pa = fcd_val * 1e6
        fyd_Pa = fyd_v  * 1e6
        fctd_v  = fctd_val(fck)  # MPa
        
        theta  = math.radians(theta_deg)
        cot_th = 1 / math.tan(theta)
        
        # ── 1. Resistência da biela comprimida (Vrd2) ──────────────────────
        # Seção 17.4.2.2
        alpha_v2 = 1 - fck / 250
        if modelo == "Modelo I — Treliça 45°":
            Vrd2 = 0.27 * alpha_v2 * fcd_val * bw_c * d_c * 1e4 / 1000  # kN
            Vsw_max = Vrd2
        else:
            Vrd2 = 0.54 * alpha_v2 * fcd_val * bw_c * d_c * 1e4 / 1000  # kN
        
        # ── 2. Parcela de resistência do concreto (Vc) ────────────────────
        # Seção 17.4.2.1.1 — Modelo I
        rho_l = As_c / (bw_c * d_c)  # adimensional (cm²/cm²)
        Vc0 = 0.6 * fctd_v * bw_c * d_c * 1e4 / 1e6 * 1e3  # kN (convertendo de N·cm para kN)
        # Simplificação: Vc = Vc0 (sem incremento de esforço normal)
        Vc = Vc0
        
        # ── 3. Verificação se dispensa armadura ───────────────────────────
        Vrdc_min = Vc  # resistência mínima sem estribos
        
        # ── 4. Armadura de cisalhamento necessária ────────────────────────
        Vsw_necessario = max(Vd_kN - Vc, 0)
        
        # Asw / s  (cm²/m)
        if modelo == "Modelo I — Treliça 45°":
            Asw_s = Vsw_necessario * 1e3 / (fyd_v * d_c * 1e4 / 1e6 * 1e3)  # cm²/m
        else:
            Asw_s = Vsw_necessario * 1e3 / (fyd_v * cot_th * d_c * 1e4/1e6*1e3)  # cm²/m
        
        Asw_ramo = area_barra(phi_est) * ramos  # cm²
        s_max_calc = Asw_ramo / Asw_s * 100 if Asw_s > 0 else 999  # cm
        
        # Espaçamento máximo (seção 17.4.2.2)
        s_max_norma = min(0.6 * d_c, 30.0)  # cm
        s_adotado = min(s_max_calc, s_max_norma)
        
        # Armadura mínima de cisalhamento (seção 17.3.5.4)
        fctm_v = 0.3*fck**(2/3) if fck<=50 else 2.12*math.log(1+0.1*(fck+8))
        rho_sw_min = 0.2 * fctm_v / fyk
        Asw_min_s  = rho_sw_min * bw_c / ramos  # cm²/cm × ramos → cm²/m ×100
        Asw_min_s_cm = rho_sw_min * bw_c  # cm²/m (considerando 1m = 100cm)
        s_min_check = Asw_ramo / Asw_min_s_cm * 100 if Asw_min_s_cm > 0 else s_adotado
        
        s_final = min(s_adotado, s_min_check, s_max_norma)
        s_final = max(s_final, 5.0)  # mínimo construtivo
        
        # Verificação
        ok_biela  = Vd_kN <= Vrd2
        ok_armada = Asw_s <= Asw_ramo / (s_final / 100) / 100  # verificação
        
        cols_c = st.columns(2)
        with cols_c[0]:
            card_class = "success" if ok_biela else "error"
            st.markdown(f"""
            <div class='result-card {card_class}'>
                <div class='result-title'>Vrd2 — Biela Comprimida</div>
                <div class='result-value'>{Vrd2:.1f}<span class='result-unit'>kN</span></div>
                <div class='result-status' style='color:{"#22c55e" if ok_biela else "#ef4444"}'>
                {"✓ Vd ≤ Vrd2" if ok_biela else "✗ Vd > Vrd2 — Revise!"}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Vc — Parcela do Concreto</div>
                <div class='result-value'>{Vc:.1f}<span class='result-unit'>kN</span></div>
            </div>""", unsafe_allow_html=True)
        
        with cols_c[1]:
            st.markdown(f"""
            <div class='result-card {"success" if Vsw_necessario < Vd_kN else "warning"}'>
                <div class='result-title'>Vsw necessário</div>
                <div class='result-value'>{Vsw_necessario:.1f}<span class='result-unit'>kN</span></div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card success'>
                <div class='result-title'>Espaçamento adotado s</div>
                <div class='result-value'>{s_final:.0f}<span class='result-unit'>cm</span></div>
                <div class='result-status' style='color:#7a8ba8'>smax_norma = {s_max_norma:.0f} cm</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='formula-box'>
        Vrd2 = 0,{"27" if modelo=="Modelo I — Treliça 45°" else "54"}·αv2·fcd·bw·d = {Vrd2:.2f} kN<br>
        αv2 = 1 - fck/250 = {alpha_v2:.4f}<br>
        Vc = 0,6·fctd·bw·d = {Vc:.2f} kN<br>
        Vsw = Vd - Vc = {Vsw_necessario:.2f} kN<br>
        Asw/s = {Asw_s:.4f} cm²/cm  →  {ramos}φ{phi_est:.0f} / {s_final:.0f} cm
        </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4: PILAR
# ═════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("<div class='section-tag'>§ 15 + § 17.3 — Pilares — ELU (Esbeltez + Flexo-compressão)</div>", unsafe_allow_html=True)
    st.markdown("### Dimensionamento de Pilar Retangular")
    
    col_p1, col_p2 = st.columns([1, 1])
    
    with col_p1:
        st.markdown("**Geometria do Pilar**")
        b_p = st.number_input("Largura b (cm)", min_value=14.0, max_value=200.0, value=float(st.session_state.get("p_b",30.0)), step=2.0)
        h_p = st.number_input("Altura h (cm)", min_value=14.0, max_value=200.0, value=float(st.session_state.get("p_h",40.0)), step=2.0)
        L_e = st.number_input("Comprimento de flambagem Le (m)", min_value=0.5, max_value=30.0, value=float(st.session_state.get("p_Le",3.6)), step=0.1)
        
        st.markdown("**Esforços de Cálculo**")
        Nd_kN    = st.number_input("Força normal Nd (kN)", min_value=0.0, value=float(st.session_state.get("p_Nd",800.0)), step=10.0)
        Mdx_kNm  = st.number_input("Momento Mdx (kN·m) — em relação ao eixo x", min_value=0.0, value=float(st.session_state.get("p_Mdx",60.0)), step=5.0)
        Mdy_kNm  = st.number_input("Momento Mdy (kN·m) — em relação ao eixo y", min_value=0.0, value=float(st.session_state.get("p_Mdy",30.0)), step=5.0)
        
        c_nom_p  = st.number_input("Cobrimento nominal (mm)", min_value=20, max_value=60,
                                    value=COBRIMENTO[classe_agress]["viga_pilar"], step=5, key="cnom_p")
        phi_p    = st.selectbox("Bitola da armadura φ (mm)", BARRAS_MM, index=5, key="phi_pilar")
    
    with col_p2:
        st.markdown("**Resultados**")
        
        Ac = b_p * h_p  # cm²
        
        # Índices de esbeltez (seção 15.4)
        ix = h_p / (2 * math.sqrt(3))  # raio de giração (cm) — seção retangular: i = h/√12
        iy = b_p / (2 * math.sqrt(3))
        # Correto: i = h/√12 = h/(2√3)
        ix = h_p / math.sqrt(12)
        iy = b_p / math.sqrt(12)
        
        lambda_x = L_e * 100 / ix  # adimensional
        lambda_y = L_e * 100 / iy
        lambda_max = max(lambda_x, lambda_y)
        
        lambda_1 = 35  # seção 15.4 — limite para pilar esbelto
        
        # Verificação de dimensões mínimas (seção 13.2.3)
        dim_min_ok = min(b_p, h_p) >= 19.0  # 19 cm mínimo (com tolerância)
        # NBR 6118:2023 Seção 13.2.3 — bw ≥ 19 cm para pilares
        
        # Resistência
        fcd_p  = fcd_val  # MPa
        
        # Força resistente mínima (compressão centrada)
        Nrd_centrado = 0.85 * fcd_p * Ac * 1e-2  # kN (Ac em cm², fcd em MPa → kN/cm² × cm²)
        Nrd_centrado_kN = 0.85 * fcd_p * Ac / 10  # kN
        
        # Excentricidades de primeira ordem
        ex = Mdy_kNm / Nd_kN * 100 if Nd_kN > 0 else 0  # cm
        ey = Mdx_kNm / Nd_kN * 100 if Nd_kN > 0 else 0  # cm
        
        # Excentricidade mínima (seção 11.3.3.4)
        e_min = max(1.5 + 0.03 * L_e * 100, h_p / 30)  # cm
        e_min = max(e_min, 2.0)
        
        ex_calc = max(ex, e_min)
        ey_calc = max(ey, e_min)
        
        # Verificação de esbeltez
        esbelto_x = lambda_x > lambda_1
        esbelto_y = lambda_y > lambda_1
        
        cols_p = st.columns(2)
        with cols_p[0]:
            color_lambda = "#ef4444" if lambda_max > 90 else ("#f59e0b" if lambda_max > lambda_1 else "#22c55e")
            st.markdown(f"""
            <div class='result-card {"success" if lambda_max<=lambda_1 else "warning"}'>
                <div class='result-title'>Esbeltez máxima λ</div>
                <div class='result-value' style='color:{color_lambda}'>{lambda_max:.1f}</div>
                <div class='result-status' style='color:{color_lambda}'>
                {"✓ λ ≤ 35 — pilar normal" if lambda_max<=lambda_1 else ("⚠ λ ≤ 90 — pilar esbelto" if lambda_max<=90 else "✗ λ > 90 — atenção!")}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>λx / λy</div>
                <div class='result-value'>{lambda_x:.1f} / {lambda_y:.1f}</div>
            </div>""", unsafe_allow_html=True)
        
        with cols_p[1]:
            taxa_nd = Nd_kN / Nrd_centrado_kN
            st.markdown(f"""
            <div class='result-card {"success" if taxa_nd<=0.9 else "error"}'>
                <div class='result-title'>Nd / Nrd,centrado</div>
                <div class='result-value'>{taxa_nd:.3f}</div>
                <div class='result-status' style='color:{"#22c55e" if taxa_nd<=0.9 else "#ef4444"}'>
                {"✓ Compressão OK" if taxa_nd <= 0.9 else "✗ Supera Nrd"}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Excentricidade mínima</div>
                <div class='result-value'>{e_min:.1f}<span class='result-unit'>cm</span></div>
            </div>""", unsafe_allow_html=True)
        
        # Armadura mínima e máxima
        As_min_p = max(0.004 * Ac, 0.15 * Nd_kN / (fyd_v / 10))  # cm²
        As_max_p = 0.08 * Ac  # cm²
        
        # Estimativa simplificada de armadura (compressão + flexão)
        # Método simplificado — interação N-M
        nu = Nd_kN / (fcd_val * Ac / 10)  # fcd em MPa, Ac em cm², resultado adimensional
        mux = Mdx_kNm * 1e3 / (fcd_val * b_p/100 * (h_p/100)**2 * 1e6)
        muy = Mdy_kNm * 1e3 / (fcd_val * h_p/100 * (b_p/100)**2 * 1e6)
        
        st.markdown(f"""
        <div class='formula-box'>
        Ac = {Ac:.0f} cm²  |  ix = {ix:.2f} cm  |  iy = {iy:.2f} cm<br>
        λx = Le/ix = {lambda_x:.1f}  |  λy = Le/iy = {lambda_y:.1f}  |  λ1 = {lambda_1}<br>
        Nrd,centrado = 0,85·fcd·Ac = {Nrd_centrado_kN:.1f} kN<br>
        e_min = max(1,5+0,03·Le·100; h/30; 2,0) = {e_min:.1f} cm<br>
        ex = {ex_calc:.1f} cm  |  ey = {ey_calc:.1f} cm<br>
        ν = Nd/(fcd·Ac) = {nu:.4f}<br>
        As_mín = {As_min_p:.2f} cm²  |  As_máx = {As_max_p:.2f} cm²
        </div>""", unsafe_allow_html=True)
        
        if not dim_min_ok:
            st.warning(f"⚠️ Dimensão mínima de {min(b_p, h_p):.0f} cm < 19 cm. Verifique a norma (§ 13.2.3).")
        
        if lambda_max > lambda_1:
            st.warning("⚠️ Pilar esbelto — necessário calcular efeitos de 2ª ordem. Utilize método geral ou método do pilar-padrão (§ 15.8).")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5: ELS — DEFORMAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("<div class='section-tag'>§ 13.3 — Estado-Limite de Deformações Excessivas (ELS-DEF)</div>", unsafe_allow_html=True)
    st.markdown("### Verificação de Flechas — Viga")
    
    col_d1, col_d2 = st.columns([1, 1])
    
    with col_d1:
        st.markdown("**Geometria**")
        bw_d  = st.number_input("Largura bw (cm)", value=float(st.session_state.get("d_bw",25.0)), min_value=10.0, max_value=200.0, key="bw_d")
        h_d   = st.number_input("Altura total h (cm)", value=float(st.session_state.get("d_h",60.0)), min_value=10.0, max_value=300.0, key="h_d")
        d_d   = st.number_input("Altura útil d (cm)", value=float(st.session_state.get("d_d",55.0)), min_value=5.0, max_value=290.0, key="d_d")
        L_d   = st.number_input("Vão livre L (m)", value=6.0, min_value=0.5, max_value=30.0, key="L_d")
        
        st.markdown("**Armaduras**")
        As_d  = st.number_input("As tração (cm²)", value=float(st.session_state.get("d_As",8.04)), min_value=0.1, key="As_d")
        Asl_d = st.number_input("As compressão (cm²)", value=0.0, min_value=0.0, key="Asl_d")
        
        st.markdown("**Carregamentos (ELS — combinação quase-permanente)**")
        Mk_kNm = st.number_input("Momento característico Mk (kN·m)", value=float(st.session_state.get("d_Mk",80.0)), min_value=0.0, key="Mk_d")
        
        st.markdown("**Tipo de viga / uso**")
        uso_viga = st.selectbox("Tipo de elemento", [
            "Viga de piso — estrutura geral (L/250)",
            "Viga de piso — com paredes (L/350)",
            "Viga de cobertura (L/250)",
            "Laje de piso (L/250)",
            "Viga em balanço (L/125)",
        ], key="uso_d")
        
        limites = {
            "Viga de piso — estrutura geral (L/250)": 250,
            "Viga de piso — com paredes (L/350)": 350,
            "Viga de cobertura (L/250)": 250,
            "Laje de piso (L/250)": 250,
            "Viga em balanço (L/125)": 125,
        }
        L_limite = limites[uso_viga]
    
    with col_d2:
        st.markdown("**Resultados**")
        
        # Módulo de elasticidade
        alpha_e = Es / Ecs  # relação modular
        
        # Seção homogeneizada — estádio I (sem fissuração)
        Ic = bw_d * h_d**3 / 12  # cm⁴
        e_s = d_d - h_d/2        # distância entre armadura e CG da seção (cm)
        A1 = bw_d * h_d + (alpha_e - 1) * As_d + (alpha_e - 1) * Asl_d  # cm²
        
        # Seção fissurada — estádio II
        # posição da linha neutra (cm) — seção retangular
        # bw/2·x² + (αe-1)·As'·(x-d') - αe·As·(d-x) = 0
        d_linha = h_d - d_d  # cobrimento compressão (aprox.)
        A_eq = bw_d / 2
        B_eq = (alpha_e - 1) * Asl_d + alpha_e * As_d
        C_eq = -(alpha_e - 1) * Asl_d * d_linha - alpha_e * As_d * d_d
        disc_ln = B_eq**2 - 4 * A_eq * C_eq
        x_n2 = (-B_eq + math.sqrt(disc_ln)) / (2 * A_eq)  # cm
        x_n2 = max(x_n2, 1.0)
        
        # Inércia no estádio II
        I2 = bw_d * x_n2**3 / 3 + alpha_e * As_d * (d_d - x_n2)**2 + (alpha_e-1)*Asl_d*(x_n2-d_linha)**2
        
        # Momento de fissuração (Seção 17.3.1)
        fctk_inf_v = fctk_inf(fck)
        y_t = h_d / 2  # distância ao CG (seção simétrica)
        Mr_kNm = fctk_inf_v * Ic / y_t / 100  # kN·m
        
        # Inércia efetiva — Branson adaptado para NBR (Seção 17.3.2)
        if Mk_kNm < Mr_kNm:
            Ief = Ic
            fissurada = False
        else:
            zeta = 1 - 0.5 * (Mr_kNm / Mk_kNm)**2  # coeficiente de participação da fissuração
            Ief = 1 / (zeta / I2 + (1 - zeta) / Ic)
            fissurada = True
        
        # Flecha imediata — viga biapoiada com carga distribuída
        # δ = 5/384 · q·L⁴ / (E·I)  ↔  δ = Mk·L² / (8·E·I) (relação com momento máximo M=qL²/8)
        E_c = Ecs / 1e4  # kN/cm²  (Ecs em MPa = kN/cm², /1e4 para converter MPa→kN/cm²... )
        # Ecs em MPa = N/mm² = 0.001 kN/mm² = 0.1 kN/cm² → × 0.1
        E_kN_cm2 = Ecs * 0.1  # kN/cm²
        L_cm = L_d * 100     # cm
        
        delta_imediata = Mk_kNm * 100 * L_cm**2 / (8 * E_kN_cm2 * Ief) if Ief > 0 else 0  # cm
        # (kN·m → kN·cm por ×100; E em kN/cm²; Ief em cm⁴; L em cm)
        
        # Flecha diferida (fluência) — seção 17.3.2.1.2
        # φ_inf (coeficiente de fluência) — Tab 8.4 simplificado
        fi_inf = 2.5  # valor conservativo para umidade relativa ≥ 40%
        delta_fluencia = fi_inf * delta_imediata  # simplificação: δf ≈ φ·δi
        
        # Flecha total e limite
        delta_total = delta_imediata + delta_fluencia
        delta_limite = L_d * 100 / L_limite  # cm
        
        ok_flecha = delta_total <= delta_limite
        
        cols_d = st.columns(2)
        with cols_d[0]:
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Mr — Momento de fissuração</div>
                <div class='result-value'>{Mr_kNm:.1f}<span class='result-unit'>kN·m</span></div>
                <div class='result-status' style='color:{"#f59e0b" if fissurada else "#22c55e"}'>
                {"⚠ Seção fissurada" if fissurada else "✓ Seção não fissurada"}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Ief</div>
                <div class='result-value'>{Ief:.0f}<span class='result-unit'>cm⁴</span></div>
            </div>""", unsafe_allow_html=True)
        
        with cols_d[1]:
            st.markdown(f"""
            <div class='result-card {"success" if ok_flecha else "error"}'>
                <div class='result-title'>Flecha total δ</div>
                <div class='result-value'>{delta_total*10:.1f}<span class='result-unit'>mm</span></div>
                <div class='result-status' style='color:{"#22c55e" if ok_flecha else "#ef4444"}'>
                {"✓ δ ≤ L/"+str(L_limite) if ok_flecha else "✗ δ > L/"+str(L_limite)}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Flecha limite L/{L_limite}</div>
                <div class='result-value'>{delta_limite*10:.1f}<span class='result-unit'>mm</span></div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='formula-box'>
        αe = Es/Ecs = {alpha_e:.2f}<br>
        I (estádio I) = {Ic:.0f} cm⁴  |  Mr = fctk,inf·I/yt = {Mr_kNm:.2f} kN·m<br>
        x (est. II) = {x_n2:.2f} cm  |  I2 = {I2:.0f} cm⁴<br>
        {"ζ = 1 - 0,5·(Mr/Mk)² = "+str(round(1-0.5*(Mr_kNm/Mk_kNm)**2, 4)) if fissurada else "Seção não fissurada → Ief = I"}<br>
        Ief = {Ief:.0f} cm⁴<br>
        δi = Mk·L² / (8·Ecs·Ief) = {delta_imediata*10:.2f} mm<br>
        δf (fluência) ≈ φ·δi = {delta_fluencia*10:.2f} mm<br>
        δtotal = {delta_total*10:.2f} mm  |  δlim = L/{L_limite} = {delta_limite*10:.2f} mm
        </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6: ELS — FISSURAS
# ═════════════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown("<div class='section-tag'>§ 13.4 + § 17.3.3 — Estado-Limite de Abertura de Fissuras (ELS-W)</div>", unsafe_allow_html=True)
    st.markdown("### Verificação da Abertura de Fissuras")
    
    col_f1, col_f2 = st.columns([1, 1])
    
    with col_f1:
        st.markdown("**Geometria e Armadura**")
        bw_f  = st.number_input("Largura bw (cm)", value=float(st.session_state.get("f_bw",25.0)), key="bw_f")
        h_f   = st.number_input("Altura h (cm)", value=float(st.session_state.get("f_h",60.0)), key="h_f")
        d_f   = st.number_input("Altura útil d (cm)", value=float(st.session_state.get("f_d",55.0)), key="d_f")
        As_f  = st.number_input("As tração (cm²)", value=float(st.session_state.get("f_As",8.04)), key="As_f")
        c_f   = st.number_input("Cobrimento (mm)", value=float(COBRIMENTO[classe_agress]["viga_pilar"]), key="c_f")
        phi_f = st.selectbox("Bitola principal φ (mm)", BARRAS_MM, index=5, key="phi_f")
        n_f   = st.number_input("Nº de barras", value=int(st.session_state.get("f_n",4)), min_value=1, key="n_f")
        
        st.markdown("**Esforços**")
        Ms_kNm = st.number_input("Momento de serviço Ms (kN·m)", value=float(st.session_state.get("f_Ms",80.0)), key="Ms_f")
        
        st.markdown("**Classe de exposição**")
        wk_limite_key = st.selectbox("Classe de agressividade / wk,lim", [
            "CAA I — wk ≤ 0,4 mm",
            "CAA II — wk ≤ 0,3 mm",
            "CAA III — wk ≤ 0,2 mm (faces não expostas à chuva)",
            "CAA III/IV — wk ≤ 0,1 mm (faces expostas a umidade)",
        ], key="wk_lim")
        
        wk_lim_map = {
            "CAA I — wk ≤ 0,4 mm": 0.4,
            "CAA II — wk ≤ 0,3 mm": 0.3,
            "CAA III — wk ≤ 0,2 mm (faces não expostas à chuva)": 0.2,
            "CAA III/IV — wk ≤ 0,1 mm (faces expostas a umidade)": 0.1,
        }
        wk_lim = wk_lim_map[wk_limite_key]
    
    with col_f2:
        st.markdown("**Resultados**")
        
        alpha_e_f = Es / Ecs
        d_linha_f = h_f - d_f
        
        # Posição da linha neutra (estádio II)
        A_eq_f = bw_f / 2
        B_eq_f = alpha_e_f * As_f
        C_eq_f = -alpha_e_f * As_f * d_f
        disc_f  = B_eq_f**2 - 4 * A_eq_f * C_eq_f
        x_f = (-B_eq_f + math.sqrt(disc_f)) / (2 * A_eq_f)  # cm
        
        I2_f = bw_f * x_f**3 / 3 + alpha_e_f * As_f * (d_f - x_f)**2
        
        # Tensão no aço (serviço)
        sigma_s = Ms_kNm * 1e5 * (d_f - x_f) * alpha_e_f / I2_f  # MPa
        # (Ms em kN·cm × 100; I2 em cm⁴; resultado em kN/cm² × 10 → MPa)
        
        # Abertura de fissura — formulação da NBR 6118:2023 (§ 17.3.3.2)
        # wk = phi/(4·tau_b1)·(sigma_s/Es)·(sigma_s/3 + 4·fctm/1.5·rho_r)
        # Simplificada:
        # wk = phi/12.5 · sigma_s/Es · (sigma_s + fctm/rho_r) / (sigma_s)  ← Fórmula completa
        
        # Parâmetros
        fctm_f = 0.3*fck**(2/3) if fck<=50 else 2.12*math.log(1+0.1*(fck+8))
        
        # Área efetiva de concreto em torno das barras
        h_ef = min(2.5*(h_f-d_f), (h_f-x_f)/3, h_f/2)  # cm — seção 17.3.3.2
        Ac_ef = bw_f * h_ef  # cm²
        rho_r = As_f / Ac_ef  # taxa de armadura efetiva
        
        # Espaçamento entre barras
        s_barras = (bw_f - 2*c_f/10 - phi_f/10) / max(n_f-1, 1)  # cm
        
        # Comprimento de transferência — NBR 6118:2023 § 17.3.3.2
        tau_b1 = 1.5 * fctm_f  # MPa — aderência boa, barra nervurada
        lb_rqd = phi_f / (4 * tau_b1) * sigma_s  # mm → multiplicar depois
        
        # Abertura de fissura (fórmula NBR 6118:2023)
        sigma_s_mpa = sigma_s * 10  # kN/cm² → MPa (1 kN/cm² = 10 MPa)
        wk_mm = phi_f * sigma_s_mpa / (12.5 * tau_b1) * (sigma_s_mpa/Es + 4*fctm_f/(1.5*fctm_f*rho_r)) \
                if sigma_s_mpa > 0 else 0
        # Forma simplificada — NBR 6118 (aceita para pré-dimensionamento):
        # wk ≈ phi/(10·fctm) · sigma_s/Es · (3.3·fctm/rho_r + sigma_s)
        # Usaremos formulação mais precisa:
        
        # Formulação do CEB/NBR (ver seção 17.3.3.2):
        # rm = c + phi/10 + k1·k2·phi/(4·rho_r)
        # wk = 1.7 · esrm · esm   onde esm = (sigma_s - beta·sigma_sr)/Es
        k1 = 0.4 if True else 0.8  # barras nervuradas
        k2 = 0.5  # flexão pura
        rm = c_f/10 + phi_f/10 + k1*k2*phi_f/(4*rho_r)/10  # cm — espaçamento médio de fissuras
        
        sigma_sr = Ms_kNm * 1e5 / I2_f * (d_f - x_f) * alpha_e_f * (Mr_kNm/Ms_kNm if 'Mr_kNm' in dir() else 0.8)
        beta = 0.6  # cargas de longa duração
        
        sigma_s_mpa = sigma_s * 10  # MPa (1 kN/cm² = 10 MPa)
        sigma_sr_mpa = sigma_sr * 10
        
        esm = max((sigma_s_mpa - beta * sigma_sr_mpa) / Es, 0.4 * sigma_s_mpa / Es)
        wk_calc = 1.7 * rm * esm * 10  # mm (rm em cm × 10 = mm)
        wk_calc = max(wk_calc, 0.0)
        
        ok_wk = wk_calc <= wk_lim
        
        cols_f = st.columns(2)
        with cols_f[0]:
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Tensão no aço σs</div>
                <div class='result-value'>{sigma_s_mpa:.1f}<span class='result-unit'>MPa</span></div>
                <div class='result-status' style='color:{"#22c55e" if sigma_s_mpa<=0.8*fyk else "#f59e0b"}'>
                {"✓ σs ≤ 0,8·fyk" if sigma_s_mpa <= 0.8*fyk else "⚠ σs > 0,8·fyk"}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>Espaç. médio de fissuras rm</div>
                <div class='result-value'>{rm*10:.1f}<span class='result-unit'>mm</span></div>
            </div>""", unsafe_allow_html=True)
        
        with cols_f[1]:
            st.markdown(f"""
            <div class='result-card {"success" if ok_wk else "error"}'>
                <div class='result-title'>Abertura característica wk</div>
                <div class='result-value'>{wk_calc:.3f}<span class='result-unit'>mm</span></div>
                <div class='result-status' style='color:{"#22c55e" if ok_wk else "#ef4444"}'>
                {"✓ wk ≤ wk,lim = "+str(wk_lim)+" mm" if ok_wk else "✗ wk > wk,lim = "+str(wk_lim)+" mm"}
                </div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='result-card info'>
                <div class='result-title'>ρr (taxa efetiva)</div>
                <div class='result-value'>{rho_r*100:.3f}<span class='result-unit'>%</span></div>
                <div class='result-status' style='color:#7a8ba8'>hef = {h_ef:.1f} cm | Acef = {Ac_ef:.1f} cm²</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='formula-box'>
        x (est. II) = {x_f:.2f} cm  |  I2 = {I2_f:.0f} cm⁴<br>
        σs = Ms·(d-x)·αe / I2 = {sigma_s_mpa:.2f} MPa<br>
        hef = min(2,5·(h-d); (h-x)/3; h/2) = {h_ef:.2f} cm<br>
        ρr = As/Acef = {rho_r:.5f} = {rho_r*100:.3f}%<br>
        rm = c/10 + φ/10 + k1·k2·φ/(4·ρr)/10 = {rm*10:.2f} mm<br>
        εsm = max((σs - β·σsr)/Es; 0,4·σs/Es) = {esm:.6f}<br>
        wk = 1,7·rm·εsm = {wk_calc:.4f} mm  |  wk,lim = {wk_lim} mm
        </div>""", unsafe_allow_html=True)
        
        # Gráfico wk vs Ms
        ms_range = np.linspace(0.1, Ms_kNm * 1.5, 80)
        wk_range = []
        for ms in ms_range:
            sigma_s_i = ms * 1e5 * (d_f - x_f) * alpha_e_f / I2_f * 10
            esm_i = max((sigma_s_i - beta * sigma_sr_mpa) / Es, 0.4 * sigma_s_i / Es)
            wk_range.append(max(1.7 * rm * esm_i * 10, 0))
        
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=ms_range, y=wk_range, mode='lines',
            line=dict(color='#f87171', width=2), name='wk'))
        fig_w.add_hline(y=wk_lim, line_dash="dash", line_color="#fbbf24",
            annotation_text=f"wk,lim = {wk_lim} mm", annotation_font_color="#fbbf24")
        fig_w.add_vline(x=Ms_kNm, line_dash="dot", line_color="#60a5fa",
            annotation_text=f"Ms = {Ms_kNm} kN·m", annotation_font_color="#60a5fa")
        fig_w.update_layout(
            plot_bgcolor='#0d111a', paper_bgcolor='#0d111a', font_color='#9aaec8',
            xaxis_title="Ms (kN·m)", yaxis_title="wk (mm)",
            title="Abertura de Fissura × Momento de Serviço",
            title_font_color='#e8eaf0',
            xaxis=dict(gridcolor='#1e2535'), yaxis=dict(gridcolor='#1e2535'),
            height=280, margin=dict(t=45, b=40, l=60, r=40)
        )
        st.plotly_chart(fig_w, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 7: AÇÕES — NBR 6120:2019
# ═════════════════════════════════════════════════════════════════════════════

# ── Dados NBR 6120:2019 ───────────────────────────────────────────────────────

# Tabela 1 — Pesos específicos de materiais (kN/m³)
PESOS_MATERIAIS = {
    "Concreto armado": 25.0,
    "Concreto simples": 24.0,
    "Aço / ferro fundido": 77.8,
    "Argamassa de cimento e areia": 21.0,
    "Tijolo cerâmico maciço": 18.0,
    "Tijolo cerâmico furado": 13.0,
    "Bloco de concreto simples": 21.0,
    "Bloco de concreto leve": 14.0,
    "Madeira de lei": 11.0,
    "Madeira de pinho/ipê": 8.0,
    "Vidro": 25.0,
    "Solo (argila)": 19.0,
    "Areia úmida": 18.0,
    "Água doce": 10.0,
}

# Tabela 2 — Alvenarias por espessura (kN/m²)
ALVENARIA = {
    "Bloco cerâmico 9 cm": 1.2,
    "Bloco cerâmico 14 cm": 1.8,
    "Bloco cerâmico 19 cm": 2.3,
    "Bloco sílico-calcário 14 cm": 2.1,
    "Bloco sílico-calcário 19 cm": 2.6,
    "Bloco concreto 14 cm": 2.5,
    "Bloco concreto 19 cm": 3.2,
    "Tijolo maciço 10 cm": 2.0,
    "Tijolo maciço 15 cm": 2.8,
    "Tijolo maciço 25 cm": 4.4,
}

# Tabela 3 — Divisórias e caixilhos (kN/m²)
DIVISORIAS = {
    "Drywall simples (1 face)": 0.3,
    "Drywall duplo (2 faces)": 0.5,
    "Divisória de madeira": 0.4,
    "Divisória de vidro (esp. 6mm)": 0.15,
    "Caixilho de alumínio": 0.15,
    "Caixilho de madeira": 0.20,
}

# Tabela 4 — Revestimentos de piso (kN/m²) por espessura base de argamassa
REVESTIMENTOS_PISO = {
    "Cerâmica/porcelanato 5 cm argamassa": 1.0,
    "Cerâmica/porcelanato 7 cm argamassa": 1.4,
    "Marmorite 5 cm argamassa": 1.2,
    "Pedra natural 5 cm argamassa": 1.3,
    "Madeira (assoalho) sobre regularização": 0.5,
    "Carpete sobre regularização 5 cm": 0.9,
    "Revestimento vinílico sobre regularização": 0.6,
    "Piso elevado (sistema aço/alumínio)": 0.4,
}

# Tabela 5 — Telhas (kN/m²)
TELHAS = {
    "Telha cerâmica": 0.53,
    "Telha de concreto": 0.55,
    "Telha de fibrocimento ondulada 5 mm": 0.14,
    "Telha de fibrocimento ondulada 8 mm": 0.22,
    "Telha metálica de aço galvanizado": 0.04,
    "Telha metálica de alumínio": 0.03,
    "Telha de PVC": 0.05,
    "Telha sanduíche (aço + EPS)": 0.12,
}

# Tabela 8 — Forros (kN/m²)
FORROS = {
    "Forro de gesso acartonado": 0.25,
    "Forro de gesso moldado": 0.35,
    "Forro de fibra mineral": 0.10,
    "Forro de PVC": 0.05,
    "Forro de madeira": 0.20,
    "Forro metálico": 0.15,
    "Sem forro": 0.0,
}

# Tabela 10 — Cargas variáveis por tipo de uso (kN/m²)
CARGAS_VARIAVEIS = {
    # Residencial
    "Residencial — Dormitórios / sala / cozinha": 1.5,
    "Residencial — Despensa / lavanderia / circulação privativa": 2.0,
    "Residencial — Corredores / escadas comuns (acesso a apartamentos)": 3.0,
    # Escritórios
    "Escritórios — Salas de trabalho": 2.5,
    "Escritórios — Corredores e escadas comuns": 3.0,
    "Escritórios — Arquivo morto / depósito de materiais": 4.0,
    # Comercial / lojas
    "Lojas e comércio — Piso de vendas": 4.0,
    "Lojas e comércio — Circulações coletivas (shopping, galerias)": 5.0,
    # Cobertura
    "Cobertura — Manutenção (inclinação ≤ 1%)": 1.0,
    "Cobertura — Com painéis solares (inclinação ≤ 1%)": 1.5,
    "Cobertura — Jardim / cobertura ajardinada": 2.0,
    # Garagem
    "Garagem Cat. I — PBT ≤ 30 kN (automoveis)": 3.0,
    "Garagem Cat. II — PBT ≤ 90 kN (van/SUV)": 5.0,
    "Garagem Cat. III — PBT ≤ 160 kN (caminhão leve)": 7.0,
    "Garagem Cat. IV — PBT > 160 kN (caminhão pesado)": 10.0,
    # Escolar
    "Escola — Salas de aula": 3.0,
    "Escola — Auditório (assentos fixos)": 4.0,
    "Escola — Auditório (assentos móveis)": 5.0,
    "Escola — Corredores e escadas": 3.0,
    # Hospital
    "Hospital — Dormitório / enfermaria": 2.0,
    "Hospital — Corredores": 3.0,
    "Hospital — Centros cirúrgicos / salas especiais": 3.0,
    # Hotel
    "Hotel — Dormitórios": 1.5,
    "Hotel — Salas / restaurante / salão": 3.0,
    "Hotel — Corredores / escadas": 3.0,
    # Arquibancada / esporte
    "Arquibancada esportiva (assentos fixos)": 4.0,
    "Arquibancada esportiva (assentos móveis)": 5.0,
    "Biblioteca — Salas de leitura": 3.0,
    "Biblioteca — Depósito de livros": 6.0,
    # Indústria leve
    "Indústria leve": 5.0,
    "Indústria pesada — verificar especificamente": 10.0,
}

# Tabela 11 — Divisórias sem posição definida (kN/m²)
DIVISORIA_CARGA_ADICIONAL = {
    "Sem divisórias": 0.0,
    "p.p. ≤ 1,0 kN/m → +0,5 kN/m²": 0.5,
    "1,0 < p.p. ≤ 2,0 kN/m → +0,75 kN/m²": 0.75,
    "2,0 < p.p. ≤ 3,0 kN/m → +1,0 kN/m²": 1.0,
}

# Tabela 12 — Forças horizontais em guarda-corpos (kN/m)
GUARDACORPOS = {
    "Manutenção": 0.4,
    "Residencial privativo / sem acesso público": 1.0,
    "Acesso público geral": 1.0,
    "Zonas de grande fluxo — paralelo": 2.0,
    "Zonas de grande fluxo — perpendicular": 3.0,
    "Shopping / plataforma / multidão": 3.0,
    "Arquibancada esportiva": 2.0,
}

# Tabela 19 — Redução de cargas variáveis (αn) por número de andares
def alpha_n(n_andares: int) -> float:
    """Fator de redução de carga variável acumulada (Tab. 19 — NBR 6120)"""
    if n_andares <= 3:
        return 1.0
    elif n_andares == 4:
        return 0.8
    elif n_andares == 5:
        return 0.6
    else:
        return 0.4


with tab7:
    st.markdown("<div class='section-tag'>NBR 6120:2019 — Ações para o Cálculo de Estruturas de Edificações</div>",
                unsafe_allow_html=True)
    st.markdown("### ⚖️ Levantamento e Combinação de Ações")

    subtab_a, subtab_b, subtab_c, subtab_d = st.tabs([
        "📦 Cargas Permanentes",
        "🔄 Cargas Variáveis",
        "📐 Combinação de Ações",
        "📚 Tabelas de Referência",
    ])

    # ── Cargas Permanentes ────────────────────────────────────────────────────
    with subtab_a:
        st.markdown("#### Cargas Permanentes — Peso Próprio e Revestimentos")
        st.caption("§ 5 — NBR 6120:2019 | Tabelas 1–9")

        col_pp1, col_pp2 = st.columns([1, 1])

        with col_pp1:
            st.markdown("**Laje / Estrutura**")
            tipo_laje = st.selectbox("Tipo de laje", [
                "Laje maciça de concreto armado",
                "Laje nervurada (verificar peso específico)",
                "Laje pré-moldada (fornecer peso manualmente)",
            ])
            esp_laje = st.number_input("Espessura da laje (cm)", 8.0, 40.0, 12.0, 1.0)
            pp_laje = 25.0 * esp_laje / 100  # kN/m²

            st.markdown("**Revestimento de Piso**")
            rev_piso_key = st.selectbox("Revestimento de piso", list(REVESTIMENTOS_PISO.keys()), index=0)
            pp_piso = REVESTIMENTOS_PISO[rev_piso_key]

            st.markdown("**Forro**")
            forro_key = st.selectbox("Forro", list(FORROS.keys()), index=0)
            pp_forro = FORROS[forro_key]

            st.markdown("**Divisórias fixas (kN/m²)**")
            alvenaria_key = st.selectbox("Parede de alvenaria (por m² de piso)",
                                          ["Sem alvenaria na laje"] + list(ALVENARIA.keys()), index=0)
            if alvenaria_key == "Sem alvenaria na laje":
                pp_alv = 0.0
            else:
                h_alv = st.number_input("Altura da parede (m)", 2.0, 5.0, 2.80, 0.05)
                comp_alv = st.number_input("Comprimento total de paredes (m)", 0.0, 200.0, 10.0, 0.5)
                area_laje = st.number_input("Área da laje em planta (m²)", 1.0, 500.0, 50.0, 1.0)
                pp_alv_linear = ALVENARIA[alvenaria_key] * h_alv  # kN/m (linear)
                pp_alv = pp_alv_linear * comp_alv / area_laje  # kN/m²

        with col_pp2:
            st.markdown("**Instalações e Enchimentos**")
            pp_inst = st.number_input("Instalações hidro/elétricas/ar-cond. (kN/m²)", 0.0, 1.0, 0.10, 0.05)
            pp_extra = st.number_input("Outras cargas permanentes (kN/m²)", 0.0, 5.0, 0.0, 0.1)

            # Totais
            gk_total = pp_laje + pp_piso + pp_forro + pp_alv + pp_inst + pp_extra

            st.markdown("---")
            st.markdown("**📊 Resumo das Cargas Permanentes**")
            st.markdown(f"""
            <div style='background:#0d111a;border-radius:8px;padding:1rem;font-family:JetBrains Mono,monospace;font-size:0.82rem;line-height:2'>
                <span style='color:#7a8ba8'>Peso próprio laje  = </span><span style='color:#60a5fa'>{pp_laje:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>Revestimento piso  = </span><span style='color:#60a5fa'>{pp_piso:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>Forro              = </span><span style='color:#60a5fa'>{pp_forro:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>Alvenaria (dist.)  = </span><span style='color:#60a5fa'>{pp_alv:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>Instalações        = </span><span style='color:#60a5fa'>{pp_inst:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>Outras             = </span><span style='color:#60a5fa'>{pp_extra:.2f} kN/m²</span><br>
                <hr style='border-color:#2a3040;margin:4px 0'>
                <span style='color:#fbbf24;font-weight:700'>gk total           = {gk_total:.2f} kN/m²</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Para coberturas:**")
            incl = st.number_input("Inclinação da cobertura i (%)", 0.0, 30.0, 5.0, 0.5)
            telha_key = st.selectbox("Tipo de telha", list(TELHAS.keys()), index=0)
            pp_telha = TELHAS[telha_key]
            # fórmula NBR 6120 cobertura
            if incl <= 1.0:
                alpha_cob = 1.0
            elif incl < 3.0:
                alpha_cob = 2.0 - 0.5 * incl
            else:
                alpha_cob = 0.5
            q_cob_var = max(0.25, min(0.5, 0.5 * alpha_cob))
            st.markdown(f"""
            <div style='background:#0d111a;border-radius:8px;padding:0.8rem;font-size:0.82rem;font-family:JetBrains Mono,monospace;line-height:1.8'>
                <span style='color:#7a8ba8'>Peso telha         = </span><span style='color:#60a5fa'>{pp_telha:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>q variável cob.    = </span><span style='color:#34d399'>{q_cob_var:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>(α={alpha_cob:.2f}, i={incl:.1f}%)</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Cargas Variáveis ─────────────────────────────────────────────────────
    with subtab_b:
        st.markdown("#### Cargas Variáveis — por Tipo de Uso")
        st.caption("§ 6 — NBR 6120:2019 | Tabela 10, 11, 12")

        col_v1, col_v2 = st.columns([1, 1])

        with col_v1:
            st.markdown("**Uso do Pavimento**")
            uso_key = st.selectbox("Tipo de ocupação", list(CARGAS_VARIAVEIS.keys()), index=0)
            qk_uso = CARGAS_VARIAVEIS[uso_key]
            st.info(f"qk (uso) = **{qk_uso:.1f} kN/m²** — Tabela 10 | NBR 6120:2019")

            st.markdown("**Divisórias sem posição definida (Tab. 11)**")
            div_key = st.selectbox("Carga adicional de divisórias móveis", list(DIVISORIA_CARGA_ADICIONAL.keys()), index=0)
            qk_div = DIVISORIA_CARGA_ADICIONAL[div_key]
            if qk_div > 0:
                if qk_uso >= 4.0:
                    st.caption("ℹ️ Dispensa-se a carga adicional para q ≥ 4,0 kN/m² (exceto paredes > 3,0 kN/m)")
                    qk_div_efetivo = 0.0
                else:
                    qk_div_efetivo = qk_div
            else:
                qk_div_efetivo = 0.0

            qk_total_var = qk_uso + qk_div_efetivo
            st.markdown(f"""
            <div style='background:#0d111a;border-radius:8px;padding:0.8rem;font-family:JetBrains Mono,monospace;font-size:0.82rem;line-height:1.8;margin-top:0.5rem'>
                <span style='color:#7a8ba8'>qk (uso)           = </span><span style='color:#60a5fa'>{qk_uso:.2f} kN/m²</span><br>
                <span style='color:#7a8ba8'>qk (divisórias)    = </span><span style='color:#60a5fa'>{qk_div_efetivo:.2f} kN/m²</span><br>
                <hr style='border-color:#2a3040;margin:4px 0'>
                <span style='color:#fbbf24;font-weight:700'>qk total           = {qk_total_var:.2f} kN/m²</span>
            </div>
            """, unsafe_allow_html=True)

        with col_v2:
            st.markdown("**Redução por número de pavimentos (Tab. 19)**")
            n_pav = st.number_input("Número de pavimentos acima (para pilar/fundação)", 1, 30, 1, 1)
            an = alpha_n(n_pav)
            st.markdown(f"""
            <div style='background:#111827;border-radius:8px;padding:0.8rem;font-size:0.82rem;font-family:JetBrains Mono,monospace;line-height:1.8'>
                <span style='color:#7a8ba8'>n pavimentos = </span><span style='color:#60a5fa'>{n_pav}</span><br>
                <span style='color:#fbbf24;font-weight:700'>αn = {an:.2f}</span><br>
                <span style='color:#7a8ba8;font-size:0.75rem'>Nota: não aplicável a garagens, coberturas, depósitos, arquibancadas</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Forças horizontais em guarda-corpos (Tab. 12)**")
            gc_key = st.selectbox("Tipo de guarda-corpo", list(GUARDACORPOS.keys()), index=0)
            fh_gc = GUARDACORPOS[gc_key]
            st.markdown(f"""
            <div style='background:#0d111a;border-radius:8px;padding:0.8rem;font-size:0.82rem;font-family:JetBrains Mono,monospace;line-height:1.8;margin-top:0.5rem'>
                <span style='color:#7a8ba8'>Força horiz. guarda-corpo = </span><span style='color:#f9a8d4'>{fh_gc:.1f} kN/m</span><br>
                <span style='color:#7a8ba8;font-size:0.75rem'>Aplicada horizontalmente a 1,0 m do piso</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Combinação de Ações ───────────────────────────────────────────────────
    with subtab_c:
        st.markdown("#### Combinação de Ações — ELU e ELS")
        st.caption("§ 11 — NBR 6118:2023 | Combinações Normal, Especial e Excepcional")

        col_c1, col_c2 = st.columns([1, 1])

        with col_c1:
            st.markdown("**Ações de entrada**")
            gk_in = st.number_input("gk — carga permanente total (kN/m²)", 0.0, 50.0, 5.0, 0.1)
            qk_in = st.number_input("qk — carga variável principal (kN/m²)", 0.0, 20.0, 2.0, 0.1)
            qk2_in = st.number_input("qk₂ — ação variável secundária (kN/m²)", 0.0, 10.0, 0.0, 0.1)
            comb_tipo = st.selectbox("Tipo de combinação", ["Normal", "Especial/Construção", "Excepcional"])

        with col_c2:
            st.markdown("**Coeficientes (Tab. 11.2 — NBR 6118:2023)**")

            if comb_tipo == "Normal":
                gf1 = 1.4  # permanente desfavorável
                gf2 = 1.4  # variável
                psi0 = 0.7
                psi1 = 0.6  # ELS quase-permanente ψ2
                psi2 = 0.4  # ELS frequente ψ1
            elif comb_tipo == "Especial/Construção":
                gf1 = 1.3
                gf2 = 1.3
                psi0 = 0.7
                psi1 = 0.6
                psi2 = 0.4
            else:  # Excepcional
                gf1 = 1.2
                gf2 = 1.0
                psi0 = 1.0
                psi1 = 0.6
                psi2 = 0.4

            # ELU — combinação última
            Fd_elu = gf1 * gk_in + gf2 * qk_in + gf2 * psi0 * qk2_in
            # ELS — combinação rara
            Fd_els_rara = gk_in + qk_in + psi0 * qk2_in
            # ELS — combinação frequente
            Fd_els_freq = gk_in + psi2 * qk_in
            # ELS — combinação quase-permanente
            Fd_els_qp = gk_in + psi1 * qk_in

            st.markdown(f"""
            <div style='background:#0d111a;border-radius:8px;padding:1rem;font-family:JetBrains Mono,monospace;font-size:0.82rem;line-height:2'>
                <span style='color:#7a8ba8;font-size:0.8rem'>γf1 = {gf1} | γf2 = {gf2} | ψ0 = {psi0} | ψ1 = {psi2} | ψ2 = {psi1}</span><br>
                <hr style='border-color:#2a3040;margin:4px 0'>
                <span style='color:#ef4444;font-weight:700'>ELU  (última):        Fd = {Fd_elu:.2f} kN/m²</span><br>
                <span style='color:#fbbf24'>ELS  (rara):          Fd = {Fd_els_rara:.2f} kN/m²</span><br>
                <span style='color:#60a5fa'>ELS  (frequente):     Fd = {Fd_els_freq:.2f} kN/m²</span><br>
                <span style='color:#34d399'>ELS  (quase-perm.):   Fd = {Fd_els_qp:.2f} kN/m²</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='formula-box' style='margin-top:0.8rem'>
            <b>ELU (normal):</b>  Fd = γf1·gk + γf2·(qk + ψ0·qk₂)<br>
               = {gf1}×{gk_in} + {gf2}×({qk_in} + {psi0}×{qk2_in}) = <b>{Fd_elu:.2f} kN/m²</b><br><br>
            <b>ELS — quase-permanente:</b>  Fd = gk + ψ2·qk<br>
               = {gk_in} + {psi1}×{qk_in} = <b>{Fd_els_qp:.2f} kN/m²</b>
            </div>
            """, unsafe_allow_html=True)

    # ── Tabelas de referência ─────────────────────────────────────────────────
    with subtab_d:
        st.markdown("#### 📚 Tabelas de Referência — NBR 6120:2019")

        ref_tab = st.radio("Selecionar tabela", [
            "Tab. 1 — Pesos específicos",
            "Tab. 2 — Alvenarias",
            "Tab. 5 — Telhas",
            "Tab. 10 — Cargas variáveis por uso",
            "Tab. 12 — Guarda-corpos",
            "Tab. 19 — Redução por pavimentos",
        ], horizontal=True)

        if ref_tab == "Tab. 1 — Pesos específicos":
            df_mat = pd.DataFrame([
                {"Material": k, "γ (kN/m³)": v}
                for k, v in PESOS_MATERIAIS.items()
            ])
            st.dataframe(df_mat, use_container_width=True, hide_index=True)
            st.caption("Fonte: Tabela 1, ABNT NBR 6120:2019 (seleção)")

        elif ref_tab == "Tab. 2 — Alvenarias":
            df_alv = pd.DataFrame([
                {"Tipo de Alvenaria": k, "Carga (kN/m²)": v}
                for k, v in ALVENARIA.items()
            ])
            st.dataframe(df_alv, use_container_width=True, hide_index=True)
            st.caption("Carga por metro quadrado de parede. Fonte: Tabela 2, ABNT NBR 6120:2019")

        elif ref_tab == "Tab. 5 — Telhas":
            df_tel = pd.DataFrame([
                {"Tipo de Telha": k, "Carga (kN/m²)": v}
                for k, v in TELHAS.items()
            ])
            st.dataframe(df_tel, use_container_width=True, hide_index=True)
            st.caption("Fonte: Tabela 5, ABNT NBR 6120:2019")

        elif ref_tab == "Tab. 10 — Cargas variáveis por uso":
            df_var = pd.DataFrame([
                {"Uso / Ocupação": k, "qk (kN/m²)": v}
                for k, v in CARGAS_VARIAVEIS.items()
            ])
            st.dataframe(df_var, use_container_width=True, hide_index=True)
            st.caption("Fonte: Tabela 10, ABNT NBR 6120:2019 (seleção)")

        elif ref_tab == "Tab. 12 — Guarda-corpos":
            df_gc = pd.DataFrame([
                {"Tipo de Guarda-corpo / Área": k, "Fh (kN/m)": v}
                for k, v in GUARDACORPOS.items()
            ])
            st.dataframe(df_gc, use_container_width=True, hide_index=True)
            st.caption("Forças horizontais. Fonte: Tabela 12, ABNT NBR 6120:2019")

        elif ref_tab == "Tab. 19 — Redução por pavimentos":
            df_an = pd.DataFrame([
                {"Número de pavimentos": n, "αn (fator de redução)": alpha_n(n)}
                for n in [1, 2, 3, 4, 5, 6, 7, 8, 10]
            ])
            st.dataframe(df_an, use_container_width=True, hide_index=True)
            st.caption("Redução de cargas variáveis para pilares e fundações. Fonte: Tabela 19, ABNT NBR 6120:2019")
            st.warning("Não aplicável a: garagens, reservatórios, coberturas, jardins, depósitos, áreas técnicas, indústrias, estádios, teatros, cinemas, passarelas, assembleias.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 8: LOTE SKETCHUP — Processamento em lote do modelo importado
# ═════════════════════════════════════════════════════════════════════════════

with tab8:
    st.markdown("<div class='section-tag'>Processamento em Lote — Modelo SketchUp</div>", unsafe_allow_html=True)
    st.markdown("### 📊 Verificação de Todos os Elementos Importados")

    _els_batch = st.session_state.get("sk_elements", [])

    if not _els_batch:
        st.info("Nenhum modelo importado. Use o painel **📥 Importar do SketchUp** na barra lateral.")
        st.markdown("""
        <div style='background:#1a2235;border:1px solid #2a3a55;border-radius:8px;padding:1.5rem;margin-top:1rem'>
        <h4 style='color:#60a5fa;margin-bottom:0.8rem'>Como usar</h4>
        <ol style='color:#9aaec8;line-height:2'>
        <li>Abra o SketchUp Pro com a extensão v2.0 instalada</li>
        <li>Selecione cada elemento e use <strong>⚙️ Configurar Elemento</strong> para inserir os esforços</li>
        <li>Use <strong>📤 Exportar Modelo → Python</strong> para gerar o arquivo JSON</li>
        <li>Faça upload do JSON no painel lateral desta aplicação</li>
        <li>Clique em <strong>⚡ Aplicar nos formulários</strong> para pré-preencher um elemento</li>
        <li>Nesta aba, todos os elementos são verificados automaticamente</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    else:
        _data_batch = st.session_state.get("sk_data", {})
        _gp_b = _data_batch.get("global_parameters", {})
        _exp_date = _data_batch.get("exportado_em", "—")

        # Cabeçalho do modelo
        col_hb1, col_hb2, col_hb3, col_hb4 = st.columns(4)
        col_hb1.metric("Total de Elementos", len(_els_batch))
        col_hb2.metric("Vigas", sum(1 for e in _els_batch if e.get("tipo") == "viga"))
        col_hb3.metric("Pilares", sum(1 for e in _els_batch if e.get("tipo") == "pilar"))
        col_hb4.metric("Lajes", sum(1 for e in _els_batch if e.get("tipo") == "laje"))

        st.markdown(f"""<div style='background:#0d111a;border-radius:6px;padding:0.6rem 1rem;
            font-size:0.78rem;color:#7a8ba8;font-family:monospace;margin-bottom:1rem'>
            Concreto: {_gp_b.get("classe_concreto","?")} | Aço: {_gp_b.get("tipo_aco","?")} |
            Combinação: {_gp_b.get("tipo_combinacao","?")} |
            Agressividade: {_gp_b.get("classe_agressividade","?")} |
            Exportado em: {_exp_date}
        </div>""", unsafe_allow_html=True)

        # Executa cálculos em lote
        _batch_results = []
        for _el in _els_batch:
            _r = _batch_calc(_el, fck, fyd_v, fcd_val, fctd_val(fck))
            _batch_results.append(_r)

        # Tabela de resumo
        _n_ok   = sum(1 for r in _batch_results if r["status"] == "✅")
        _n_fail = sum(1 for r in _batch_results if r["status"] == "❌")

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("✅ Aprovados",  _n_ok)
        col_s2.metric("❌ Reprovados", _n_fail)
        col_s3.metric("Taxa de aprovação", f"{_n_ok/len(_batch_results)*100:.0f}%")

        st.markdown("---")

        # Resultados por elemento
        for _r in _batch_results:
            _color = "#22c55e" if _r["status"] == "✅" else "#ef4444"
            _icon  = "✅" if _r["status"] == "✅" else "❌"

            with st.expander(f"{_icon} **[{_r['tipo']}]** {_r['nome']}", expanded=(_r["status"] == "❌")):
                if not _r["checks"]:
                    st.warning("Nenhuma verificação executada — esforços = 0 ou tipo não suportado.")
                else:
                    _rows = []
                    for _c in _r["checks"]:
                        _rows.append({
                            "Verificação": _c["V"],
                            "Resultado": _c["R"],
                            "Limite": _c["L"],
                            "Status": "✅ OK" if _c["ok"] else "❌ FALHOU",
                        })
                    _df = pd.DataFrame(_rows)
                    st.dataframe(
                        _df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Status": st.column_config.TextColumn(width="small"),
                        }
                    )

        # Exportar tabela como CSV
        st.markdown("---")
        _export_rows = []
        for _r in _batch_results:
            for _c in _r.get("checks", []):
                _export_rows.append({
                    "Nome": _r["nome"],
                    "Tipo": _r["tipo"],
                    "Status Geral": _r["status"],
                    "Verificação": _c["V"],
                    "Resultado": _c["R"],
                    "Limite": _c["L"],
                    "OK": "SIM" if _c["ok"] else "NÃO",
                })
        if _export_rows:
            _export_df = pd.DataFrame(_export_rows)
            st.download_button(
                label="📥 Exportar resultados como CSV",
                data=_export_df.to_csv(index=False, sep=";").encode("utf-8"),
                file_name="verificacao_estrutural.csv",
                mime="text/csv",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 9 — ANÁLISE ESTRUTURAL (SOLVER 3D)
# Fase 6 do plano de implementação
# Tasks: T6.1–T6.9
# ═══════════════════════════════════════════════════════════════════════════════

# ── Imports dos módulos do solver (lazy, para não quebrar se não instalados) ──
def _import_solver_modules():
    """Importa módulos do solver. Retorna dict com módulos ou erros."""
    mods = {}
    for name, mod_name in [
        ("pw",  "pynite_wrapper"),
        ("fd",  "floor_detector"),
        ("ld",  "load_distributor"),
        ("lc",  "load_combiner"),
        ("ji",  "json_importer"),
    ]:
        try:
            import importlib
            mods[name] = importlib.import_module(mod_name)
        except ImportError as e:
            mods[name] = None
            mods[f"{name}_err"] = str(e)
    return mods


# ─── TAB 9: ANÁLISE ESTRUTURAL ────────────────────────────────────────────────
with tab9:
    st.markdown("<div class='section-tag'>Análise Estrutural 3D — PyNiteFEA + NBR 6118:2023</div>",
                unsafe_allow_html=True)

    _smods = _import_solver_modules()
    _solver_ok = all(_smods.get(k) is not None for k in ("pw","fd","lc","ji"))

    if not _solver_ok:
        _missing = [k for k in ("pw","fd","lc","ji") if _smods.get(k) is None]
        st.error(f"❌ Módulos não encontrados: {', '.join(_missing)}. "
                 f"Verifique se todos os arquivos estão em `streamlit_app/`.")
        st.stop()

    pw_mod = _smods["pw"]
    fd_mod = _smods["fd"]
    lc_mod = _smods["lc"]

    # ── T6.8: Compatibilidade v2.0 / v3.0 ─────────────────────────────────────
    _sk_data = st.session_state.get("sk_data")

    if _sk_data is None:
        st.info("📥 Nenhum modelo carregado. Faça o upload do JSON exportado pelo SketchUp no painel lateral.")
        st.markdown("""
        <div style='background:#1a2235;border:1px solid #2a3a55;border-radius:8px;padding:1.5rem;margin-top:1rem'>
        <h4 style='color:#60a5fa;margin-bottom:0.8rem'>Fluxo de trabalho</h4>
        <ol style='color:#9aaec8;line-height:2.2'>
          <li>No SketchUp, modele vigas e pilares com a extensão v3.0</li>
          <li>Insira as cargas (paredes, revestimento, variável) em cada elemento</li>
          <li>Exporte o JSON via <strong>Plugins → Exportador Estrutural → Exportar</strong></li>
          <li>Faça upload do JSON no painel lateral (📥 Importar do SketchUp)</li>
          <li>Volte aqui e clique em <strong>🔍 Analisar Estrutura</strong></li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    else:
        _schema_ver = _sk_data.get("schema_version", "2.0")
        _elements   = _sk_data.get("elementos_estruturais", [])
        _has_posicao = any("posicao" in el for el in _elements)

        if _schema_ver == "2.0" or not _has_posicao:
            st.warning(
                "⚠️ **JSON v2.0 detectado** — este arquivo não contém coordenadas 3D (`posicao`). "
                "O solver automático requer o exportador v3.0. "
                "Use a aba **📊 Lote SketchUp** para verificação manual com esforços inseridos manualmente."
            )
        else:
            # ── T6.2: Detecção e confirmação de pavimentos ─────────────────────
            st.markdown("### 1️⃣ Pavimentos detectados")

            _floors_detected = fd_mod.detect_floors(_elements)
            _floor_assign    = fd_mod.assign_elements_to_floors(_elements, _floors_detected)

            _n_floors = len(_floors_detected)
            _floor_labels = [f"Pav {i+1} — Z={f['z_ref']:.2f}m ({f['n_elements']} elem.)"
                             for i, f in enumerate(_floors_detected)]

            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                _floor_rows = []
                for i, fl in enumerate(_floors_detected):
                    _floor_rows.append({
                        "Pavimento": f"Pav {i+1}",
                        "Z ref (m)": round(fl["z_ref"], 3),
                        "Elementos": fl["n_elements"],
                        "Vigas":     fl.get("n_vigas", 0),
                        "Pilares":   fl.get("n_pilares", 0),
                    })
                _floor_df = pd.DataFrame(_floor_rows)
                st.dataframe(_floor_df, use_container_width=True, hide_index=True)
            with col_f2:
                st.metric("Pavimentos", _n_floors)
                st.metric("Total elementos", len(_elements))
                vigas_t   = sum(1 for e in _elements if e.get("tipo") == "viga")
                pilares_t = sum(1 for e in _elements if e.get("tipo") == "pilar")
                st.metric("Vigas / Pilares", f"{vigas_t} / {pilares_t}")

            st.markdown("---")

            # ── T6.3: Revisão de cargas ────────────────────────────────────────
            st.markdown("### 2️⃣ Cargas por elemento")

            _load_totals_preview = lc_mod.combine_loads(_elements, slab_loads={})
            _warnings = lc_mod.get_load_warnings(_elements, _load_totals_preview)
            for w in _warnings:
                st.warning(w)

            _load_rows = []
            for eid, ltot in _load_totals_preview.items():
                _el = next((e for e in _elements if e["id"] == eid), {})
                _load_rows.append({
                    "ID": eid,
                    "Nome": _el.get("nome", eid),
                    "Tipo": _el.get("tipo", "?"),
                    "G (kN/m)": round(ltot.get("G_kN_m", 0), 2),
                    "Q (kN/m)": round(ltot.get("Q_kN_m", 0), 2),
                    "Total G+Q": round(ltot.get("G_kN_m", 0) + ltot.get("Q_kN_m", 0), 2),
                })
            if _load_rows:
                _load_df = pd.DataFrame(_load_rows)
                _has_loads = _load_df["Total G+Q"].sum() > 0
                st.dataframe(
                    _load_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "G (kN/m)":   st.column_config.NumberColumn(format="%.2f"),
                        "Q (kN/m)":   st.column_config.NumberColumn(format="%.2f"),
                        "Total G+Q":  st.column_config.NumberColumn(format="%.2f"),
                    }
                )
                if not _has_loads:
                    st.warning("⚠️ Nenhuma carga inserida. O solver rodará com G=Q=0 (apenas peso próprio se ativado).")

            st.markdown("---")

            # ── T6.4: Botão de análise + progress ─────────────────────────────
            st.markdown("### 3️⃣ Executar análise")

            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
            with col_btn1:
                _run_analysis = st.button(
                    "🔍 Analisar Estrutura",
                    type="primary",
                    use_container_width=True,
                    help="Monta o modelo FEM 3D com PyNiteFEA e resolve ELU + ELS"
                )
            with col_btn2:
                _use_g_only = st.checkbox("Só peso próprio (G)", value=False,
                                          help="Ignora Q — útil para validação")
            with col_btn3:
                if st.button("🗑️ Limpar resultados", use_container_width=True):
                    st.session_state["solver_results"] = None
                    st.session_state["solver_ran"]     = False
                    st.session_state["solver_error"]   = None
                    st.rerun()

            if _run_analysis:
                _prog = st.progress(0, text="Montando modelo FEM...")
                try:
                    _prog.progress(20, text="Calculando cargas distribuídas...")
                    _load_totals = lc_mod.combine_loads(_elements, slab_loads={})

                    _prog.progress(45, text="Resolvendo sistema de equações (PyNiteFEA)...")
                    _results = pw_mod.run_analysis(
                        json_data   = _sk_data,
                        load_totals = _load_totals,
                        use_g_only  = _use_g_only,
                    )

                    _prog.progress(90, text="Processando resultados...")
                    st.session_state["solver_results"]    = _results
                    st.session_state["solver_load_totals"]= _load_totals
                    st.session_state["solver_json_data"]  = _sk_data
                    st.session_state["solver_ran"]        = True
                    st.session_state["solver_error"]      = None
                    _prog.progress(100, text="✅ Análise concluída!")
                    st.rerun()
                except Exception as _exc:
                    _prog.empty()
                    st.session_state["solver_error"] = str(_exc)
                    st.session_state["solver_ran"]   = False

            if st.session_state.get("solver_error"):
                st.error(f"❌ Erro na análise: {st.session_state['solver_error']}")
                with st.expander("Detalhes técnicos"):
                    st.code(st.session_state["solver_error"])

            # ── T6.5 + T6.6: Resultados — 3D + Diagramas ──────────────────────
            _results = st.session_state.get("solver_results")
            if _results:
                st.markdown("---")
                st.markdown("### 4️⃣ Resultados")

                # ── Tabela resumo de esforços ──────────────────────────────────
                _tbl = pw_mod.get_max_forces_table(_results, _elements)
                if _tbl:
                    st.markdown("**Esforços máximos de cálculo (ELU)**")
                    _tbl_df = pd.DataFrame(_tbl)
                    st.dataframe(
                        _tbl_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Md_max (kNm)": st.column_config.NumberColumn(format="%.2f"),
                            "Vd_max (kN)":  st.column_config.NumberColumn(format="%.2f"),
                            "Nd_max (kN)":  st.column_config.NumberColumn(format="%.2f"),
                        }
                    )

                # ── T6.5: Vista 3D do modelo ───────────────────────────────────
                st.markdown("**Modelo 3D — geometria e esforços**")
                _fig3d = go.Figure()
                _colormap = {"viga": "#60a5fa", "pilar": "#34d399"}

                for _el in _elements:
                    if "posicao" not in _el:
                        continue
                    _pos  = _el["posicao"]
                    _ni   = _pos.get("no_inicio", {})
                    _nf   = _pos.get("no_fim", {})
                    _tipo = _el.get("tipo", "viga")
                    _cor  = _colormap.get(_tipo, "#f9a8d4")
                    _eid  = _el["id"]
                    _r    = _results.get(_eid, {})
                    _md   = abs(_r.get("Md_max", 0)) or abs(_r.get("Md_min", 0))
                    _vd   = abs(_r.get("Vd_max", 0))

                    _fig3d.add_trace(go.Scatter3d(
                        x=[_ni.get("x",0), _nf.get("x",0)],
                        y=[_ni.get("y",0), _nf.get("y",0)],
                        z=[_ni.get("z",0), _nf.get("z",0)],
                        mode="lines+markers",
                        line=dict(color=_cor, width=6),
                        marker=dict(size=4, color=_cor),
                        name=f"{_el.get('nome',_eid)} ({_tipo})",
                        hovertemplate=(
                            f"<b>{_el.get('nome',_eid)}</b><br>"
                            f"Tipo: {_tipo}<br>"
                            f"Md={_md:.1f} kNm | Vd={_vd:.1f} kN<extra></extra>"
                        ),
                    ))

                _fig3d.update_layout(
                    scene=dict(
                        xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)",
                        bgcolor="#0d1117",
                        xaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
                        yaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
                        zaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
                    ),
                    paper_bgcolor="#0d1117",
                    font=dict(color="#e8eaf0"),
                    height=500,
                    margin=dict(l=0, r=0, t=30, b=0),
                    legend=dict(
                        bgcolor="#161b27", bordercolor="#2a3040", borderwidth=1,
                        font=dict(size=11),
                    ),
                )
                st.plotly_chart(_fig3d, use_container_width=True)

                # ── T6.6: Diagramas M/V/N por elemento ────────────────────────
                st.markdown("**Diagramas de esforços por elemento**")
                _el_ids_with_results = [eid for eid in _results if _results[eid].get("diag_M")]
                if _el_ids_with_results:
                    _el_labels_diag = {
                        eid: next((e.get("nome", eid) for e in _elements if e["id"] == eid), eid)
                        for eid in _el_ids_with_results
                    }
                    _sel_diag = st.selectbox(
                        "Elemento",
                        _el_ids_with_results,
                        format_func=lambda eid: f"{_el_labels_diag[eid]} [{eid}]",
                        key="solver_diag_sel"
                    )
                    _r_diag = _results[_sel_diag]
                    _x_rel  = _r_diag.get("x_pontos", [])
                    _L_m    = _r_diag.get("L_m", 1.0)
                    _x_m    = [round(x * _L_m, 3) for x in _x_rel]

                    _fig_diag = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=("Momento Fletor Md (kNm)", "Força Cortante Vd (kN)", "Força Normal Nd (kN)"),
                        vertical_spacing=0.10,
                    )
                    _diag_style = dict(mode="lines", fill="tozeroy")
                    _fig_diag.add_trace(go.Scatter(
                        x=_x_m, y=_r_diag.get("diag_M", []),
                        line=dict(color="#60a5fa", width=2),
                        fillcolor="rgba(96,165,250,0.15)",
                        name="M (kNm)", **_diag_style
                    ), row=1, col=1)
                    _fig_diag.add_trace(go.Scatter(
                        x=_x_m, y=_r_diag.get("diag_V", []),
                        line=dict(color="#f87171", width=2),
                        fillcolor="rgba(248,113,113,0.15)",
                        name="V (kN)", **_diag_style
                    ), row=2, col=1)
                    _fig_diag.add_trace(go.Scatter(
                        x=_x_m, y=_r_diag.get("diag_N", []),
                        line=dict(color="#34d399", width=2),
                        fillcolor="rgba(52,211,153,0.15)",
                        name="N (kN)", **_diag_style
                    ), row=3, col=1)

                    _fig_diag.update_layout(
                        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                        font=dict(color="#e8eaf0"), height=600,
                        showlegend=False,
                        margin=dict(l=50, r=20, t=50, b=40),
                    )
                    for _ax in ["xaxis", "xaxis2", "xaxis3"]:
                        _fig_diag.update_layout(**{_ax: dict(
                            title="x (m)", gridcolor="#2a3040", zerolinecolor="#4a5568"
                        )})
                    st.plotly_chart(_fig_diag, use_container_width=True)

                    # Valores extremos do elemento selecionado
                    col_ext1, col_ext2, col_ext3, col_ext4 = st.columns(4)
                    col_ext1.metric("Md⁺ máx (kNm)", f"{_r_diag.get('Md_max',0):.2f}")
                    col_ext2.metric("Md⁻ máx (kNm)", f"{_r_diag.get('Md_min',0):.2f}")
                    col_ext3.metric("Vd máx (kN)",   f"{_r_diag.get('Vd_max',0):.2f}")
                    col_ext4.metric("Nd máx (kN)",   f"{_r_diag.get('Nd_max',0):.2f}")

                st.markdown("---")

                # ── T6.7: Exportar esforços para as abas de verificação NBR ────
                st.markdown("### 5️⃣ Exportar para verificações NBR")
                st.markdown(
                    "Selecione um elemento para preencher automaticamente os formulários "
                    "das abas **Flexão**, **Cisalhamento** e **Pilar**."
                )

                _exp_ids = [eid for eid in _results]
                _exp_labels = {
                    eid: next((f"[{e.get('tipo','?').upper()}] {e.get('nome',eid)}"
                               for e in _elements if e["id"] == eid), eid)
                    for eid in _exp_ids
                }
                col_ex1, col_ex2 = st.columns([3, 1])
                with col_ex1:
                    _exp_sel = st.selectbox(
                        "Elemento a exportar",
                        _exp_ids,
                        format_func=lambda eid: _exp_labels[eid],
                        key="solver_export_sel"
                    )
                with col_ex2:
                    _do_export = st.button("⚡ Aplicar nos formulários",
                                           use_container_width=True, type="primary")

                if _do_export and _exp_sel:
                    _exp_el = next((e for e in _elements if e["id"] == _exp_sel), None)
                    _exp_r  = _results[_exp_sel]
                    if _exp_el:
                        # Preenche _apply_element com geometria do elemento
                        _apply_element(_exp_el)
                        # Sobrescreve os esforços com os calculados pelo solver
                        _geom = _exp_el.get("geometria", {})
                        _tipo_exp = _exp_el.get("tipo", "viga")
                        _h_exp    = float(_geom.get("altura",  60.0))
                        _bw_exp   = float(_geom.get("largura", 25.0))
                        _cnom_exp = float(_exp_el.get("parametros_calculo", {}).get("cobrimento_nominal", 30.0))
                        _phi_e    = float(_exp_el.get("parametros_calculo", {}).get("phi_estribo", 8.0))
                        _phi_l    = float(_exp_el.get("parametros_calculo", {}).get("phi_longitudinal", 20.0))
                        _d_exp    = _h_exp - _cnom_exp/10 - _phi_e/10 - _phi_l/20

                        _Md = max(abs(_exp_r.get("Md_max", 0)), abs(_exp_r.get("Md_min", 0)))
                        _Vd = abs(_exp_r.get("Vd_max", 0))
                        _Nd = abs(_exp_r.get("Nd_max", 0))

                        if _tipo_exp == "viga":
                            st.session_state["v_bw"]  = _bw_exp
                            st.session_state["v_h"]   = _h_exp
                            st.session_state["v_Md"]  = round(_Md, 2)
                            st.session_state["c_bw"]  = _bw_exp
                            st.session_state["c_d"]   = round(_d_exp, 1)
                            st.session_state["c_Vd"]  = round(_Vd, 2)
                            st.success(f"✅ Esforços de **{_exp_labels[_exp_sel]}** aplicados nas abas Flexão e Cisalhamento.")
                        elif _tipo_exp == "pilar":
                            st.session_state["p_b"]   = _bw_exp
                            st.session_state["p_h"]   = _h_exp
                            st.session_state["p_Nd"]  = round(_Nd, 2)
                            st.session_state["p_Mdx"] = round(_Md, 2)
                            st.success(f"✅ Esforços de **{_exp_labels[_exp_sel]}** aplicados na aba Pilar.")
                        st.rerun()

                # ── T7: Relatório PDF ──────────────────────────────────
                st.markdown("---")
                st.markdown("### 6️⃣ Relatório PDF")
                if not _HAS_REPORT:
                    st.warning("⚠️ `report_generator.py` não encontrado em `streamlit_app/`.")
                else:
                    col_pdf1, col_pdf2 = st.columns([3, 1])
                    with col_pdf1:
                        _titulo_pdf = st.text_input(
                            "Nome do projeto / obra",
                            value="Sobrado",
                            key="pdf_titulo",
                        )
                    with col_pdf2:
                        _gerar_btn = st.button(
                            "📄 Gerar PDF",
                            use_container_width=True,
                            type="primary",
                        )
                    if _gerar_btn:
                        with st.spinner("Gerando relatório..."):
                            try:
                                import importlib as _il
                                import datetime as _dt
                                _fd2     = _il.import_module("floor_detector")
                                _jd_pdf  = st.session_state.get("solver_json_data", {})
                                _fl_pdf  = _fd2.detect_floors(
                                    _jd_pdf.get("elementos_estruturais", []))
                                _pdf_b   = _gerar_pdf(
                                    json_data   = _jd_pdf,
                                    results     = st.session_state.get("solver_results", {}),
                                    load_totals = st.session_state.get("solver_load_totals", {}),
                                    floors      = _fl_pdf,
                                    titulo      = _titulo_pdf,
                                )
                                _ts    = _dt.datetime.now().strftime("%Y%m%d_%H%M")
                                _fname = f"relatorio_estrutural_{_ts}.pdf"
                                st.download_button(
                                    label="⬇️ Baixar Relatório PDF",
                                    data=_pdf_b,
                                    file_name=_fname,
                                    mime="application/pdf",
                                    use_container_width=True,
                                )
                                st.success(
                                    f"✅ Relatório gerado com sucesso — "
                                    f"{len(_pdf_b)//1024} KB"
                                )
                            except Exception as _pdf_exc:
                                st.error(f"❌ Erro ao gerar PDF: {_pdf_exc}")
