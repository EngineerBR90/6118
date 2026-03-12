"""
floor_detector.py
=================
Detecta pavimentos automaticamente por clustering de coordenada Z.
Usado pelo pipeline de análise após json_importer e antes de load_distributor.

API principal:
    floors = detect_floors(elements)
    # floors = {
    #   0: {"z_ref": 0.0,  "label": "Térreo",     "elements": [...ids...]},
    #   1: {"z_ref": 3.0,  "label": "Pavimento 1", "elements": [...ids...]},
    # }

    assignment = assign_elements_to_floors(elements, floors)
    # assignment = {"V1": 0, "P1": 0, "V3": 1, ...}
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import math


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TOL_M      = 0.10   # 10cm — tolerância para agrupar Z's no mesmo pavimento
DEFAULT_LABEL_BASE = ["Térreo", "Pavimento 1", "Pavimento 2",
                       "Pavimento 3", "Pavimento 4", "Cobertura"]


# ─────────────────────────────────────────────────────────────────────────────
# Funções de extração de Z
# ─────────────────────────────────────────────────────────────────────────────

def _z_min(element: Dict) -> float:
    """
    Retorna a menor coordenada Z do elemento.
    Para vigas e pilares, usa posicao.no_inicio.z (ponto mais baixo).
    Para lajes, usa posicao.no_inicio.z (face inferior).
    Fallback: 0.0 se posicao ausente (modo manual v2.0).
    """
    pos = element.get("posicao")
    if pos is None:
        return 0.0
    zi = pos.get("no_inicio", {}).get("z", 0.0)
    zf = pos.get("no_fim",    {}).get("z", 0.0)
    return min(zi, zf)


def _z_max(element: Dict) -> float:
    pos = element.get("posicao")
    if pos is None:
        return 0.0
    zi = pos.get("no_inicio", {}).get("z", 0.0)
    zf = pos.get("no_fim",    {}).get("z", 0.0)
    return max(zi, zf)


def _z_representativo(element: Dict) -> float:
    """
    Z de associação do elemento a um pavimento:
    - Viga: Z do nó (ambos iguais para viga horizontal)
    - Pilar: Z da base (no_inicio, menor Z)
    - Laje: Z da face superior (no_fim.z ou max Z)
    """
    tipo = element.get("tipo")
    if tipo == "laje":
        return _z_max(element)
    return _z_min(element)


# ─────────────────────────────────────────────────────────────────────────────
# Algoritmo de clustering
# ─────────────────────────────────────────────────────────────────────────────

def _cluster_z_values(z_list: List[float], tol: float) -> List[float]:
    """
    Agrupa valores de Z próximos (distância < tol) em clusters.
    Retorna lista de z_ref (centroide de cada cluster), ordenada crescente.

    Algoritmo: greedy single-linkage.
    """
    if not z_list:
        return []

    sorted_z = sorted(z_list)
    clusters: List[List[float]] = [[sorted_z[0]]]

    for z in sorted_z[1:]:
        # Verifica se pertence ao último cluster
        if abs(z - clusters[-1][-1]) <= tol:
            clusters[-1].append(z)
        else:
            clusters.append([z])

    # Centroide de cada cluster
    return [sum(c) / len(c) for c in clusters]


# ─────────────────────────────────────────────────────────────────────────────
# API principal
# ─────────────────────────────────────────────────────────────────────────────

def detect_floors(
    elements:       List[Dict],
    tol_m:          float = DEFAULT_TOL_M,
    pavimento_hints: bool = True,
) -> Dict[int, Dict]:
    """
    Detecta pavimentos por clustering da coordenada Z representativa
    de cada elemento.

    Parâmetros:
        elements        : lista de elementos do JSON v3.0
        tol_m           : tolerância em metros para agrupar Z's (padrão 10cm)
        pavimento_hints : se True, usa pavimento_hint do SketchUp como
                          desempate quando dois Z's estão na fronteira

    Retorna:
        dict com índice → {z_ref, label, elements: [ids]}

    Exemplo de retorno:
        {
            0: {"z_ref": 0.0, "label": "Térreo",     "elements": ["P1","P2","V1","V2","L1"]},
            1: {"z_ref": 3.0, "label": "Pavimento 1", "elements": ["P3","P4","V3","V4","L2"]},
        }
    """
    if not elements:
        return {}

    # Extrai Z representativo de cada elemento
    z_per_id = {el["id"]: _z_representativo(el) for el in elements}

    # Clustering dos Z's únicos
    z_refs = _cluster_z_values(list(z_per_id.values()), tol=tol_m)

    if not z_refs:
        return {0: {"z_ref": 0.0, "label": "Térreo", "elements": [el["id"] for el in elements]}}

    # Monta estrutura de pavimentos
    floors: Dict[int, Dict] = {}
    for idx, z_ref in enumerate(z_refs):
        label = DEFAULT_LABEL_BASE[idx] if idx < len(DEFAULT_LABEL_BASE) else f"Pavimento {idx}"
        floors[idx] = {
            "z_ref":    round(z_ref, 3),
            "label":    label,
            "elements": [],
        }

    # Associa cada elemento ao pavimento mais próximo
    for el in elements:
        eid = el["id"]
        z   = z_per_id[eid]

        # Distância a cada z_ref
        dists  = [(idx, abs(z - fl["z_ref"])) for idx, fl in floors.items()]
        # Candidatos dentro da tolerância
        within = [(idx, d) for idx, d in dists if d <= tol_m]

        if within:
            best_idx = min(within, key=lambda x: x[1])[0]
        else:
            # Fora da tolerância: associa ao mais próximo
            best_idx = min(dists, key=lambda x: x[1])[0]

        # Desempate por pavimento_hint quando dois índices têm mesma distância
        if pavimento_hints and len(within) > 1:
            hint = el.get("pavimento_hint", -1)
            hint_match = [idx for idx, _ in within if idx == hint]
            if hint_match:
                best_idx = hint_match[0]

        floors[best_idx]["elements"].append(eid)

    # Remove pavimentos sem elementos (pode acontecer com hints imprecisos)
    floors = {k: v for k, v in floors.items() if v["elements"]}

    # Renumera sequencialmente
    floors = {new_idx: v for new_idx, (_, v) in enumerate(sorted(floors.items()))}

    return floors


def assign_elements_to_floors(
    elements: List[Dict],
    floors:   Dict[int, Dict],
) -> Dict[str, int]:
    """
    Retorna {element_id: floor_index} para acesso rápido.
    """
    assignment: Dict[str, int] = {}
    for idx, fl in floors.items():
        for eid in fl["elements"]:
            assignment[eid] = idx
    return assignment


def get_elements_by_floor(
    elements:   List[Dict],
    floors:     Dict[int, Dict],
    floor_idx:  int,
) -> List[Dict]:
    """
    Retorna os dicts completos dos elementos de um dado pavimento.
    """
    ids_in_floor = set(floors.get(floor_idx, {}).get("elements", []))
    return [el for el in elements if el["id"] in ids_in_floor]


def get_beams_and_slabs_by_floor(
    elements:  List[Dict],
    floors:    Dict[int, Dict],
    floor_idx: int,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Retorna (vigas, lajes) do pavimento especificado.
    Conveniente para load_distributor.
    """
    floor_els = get_elements_by_floor(elements, floors, floor_idx)
    vigas  = [el for el in floor_els if el.get("tipo") == "viga"]
    lajes  = [el for el in floor_els if el.get("tipo") == "laje"]
    return vigas, lajes


