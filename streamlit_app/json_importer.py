"""
json_importer.py — v3.1
Importação e validação de dados estruturais do SketchUp.
Suporte a schema v3.1 (extraction_score, carga_cor_id, point_loads, vinculo_source)
+ retrocompatibilidade v3.0 e v2.0.

Mudanças v3.1:
  - resolve_carga_cor(): mapeia carga_cor_id → revestimento_id + variavel_id
  - validate_elements(): alerta de extraction_score < 0.80
  - get_load_completeness(): aceita carga_cor_id como forma válida de definir cargas
  - is_solver_ready(): aceita v3.1 além de v3.0
  - point_loads passados sem modificação ao load_combiner / pynite_wrapper
"""

import json
import os
from typing import Dict, List, Optional, Tuple
import streamlit as st

try:
    from jsonschema import validate as _jsonschema_validate, ValidationError
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

_DIR = os.path.dirname(os.path.abspath(__file__))
_SCHEMA_V3_PATH  = os.path.join(_DIR, "schema_v3.json")
_SCHEMA_V2_PATH  = os.path.join(_DIR, "schema.json")

VALID_TIPOS = {"viga", "pilar", "laje"}

# ── Mapeamento carga_cor_id → IDs do load_library ────────────────────────────
_COR_MAP: Dict[str, Tuple[str, str]] = {
    "dormitorio":  ("ceramica_contrapiso_5cm",      "residencial_dormitorio"),
    "sala_circ":   ("ceramica_contrapiso_5cm",      "residencial_sala_cozinha"),
    "cozinha":     ("ceramica_contrapiso_5cm",      "residencial_sala_cozinha"),
    "escritorio":  ("porcelanato_contrapiso_5cm",   "comercial_escritorio"),
    "cob_acesso":  ("impermeabilizacao",            "cobertura_acessivel"),
    "cob_fechado": ("sem_revestimento",             "cobertura_nao_acessivel"),
    "garagem":     ("impermeabilizacao",            "garagem"),
    "maquinas":    ("sem_revestimento",             "area_tecnica"),
}


# ── Utilitários públicos ──────────────────────────────────────────────────────

def get_schema_version(data: Dict) -> str:
    return str(data.get("schema_version", "unknown"))


def is_solver_ready(data: Dict) -> bool:
    """True se v3.0 ou v3.1 e todos os elementos de barra têm posicao definida."""
    version = get_schema_version(data)
    if version not in ("3.0", "3.1"):
        return False
    for el in data.get("elementos_estruturais", []):
        if el.get("tipo") in ("viga", "pilar"):
            pos = el.get("posicao", {})
            if not pos.get("no_inicio") or not pos.get("no_fim"):
                return False
    return True


def resolve_carga_cor(element: Dict) -> Dict:
    """
    Se o elemento tem carga_cor_id, resolve para revestimento_id e variavel_id.
    Aplica SOMENTE se os campos não foram preenchidos manualmente pelo usuário.

    Retorna o elemento com campos preenchidos (não modifica o original).
    """
    el = dict(element)  # cópia rasa
    cor_id = el.get("cargas", {}).get("carga_cor_id") or el.get("carga_cor_id")
    if not cor_id or cor_id not in _COR_MAP:
        return el

    rev_id, var_id = _COR_MAP[cor_id]

    # Só preenche se estiver vazio
    if not el.get("revestimento_id"):
        el["revestimento_id"] = rev_id
    if not el.get("variavel_id"):
        el["variavel_id"] = var_id

    # Também preenche dentro de cargas.revestimento e cargas.variavel se vazios
    cargas = el.setdefault("cargas", {})
    if not cargas.get("revestimento"):
        cargas["revestimento"] = {"tipo_id": rev_id, "nome": rev_id.replace("_", " "), "kN_m2": 0.0}
    if not cargas.get("variavel"):
        from .load_library import get_q_value  # lazy import to avoid circular
        cargas["variavel"] = {"tipo_id": var_id, "nome": var_id.replace("_", " "), "kN_m2": 0.0}

    return el


