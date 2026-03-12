"""
load_combiner.py
================
Agrega todas as cargas por elemento (G permanente e Q variável) separadas,
prontas para serem passadas ao pynite_wrapper.py.

Fontes de carga consideradas:
  - Paredes apoiadas sobre vigas    → G
  - Distribuição de lajes (do load_distributor) → G e Q
  - Cargas especiais lineares       → G
  - Peso próprio do concreto        → NÃO entra aqui (PyNite calcula via rho)

API:
    load_totals = combine_loads(elements, slab_loads)
    # {element_id: {"G_kN_m": float, "Q_kN_m": float, "breakdown": {...}}}
"""

from __future__ import annotations
from typing import Dict, List


# Importação do load_library — resolvido uma vez por chamada
import json as _json_mod
import os as _os_mod

def _load_library_index(load_library: Dict | None) -> Dict[str, Dict]:
    """
    Retorna um índice plano {item_id: item_dict} cobrindo
    paredes, revestimentos e variavel_nbr6120.
    Aceita o dict já carregado ou carrega do arquivo load_library.json
    na mesma pasta do módulo.
    """
    if load_library is None:
        _here = _os_mod.path.dirname(_os_mod.path.abspath(__file__))
        _path = _os_mod.path.join(_here, "load_library.json")
        try:
            with open(_path, encoding="utf-8") as _f:
                load_library = _json_mod.load(_f)
        except Exception:
            return {}
    index: Dict[str, Dict] = {}
    for section in ("paredes", "revestimentos", "variavel_nbr6120"):
        for item in load_library.get(section, []):
            index[item["id"]] = item
    return index


