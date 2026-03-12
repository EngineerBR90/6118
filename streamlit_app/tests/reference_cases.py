"""
Casos de Referência para Validação do pynite_wrapper.py
========================================================
Todos os casos usam pórticos completos (vigas + pilares) que são
estruturalmente estáveis em 3D.

As verificações são baseadas em equilíbrio estático — valores que
independem da rigidez relativa dos elementos e são sempre corretos.

Caso 1: Pórtico simples — cortante na viga = q×L/2 = 30 kN
Caso 2: Pórtico em L   — força axial no pilar = P = 20 kN (compressão)
Caso 3: Pórtico 3 vãos — cortante em cada viga = q×L/2 = 25 kN
Caso 4: Pórtico 2 pav  — reação horizontal total nas bases = H1+H2 = 20 kN
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def relative_error(calculated, reference):
    if abs(reference) < 1e-12:
        return abs(calculated)
    return abs(calculated - reference) / abs(reference)


def assert_within(calculated, reference, tolerance, label=""):
    err = relative_error(calculated, reference)
    status = "✅ PASS" if err <= tolerance else "❌ FAIL"
    print(f"  {status}  {label}")
    print(f"         calculado={calculated:.4f}  referência={reference:.4f}  "
          f"erro={err*100:.2f}%  tol={tolerance*100:.1f}%")
    assert err <= tolerance, (
        f"FALHA em '{label}': calculado={calculated:.4f}, "
        f"referência={reference:.4f}, erro={err*100:.2f}% > {tolerance*100:.1f}%"
    )


def _gp():
    return {"classe_concreto": "C30", "tipo_aco": "CA-50",
            "tipo_combinacao": "normal", "classe_agressividade": "II"}

def _pilar(eid, nome, x, z0, z1, vinculo="engastado"):
    return {"id": eid, "tipo": "pilar", "nome": nome,
            "geometria": {"comprimento": abs(z1-z0), "largura": 30.0, "altura": 40.0},
            "posicao": {"no_inicio": {"x": x, "y": 0.0, "z": z0},
                        "no_fim":    {"x": x, "y": 0.0, "z": z1}},
            "cargas": {"pp_automatico": False},
            "parametros_calculo": {"cobrimento_nominal": 30, "phi_longitudinal": 20, "phi_estribo": 8},
            "vinculo_base": vinculo}

def _viga(eid, nome, x0, x1, z):
    return {"id": eid, "tipo": "viga", "nome": nome,
            "geometria": {"comprimento": abs(x1-x0), "largura": 25.0, "altura": 50.0},
            "posicao": {"no_inicio": {"x": x0, "y": 0.0, "z": z},
                        "no_fim":    {"x": x1, "y": 0.0, "z": z}},
            "cargas": {"pp_automatico": False},
            "parametros_calculo": {"cobrimento_nominal": 30, "phi_longitudinal": 20, "phi_estribo": 8}}


# ── CASO 1 ────────────────────────────────────────────────────────────────────
# 2 pilares engastados (h=3m) + viga (L=6m), q=10 kN/m
# Cortante máximo na viga = q×L/2 = 30 kN (equilíbrio, independe de rigidez)
CASO1 = {
    "name": "Caso 1 — Pórtico simples, q=10 kN/m, L=6m",
    "analytic": {"V_max_kN": 30.0},
    "tolerance": {"V": 0.01},
    "json": {"schema_version": "3.0", "global_parameters": _gp(),
             "elementos_estruturais": [
                 _pilar("P1","Esq", 0.0, 0.0, 3.0),
                 _pilar("P2","Dir", 6.0, 0.0, 3.0),
                 _viga ("V1","Viga",0.0, 6.0, 3.0)]},
    "loads": {"V1": {"G_kN_m": 10.0, "Q_kN_m": 0.0}},
}

# ── CASO 2 ────────────────────────────────────────────────────────────────────
# Pilar engastado (h=4m) + viga em balanço (L=4m), P=20 kN na ponta
# Força axial no pilar = P = 20 kN em compressão (equilíbrio vertical)
# O wrapper deve retornar Nd_max com sinal negativo (compressão) → |Nd_max| = 20
CASO2 = {
    "name": "Caso 2 — Pórtico em L, P=20 kN na ponta",
    "analytic": {"V_viga_kN": 20.0, "N_pilar_kN": 20.0},
    "tolerance": {"V": 0.01, "N": 0.01},
    "json": {"schema_version": "3.0", "global_parameters": _gp(),
             "elementos_estruturais": [
                 _pilar("P1","Pilar",0.0, 0.0, 4.0),
                 _viga ("V1","Viga", 0.0, 4.0, 4.0)]},
    "loads": {"V1": {"G_kN_m": 0.0, "Q_kN_m": 0.0}},
    "point_load": {"element": "V1", "Fy": -20.0, "x_rel": 1.0},
}

# ── CASO 3 ────────────────────────────────────────────────────────────────────
# 4 pilares + 3 vigas de 5m com q=10 kN/m
# Cortante máximo em cada viga = q×L/2 = 25 kN (equilíbrio)
CASO3 = {
    "name": "Caso 3 — Pórtico 3 vãos, q=10 kN/m, L=5m",
    "analytic": {"V_central_kN": 25.0},
    "tolerance": {"V": 0.01, "simetria": 0.02},
    "json": {"schema_version": "3.0", "global_parameters": _gp(),
             "elementos_estruturais": [
                 _pilar("P1","A0",  0.0, 0.0, 3.0),
                 _pilar("P2","A1",  5.0, 0.0, 3.0),
                 _pilar("P3","A2", 10.0, 0.0, 3.0),
                 _pilar("P4","A3", 15.0, 0.0, 3.0),
                 _viga ("V1","Vao1",  0.0,  5.0, 3.0),
                 _viga ("V2","Vao2",  5.0, 10.0, 3.0),
                 _viga ("V3","Vao3", 10.0, 15.0, 3.0)]},
    "loads": {"V1": {"G_kN_m": 10.0, "Q_kN_m": 0.0},
              "V2": {"G_kN_m": 10.0, "Q_kN_m": 0.0},
              "V3": {"G_kN_m": 10.0, "Q_kN_m": 0.0}},
}

# ── CASO 4 ────────────────────────────────────────────────────────────────────
# 2 pilares engastados (2 pavimentos) + 2 vigas, H=10 kN em cada nível
# Reação horizontal total nas 2 bases = H1+H2 = 20 kN (equilíbrio horizontal)
# O wrapper retorna Vd_max dos pilares. Para pilares verticais com carga
# horizontal em X, a força transversal no plano XZ é Fz (não Fy).
# O wrapper já compara Fy e Fz e retorna o maior — Vd_max deve ser ~10 kN/pilar.
CASO4 = {
    "name": "Caso 4 — Pórtico 2 pavimentos, H=10 kN/pav",
    "analytic": {"V_base_por_pilar_kN": 10.0},
    "tolerance": {"V": 0.05},  # 5% — pórtico multi-pav tem redistribuição
    "json": {"schema_version": "3.0", "global_parameters": _gp(),
             "elementos_estruturais": [
                 _pilar("P1L","P1_esq",0.0, 0.0, 3.0),
                 _pilar("P1R","P1_dir",4.0, 0.0, 3.0),
                 _viga ("V1", "Viga1", 0.0, 4.0, 3.0),
                 _pilar("P2L","P2_esq",0.0, 3.0, 6.0),
                 _pilar("P2R","P2_dir",4.0, 3.0, 6.0),
                 _viga ("V2", "Viga2", 0.0, 4.0, 6.0)]},
    "loads": {"V1": {"G_kN_m": 0.0, "Q_kN_m": 0.0},
              "V2": {"G_kN_m": 0.0, "Q_kN_m": 0.0}},
    "nodal_loads": [
        {"node_coords": (0.0, 0.0, 3.0), "Fx": 10.0},
        {"node_coords": (0.0, 0.0, 6.0), "Fx": 10.0},
    ],
}

ALL_CASES = [CASO1, CASO2, CASO3, CASO4]


def run_validation():
    print("=" * 65)
    print("  VALIDAÇÃO DO SOLVER — CASOS DE REFERÊNCIA")
    print("=" * 65)

    try:
        import pynite_wrapper as pw
        solver_available = True
        print("  Engine: PyniteFEA via pynite_wrapper.py\n")
    except ImportError:
        solver_available = False
        print("  ⚠️  pynite_wrapper.py não encontrado.\n")

    passed = 0
    failed = 0

    for caso in ALL_CASES:
        print(f"\n{'─'*65}")
        print(f"  {caso['name']}")
        print(f"{'─'*65}")
        print("  Solução analítica:")
        for k, v in caso['analytic'].items():
            print(f"    {k} = {v:.4f}")

        if not solver_available:
            continue

        try:
            results = pw.run_analysis(
                json_data=caso['json'],
                load_totals=caso.get('loads', {}),
                point_loads=caso.get('point_load'),
                nodal_loads=caso.get('nodal_loads'),
                use_g_only=True,
            )
            print("\n  Resultados do solver:")
            tol = caso['tolerance']

            if caso['name'].startswith("Caso 1"):
                V = abs(results['V1']['Vd_max'])
                assert_within(V, caso['analytic']['V_max_kN'], tol['V'], "V_max viga (kN)")

            elif caso['name'].startswith("Caso 2"):
                V = abs(results['V1']['Vd_max'])
                N = abs(results['P1']['Nd_max'])   # wrapper agora retorna max(|max|,|min|)
                assert_within(V, caso['analytic']['V_viga_kN'],  tol['V'], "V_max viga (kN)")
                assert_within(N, caso['analytic']['N_pilar_kN'], tol['N'], "N_max pilar (kN)")

            elif caso['name'].startswith("Caso 3"):
                # V2 (vão central, simétrico) = exatamente q*L/2 = 25 kN
                V2 = abs(results['V2']['Vd_max'])
                assert_within(V2, caso['analytic']['V_central_kN'], tol['V'], "V_max V2 central (kN)")
                # V1 e V3 devem ser iguais por simetria (pórtico simétrico)
                V1 = abs(results['V1']['Vd_max'])
                V3 = abs(results['V3']['Vd_max'])
                assert_within(V1, V3, tol['simetria'], "simetria V1==V3 (kN)")
                # Soma total das reações = carga total = 3×10×5 = 150 kN
                # Cada viga entrega 2×V_max às colunas → soma = V1+V2+V3 ≈ 75 kN por lado
                # Verificação de equilíbrio: 2*(V1+V2+V3)/2 não é direto via Vd_max
                # Basta simetria + V2 correto

            elif caso['name'].startswith("Caso 4"):
                # Reação horizontal = Vd_max de cada pilar de base
                # (wrapper retorna max(|Fy|,|Fz|) — captura força horizontal)
                V_P1L = abs(results['P1L']['Vd_max'])
                V_P1R = abs(results['P1R']['Vd_max'])
                assert_within(V_P1L, caso['analytic']['V_base_por_pilar_kN'],
                               tol['V'], "V_base P1L (kN)")
                assert_within(V_P1R, caso['analytic']['V_base_por_pilar_kN'],
                               tol['V'], "V_base P1R (kN)")

            passed += 1

        except AssertionError as e:
            print(f"  ❌ {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"  ⚠️  Erro: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*65}")
    print(f"  Resultado: {passed} aprovados, {failed} reprovados")
    if failed == 0 and solver_available:
        print("  ✅ GATE LIBERADO — pynite_wrapper validado.")
    elif not solver_available:
        print("  ⚠️  Execute após instalar PyNiteFEA")
    else:
        print("  ❌ GATE BLOQUEADO — revisar pynite_wrapper.")
    print("=" * 65)


if __name__ == "__main__":
    run_validation()