def resolve_carga_cor_simple(element: Dict, load_library: Dict) -> Dict:
    """
    Versão sem importação circular. Recebe o load_library já carregado.
    Usar esta versão no app.py.
    """
    el = dict(element)
    cor_id = (el.get("cargas") or {}).get("carga_cor_id") or el.get("carga_cor_id")
    if not cor_id or cor_id not in _COR_MAP:
        return el

    rev_id, var_id = _COR_MAP[cor_id]

    # Preenche revestimento_id / variavel_id no nível raiz se vazios
    if not el.get("revestimento_id"):
        el["revestimento_id"] = rev_id
    if not el.get("variavel_id"):
        el["variavel_id"] = var_id

    # Preenche dentro de cargas se vazios
    cargas = el.setdefault("cargas", {})
    if not cargas.get("revestimento"):
        # Busca kN_m2 no load_library
        rev_kn = 0.0
        for entry in load_library.get("revestimentos", []):
            if entry.get("id") == rev_id:
                rev_kn = float(entry.get("kN_m2", 0.0))
                break
        cargas["revestimento"] = {
            "tipo_id": rev_id,
            "nome":    rev_id.replace("_", " ").title(),
            "kN_m2":   rev_kn
        }
    if not cargas.get("variavel"):
        var_kn = 0.0
        for entry in load_library.get("variavel_nbr6120", []):
            if entry.get("id") == var_id:
                var_kn = float(entry.get("kN_m2", 0.0))
                break
        cargas["variavel"] = {
            "tipo_id": var_id,
            "nome":    var_id.replace("_", " ").title(),
            "kN_m2":   var_kn
        }

    return el


def validate_extraction_scores(elements: List[Dict]) -> List[Dict]:
    """
    Retorna lista de avisos para elementos com extraction_score < 0.80.
    Cada aviso: {"id", "nome", "score", "tipo", "msg"}
    """
    warnings = []
    for el in elements:
        score = el.get("extraction_score")
        if score is None:
            continue
        if float(score) < 0.80:
            warnings.append({
                "id":    el.get("id", "?"),
                "nome":  el.get("nome", el.get("id", "?")),
                "score": float(score),
                "tipo":  el.get("tipo", "?"),
                "msg":   (
                    f"Classificação automática com {float(score)*100:.0f}% de confiança. "
                    "Revisar tipo e dimensões no SketchUp (📐 Revisar Geometria Extraída)."
                )
            })
    return warnings


def get_load_completeness(elements: List[Dict]) -> Dict[str, str]:
    """
    Retorna {element_id: 'ok'|'warning'|'error'} para checklist de cargas.
    v3.1: carga_cor_id é considerada forma válida de definir cargas.
    """
    status = {}
    for el in elements:
        eid    = el.get("id", "?")
        tipo   = el.get("tipo")
        cargas = el.get("cargas", {})
        cor_id = cargas.get("carga_cor_id")

        if tipo == "pilar":
            status[eid] = "ok"
        elif tipo == "viga":
            has_paredes  = bool(cargas.get("paredes"))
            has_variavel = cargas.get("variavel") is not None
            has_especial = cargas.get("especiais_kN_m", 0.0) > 0
            has_cor      = bool(cor_id)
            if has_variavel or has_cor:
                status[eid] = "ok"
            elif has_paredes or has_especial:
                status[eid] = "warning"
            else:
                status[eid] = "error"
        elif tipo == "laje":
            has_rev = cargas.get("revestimento") is not None
            has_var = cargas.get("variavel") is not None
            has_cor = bool(cor_id)
            if (has_rev and has_var) or has_cor:
                status[eid] = "ok"
            elif has_rev or has_var:
                status[eid] = "warning"
            else:
                status[eid] = "error"
        else:
            status[eid] = "ok"
    return status


# ── Classe principal ──────────────────────────────────────────────────────────

