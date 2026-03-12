# Guia de Uso — Calculadora Estrutural NBR 6118 v4.0

## Fluxo resumido

```
Modelar componentes → 📐 Revisar → 🎨 Pintar cargas → 🔧 Inserir apoios → 📤 Exportar
```

---

## 1. Modelar no SketchUp

Cada elemento estrutural deve ser um **Componente** ou **Grupo** (não linhas soltas).

| Elemento | Como modelar |
|---|---|
| Pilar | Sólido vertical (Push/Pull de retângulo no plano XY) |
| Viga | Sólido horizontal (Push/Pull no plano XZ ou YZ) |
| Laje | Sólido plano horizontal (espessura < 20 cm) |

> **Conectividade:** use **snap em vértice** ao posicionar. O topo de um pilar e a ponta de uma viga devem compartilhar o mesmo vértice no modelo — os sólidos podem se sobrepor ou ficar encostados, o que importa é que as coordenadas coincidam (tolerância 5 mm).

---

## 2. 📐 Revisar Geometria Extraída

**Menu:** Extensions → Calculadora Estrutural → 📐 Revisar Geometria Extraída

Este painel lê a geometria de todos os componentes e propõe tipo + dimensões automaticamente.

### O que aparece na tabela

| Coluna | Significado |
|---|---|
| Checkbox | Marque os elementos a confirmar |
| Nome | Nome do componente no SketchUp |
| Tipo | Dropdown editável: `viga`, `pilar`, `laje` |
| bw cm | Largura da seção transversal (editável) |
| h cm | Altura da seção transversal (editável) |
| L m | Comprimento do elemento (editável) |
| Score | Confiança da classificação automática |
| Status | ✅ Auto (≥80%) ou ⚠️ Revisar (<80%) |

### Passo a passo

1. Verifique se o tipo proposto está correto (dropdown na coluna Tipo)
2. Corrija bw/h/L se necessário (clique no campo e edite)
3. Marque os checkboxes dos elementos prontos (auto-aprovados já vêm marcados)
4. Clique **✅ Confirmar selecionados**

> ⚠️ **Este passo é obrigatório.** Sem confirmar, o exportador não enxerga os elementos.

### Alerta de nós desconectados

Se aparecer aviso laranja de "pares possivelmente desconectados", dois endpoints estão entre 5 mm e 30 mm de distância — provavelmente deveriam ser o mesmo nó. Corrija no SketchUp com snap e clique **↻ Reler**.

---

## 3. 🎨 Atribuir Cargas à Seleção

**Menu:** Extensions → Calculadora Estrutural → 🎨 Atribuir Cargas à Seleção

### Como usar

1. **Selecione** um ou mais componentes estruturais no modelo (Ctrl+clique para múltiplos, ou janela de seleção)
2. Acione o menu → abre o painel de paleta
3. Clique em uma categoria — todos os elementos selecionados recebem aquela carga e mudam de cor

### Paleta de usos (NBR 6120)

| Cor | Uso | Q (kN/m²) |
|---|---|---|
| 🟦 Azul | Dormitório / quarto | 1,5 |
| 🟩 Verde | Sala / circulação interna | 2,0 |
| 🟨 Amarelo | Cozinha / lavanderia | 2,0 |
| 🟧 Laranja | Escritório | 2,0 |
| 🟥 Vermelho | Cobertura acessível | 2,0 |
| ⬜ Branco/Cinza | Cobertura não-acessível | 0,5 |
| 🟫 Marrom | Garagem | 3,0 |
| ⬛ Preto | Área técnica / máquinas | 5,0 |

### Cargas pontuais

No mesmo painel, seção **📍 Carga pontual (kN)**:

- **Descrição** — ex.: "Reservatório 1500L"
- **kN** — valor da força (positivo; a extensão aplica para baixo)
- **x/L (0–1)** — posição ao longo do elemento (0 = início, 0.5 = meio, 1 = fim)

Clique **➕ Adicionar carga pontual** — pode adicionar várias ao mesmo elemento.

> Aplicável principalmente a vigas. Útil para reservatórios, caixas d'água, escadas.

### Restaurar cores

**Menu:** 🎨 Restaurar Cores Originais — remove os materiais de carga de todos os elementos.

---

## 4. 🔧 Inserir Apoio

**Menu:** Extensions → Calculadora Estrutural → 🔧 Inserir Apoio → escolha o tipo

| Símbolo | Tipo | Graus fixos |
|---|---|---|
| 🔺 Pirâmide azul | Rótula | Tx, Ty, Tz (rotações livres) |
| ⬛ Cubo vermelho | Engastamento | Todos os 6 DOF |
| 🟢 Cilindro verde X | Rolete eixo X | Ty, Tz (desliza em X) |
| 🟢 Cilindro verde Y | Rolete eixo Y | Tx, Tz (desliza em Y) |

