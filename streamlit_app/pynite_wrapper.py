"""
pynite_wrapper.py — v3.1
Mudanças em relação à v3.0:
  - _apply_member_loads(): lê point_loads[] do elemento JSON e aplica via add_member_pt_load
  - run_analysis(): passa json_data diretamente para _apply_member_loads poder ler point_loads por elemento
  - Resto inalterado.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any


# ── Constantes de material ────────────────────────────────────────────────────

_CONCRETOS: Dict[str, Dict[str, float]] = {
    "C20": {"fck": 20, "Ecs": 0.85 * 5600 * math.sqrt(20)},
    "C25": {"fck": 25, "Ecs": 0.85 * 5600 * math.sqrt(25)},
    "C30": {"fck": 30, "Ecs": 0.85 * 5600 * math.sqrt(30)},
    "C35": {"fck": 35, "Ecs": 0.85 * 5600 * math.sqrt(35)},
    "C40": {"fck": 40, "Ecs": 0.85 * 5600 * math.sqrt(40)},
    "C45": {"fck": 45, "Ecs": 0.85 * 5600 * math.sqrt(45)},
    "C50": {"fck": 50, "Ecs": 0.85 * 5600 * math.sqrt(50)},
}

_COMBOS = {
    "normal":      {"G": 1.4, "Q": 1.4},
    "especial":    {"G": 1.3, "Q": 1.3},
    "excepcional": {"G": 1.2, "Q": 1.0},
}

_COMBOS_ELS = {
    "ELS_qperm":  {"G": 1.0, "Q": 0.3},
    "ELS_freq":   {"G": 1.0, "Q": 0.6},
    "ELS_rara":   {"G": 1.0, "Q": 1.0},
}

N_DIAG_POINTS   = 20
RHO_CONCRETO    = 25.0
DEFAULT_TOL_NOS = 0.005


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários internos (inalterados)
# ─────────────────────────────────────────────────────────────────────────────

def _torsion_J(b: float, h: float) -> float:
    b, h = min(b, h), max(b, h)
    return (b * h**3 / 3.0) * (1.0 - 0.63 * b / h)


def _snap_key(x: float, y: float, z: float, tol: float) -> Tuple[int, int, int]:
    factor = 1.0 / tol
    return (round(x * factor), round(y * factor), round(z * factor))


def _to_pynite(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """SketchUp Z=vertical → PyNite Y=vertical."""
    return (x, z, y)


def _extract_nodes(elements: List[Dict], tol: float = DEFAULT_TOL_NOS) -> Dict[Tuple, str]:
    nodes: Dict[Tuple, str] = {}
    counter = [0]

    def _get_or_create(x, y, z):
        key = _snap_key(x, y, z, tol)
        if key not in nodes:
            counter[0] += 1
            nodes[key] = f"N{counter[0]}"
        return nodes[key]

    for el in elements:
        if el.get("tipo") not in ("viga", "pilar"):
            continue
        pos = el.get("posicao", {})
        ni  = pos.get("no_inicio", {})
        nf  = pos.get("no_fim",    {})
        _get_or_create(ni.get("x", 0), ni.get("y", 0), ni.get("z", 0))
        _get_or_create(nf.get("x", 0), nf.get("y", 0), nf.get("z", 0))

    return nodes


def _node_id(pt: Dict, nodes: Dict[Tuple, str], tol: float = DEFAULT_TOL_NOS) -> str:
    key = _snap_key(pt.get("x", 0), pt.get("y", 0), pt.get("z", 0), tol)
    if key not in nodes:
        raise ValueError(
            f"Nó não encontrado para coordenada "
            f"({pt.get('x'):.4f}, {pt.get('y'):.4f}, {pt.get('z'):.4f}). "
            f"Verifique a tolerância de snap ({tol}m)."
        )
    return nodes[key]


# ─────────────────────────────────────────────────────────────────────────────
# Aplicação de cargas por elemento (NOVO v3.1: inclui point_loads)
# ─────────────────────────────────────────────────────────────────────────────

def _apply_member_loads(
    model,
    eid:         str,
    element:     Dict,
    load_totals: Dict[str, Dict],
    use_g_only:  bool = False,
) -> None:
    """
    Aplica todas as cargas ao membro eid:
      1. Cargas distribuídas (G e Q) — vindas do load_combiner
      2. Cargas pontuais (point_loads[]) — vindas do JSON v3.1

    PyNite: FY = direção global Y (vertical, para baixo = negativo).
    """
    G = load_totals.get(eid, {}).get("G_kN_m", 0.0)
    Q = load_totals.get(eid, {}).get("Q_kN_m", 0.0) if not use_g_only else 0.0

    if G != 0.0:
        model.add_member_dist_load(eid, "FY", -G, -G, case="G")
    if Q != 0.0:
        model.add_member_dist_load(eid, "FY", -Q, -Q, case="Q")

    # ── NOVO v3.1: cargas pontuais ────────────────────────────────────────────
    pt_loads = element.get("cargas", {}).get("point_loads", [])
    if not pt_loads:
        return

    try:
        member = model.members[eid]
        L_m    = member.L()
    except (KeyError, AttributeError):
        return

    for pl in pt_loads:
        x_rel = float(pl.get("x_rel", 0.5))
        Fy    = float(pl.get("Fy",    0.0))

        # Valida
        x_rel = max(0.0, min(1.0, x_rel))
        if Fy == 0.0:
            continue

        x_abs = x_rel * L_m   # posição absoluta em metros

        try:
            # PyNite: add_member_pt_load(member_name, direction, P, x, case)
            # P negativo = para baixo; x em metros
            model.add_member_pt_load(eid, "FY", Fy, x_abs, case="G")
        except Exception as e:
            # Alguns builds do PyNite usam outro nome
            try:
                model.add_member_point_load(eid, "FY", Fy, x_abs, case="G")
            except Exception:
                pass  # log silencioso — não quebra a análise


# ─────────────────────────────────────────────────────────────────────────────
# Função principal
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(
    json_data:    Dict,
    load_totals:  Dict[str, Dict],
    point_loads:  Optional[Dict]       = None,   # mantido para retrocompat. de testes
    nodal_loads:  Optional[List[Dict]] = None,
    use_g_only:   bool                 = False,
) -> Dict[str, Dict]:
    """
    Monta e resolve o modelo estrutural com PyniteFEA.

    v3.1: lê point_loads[] de cada elemento via json_data diretamente,
    eliminando a necessidade do parâmetro avulso point_loads (mantido
    apenas para casos de teste legados).
    """
    FEModel3D = None
    for _mod_name in ("Pynite", "PyNite", "PyNiteFEA"):
        try:
            import importlib
            _mod = importlib.import_module(_mod_name)
            FEModel3D = getattr(_mod, "FEModel3D")
            break
        except (ImportError, AttributeError):
            continue
    if FEModel3D is None:
        raise ImportError("PyNiteFEA não encontrado. Execute: pip install PyNiteFEA")

    gp          = json_data.get("global_parameters", {})
    classe_conc = gp.get("classe_concreto", "C30")
    tipo_combo  = gp.get("tipo_combinacao", "normal")
    tol_nos     = float(gp.get("tolerancia_nos_m", DEFAULT_TOL_NOS))

    if classe_conc not in _CONCRETOS:
        raise ValueError(f"Classe de concreto desconhecida: '{classe_conc}'")

    mat  = _CONCRETOS[classe_conc]
    Ecs  = mat["Ecs"]
    G_sh = Ecs / 2.4
    nu   = 0.2

    elements = json_data.get("elementos_estruturais", [])
    nodes    = _extract_nodes(elements, tol=tol_nos)
    model    = FEModel3D()

    model.add_material("concreto", E=Ecs, G=G_sh, nu=nu, rho=RHO_CONCRETO)

    # ── Coordenadas reais dos nós ─────────────────────────────────────────────
    real_coords: Dict[str, Tuple[float, float, float]] = {}
    for el in elements:
        if el.get("tipo") not in ("viga", "pilar"):
            continue
        pos = el.get("posicao", {})
        for end_key in ("no_inicio", "no_fim"):
            pt  = pos.get(end_key, {})
            x   = pt.get("x", 0)
            y   = pt.get("y", 0)
            z   = pt.get("z", 0)
            key = _snap_key(x, y, z, tol_nos)
            nid = nodes.get(key)
            if nid and nid not in real_coords:
                real_coords[nid] = _to_pynite(x, y, z)

    # Adiciona nós ao modelo
    for nid, (px, py, pz) in real_coords.items():
        model.add_node(nid, px, py, pz)

    # ── Apoios ────────────────────────────────────────────────────────────────
    for el in elements:
        if el.get("tipo") != "pilar":
            continue
        vinculo = el.get("vinculo_base", "engastado").lower()
        pos     = el.get("posicao", {})
        ni      = pos.get("no_inicio", {})
        nid     = _node_id(ni, nodes, tol_nos)

        if "engast" in vinculo:
            model.def_support(nid, True, True, True, True, True, True)
        elif "rotul" in vinculo or "pino" in vinculo:
            model.def_support(nid, True, True, True, False, False, False)
        elif "rolete_x" in vinculo:
            model.def_support(nid, False, True, True, False, False, False)
        elif "rolete_y" in vinculo:
            model.def_support(nid, True, False, True, False, False, False)
        else:
            model.def_support(nid, True, True, True, True, True, True)

    # ── Elementos de barra ────────────────────────────────────────────────────
    el_by_id: Dict[str, Dict] = {}
    for el in elements:
        if el.get("tipo") not in ("viga", "pilar"):
            continue
        eid  = el["id"]
        geom = el.get("geometria", {})
        b    = geom.get("largura",    25.0) / 100.0
        h    = geom.get("altura",     50.0) / 100.0

        A   = b * h
        Iy  = b * h**3 / 12.0
        Iz  = h * b**3 / 12.0
        J   = _torsion_J(b, h)

        sec_id = f"SEC_{eid}"
        model.add_section(sec_id, A=A, Iy=Iy, Iz=Iz, J=J)

        pos = el.get("posicao", {})
        ni  = _node_id(pos.get("no_inicio", {}), nodes, tol_nos)
        nf  = _node_id(pos.get("no_fim",    {}), nodes, tol_nos)
        model.add_member(eid, ni, nf, "concreto", sec_id)
        el_by_id[eid] = el

    # ── Combinações de ações ──────────────────────────────────────────────────
    if use_g_only:
        model.add_load_combo("ELU",       {"G": 1.0})
        model.add_load_combo("ELS_qperm", {"G": 1.0})
    else:
        coefs_elu = _COMBOS.get(tipo_combo, _COMBOS["normal"])
        model.add_load_combo("ELU", {"G": coefs_elu["G"], "Q": coefs_elu["Q"]})
        for combo_name, coefs in _COMBOS_ELS.items():
            model.add_load_combo(combo_name, {"G": coefs["G"], "Q": coefs["Q"]})

    # ── Cargas por elemento (distribuídas + pontuais v3.1) ────────────────────
    for eid, el in el_by_id.items():
        _apply_member_loads(model, eid, el, load_totals, use_g_only)

    # ── Carga pontual de teste (parâmetro legado) ─────────────────────────────
    if point_loads:
        pl = point_loads
        try:
            _pt_L = model.members[pl["element"]].L()
            _pt_x = pl.get("x_rel", 1.0) * _pt_L
            model.add_member_pt_load(pl["element"], "FY", pl.get("Fy", 0.0), _pt_x, case="G")
        except Exception:
            pass

    # ── Cargas nodais (testes) ────────────────────────────────────────────────
    if nodal_loads:
        for nl in nodal_loads:
            Fx = nl.get("Fx", 0.0)
            Fy = nl.get("Fy", 0.0)
            Fz = nl.get("Fz", 0.0)
            if Fx == 0.0 and Fy == 0.0 and Fz == 0.0:
                continue
            pt = nl["node_coords"]
            try:
                nid = _node_id({"x": pt[0], "y": pt[1], "z": pt[2]}, nodes, tol_nos)
            except ValueError:
                import uuid
                nid = f"NL_{uuid.uuid4().hex[:6]}"
                model.add_node(nid, pt[0], pt[1], pt[2])
                key = _snap_key(pt[0], pt[1], pt[2], tol_nos)
                nodes[key] = nid
                real_coords[nid] = (pt[0], pt[1], pt[2])
            if Fx != 0.0: model.add_node_load(nid, "FX", Fx, "G")
            if Fy != 0.0: model.add_node_load(nid, "FY", Fy, "G")
            if Fz != 0.0: model.add_node_load(nid, "FZ", Fz, "G")

    # ── Resolução ─────────────────────────────────────────────────────────────
    try:
        model.analyze_linear()
    except Exception as exc:
        raise RuntimeError(
            f"Falha na análise estrutural: {exc}. "
            "Verifique se a estrutura está estável (vínculos suficientes) e "
            "se todos os elementos estão conectados."
        ) from exc

    # ── Extração de resultados ─────────────────────────────────────────────────
    elu_combo = "ELU"
    els_combo = "ELS_qperm"
    results: Dict[str, Dict] = {}

    for el in elements:
        if el.get("tipo") not in ("viga", "pilar"):
            continue

        eid    = el["id"]
        member = model.members[eid]
        L_m    = member.L()
        x_abs  = [L_m * i / (N_DIAG_POINTS - 1) for i in range(N_DIAG_POINTS)]
        x_rel  = [x / L_m for x in x_abs]

        Md_max   = member.max_moment("Mz", elu_combo)
        Md_min   = member.min_moment("Mz", elu_combo)
        Md_max_y = member.max_moment("My", elu_combo)
        Md_min_y = member.min_moment("My", elu_combo)
        if abs(Md_max_y) > abs(Md_max) or abs(Md_min_y) > abs(Md_min):
            Md_max = Md_max_y
            Md_min = Md_min_y

        Vd_max   = member.max_shear("Fy", elu_combo)
        _vmin    = member.min_shear("Fy", elu_combo)
        if abs(_vmin) > abs(Vd_max): Vd_max = _vmin
        Vd_max_z = member.max_shear("Fz", elu_combo)
        _vz_min  = member.min_shear("Fz", elu_combo)
        _vz_dom  = Vd_max_z if abs(Vd_max_z) >= abs(_vz_min) else _vz_min
        if abs(_vz_dom) > abs(Vd_max): Vd_max = _vz_dom

        _axial_max = member.max_axial(elu_combo)
        _axial_min = member.min_axial(elu_combo)
        Nd_max = _axial_max if abs(_axial_max) >= abs(_axial_min) else _axial_min

        Ms_qp  = member.max_moment("Mz", els_combo) if not use_g_only else Md_max * 0.5

        diag_M = [member.moment("Mz", x, elu_combo) for x in x_abs]
        diag_V = [member.shear( "Fy", x, elu_combo) for x in x_abs]
        diag_N = [member.axial(        x, elu_combo) for x in x_abs]

        # Inclui info de cargas pontuais no resultado para exibição
        pt_loads_info = el.get("cargas", {}).get("point_loads", [])

        results[eid] = {
            "Md_max":      round(Md_max, 3),
            "Md_min":      round(Md_min, 3),
            "Vd_max":      round(Vd_max, 3),
            "Nd_max":      round(Nd_max, 3),
            "Ms_qp":       round(Ms_qp,  3),
            "diag_M":      [round(v, 3) for v in diag_M],
            "diag_V":      [round(v, 3) for v in diag_V],
            "diag_N":      [round(v, 3) for v in diag_N],
            "n_pontos":    N_DIAG_POINTS,
            "x_pontos":    x_rel,
            "L_m":         L_m,
            "combo_elu":   elu_combo,
            "combo_els_qp":els_combo,
            # v3.1: incluir cargas pontuais para exibição nos diagramas
            "point_loads": pt_loads_info,
            "extraction_score": el.get("extraction_score"),
        }

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Funções auxiliares para o Streamlit (inalteradas)
# ─────────────────────────────────────────────────────────────────────────────

def results_to_session_state_dict(results: Dict[str, Dict]) -> Dict[str, Any]:
    ss = {}
    for eid, r in results.items():
        ss[eid] = {
            "v_Md": abs(r["Md_max"]) if abs(r["Md_max"]) >= abs(r["Md_min"]) else abs(r["Md_min"]),
            "v_Vd": abs(r["Vd_max"]),
            "p_Nd": abs(r["Nd_max"]),
            "v_Mk": abs(r.get("Ms_qp", r["Md_max"]) * 0.7),
            "v_Ms": abs(r.get("Ms_qp", r["Md_max"])),
        }
    return ss


def get_max_forces_table(results: Dict[str, Dict], elements: List[Dict]) -> List[Dict]:
    el_by_id = {el["id"]: el for el in elements}
    rows = []
    for eid, r in sorted(results.items()):
        el = el_by_id.get(eid, {})
        rows.append({
            "ID":            eid,
            "Nome":          el.get("nome", eid),
            "Tipo":          el.get("tipo", "?").capitalize(),
            "Pavimento":     el.get("pavimento_hint", "—"),
            "Md_max (kNm)":  r["Md_max"],
            "Md_min (kNm)":  r["Md_min"],
            "Vd_max (kN)":   r["Vd_max"],
            "Nd_max (kN)":   r["Nd_max"],
            "Ms_qp (kNm)":   r["Ms_qp"],
            "Score extração":f"{r['extraction_score']*100:.0f}%" if r.get("extraction_score") else "—",
        })
    return rows