class JSONImporter:

    def __init__(self):
        self._schema_v3 = self._load_schema(_SCHEMA_V3_PATH)
        self._schema_v2 = self._load_schema(_SCHEMA_V2_PATH)

    def _load_schema(self, path: str) -> Optional[Dict]:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def load_json_file(self, uploaded_file) -> Tuple[bool, Optional[Dict], str]:
        try:
            data = json.load(uploaded_file)
            return True, data, "Arquivo JSON carregado com sucesso."
        except json.JSONDecodeError as e:
            return False, None, f"JSON inválido: {e}"
        except Exception as e:
            return False, None, f"Erro ao carregar arquivo: {e}"

    def validate_data(self, data: Dict) -> Tuple[bool, str]:
        version = get_schema_version(data)
        # v3.1 usa o mesmo schema v3 (campos novos são opcionais)
        schema  = self._schema_v3 if version in ("3.0", "3.1") else self._schema_v2

        if _HAS_JSONSCHEMA and schema:
            try:
                _jsonschema_validate(instance=data, schema=schema)
                return True, f"Validado com jsonschema (v{version})."
            except ValidationError as e:
                path = ".".join(str(p) for p in e.path)
                return False, f"Erro de validação: {e.message} | {path}"

        return self._validate_manual(data, version)

    def _validate_manual(self, data: Dict, version: str) -> Tuple[bool, str]:
        errors: List[str] = []
        gp = data.get("global_parameters", {})
        for f in ("classe_concreto", "tipo_aco", "tipo_combinacao", "classe_agressividade"):
            if not gp.get(f):
                errors.append(f"global_parameters.{f} ausente")

        elementos = data.get("elementos_estruturais", [])
        if not isinstance(elementos, list) or not elementos:
            errors.append("elementos_estruturais deve ser lista não vazia")
            return False, "\n• ".join(errors)

        for i, el in enumerate(elementos):
            nome = el.get("nome", f"elemento[{i}]")
            for f in ("id", "tipo", "nome", "geometria"):
                if f not in el:
                    errors.append(f"{nome}: '{f}' ausente")
            if el.get("tipo") not in VALID_TIPOS:
                errors.append(f"{nome}: tipo inválido '{el.get('tipo')}'")
            if version in ("3.0", "3.1") and el.get("tipo") in ("viga", "pilar"):
                pos = el.get("posicao", {})
                if not pos.get("no_inicio") or not pos.get("no_fim"):
                    errors.append(f"{nome}: posicao ausente (obrigatório no v{version})")

        if errors:
            return False, "Erros:\n• " + "\n• ".join(errors)
        return True, f"Validado manualmente (v{version})."

    def extract_global_parameters(self, data: Dict) -> Dict:
        return data.get("global_parameters", {})

    def extract_elements(self, data: Dict) -> List[Dict]:
        return data.get("elementos_estruturais", [])

    def filter_by_type(self, elements: List[Dict], tipo: str) -> List[Dict]:
        return [el for el in elements if el.get("tipo") == tipo]

    def get_element_summary(self, elements: List[Dict]) -> Dict:
        return {
            "total":   len(elements),
            "vigas":   len(self.filter_by_type(elements, "viga")),
            "pilares": len(self.filter_by_type(elements, "pilar")),
            "lajes":   len(self.filter_by_type(elements, "laje")),
        }

    def get_posicao(self, el: Dict) -> Optional[Dict]:
        return el.get("posicao")

    def get_cargas(self, el: Dict) -> Dict:
        return el.get("cargas", {"pp_automatico": True})

    def get_vinculo_base(self, el: Dict) -> str:
        return el.get("vinculo_base", "engastado")

    def get_pavimento_hint(self, el: Dict) -> int:
        return int(el.get("pavimento_hint", 0))

    def get_point_loads(self, el: Dict) -> List[Dict]:
        """Retorna lista de cargas pontuais do elemento (pode ser vazia)."""
        return el.get("cargas", {}).get("point_loads", [])

    def get_vinculo_source(self, el: Dict) -> str:
        return el.get("vinculo_source", "manual")


# ── Widgets Streamlit ─────────────────────────────────────────────────────────

def import_json_in_streamlit(uploader_key: str = "json_uploader") -> Optional[Dict]:
    st.markdown("### 📥 Importar Modelo do SketchUp")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo JSON exportado pela extensão SketchUp",
        type=["json"], key=uploader_key,
    )
    if uploaded_file is None:
        return None

    importer = JSONImporter()
    ok, data, msg = importer.load_json_file(uploaded_file)
    if not ok:
        st.error(f"❌ {msg}")
        return None
    st.success(f"✅ {msg}")

    valid, vmsg = importer.validate_data(data)
    if not valid:
        st.error(f"❌ {vmsg}")
        return None

    version = get_schema_version(data)
    if is_solver_ready(data):
        st.success(f"✅ Schema v{version} — **modo solver habilitado**.")
    elif version in ("3.0", "3.1"):
        st.warning(f"⚠️ Schema v{version}, mas posicao incompleta. Modo manual ativo.")
    else:
        st.info(
            f"ℹ️ Schema v{version} — **modo manual**. "
            "Reexporte com a extensão v4.0 para habilitar o solver."
        )

    # Avisos de score baixo
    elements = importer.extract_elements(data)
    score_warns = validate_extraction_scores(elements)
    if score_warns:
        with st.expander(f"⚠️ {len(score_warns)} elemento(s) com classificação incerta (score < 80%)"):
            for w in score_warns:
                st.warning(
                    f"**{w['nome']}** ({w['tipo']}) — {w['score']*100:.0f}% — {w['msg']}"
                )

    summary = importer.get_element_summary(elements)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total",   summary["total"])
    c2.metric("Vigas",   summary["vigas"])
    c3.metric("Pilares", summary["pilares"])
    c4.metric("Lajes",   summary["lajes"])
    return data