def _parse_paredes_field(raw) -> List[Dict]:
    """
    Aceita tanto o formato antigo (lista de dicts com carga_kN_m)
    quanto o novo formato v3 (JSON string ou lista com id + comprimento_m).
    Retorna lista normalizada [{"id": ..., "comprimento_m": ...}] ou
    [{"carga_kN_m": ...}] para o formato antigo.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = _json_mod.loads(raw)
        except Exception:
            return []
    if not isinstance(raw, list):
        return []
    return raw


def combine_loads(
    elements:     List[Dict],
    slab_loads:   Dict[str, Dict[str, float]],
    load_library: Dict | None = None,
) -> Dict[str, Dict]:
    """
    Combina todas as cargas lineares (kN/m) por elemento.

    Compatível com formato de cargas v2 (carga_kN_m direto) e
    v3 (paredes por id + comprimento_m, revestimento_id, variavel_id).

    Parâmetros
    ----------
    elements     : lista de elementos do JSON v3.0
    slab_loads   : saída de distribute_all_slabs()
    load_library : dict da biblioteca de cargas (opcional; lê do arquivo se None)

    Retorna
    -------
    {
      element_id: {
        "G_kN_m":    total permanente (kN/m),
        "Q_kN_m":    total variável   (kN/m),
        "breakdown": {
            "paredes_kN_m":     ...,
            "revestimento_kN_m":...,
            "laje_G_kN_m":      ...,
            "especiais_kN_m":   ...,
            "laje_Q_kN_m":      ...,
            "variavel_dir_kN_m":...,
        }
      }
    }
    """
    lib_idx = _load_library_index(load_library)
    totals: Dict[str, Dict] = {}

    for el in elements:
        tipo = el.get("tipo")
        if tipo not in ("viga", "pilar"):
            continue

        eid    = el["id"]
        cargas = el.get("cargas", {})

        # ── Permanente ────────────────────────────────────────────────────────

        # 1a. Paredes — formato v2: [{carga_kN_m: x}, ...]
        # 1b. Paredes — formato v3: JSON string "[{id, comprimento_m}, ...]"
        #     carga = kN/m² × altura_parede_m × comprimento_m
        paredes_raw  = _parse_paredes_field(
            cargas.get("paredes") or el.get("paredes")
        )
        h_pared = float(
            cargas.get("altura_parede_m") or el.get("altura_parede_m") or 2.80
        )
        paredes_G = 0.0
        for pw in paredes_raw:
            if "carga_kN_m" in pw:
                # formato v2 — valor pré-calculado
                paredes_G += float(pw["carga_kN_m"])
            elif "id" in pw:
                # formato v3 — lookup na biblioteca
                item = lib_idx.get(pw["id"], {})
                kn_m2 = float(item.get("kN_m2", 0.0))
                comp  = float(pw.get("comprimento_m", 1.0))
                # kN/m² × h × comprimento → kN/m linear (distribuída ao longo da viga)
                # comprimento aqui é o cumprimento da parede PERPENDICULAR à viga
                # = comprimento tributário. Para paredes na mesma direção da viga:
                # carga = kN/m² × h  (por metro linear da viga)
                paredes_G += kn_m2 * h_pared * comp

        # 2. Revestimento — formato v3: revestimento_id → kN/m² sobre a laje
        #    Para vigas, conversor: kN/m² × largura_tributária
        #    (usamos largura_tributaria = 1.0 m como convenção; o load_distributor
        #     já trata a distribuição de laje separadamente quando há lajes)
        rev_id   = cargas.get("revestimento_id") or el.get("revestimento_id", "")
        rev_item = lib_idx.get(rev_id, {})
        rev_G    = float(rev_item.get("kN_m2", 0.0)) if rev_id else 0.0

        # 3. Distribuição de laje (permanente) — do load_distributor
        laje_G = slab_loads.get(eid, {}).get("G_laje_kN_m", 0.0)

        # 4. Cargas especiais lineares
        especiais_G = float(
            cargas.get("especiais_kN_m") or el.get("especiais_kN_m") or 0.0
        )

        G_total = paredes_G + rev_G + laje_G + especiais_G

        # ── Variável ──────────────────────────────────────────────────────────

        # Distribuição de laje (variável) — do load_distributor
        laje_Q = slab_loads.get(eid, {}).get("Q_laje_kN_m", 0.0)

        # Carga variável direta na viga — formato v3: variavel_id
        var_id   = cargas.get("variavel_id") or el.get("variavel_id", "")
        var_item = lib_idx.get(var_id, {})
        var_dir  = float(var_item.get("kN_m2", 0.0)) if var_id else 0.0

        # Formato v2: variavel como dict inline
        if not var_id:
            var_dir = float(cargas.get("variavel", {}).get("kN_m2", 0.0))

        Q_total = laje_Q + var_dir

        # ── Resultado ─────────────────────────────────────────────────────────
        totals[eid] = {
            "G_kN_m": round(G_total, 4),
            "Q_kN_m": round(Q_total, 4),
            "breakdown": {
                "paredes_kN_m":      round(paredes_G,   4),
                "revestimento_kN_m": round(rev_G,       4),
                "laje_G_kN_m":       round(laje_G,      4),
                "especiais_kN_m":    round(especiais_G, 4),
                "laje_Q_kN_m":       round(laje_Q,      4),
                "variavel_dir_kN_m": round(var_dir,     4),
            }
        }

    return totals


def combine_loads_summary(load_totals: Dict[str, Dict]) -> str:
    """Gera string de resumo das cargas por elemento para log/debug."""
    lines = ["Cargas combinadas por elemento (kN/m):"]
    lines.append(f"  {'ID':20s} {'G total':>10s} {'Q total':>10s}  Breakdown")
    lines.append("  " + "─" * 70)
    for eid, data in sorted(load_totals.items()):
        bk = data.get("breakdown", {})
        bk_str = (
            f"paredes={bk.get('paredes_kN_m',0):.2f}  "
            f"rev={bk.get('revestimento_kN_m',0):.2f}  "
            f"laje_G={bk.get('laje_G_kN_m',0):.2f}  "
            f"esp={bk.get('especiais_kN_m',0):.2f}  "
            f"laje_Q={bk.get('laje_Q_kN_m',0):.2f}  "
            f"var_dir={bk.get('variavel_dir_kN_m',0):.2f}"
        )
        lines.append(
            f"  {eid:20s} {data['G_kN_m']:>10.3f} {data['Q_kN_m']:>10.3f}  {bk_str}"
        )
    return "\n".join(lines)


def get_load_warnings(
    elements:    List[Dict],
    load_totals: Dict[str, Dict],
) -> List[Dict[str, str]]:
    """
    Retorna lista de avisos sobre cargas suspeitas ou ausentes.
    Usado no Streamlit para exibir alertas na revisão de cargas.

    Retorna:
        [{"id": eid, "nome": nome, "tipo": tipo, "nivel": "warning"|"error", "msg": str}]
    """
    warnings = []
    el_by_id = {el["id"]: el for el in elements}

    for eid, data in load_totals.items():
        el   = el_by_id.get(eid, {})
        tipo = el.get("tipo", "?")
        nome = el.get("nome", eid)

        G = data.get("G_kN_m", 0.0)
        Q = data.get("Q_kN_m", 0.0)

        if tipo == "viga":
            if G == 0.0 and Q == 0.0:
                warnings.append({
                    "id": eid, "nome": nome, "tipo": tipo,
                    "nivel": "error",
                    "msg": "Nenhuma carga definida além do peso próprio. "
                           "Verifique se paredes, revestimento ou variável foram informados."
                })
            elif Q == 0.0:
                warnings.append({
                    "id": eid, "nome": nome, "tipo": tipo,
                    "nivel": "warning",
                    "msg": "Carga variável zero. Confirme se o tipo de uso foi definido "
                           "na laje de contorno ou diretamente na viga."
                })

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Teste rápido
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _elements = [
        {
            "id": "V1", "tipo": "viga", "nome": "V1",
            "cargas": {
                "pp_automatico": True,
                "paredes": [
                    {"tipo_id": "bloco_ceramico_14cm", "altura_m": 2.8, "carga_kN_m": 5.04}
                ],
                "variavel": {"tipo_id": "residencial_dormitorio", "kN_m2": 1.5},
                "especiais_kN_m": 0.0,
            }
        },
        {
            "id": "P1", "tipo": "pilar", "nome": "P1",
            "cargas": {"pp_automatico": True},
            "vinculo_base": "engastado",
        },
    ]
    _slab_loads = {
        "V1": {"G_laje_kN_m": 2.05, "Q_laje_kN_m": 2.56}
    }
    totals = combine_loads(_elements, _slab_loads)
    print(combine_loads_summary(totals))
    # V1: G = 5.04 + 2.05 = 7.09  |  Q = 2.56