### Como posicionar

Ao selecionar um tipo, uma caixa pedirá as coordenadas X, Y, Z em metros. Posicione o apoio na base do pilar correspondente (coordenada Z = 0 para pilares no térreo).

O exportador detecta automaticamente qual pilar está mais próximo (tolerância 10 cm) e associa o vínculo.

> Se nenhum apoio gráfico for inserido num pilar, o exportador assume **engastado** por padrão.

---

## 5. ⚙️ Configurar Elemento (override manual)

**Menu:** Extensions → Calculadora Estrutural → ⚙️ Configurar Elemento Selecionado

Use este dialog para ajustar qualquer campo individualmente após a revisão automática, ou para adicionar paredes, cobrimento, φ de armadura, etc.

O dialog tem 3 abas:
- **Geometria** — tipo, bw, h, comprimento, nome, ID
- **Cargas** — paredes (múltiplas), revestimento, variável, cargas especiais
- **Vínculos** — engastado/rotulado, pavimento

> Os valores configurados aqui têm **prioridade** sobre os valores extraídos automaticamente.

---

## 6. 📤 Exportar Modelo → Python

**Menu:** Extensions → Calculadora Estrutural → 📤 Exportar Modelo → Python

### Pré-requisitos (antes de clicar Exportar)

- [ ] Todos os elementos passaram pelo **📐 Confirmar** (passo 2)
- [ ] Cargas atribuídas por cor ou pelo dialog ⚙️
- [ ] Pilares com apoio gráfico ou vínculo configurado

### Como usar

1. Clique **↻** ao lado de "Elementos no modelo" — deve mostrar a contagem correta
2. Clique **🔍 Verificar** — resolva avisos antes de exportar
3. Selecione Concreto, Aço, Combinação e Agressividade
4. Clique **📤 Exportar JSON**
5. O arquivo é salvo na **Área de Trabalho** com nome `estrutural_YYYYMMDD_HHMMSS.json`

---

## 7. Verificar modelo antes de exportar

**Menu:** 🔍 Verificar modelo antes de exportar

Mostra alertas de:
- Elementos sem nome
- Vigas sem cargas definidas
- Pilares sem vínculo de base
- Elementos com score de classificação < 80%
- Nomes duplicados

---

## Sequência completa — exemplo prático

```
1. Desenhe pilar 30×40cm, 3m de altura como Componente
2. Desenhe pilar 30×40cm, 3m de altura como Componente
3. Desenhe viga 25×50cm, 5m de comprimento como Componente
   → Use snap para que a extremidade da viga toque o topo dos pilares

4. Menu: 📐 Revisar Geometria Extraída
   → Vê: p1 (pilar 97%), p2 (pilar 97%), v1 (viga 97%)
   → Todos já marcados ✅
   → Clica "✅ Confirmar selecionados"
   → Mensagem: "3 elemento(s) confirmado(s)"

5. Seleciona a viga no modelo
   Menu: 🎨 Atribuir Cargas à Seleção
   → Clica "🟦 Dormitório" (Q = 1,5 kN/m²)

6. Menu: 🔧 Inserir Apoio → Engastamento
   → X: 0, Y: 0, Z: 0  (base do pilar 1)
   Menu: 🔧 Inserir Apoio → Engastamento
   → X: 5, Y: 0, Z: 0  (base do pilar 2)

7. Menu: 📤 Exportar Modelo → Python
   → Clica ↻ → mostra: Total 3, Vigas 1, Pilares 2
   → Clica 🔍 Verificar → nenhum problema
   → Seleciona C30, CA-50, Normal, II
   → Clica 📤 Exportar JSON
   → Arquivo salvo na Área de Trabalho
```

---

## Dúvidas frequentes

**Os sólidos precisam se sobrepor para os nós coincidirem?**
Não. O que importa é que as coordenadas das extremidades dos eixos coincidam (tolerância 5 mm). Com snap ativo em vértice, isso acontece automaticamente.

**Confirmei os elementos mas o exportador mostra "—".**
Feche e reabra o dialog de exportação. Se continuar, clique ↻ (atualizar) dentro do dialog.

**O tipo foi classificado errado (viga virou pilar).**
Edite o dropdown Tipo diretamente no painel 📐, corrija e confirme novamente.

**Posso configurar elementos sem usar a revisão automática?**
Sim. Use ⚙️ Configurar Elemento diretamente em cada componente — o fluxo manual continua funcionando como na v3.0.

**Onde ficam os dados gravados?**
Nos atributos do componente SketchUp (dicionário `structural_data`). Salvando o arquivo `.skp` os dados são preservados.