def floor_summary_text(floors: Dict[int, Dict], elements: List[Dict]) -> str:
    """
    Gera string de resumo dos pavimentos detectados para log/debug.
    """
    el_by_id = {el["id"]: el for el in elements}
    lines = ["Pavimentos detectados:"]
    for idx, fl in floors.items():
        tipos = {}
        for eid in fl["elements"]:
            t = el_by_id.get(eid, {}).get("tipo", "?")
            tipos[t] = tipos.get(t, 0) + 1
        tipo_str = ", ".join(f"{n} {t}" for t, n in sorted(tipos.items()))
        lines.append(
            f"  [{idx}] {fl['label']:15s} Z={fl['z_ref']:6.2f}m  "
            f"({len(fl['elements'])} elementos: {tipo_str})"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Funções para ajuste manual no Streamlit
# ─────────────────────────────────────────────────────────────────────────────

def rename_floor(floors: Dict[int, Dict], floor_idx: int, new_label: str) -> Dict[int, Dict]:
    """Renomeia um pavimento (para uso no widget de confirmação do Streamlit)."""
    if floor_idx in floors:
        floors[floor_idx]["label"] = new_label
    return floors


def adjust_floor_z(floors: Dict[int, Dict], floor_idx: int, new_z: float) -> Dict[int, Dict]:
    """Ajusta a cota Z de referência de um pavimento manualmente."""
    if floor_idx in floors:
        floors[floor_idx]["z_ref"] = round(new_z, 3)
    return floors


def merge_floors(
    floors: Dict[int, Dict],
    idx_a:  int,
    idx_b:  int,
) -> Dict[int, Dict]:
    """
    Mescla dois pavimentos em um (para corrigir detecções incorretas em
    modelos com mezanino muito próximo ao nível principal).
    O pavimento resultante usa z_ref médio e label do menor índice.
    """
    if idx_a not in floors or idx_b not in floors:
        return floors
    a, b = floors[idx_a], floors[idx_b]
    merged = {
        "z_ref":    round((a["z_ref"] + b["z_ref"]) / 2, 3),
        "label":    a["label"],
        "elements": a["elements"] + b["elements"],
    }
    new_floors = {k: v for k, v in floors.items() if k not in (idx_a, idx_b)}
    new_floors[min(idx_a, idx_b)] = merged
    # Renumera
    return {i: v for i, (_, v) in enumerate(sorted(new_floors.items()))}


# ─────────────────────────────────────────────────────────────────────────────
# Teste rápido (python floor_detector.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _test_elements = [
        {"id": "P1", "tipo": "pilar", "pavimento_hint": 0,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":0.0}, "no_fim": {"x":0,"y":0,"z":3.0}}},
        {"id": "P2", "tipo": "pilar", "pavimento_hint": 0,
         "posicao": {"no_inicio": {"x":4,"y":0,"z":0.0}, "no_fim": {"x":4,"y":0,"z":3.0}}},
        {"id": "V1", "tipo": "viga",  "pavimento_hint": 0,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":3.0}, "no_fim": {"x":4,"y":0,"z":3.0}}},
        {"id": "L1", "tipo": "laje",  "pavimento_hint": 0,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":3.0}, "no_fim": {"x":4,"y":4,"z":3.0}}},
        {"id": "P3", "tipo": "pilar", "pavimento_hint": 1,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":3.0}, "no_fim": {"x":0,"y":0,"z":6.0}}},
        {"id": "P4", "tipo": "pilar", "pavimento_hint": 1,
         "posicao": {"no_inicio": {"x":4,"y":0,"z":3.0}, "no_fim": {"x":4,"y":0,"z":6.0}}},
        {"id": "V2", "tipo": "viga",  "pavimento_hint": 1,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":6.0}, "no_fim": {"x":4,"y":0,"z":6.0}}},
        {"id": "L2", "tipo": "laje",  "pavimento_hint": 1,
         "posicao": {"no_inicio": {"x":0,"y":0,"z":6.0}, "no_fim": {"x":4,"y":4,"z":6.0}}},
    ]

    floors = detect_floors(_test_elements)
    print(floor_summary_text(floors, _test_elements))
    assignment = assign_elements_to_floors(_test_elements, floors)
    print("\nAssociação elemento → pavimento:")
    for eid, fidx in assignment.items():
        print(f"  {eid:4s} → Pavimento {fidx} ({floors[fidx]['label']})")