def display_imported_data_summary(data: Dict, load_library: Optional[Dict] = None) -> None:
    st.markdown("### 📊 Resumo dos Dados Importados")
    version = get_schema_version(data)
    gp      = data.get("global_parameters", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**Concreto**: {gp.get('classe_concreto',      'N/A')}")
    c2.info(f"**Aço**: {gp.get('tipo_aco',                  'N/A')}")
    c3.info(f"**Combinação**: {gp.get('tipo_combinacao',     'N/A')}")
    c4.info(f"**Agressividade**: {gp.get('classe_agressividade', 'N/A')}")

    elementos = data.get("elementos_estruturais", [])
    if not elementos:
        st.info("Nenhum elemento.")
        return

    # Resolve carga_cor_id antes de exibir
    if load_library:
        elementos = [resolve_carga_cor_simple(el, load_library) for el in elementos]

    load_status  = get_load_completeness(elementos) if version in ("3.0", "3.1") else {}
    status_icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}

    for i, el in enumerate(elementos, 1):
        geom   = el.get("geometria", {})
        params = el.get("parametros_calculo", {})
        tipo   = el.get("tipo", "?").upper()
        nome   = el.get("nome", "?")
        eid    = el.get("id",   "?")
        pav    = el.get("pavimento_hint", "—")
        icon   = status_icons.get(load_status.get(eid, "ok"), "")
        score  = el.get("extraction_score")
        score_str = f" | score {score*100:.0f}%" if score else ""
        vsrc   = el.get("vinculo_source", "")
        vsrc_str = f" | apoio {vsrc}" if vsrc and tipo == "PILAR" else ""

        with st.expander(f"{i}. {icon} [{tipo}] {nome}  —  Pav.{pav}  —  {eid}{score_str}{vsrc_str}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Geometria**")
                st.write(f"Comprimento: {geom.get('comprimento','?')} m")
                st.write(f"Largura: {geom.get('largura','?')} cm")
                st.write(f"Altura: {geom.get('altura','?')} cm")
            with c2:
                st.markdown("**Detalhamento**")
                st.write(f"Cobrimento: {params.get('cobrimento_nominal','?')} mm")
                st.write(f"φ long: {params.get('phi_longitudinal','?')} mm")
                st.write(f"φ estribo: {params.get('phi_estribo','?')} mm")
            with c3:
                st.markdown("**Cargas**")
                if version in ("3.0", "3.1"):
                    cargas   = el.get("cargas", {})
                    cor_id   = cargas.get("carga_cor_id")
                    par_tot  = sum(p.get("carga_kN_m", 0) for p in cargas.get("paredes", []))
                    var_obj  = cargas.get("variavel")
                    pt_loads = cargas.get("point_loads", [])
                    if cor_id:
                        st.write(f"🎨 Cor: {cor_id}")
                    st.write(f"Paredes: {par_tot:.2f} kN/m")
                    st.write(f"Variável: {var_obj['kN_m2'] if var_obj else '—'} kN/m²")
                    if pt_loads:
                        st.write(f"Pontuais: {len(pt_loads)} carga(s)")
                        for pl in pt_loads:
                            st.caption(f"  {pl.get('Fy',0):.1f} kN @ x/L={pl.get('x_rel',0):.2f} — {pl.get('descricao','')}")
                    st.write("pp: automático (PyNite)")
                    if tipo == "PILAR":
                        vsrc = el.get("vinculo_source", "manual")
                        vico = "🔷" if vsrc == "grafico" else "⚙️"
                        st.write(f"Vínculo: {vico} {el.get('vinculo_base','—')} ({vsrc})")
                else:
                    if tipo == "VIGA":
                        st.write(f"Md: {params.get('momento_fletor_Md','?')} kN·m")
                        st.write(f"Vd: {params.get('forca_cortante_Vd','?')} kN")
                    elif tipo == "PILAR":
                        st.write(f"Nd: {params.get('forca_normal_Nd','?')} kN")
                    elif tipo == "LAJE":
                        st.write(f"Md: {params.get('momento_fletor_Md','?')} kN·m/m")

            if version in ("3.0", "3.1"):
                pos = el.get("posicao")
                if pos:
                    ni, nf = pos.get("no_inicio", {}), pos.get("no_fim", {})
                    st.caption(
                        f"({ni.get('x',0):.3f}, {ni.get('y',0):.3f}, {ni.get('z',0):.3f}) m"
                        f" → ({nf.get('x',0):.3f}, {nf.get('y',0):.3f}, {nf.get('z',0):.3f}) m"
                    )
