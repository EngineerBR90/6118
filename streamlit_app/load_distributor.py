"""
load_distributor.py
===================
Distribui cargas de área das lajes para as vigas de contorno do mesmo nível Z.
Método: triângulos e trapézios conforme relação lx/ly (NBR 6118 §14.7.8).

API:
    load_map = distribute_all_slabs(elements, floors, load_library)
    # load_map = {"V1": {"G_laje_kN_m": 8.4, "Q_laje_kN_m": 3.0}, ...}
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import math


# ─────────────────────────────────────────────────────────────────────────────
# Tolerância para detectar vigas de contorno
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TOL_M = 0.005   # 5mm


# ─────────────────────────────────────────────────────────────────────────────
# Geometria de laje
# ─────────────────────────────────────────────────────────────────────────────

def _slab_bbox(laje: Dict) -> Tuple[float, float, float, float, float]:
    """
    Retorna (x_min, y_min, x_max, y_max, z_ref) da laje a partir de posicao.
    z_ref = Z do plano da laje (face superior = no_fim.z ou max das z's).
    """
    pos  = laje.get("posicao", {})
    ni   = pos.get("no_inicio", {})
    nf   = pos.get("no_fim",    {})
    x_min = min(ni.get("x", 0.0), nf.get("x", 0.0))
    y_min = min(ni.get("y", 0.0), nf.get("y", 0.0))
    x_max = max(ni.get("x", 0.0), nf.get("x", 0.0))
    y_max = max(ni.get("y", 0.0), nf.get("y", 0.0))
    z_ref = max(ni.get("z", 0.0), nf.get("z", 0.0))
    return x_min, y_min, x_max, y_max, z_ref


def _slab_spans(laje: Dict) -> Tuple[float, float]:
    """Retorna (lx, ly) com lx <= ly."""
    geom = laje.get("geometria", {})
    a = geom.get("comprimento", 0.0)
    b = geom.get("largura",     0.0)
    return (min(a, b), max(a, b))


# ─────────────────────────────────────────────────────────────────────────────
# Distribuição por triângulo / trapézio (NBR 6118 §14.7.8)
# ─────────────────────────────────────────────────────────────────────────────

def distribute_slab_load(
    lx:    float,   # vão menor (m)
    ly:    float,   # vão maior (m)
    q_g:   float,   # carga permanente de área (kN/m²) — SEM peso próprio da laje
    q_q:   float,   # carga variável de área (kN/m²)
) -> Dict[str, Dict[str, float]]:
    """
    Calcula as cargas lineares equivalentes nas vigas de contorno.

    Referência: NBR 6118:2023 §14.7.8 — método simplificado (tabelas).
    Para painéis com 4 bordas engastadas/simplesmente apoiadas:
        Viga do vão menor (lx): carregamento triangular
            q_viga_x = q × lx / 3
        Viga do vão maior (ly): carregamento trapezoidal
            q_viga_y = q × lx × (3 − λ²) / 6,  λ = lx/ly

    Retorna:
        {
          "viga_vao_menor": {"G_kN_m": ..., "Q_kN_m": ...},  # vigas paralelas ao vão menor
          "viga_vao_maior": {"G_kN_m": ..., "Q_kN_m": ...},  # vigas paralelas ao vão maior
        }
    """
    if lx <= 0 or ly <= 0:
        return {
            "viga_vao_menor": {"G_kN_m": 0.0, "Q_kN_m": 0.0},
            "viga_vao_maior": {"G_kN_m": 0.0, "Q_kN_m": 0.0},
        }

    lam = min(lx / ly, 1.0)   # λ = lx/ly ≤ 1

    # Triangular (viga paralela ao vão maior, carrega vão menor)
    coef_x = lx / 3.0

    # Trapezoidal (viga paralela ao vão menor, carrega vão maior)
    coef_y = lx * (3.0 - lam**2) / 6.0

    return {
        "viga_vao_menor": {
            "G_kN_m": round(q_g * coef_x, 4),
            "Q_kN_m": round(q_q * coef_x, 4),
        },
        "viga_vao_maior": {
            "G_kN_m": round(q_g * coef_y, 4),
            "Q_kN_m": round(q_q * coef_y, 4),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Identificação de vigas de contorno
# ─────────────────────────────────────────────────────────────────────────────

def _beam_is_on_z(viga: Dict, z_ref: float, tol: float) -> bool:
    """Verifica se a viga está no plano Z da laje (ambos os nós no mesmo Z)."""
    pos = viga.get("posicao", {})
    zi  = pos.get("no_inicio", {}).get("z", None)
    zf  = pos.get("no_fim",    {}).get("z", None)
    if zi is None or zf is None:
        return False
    return abs(zi - z_ref) <= tol and abs(zf - z_ref) <= tol


def _point_near_segment(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float,
    tol: float,
) -> bool:
    """
    Retorna True se o ponto (px,py) está a menos de tol da reta AB,
    E a projeção do ponto cai dentro do segmento AB.
    Usado para verificar se uma viga está na borda de uma laje.
    """
    dx, dy = bx - ax, by - ay
    length_sq = dx*dx + dy*dy
    if length_sq < 1e-12:
        return math.hypot(px - ax, py - ay) <= tol

    # Parâmetro t da projeção
    t = ((px - ax)*dx + (py - ay)*dy) / length_sq
    t = max(0.0, min(1.0, t))

    # Ponto mais próximo no segmento
    cx = ax + t*dx
    cy = ay + t*dy
    return math.hypot(px - cx, py - cy) <= tol


def _beam_on_slab_edge(
    viga: Dict,
    x_min: float, y_min: float,
    x_max: float, y_max: float,
    tol:   float,
) -> Optional[str]:
    """
    Verifica se a viga está numa das 4 bordas da laje retangular.

    Retorna:
        'x_min' | 'x_max' | 'y_min' | 'y_max' — borda correspondente
        None — a viga não é de contorno desta laje
    """
    pos  = viga.get("posicao", {})
    ni   = pos.get("no_inicio", {})
    nf   = pos.get("no_fim",    {})
    ax, ay = ni.get("x", 0.0), ni.get("y", 0.0)
    bx, by = nf.get("x", 0.0), nf.get("y", 0.0)

    # Bordas da laje (4 segmentos)
    edges = {
        "y_min": ((x_min, y_min), (x_max, y_min)),  # borda inferior
        "y_max": ((x_min, y_max), (x_max, y_max)),  # borda superior
        "x_min": ((x_min, y_min), (x_min, y_max)),  # borda esquerda
        "x_max": ((x_max, y_min), (x_max, y_max)),  # borda direita
    }

    for edge_name, ((ex1, ey1), (ex2, ey2)) in edges.items():
        # Ambas as extremidades da viga precisam estar próximas da borda
        a_near = _point_near_segment(ax, ay, ex1, ey1, ex2, ey2, tol)
        b_near = _point_near_segment(bx, by, ex1, ey1, ex2, ey2, tol)
        if a_near and b_near:
            return edge_name

    return None


def find_contour_beams(
    laje:  Dict,
    vigas: List[Dict],
    tol:   float = DEFAULT_TOL_M,
) -> Dict[str, List[str]]:
    """
    Identifica as vigas de contorno de uma laje.

    Retorna:
        {
          "y_min": ["V1"],   # borda paralela ao eixo X (vão maior → recebe carga trapezoidal)
          "y_max": ["V2"],
          "x_min": ["V3"],   # borda paralela ao eixo Y (vão menor → recebe carga triangular)
          "x_max": ["V4"],
        }
    """
    x_min, y_min, x_max, y_max, z_ref = _slab_bbox(laje)

    contour: Dict[str, List[str]] = {
        "y_min": [], "y_max": [], "x_min": [], "x_max": []
    }

    for viga in vigas:
        if not _beam_is_on_z(viga, z_ref, tol):
            continue
        edge = _beam_on_slab_edge(viga, x_min, y_min, x_max, y_max, tol)
        if edge:
            contour[edge].append(viga["id"])

    return contour


# ─────────────────────────────────────────────────────────────────────────────
# Função de distribuição completa para uma laje
# ─────────────────────────────────────────────────────────────────────────────

def distribute_one_slab(
    laje:          Dict,
    vigas_nivel:   List[Dict],
    tol:           float = DEFAULT_TOL_M,
) -> Dict[str, Dict[str, float]]:
    """
    Distribui a carga de uma laje para as vigas de contorno do mesmo nível.

    Retorna:
        {viga_id: {"G_laje_kN_m": x, "Q_laje_kN_m": y}, ...}
    """
    result: Dict[str, Dict[str, float]] = {}

    cargas  = laje.get("cargas", {})
    rev_obj = cargas.get("revestimento")
    var_obj = cargas.get("variavel")
    q_g = rev_obj["kN_m2"] if rev_obj else 0.0
    q_q = var_obj["kN_m2"] if var_obj else 0.0

    if q_g == 0.0 and q_q == 0.0:
        return {}

    lx, ly = _slab_spans(laje)
    if lx <= 0 or ly <= 0:
        return {}

    dist = distribute_slab_load(lx, ly, q_g, q_q)

    # Identifica vigas de contorno
    contour = find_contour_beams(laje, vigas_nivel, tol)

    # Relação vão / borda:
    #   lx = vão menor → bordas y_min, y_max estão paralelas ao eixo X
    #                    (comprimento da viga ≈ ly → recebe carga trapezoidal)
    #   ly = vão maior → bordas x_min, x_max estão paralelas ao eixo Y
    #                    (comprimento da viga ≈ lx → recebe carga triangular)
    #
    # Nota: a nomenclatura "viga_vao_menor/maior" em distribute_slab_load
    # refere-se ao VAZIO que a viga cobre, não ao seu comprimento.
    #
    # Bordas y_min / y_max: paralelas a X → vão ly (maior) → carga trapezoidal
    for vid in contour["y_min"] + contour["y_max"]:
        prev = result.get(vid, {"G_laje_kN_m": 0.0, "Q_laje_kN_m": 0.0})
        result[vid] = {
            "G_laje_kN_m": prev["G_laje_kN_m"] + dist["viga_vao_maior"]["G_kN_m"],
            "Q_laje_kN_m": prev["Q_laje_kN_m"] + dist["viga_vao_maior"]["Q_kN_m"],
        }

    # Bordas x_min / x_max: paralelas a Y → vão lx (menor) → carga triangular
    for vid in contour["x_min"] + contour["x_max"]:
        prev = result.get(vid, {"G_laje_kN_m": 0.0, "Q_laje_kN_m": 0.0})
        result[vid] = {
            "G_laje_kN_m": prev["G_laje_kN_m"] + dist["viga_vao_menor"]["G_kN_m"],
            "Q_laje_kN_m": prev["Q_laje_kN_m"] + dist["viga_vao_menor"]["Q_kN_m"],
        }

    return result


# ─────────────────────────────────────────────────────────────────────────────
# API principal: distribui todas as lajes do modelo
# ─────────────────────────────────────────────────────────────────────────────

def distribute_all_slabs(
    elements: List[Dict],
    floors:   Dict[int, Dict],
    tol:      float = DEFAULT_TOL_M,
) -> Dict[str, Dict[str, float]]:
    """
    Distribui as cargas de todas as lajes do modelo para suas vigas de contorno.

    Retorna:
        {viga_id: {"G_laje_kN_m": total_G, "Q_laje_kN_m": total_Q}, ...}

    As cargas são ACUMULATIVAS — se uma viga é contorno de 2 lajes, recebe a soma.
    """
    # Índice de acesso rápido
    el_by_id: Dict[str, Dict] = {el["id"]: el for el in elements}

    # Resultado acumulado por viga
    slab_loads: Dict[str, Dict[str, float]] = {}

    for floor_idx, floor in floors.items():
        # Elementos do pavimento
        floor_els = [el_by_id[eid] for eid in floor["elements"] if eid in el_by_id]
        vigas_nivel = [el for el in floor_els if el.get("tipo") == "viga"]
        lajes_nivel = [el for el in floor_els if el.get("tipo") == "laje"]

        for laje in lajes_nivel:
            dist = distribute_one_slab(laje, vigas_nivel, tol)
            for vid, loads in dist.items():
                prev = slab_loads.get(vid, {"G_laje_kN_m": 0.0, "Q_laje_kN_m": 0.0})
                slab_loads[vid] = {
                    "G_laje_kN_m": prev["G_laje_kN_m"] + loads["G_laje_kN_m"],
                    "Q_laje_kN_m": prev["Q_laje_kN_m"] + loads["Q_laje_kN_m"],
                }

    return slab_loads


# ─────────────────────────────────────────────────────────────────────────────
# Teste rápido
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Painel 4×6m, q_g=1.2 kN/m², q_q=1.5 kN/m²
    # Referência Czerny: viga ly (6m) recebe q×lx×(3-λ²)/6 ≈ 1.2×4×(3-0.44)/6 = 2.05 kN/m
    lx, ly = 4.0, 6.0
    q_g, q_q = 1.2, 1.5
    dist = distribute_slab_load(lx, ly, q_g, q_q)
    print("Distribuição — painel 4×6m:")
    print(f"  Viga vão menor (6m, trapezoidal): G={dist['viga_vao_maior']['G_kN_m']:.3f} kN/m  Q={dist['viga_vao_maior']['Q_kN_m']:.3f} kN/m")
    print(f"  Viga vão maior (4m, triangular):  G={dist['viga_vao_menor']['G_kN_m']:.3f} kN/m  Q={dist['viga_vao_menor']['Q_kN_m']:.3f} kN/m")

    # Verificação analítica
    lam = lx / ly
    ref_trap = q_g * lx * (3 - lam**2) / 6
    ref_tri  = q_g * lx / 3
    print(f"\n  Referência analítica:")
    print(f"  Trapezoidal: {ref_trap:.3f} kN/m")
    print(f"  Triangular:  {ref_tri:.3f} kN/m")
