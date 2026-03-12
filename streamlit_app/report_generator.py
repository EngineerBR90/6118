"""
report_generator.py — Fase 7
Gerador de relatório PDF para resultados da análise estrutural NBR 6118:2023.

Dependências: reportlab>=4.0, matplotlib>=3.5
Uso:
    from report_generator import gerar_relatorio_pdf
    pdf_bytes = gerar_relatorio_pdf(json_data, results, load_totals, floors)
"""

from __future__ import annotations
import io
import math
import datetime
from typing import Dict, List, Optional, Any

# ── ReportLab ─────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image, KeepTogether,
)
from reportlab.platypus.flowables import Flowable

# ── Matplotlib (diagramas) ────────────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ─────────────────────────────────────────────────────────────────────────────
# Paleta de cores (tema escuro → PDF claro profissional)
# ─────────────────────────────────────────────────────────────────────────────
AZUL       = colors.HexColor("#1a4a8a")
AZUL_CLARO = colors.HexColor("#3b82f6")
VERDE      = colors.HexColor("#166534")
CINZA_ESC  = colors.HexColor("#1f2937")
CINZA_MED  = colors.HexColor("#6b7280")
CINZA_CLR  = colors.HexColor("#f3f4f6")
BRANCO     = colors.white
VERMELHO   = colors.HexColor("#dc2626")
AMARELO    = colors.HexColor("#d97706")

W, H = A4   # 595 × 842 pt
MARGIN_L = MARGIN_R = 2.0 * cm
MARGIN_T = MARGIN_B = 2.2 * cm
CONTENT_W = W - MARGIN_L - MARGIN_R


# ─────────────────────────────────────────────────────────────────────────────
# Estilos de parágrafo
# ─────────────────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["titulo"] = ParagraphStyle(
        "titulo", parent=base["Title"],
        fontSize=18, textColor=AZUL, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    styles["subtitulo"] = ParagraphStyle(
        "subtitulo", parent=base["Normal"],
        fontSize=11, textColor=CINZA_MED, spaceAfter=12,
        fontName="Helvetica",
    )
    styles["secao"] = ParagraphStyle(
        "secao", parent=base["Heading1"],
        fontSize=12, textColor=BRANCO, spaceAfter=6, spaceBefore=14,
        fontName="Helvetica-Bold", backColor=AZUL,
        leftIndent=-MARGIN_L, rightIndent=-MARGIN_R,
        borderPadding=(4, 8, 4, 8),
    )
    styles["subsecao"] = ParagraphStyle(
        "subsecao", parent=base["Heading2"],
        fontSize=10, textColor=AZUL, spaceAfter=4, spaceBefore=8,
        fontName="Helvetica-Bold", borderPadding=(2, 0, 2, 0),
    )
    styles["corpo"] = ParagraphStyle(
        "corpo", parent=base["Normal"],
        fontSize=9, textColor=CINZA_ESC, spaceAfter=4,
        fontName="Helvetica", leading=13,
    )
    styles["mono"] = ParagraphStyle(
        "mono", parent=base["Code"],
        fontSize=8, textColor=CINZA_ESC, spaceAfter=2,
        fontName="Courier", backColor=CINZA_CLR,
        borderPadding=(3, 4, 3, 4), leftIndent=4,
    )
    styles["rodape"] = ParagraphStyle(
        "rodape", parent=base["Normal"],
        fontSize=7, textColor=CINZA_MED, alignment=TA_CENTER,
        fontName="Helvetica",
    )
    styles["aviso"] = ParagraphStyle(
        "aviso", parent=base["Normal"],
        fontSize=8, textColor=AMARELO, fontName="Helvetica-Oblique",
        leftIndent=8, spaceAfter=6,
    )
    return styles


