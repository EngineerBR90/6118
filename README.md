# Calculadora Estrutural NBR 6118:2023
## SketchUp + PyniteFEA + Streamlit

---

## Estrutura de pastas

```
projeto_estrutural/
│
├── streamlit_app/              ← Aplicação Python/Streamlit
│   ├── app.py                  ← Interface principal (tabs de cálculo NBR)
│   ├── json_importer.py        ← v3.0: importa JSON do SketchUp, detecta versão
│   ├── floor_detector.py       ← Detecta pavimentos por clustering de Z
│   ├── load_distributor.py     ← Distribuição de lajes → vigas (triângulo/trapézio)
│   ├── load_combiner.py        ← Agrega G e Q por elemento para o PyNite
│   ├── pynite_wrapper.py       ← Interface com PyniteFEA (FEModel3D, ELU/ELS)
│   ├── requirements.txt        ← Dependências Python
│   ├── load_library.json       ← Catálogo de cargas (NBR 6120)
│   ├── schema_v3.json          ← Schema JSON v3.0 para validação
│   └── tests/
│       └── reference_cases.py  ← 4 casos de validação analítica do solver
│
└── sketchup_extension/         ← Extensão Ruby para SketchUp
    ├── structural_exporter.rb  ← v3.0: exporta XYZ real + cargas decompostas
    ├── setup_attributes.rb     ← UI de configuração de elementos (a refatorar F2)
    ├── extension_main.rb       ← Menu e roteamento da extensão
    └── load_library.json       ← Cópia da biblioteca (usada nos dropdowns)
```

---

## Setup rápido — Streamlit

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

### Validar o solver (obrigatório antes de usar análise automática)

```bash
cd streamlit_app
python tests/reference_cases.py
```

Esperado: `✅ GATE LIBERADO — pynite_wrapper validado.`

---

## Setup — Extensão SketchUp

1. Abra o SketchUp
2. Menu **Window → Extension Manager → Install Extension**
3. Selecione a pasta `sketchup_extension/` (ou empacote como `.rbz`)
4. O menu **Plugins → Exportador Estrutural** aparecerá

---

## Versões dos arquivos

| Arquivo | Versão | O que mudou |
|---|---|---|
| `json_importer.py` | v3.0 | Detecta schema, lê `posicao`/`cargas`/`pavimento_hint` |
| `structural_exporter.rb` | v3.0 | Exporta XYZ real via `transformation.origin`, objeto `cargas` |
| `floor_detector.py` | v1.0 | Novo — clustering por Z |
| `load_distributor.py` | v1.0 | Novo — triângulo/trapézio NBR 6118 |
| `load_combiner.py` | v1.0 | Novo — agrega G e Q |
| `pynite_wrapper.py` | v1.0 | Novo — FEModel3D completo |
| `schema_v3.json` | v3.0 | Novo — valida JSON exportado |
| `load_library.json` | v1.0 | Novo — 11 paredes, 11 revestimentos, 12 usos NBR 6120 |
| `app.py` | v3.0 | Sem alteração nesta sessão (F6 pendente) |
| `setup_attributes.rb` | v2.0 | Sem alteração (F2 pendente) |
| `extension_main.rb` | v2.0 | Sem alteração (F2 pendente) |

---

## Status de implementação

- ✅ **F0 Preparação** — 4/5
- ✅ **F1 Schema + exportador** — 6/7
- ⬜ **F2 UI SketchUp cargas** — 0/8 (próxima prioridade)
- ✅ **F3 floor_detector** — 2/4
- ✅ **F4 load_distributor + combiner** — 4/4
- 🔄 **F5 pynite_wrapper** — 4/5 (falta rodar gate T5.5)
- ⬜ **F6 app.py integração** — 0/9 (bloqueada por T5.5)
- ⬜ **F7 Relatório PDF** — 0/3

**Total: 20/45 tasks**