# ─────────────────────────────────────────────────────────────────────────────
# Flowable: faixa colorida de cabeçalho de seção
# ─────────────────────────────────────────────────────────────────────────────
class _SecaoHeader(Flowable):
    def __init__(self, texto: str, cor=AZUL):
        super().__init__()
        self.texto = texto
        self.cor   = cor
        self.width  = CONTENT_W
        self.height = 18

    def draw(self):
        c = self.canv
        c.setFillColor(self.cor)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(BRANCO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(6, 4, self.texto)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _tabela(dados: List[List], col_widths: List[float],
            header: bool = True) -> Table:
    """Cria Table com estilo NBR."""
    tbl = Table(dados, colWidths=col_widths, repeatRows=1 if header else 0)
    estilo = [
        ("BACKGROUND",  (0, 0), (-1, 0 if header else -1), AZUL),
        ("TEXTCOLOR",   (0, 0), (-1, 0 if header else -1), BRANCO),
        ("FONTNAME",    (0, 0), (-1, 0 if header else -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR",   (0, 1), (-1, -1), CINZA_ESC),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_CLR]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("ALIGN",       (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN",       (0, 0), (0, -1),  "LEFT"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(estilo))
    return tbl


def _fmt(v: float, dec: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{dec}f}"


# ─────────────────────────────────────────────────────────────────────────────
# Geração de diagrama M/V/N (matplotlib → PNG em memória)
# ─────────────────────────────────────────────────────────────────────────────
def _diagrama_png(r: Dict, nome: str, largura_cm: float = 14) -> Optional[io.BytesIO]:
    """
    Gera PNG com 3 subplots (M, V, N) para um elemento.
    Retorna BytesIO ou None se dados insuficientes.
    """
    diag_M = r.get("diag_M", [])
    diag_V = r.get("diag_V", [])
    diag_N = r.get("diag_N", [])
    x_rel  = r.get("x_pontos", [])
    L_m    = r.get("L_m", 1.0)

    if not diag_M or not x_rel:
        return None

    x_m = [round(xi * L_m, 4) for xi in x_rel]

    fig, axes = plt.subplots(3, 1, figsize=(largura_cm / 2.54, 7 / 2.54),
                              tight_layout=True)
    fig.patch.set_facecolor("white")

    datasets = [
        (diag_M, "#1a4a8a", "M (kNm)"),
        (diag_V, "#dc2626", "V (kN)"),
        (diag_N, "#166534", "N (kN)"),
    ]

    for ax, (data, cor, ylabel) in zip(axes, datasets):
        ax.fill_between(x_m, data, 0,
                        alpha=0.25, color=cor)
        ax.plot(x_m, data, color=cor, linewidth=1.2)
        ax.axhline(0, color="#9ca3af", linewidth=0.5, linestyle="--")
        ax.set_ylabel(ylabel, fontsize=7, color="#374151")
        ax.tick_params(labelsize=6)
        ax.set_facecolor("#f9fafb")
        ax.spines[["top","right"]].set_visible(False)
        ax.spines[["left","bottom"]].set_color("#d1d5db")
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

    axes[-1].set_xlabel("x (m)", fontsize=7)
    fig.suptitle(nome, fontsize=8, color="#1f2937", fontweight="bold", y=1.01)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Cabeçalho e rodapé de página
# ─────────────────────────────────────────────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4

    # Cabeçalho
    canvas.setFillColor(AZUL)
    canvas.rect(MARGIN_L, h - MARGIN_T + 4*mm, CONTENT_W, 8*mm, fill=1, stroke=0)
    canvas.setFillColor(BRANCO)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN_L + 4, h - MARGIN_T + 7*mm,
                      "NBR 6118:2023 — Relatório de Análise Estrutural")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - MARGIN_R, h - MARGIN_T + 7*mm,
                           doc._nbr_titulo or "")

    # Rodapé
    canvas.setFillColor(CINZA_CLR)
    canvas.rect(MARGIN_L, MARGIN_B - 6*mm, CONTENT_W, 5*mm, fill=1, stroke=0)
    canvas.setFillColor(CINZA_MED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN_L + 4, MARGIN_B - 4*mm,
                      f"Gerado em: {doc._nbr_data}  |  ABNT NBR 6118:2023")
    canvas.drawRightString(w - MARGIN_R, MARGIN_B - 4*mm,
                           f"Página {doc.page}")
    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Função principal
# ─────────────────────────────────────────────────────────────────────────────
def gerar_relatorio_pdf(
    json_data:   Dict,
    results:     Dict[str, Dict],
    load_totals: Dict[str, Dict],
    floors:      Optional[List[Dict]] = None,
    titulo:      str = "Sobrado",
) -> bytes:
    """
    Gera o relatório PDF completo e retorna bytes prontos para download.

    Parâmetros
    ----------
    json_data    : JSON v3.0 exportado pelo SketchUp
    results      : dict retornado por pynite_wrapper.run_analysis()
    load_totals  : dict retornado por load_combiner.combine_loads()
    floors       : lista de pavimentos de floor_detector.detect_floors()
    titulo       : nome do projeto / obra
    """
    buf = io.BytesIO()
    S   = _build_styles()
    now = datetime.datetime.now()
    gp  = json_data.get("global_parameters", {})
    elements = json_data.get("elementos_estruturais", [])

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 4*mm, bottomMargin=MARGIN_B + 4*mm,
        title=f"Relatório NBR 6118 — {titulo}",
        author="Calculadora NBR 6118:2023",
        subject="Análise Estrutural",
    )
    doc._nbr_titulo = titulo
    doc._nbr_data   = now.strftime("%d/%m/%Y %H:%M")

    story = []

    # ── Capa ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("RELATÓRIO DE ANÁLISE ESTRUTURAL", S["titulo"]))
    story.append(Paragraph(titulo, ParagraphStyle(
        "proj", parent=S["titulo"], fontSize=14, textColor=CINZA_MED,
        fontName="Helvetica",
    )))
    story.append(HRFlowable(width=CONTENT_W, thickness=2,
                             color=AZUL, spaceAfter=10))

    # Metadados em tabela 2 colunas
    meta_rows = [
        ["Norma de referência", "ABNT NBR 6118:2023 — 4ª Edição"],
        ["Classe do concreto",  gp.get("classe_concreto", "—")],
        ["Tipo de aço",         gp.get("tipo_aco", "—")],
        ["Combinação de ações", gp.get("tipo_combinacao", "normal").capitalize()],
        ["Agressividade",       f"Classe {gp.get('classe_agressividade', '—')}"],
        ["Data de emissão",     now.strftime("%d/%m/%Y %H:%M")],
        ["Schema JSON",         json_data.get("schema_version", "3.0")],
    ]
    tbl_meta = _tabela(
        [["Campo", "Valor"]] + meta_rows,
        [6 * cm, CONTENT_W - 6 * cm],
    )
    story.append(tbl_meta)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(
        "⚠️  Este relatório é gerado automaticamente por software. "
        "Os resultados devem ser verificados por engenheiro responsável "
        "antes de qualquer uso em projeto.",
        S["aviso"],
    ))

    # ── Seção 1: Modelo estrutural ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(_SecaoHeader("1. MODELO ESTRUTURAL"))
    story.append(Spacer(1, 6))

    n_vigas   = sum(1 for e in elements if e.get("tipo") == "viga")
    n_pilares = sum(1 for e in elements if e.get("tipo") == "pilar")
    n_lajes   = sum(1 for e in elements if e.get("tipo") == "laje")

    story.append(Paragraph(
        f"O modelo contém <b>{len(elements)}</b> elementos estruturais: "
        f"<b>{n_vigas}</b> vigas, <b>{n_pilares}</b> pilares e "
        f"<b>{n_lajes}</b> lajes.",
        S["corpo"],
    ))

    # Tabela de elementos
    hdr_el = [["ID", "Nome", "Tipo", "b (cm)", "h (cm)", "L (m)", "Vínculo"]]
    rows_el = []
    for el in elements:
        if el.get("tipo") not in ("viga", "pilar"):
            continue
        g   = el.get("geometria", {})
        pos = el.get("posicao", {})
        ni  = pos.get("no_inicio", {})
        nf  = pos.get("no_fim", {})
        L   = math.sqrt(
            (nf.get("x",0)-ni.get("x",0))**2 +
            (nf.get("y",0)-ni.get("y",0))**2 +
            (nf.get("z",0)-ni.get("z",0))**2
        ) if pos else g.get("comprimento", 0)
        rows_el.append([
            el.get("id", ""),
            el.get("nome", ""),
            el.get("tipo", "").capitalize(),
            _fmt(g.get("largura",  0), 0),
            _fmt(g.get("altura",   0), 0),
            _fmt(L, 2),
            el.get("vinculo_base", "—"),
        ])
    if rows_el:
        cw = [1.5*cm, 4.5*cm, 2*cm, 1.6*cm, 1.6*cm, 1.8*cm, 2.5*cm]
        story.append(_tabela(hdr_el + rows_el, cw))

    # Pavimentos
    if floors:
        story.append(Spacer(1, 8))
        story.append(Paragraph("1.1 Pavimentos detectados", S["subsecao"]))
        hdr_pav = [["Pavimento", "Z ref (m)", "Nº elementos", "Vigas", "Pilares"]]
        rows_pav = []
        for i, fl in enumerate(floors):
            rows_pav.append([
                f"Pav {i+1}",
                _fmt(fl.get("z_ref", 0), 3),
                str(fl.get("n_elements", 0)),
                str(fl.get("n_vigas", 0)),
                str(fl.get("n_pilares", 0)),
            ])
        story.append(_tabela(hdr_pav + rows_pav,
                             [3*cm, 3*cm, 3.5*cm, 2.5*cm, 2.5*cm]))

    # ── Seção 2: Cargas ────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(_SecaoHeader("2. CARGAS APLICADAS"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Cargas distribuídas por elemento conforme NBR 6120:2019. "
        "G = ações permanentes; Q = ações variáveis.",
        S["corpo"],
    ))

    hdr_cg = [["ID", "Nome", "Tipo", "G (kN/m)", "Q (kN/m)", "G+Q (kN/m)"]]
    rows_cg = []
    for el in elements:
        eid  = el.get("id", "")
        ltot = load_totals.get(eid, {})
        G    = ltot.get("G_kN_m", 0.0)
        Q    = ltot.get("Q_kN_m", 0.0)
        rows_cg.append([
            eid,
            el.get("nome", ""),
            el.get("tipo", "").capitalize(),
            _fmt(G), _fmt(Q), _fmt(G + Q),
        ])
    if rows_cg:
        story.append(_tabela(hdr_cg + rows_cg,
                             [1.8*cm, 4.2*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm]))

    # ── Seção 3: Resultados — esforços máximos ─────────────────────────────
    story.append(PageBreak())
    story.append(_SecaoHeader("3. ESFORÇOS MÁXIMOS DE CÁLCULO — ELU"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Combinação ELU normal: 1,4G + 1,4Q (NBR 6118:2023 item 11.7). "
        "Valores em kN e kN·m.",
        S["corpo"],
    ))

    hdr_res = [["ID", "Nome", "Tipo",
                "Md+ (kNm)", "Md- (kNm)", "Vd (kN)", "Nd (kN)", "Ms,qp (kNm)"]]
    rows_res = []
    for el in elements:
        eid = el.get("id", "")
        r   = results.get(eid)
        if not r:
            continue
        rows_res.append([
            eid,
            el.get("nome", ""),
            el.get("tipo", "").capitalize(),
            _fmt(r.get("Md_max", 0)),
            _fmt(r.get("Md_min", 0)),
            _fmt(r.get("Vd_max", 0)),
            _fmt(r.get("Nd_max", 0)),
            _fmt(r.get("Ms_qp", 0)),
        ])
    if rows_res:
        cw = [1.5*cm, 3.5*cm, 1.8*cm, 2.2*cm, 2.2*cm, 2.0*cm, 2.0*cm, 2.3*cm]
        story.append(_tabela(hdr_res + rows_res, cw))

    # ── Seção 4: Diagramas M/V/N ───────────────────────────────────────────
    story.append(PageBreak())
    story.append(_SecaoHeader("4. DIAGRAMAS DE ESFORÇOS INTERNOS"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Diagramas ao longo do eixo de cada elemento para a combinação ELU normal. "
        "Convenção: momento positivo = tração na face inferior (vigas).",
        S["corpo"],
    ))

    _plotados = 0
    for el in elements:
        eid  = el.get("id", "")
        r    = results.get(eid)
        nome = el.get("nome", eid)
        tipo = el.get("tipo", "")
        if not r or tipo not in ("viga", "pilar"):
            continue

        png_buf = _diagrama_png(r, f"{nome} [{eid}]", largura_cm=14)
        if png_buf is None:
            continue

        img = Image(png_buf, width=14*cm, height=7*cm)
        tipo_label = "Viga" if tipo == "viga" else "Pilar"

        bloco = [
            Paragraph(f"4.{_plotados+1} {tipo_label}: {nome}", S["subsecao"]),
            Spacer(1, 3),
            img,
            Spacer(1, 4),
        ]
        story.append(KeepTogether(bloco))
        _plotados += 1

    if _plotados == 0:
        story.append(Paragraph(
            "Nenhum diagrama disponível — verifique se a análise foi executada.",
            S["corpo"],
        ))

    # ── Seção 5: Notas técnicas ────────────────────────────────────────────
    story.append(PageBreak())
    story.append(_SecaoHeader("5. NOTAS TÉCNICAS E REFERÊNCIAS"))
    story.append(Spacer(1, 6))

    notas = [
        ("Normas aplicadas",
         "ABNT NBR 6118:2023 — Projeto de estruturas de concreto: procedimento. "
         "ABNT NBR 6120:2019 — Cargas para o cálculo de estruturas de edificações."),
        ("Engine de análise",
         "PyNiteFEA v2.x — solver de elementos finitos 3D de código aberto. "
         "Análise linear elástica, pequenas deformações, combinações ELU e ELS."),
        ("Modelo de materiais",
         "Módulo de elasticidade secante: E_cs = 0,85 × 5600 × √fck (MPa). "
         "Coeficiente de Poisson: ν = 0,2. Peso específico: γ = 25 kN/m³."),
        ("Combinações de ações",
         "ELU normal: γ_f = 1,4 (G e Q). "
         "ELS quasi-permanente: ψ_2 = 0,3Q. "
         "ELS frequente: ψ_1 = 0,6Q. ELS rara: ψ_0 = 1,0Q."),
        ("Limitações",
         "Este software realiza análise linear de 1ª ordem. "
         "Efeitos de 2ª ordem (flambagem), redistribuição plástica e "
         "análise dinâmica não estão incluídos. "
         "A responsabilidade técnica pelo projeto é do engenheiro responsável."),
    ]

    for titulo_nota, texto in notas:
        story.append(Paragraph(titulo_nota, S["subsecao"]))
        story.append(Paragraph(texto, S["corpo"]))
        story.append(Spacer(1, 4))

    # ── Build ──────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )
    return buf.getvalue()
