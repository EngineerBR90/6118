# =============================================================================
# setup_attributes.rb  — v3.0
# Extensão SketchUp: Configuração de Atributos Estruturais
#
# Novidades v3.0 (Fase 2):
#   • Dialog com 3 abas: Geometria | Cargas | Vínculos
#   • Aba Cargas: dropdowns ligados ao load_library.json
#     - Paredes: lista editável com + / × (múltiplas paredes por elemento)
#     - Revestimento: dropdown único (piso/teto)
#     - Carga variável: dropdown por tipo de uso NBR 6120
#     - Cargas especiais (kN/m): campo livre para equipamentos, fachadas etc.
#   • Aba Vínculos: engastado / rotulado + pavimento_hint manual
#   • Callback load_library: lê load_library.json e retorna ao JS
#   • Botão "Copiar cargas deste elemento" → clipboard interno para batch copy
# =============================================================================

require 'json'

module StructuralCalculatorExt
  module SetupDialog

    DICT_NAME = "structural_data"

    # ── Caminho do load_library.json ──────────────────────────────────────────
    def self.library_path
      File.join(File.dirname(File.expand_path(__FILE__)), 'load_library.json')
    end

    def self.load_library
      return {} unless File.exist?(library_path)
      JSON.parse(File.read(library_path, encoding: 'UTF-8'))
    rescue => e
      {}
    end

    # ── Entry point ───────────────────────────────────────────────────────────
    def self.show
      model     = Sketchup.active_model
      selection = model.selection
      instance  = selection.find { |e|
        e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
      }
      unless instance
        UI.messagebox(
          "Selecione um componente ou grupo no modelo\ne tente novamente.",
          MB_OK, "Calculadora Estrutural"
        )
        return
      end

      existing = load_existing(instance)
      lib      = load_library

      dlg = UI::HtmlDialog.new(
        dialog_name:     "calc_estrutural_setup_v3",
        preferences_key: "calc_estrutural_setup_v3",
        width:  600,
        height: 720,
        resizable: true
      )
      dlg.set_html(build_html(instance, existing, lib))
      register_callbacks(dlg, model, instance, lib)
      dlg.show
    end

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def self.register_callbacks(dlg, model, instance, lib)
      dlg.add_action_callback("close") { |_ctx, _| dlg.close }

      # Retorna a biblioteca de cargas ao JS (chamado no onload)
      dlg.add_action_callback("get_library") do |_ctx, _|
        dlg.execute_script("receiveLibrary(#{lib.to_json})")
      end

      # Lê atributos existentes (para sincronizar após mudança de tipo)
      dlg.add_action_callback("get_existing") do |_ctx, _|
        existing = load_existing(instance)
        dlg.execute_script("receiveExisting(#{existing.to_json})")
      end

      # Salva tudo no componente
      dlg.add_action_callback("save_attributes") do |_ctx, data_json|
        begin
          data = JSON.parse(data_json)
          save_to_instance(model, instance, data)
          dlg.execute_script("showStatus('ok', '✓ Salvo! (Ctrl+Z para desfazer)')")
        rescue => e
          msg = e.message.to_s.gsub("'", "\\'").gsub("\n", " ")
          dlg.execute_script("showStatus('err', 'Erro: #{msg}')")
        end
      end

      # Copia cargas para a área de transferência interna (batch)
      dlg.add_action_callback("copy_loads") do |_ctx, data_json|
        @@_clipboard_loads = JSON.parse(data_json) rescue {}
        dlg.execute_script("showStatus('ok', '✓ Cargas copiadas para transferência em lote.')")
      end

      # Cola cargas copiadas
      dlg.add_action_callback("paste_loads") do |_ctx, _|
        if defined?(@@_clipboard_loads) && !@@_clipboard_loads.empty?
          dlg.execute_script("pasteLoads(#{@@_clipboard_loads.to_json})")
        else
          dlg.execute_script("showStatus('warn', '⚠️ Nenhuma carga copiada ainda.')")
        end
      end
    end

    # ── Persistência ──────────────────────────────────────────────────────────
    def self.load_existing(instance)
      dict = instance.attribute_dictionary(DICT_NAME)
      return {} unless dict
      result = {}
      dict.each { |k, v| result[k.to_s] = v }
      result
    end

    def self.save_to_instance(model, instance, data)
      model.start_operation("Configurar Elemento Estrutural", true)
      dict = instance.attribute_dictionary(DICT_NAME, true)
      data["id"] ||= "#{data['tipo']}-#{Time.now.to_i}-#{rand(1000..9999)}"
      data.each do |key, value|
        next if key.nil? || key.to_s.strip.empty?
        if value.is_a?(String) && value =~ /\A[-+]?\d+\z/
          value = value.to_i
        elsif value.is_a?(String) && value =~ /\A[-+]?\d+(\.\d+)?\z/
          value = value.to_f
        end
        dict[key.to_s] = value
      end
      model.commit_operation
    end

    # ── HTML do dialog (3 abas) ───────────────────────────────────────────────
    def self.build_html(instance, existing, lib)
      tipo_atual = existing["tipo"] || "viga"
      nome_inst  = instance.respond_to?(:name) ? instance.name.to_s : ""
      nome_inst  = "(sem nome)" if nome_inst.strip.empty?

      <<~HTML
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
        <meta charset="UTF-8">
        <title>Configurar Elemento</title>
        <style>
          *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
          body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:13px;
            background:#0f1117;color:#e0e6f0;padding:0;display:flex;flex-direction:column;height:100vh}
          /* ── Header ── */
          .hdr{background:#141c2b;border-bottom:1px solid #1e2a3a;padding:12px 18px}
          .hdr h1{color:#60a5fa;font-size:15px;font-weight:700}
          .hdr p{color:#6b7fa0;font-size:11px;margin-top:2px}
          /* ── Tipo selector ── */
          .tipo-bar{display:flex;gap:6px;padding:10px 18px;background:#0f1117;border-bottom:1px solid #1e2a3a}
          .tipo-btn{flex:1;padding:7px 4px;border-radius:5px;border:1px solid #1e2a3a;
            background:#141c2b;color:#8a9bbf;cursor:pointer;font-size:12px;font-weight:600;text-align:center}
          .tipo-btn:hover{border-color:#3b82f6;color:#60a5fa}
          .tipo-btn.active{background:#1d3461;border-color:#3b82f6;color:#60a5fa}
          /* ── Tabs ── */
          .tabs{display:flex;border-bottom:1px solid #1e2a3a;background:#0f1117;padding:0 18px}
          .tab{padding:8px 16px;font-size:12px;font-weight:600;color:#6b7fa0;
            cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
          .tab:hover{color:#e0e6f0}
          .tab.active{color:#60a5fa;border-bottom-color:#3b82f6}
          /* ── Scroll content ── */
          .content{flex:1;overflow-y:auto;padding:16px 18px}
          .panel{display:none}.panel.active{display:block}
          /* ── Form ── */
          .row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
          .row.full{grid-template-columns:1fr}
          .fg label{display:block;font-size:11px;color:#8a9bbf;margin-bottom:3px}
          input,select{width:100%;padding:6px 8px;background:#141c2b;border:1px solid #1e2a3a;
            border-radius:4px;color:#e0e6f0;font-size:12px}
          input:focus,select:focus{outline:none;border-color:#3b82f6}
          .sep{font-size:10px;font-weight:700;color:#6b7fa0;text-transform:uppercase;
            letter-spacing:.8px;margin:14px 0 8px;padding-top:8px;border-top:1px solid #1e2a3a}
          /* ── Paredes list ── */
          .wall-list{background:#0a0e17;border:1px solid #1e2a3a;border-radius:6px;padding:8px;margin-bottom:8px}
          .wall-item{display:flex;align-items:center;gap:6px;margin-bottom:6px}
          .wall-item select{flex:1}
          .wall-item input[type=number]{width:70px;flex:none}
          .wall-item span{font-size:10px;color:#6b7fa0;white-space:nowrap}
          .wall-rm{background:none;border:none;color:#ef4444;cursor:pointer;font-size:16px;padding:0 4px;line-height:1}
          .wall-rm:hover{color:#dc2626}
          .btn-add{width:100%;padding:6px;border:1px dashed #1e2a3a;border-radius:4px;
            background:none;color:#6b7fa0;cursor:pointer;font-size:12px}
          .btn-add:hover{border-color:#3b82f6;color:#60a5fa}
          /* ── Badges de carga calculada ── */
          .calc-box{background:#141c2b;border:1px solid #1e2a3a;border-radius:6px;
            padding:10px 12px;margin-top:10px}
          .calc-row{display:flex;justify-content:space-between;font-size:12px;
            color:#8a9bbf;padding:2px 0}
          .calc-row span:last-child{color:#60a5fa;font-weight:600}
          .calc-total{border-top:1px solid #1e2a3a;margin-top:6px;padding-top:6px;
            font-weight:700;color:#34d399 !important}
          /* ── Footer ── */
          .footer{display:flex;gap:8px;padding:12px 18px;border-top:1px solid #1e2a3a;background:#0f1117}
          .btn{flex:1;padding:9px;border:none;border-radius:5px;font-size:12px;
            font-weight:700;cursor:pointer}
          .btn-save{background:#3b82f6;color:#fff}
          .btn-save:hover{background:#2563eb}
          .btn-copy{background:#141c2b;color:#8a9bbf;border:1px solid #1e2a3a;flex:none;padding:9px 14px}
          .btn-copy:hover{border-color:#3b82f6;color:#60a5fa}
          .btn-paste{background:#141c2b;color:#8a9bbf;border:1px solid #1e2a3a;flex:none;padding:9px 14px}
          .btn-paste:hover{border-color:#34d399;color:#34d399}
          .btn-cancel{background:#141c2b;color:#8a9bbf;border:1px solid #1e2a3a;flex:none;padding:9px 14px}
          /* ── Status ── */
          #status{display:none;margin:8px 18px 0;padding:8px 12px;border-radius:5px;font-size:12px}
          #status.ok  {background:#052e16;border:1px solid #16a34a;color:#4ade80}
          #status.err {background:#2d0a0a;border:1px solid #dc2626;color:#f87171}
          #status.warn{background:#2d2006;border:1px solid #d97706;color:#fbbf24}
        </style>
        </head>
        <body>

        <div class="hdr">
          <h1>⚙️ Configurar Elemento Estrutural</h1>
          <p>Componente: <strong style="color:#e0e6f0">#{nome_inst}</strong></p>
        </div>

        <!-- Seletor de tipo -->
        <div class="tipo-bar">
          <div class="tipo-btn #{tipo_atual=='viga'  ? 'active' : ''}" onclick="setTipo('viga',this)">🔩 Viga</div>
          <div class="tipo-btn #{tipo_atual=='pilar' ? 'active' : ''}" onclick="setTipo('pilar',this)">🏛️ Pilar</div>
          <div class="tipo-btn #{tipo_atual=='laje'  ? 'active' : ''}" onclick="setTipo('laje',this)">🧱 Laje</div>
        </div>
        <input type="hidden" id="tipo" value="#{tipo_atual}">

        <!-- Abas -->
        <div class="tabs">
          <div class="tab active" onclick="showTab('geo',this)">📐 Geometria</div>
          <div class="tab" onclick="showTab('loads',this)">⚖️ Cargas</div>
          <div class="tab" onclick="showTab('vinc',this)">🔒 Vínculos</div>
        </div>

        <div class="content">

          <!-- ── ABA GEOMETRIA ─────────────────────────────────────────── -->
          <div id="panel-geo" class="panel active">
            <div class="sep" style="margin-top:4px;border-top:none">Identificação</div>
            <div class="row">
              <div class="fg">
                <label>Nome do elemento</label>
                <input type="text" id="g-nome" value="#{existing['nome'] || 'Elemento'}">
              </div>
              <div class="fg">
                <label>Cobrimento nominal (mm)</label>
                <input type="number" id="g-cnom" value="#{existing['cobrimento_nominal'] || 30}" step="1" min="10">
              </div>
            </div>
            <div class="row">
              <div class="fg">
                <label>φ longitudinal (mm)</label>
                <input type="number" id="g-phil" value="#{existing['phi_longitudinal'] || 20}" step="1">
              </div>
              <div class="fg">
                <label>φ estribo (mm)</label>
                <input type="number" id="g-phie" value="#{existing['phi_estribo'] || 8}" step="1">
              </div>
            </div>
            <div class="sep">Seção Transversal</div>
            <div class="row">
              <div class="fg">
                <label>Largura b<sub>w</sub> (cm)</label>
                <input type="number" id="g-bw" value="#{existing['largura'] || 25}" step="1" min="1">
              </div>
              <div class="fg">
                <label>Altura h (cm)</label>
                <input type="number" id="g-h" value="#{existing['altura'] || 50}" step="1" min="1">
              </div>
            </div>
            <div id="pilar-le" style="display:#{tipo_atual=='pilar' ? 'block' : 'none'}">
              <div class="sep">Comprimento Efetivo (pilares)</div>
              <div class="row">
                <div class="fg">
                  <label>Le,x — eixo x (m)</label>
                  <input type="number" id="g-lex" value="#{existing['comprimento_le_x'] || 0}" step="0.01">
                </div>
                <div class="fg">
                  <label>Le,y — eixo y (m)</label>
                  <input type="number" id="g-ley" value="#{existing['comprimento_le_y'] || 0}" step="0.01">
                </div>
              </div>
            </div>
          </div>

          <!-- ── ABA CARGAS ────────────────────────────────────────────── -->
          <div id="panel-loads" class="panel">
            <div class="sep" style="margin-top:4px;border-top:none">Paredes sobre o elemento</div>
            <div class="wall-list" id="wall-list">
              <!-- preenchido pelo JS -->
            </div>
            <button class="btn-add" onclick="addWall()">+ Adicionar parede</button>

            <div class="sep">Revestimento de piso/teto</div>
            <div class="row full">
              <div class="fg">
                <label>Tipo de revestimento</label>
                <select id="l-rev"></select>
              </div>
            </div>

            <div class="sep">Carga variável (NBR 6120)</div>
            <div class="row full">
              <div class="fg">
                <label>Tipo de uso / ocupação</label>
                <select id="l-var"></select>
              </div>
            </div>

            <div class="sep">Cargas especiais</div>
            <div class="row">
              <div class="fg">
                <label>Carga especial G (kN/m)</label>
                <input type="number" id="l-gesp" value="#{existing['especiais_kN_m'] || 0}" step="0.1" min="0"
                  oninput="recalc()">
              </div>
              <div class="fg">
                <label>Altura livre da parede (m)</label>
                <input type="number" id="l-hpared" value="#{existing['altura_parede_m'] || 2.80}" step="0.05" min="0.5"
                  oninput="recalc()">
              </div>
            </div>

            <!-- Resumo calculado -->
            <div class="calc-box">
              <div style="font-size:11px;color:#6b7fa0;margin-bottom:6px;font-weight:700">
                RESUMO — Cargas sobre o elemento (kN/m lineares)
              </div>
              <div class="calc-row"><span>Paredes</span><span id="r-paredes">—</span></div>
              <div class="calc-row"><span>Revestimento</span><span id="r-rev">—</span></div>
              <div class="calc-row"><span>Especiais</span><span id="r-esp">—</span></div>
              <div class="calc-row"><span>Carga variável Q</span><span id="r-var">—</span></div>
              <div class="calc-row calc-total"><span>Total G</span><span id="r-gtot">—</span></div>
            </div>
          </div>

          <!-- ── ABA VÍNCULOS ──────────────────────────────────────────── -->
          <div id="panel-vinc" class="panel">
            <div class="sep" style="margin-top:4px;border-top:none">Vínculo na base</div>
            <div class="row full">
              <div class="fg">
                <label>Tipo de vínculo</label>
                <select id="v-vinc">
                  <option value="engastado" #{(existing['vinculo_base']||'engastado')=='engastado' ? 'selected' : ''}>
                    Engastado — todos os 6 DOFs fixos
                  </option>
                  <option value="rotulado" #{existing['vinculo_base']=='rotulado' ? 'selected' : ''}>
                    Rotulado — translações fixas, rotações livres
                  </option>
                </select>
              </div>
            </div>
            <div class="row full">
              <div class="fg">
                <label>Pavimento (hint para o solver — 0 = automático)</label>
                <input type="number" id="v-pav" value="#{existing['pavimento_hint'] || 0}" step="1" min="0">
              </div>
            </div>
            <div style="background:#141c2b;border:1px solid #1e2a3a;border-radius:6px;padding:10px 12px;margin-top:12px">
              <div style="font-size:11px;color:#6b7fa0;margin-bottom:6px">
                ℹ️ <strong style="color:#e0e6f0">Sobre vínculos</strong>
              </div>
              <div style="font-size:11px;color:#8a9bbf;line-height:1.7">
                <b>Engastado:</b> fundação rígida, sapata, bloco de coroamento.<br>
                <b>Rotulado:</b> apoio em viga, pilar inferior ou fundação tipo pino.<br>
                O solver detecta automaticamente vínculos de pavimentos superiores
                (pilares cujo nó de base coincide com o topo de outro pilar).
              </div>
            </div>
          </div>

        </div><!-- /content -->

        <div id="status"></div>

        <!-- Footer -->
        <div class="footer">
          <button class="btn btn-save"   onclick="save()">💾 Salvar</button>
          <button class="btn btn-copy"   onclick="copyLoads()" title="Copiar cargas para colar em outros elementos">📋</button>
          <button class="btn btn-paste"  onclick="sketchup.paste_loads('')"  title="Colar cargas copiadas">📥</button>
          <button class="btn btn-cancel" onclick="sketchup.close()">✕</button>
        </div>

        <script>
        // ── Estado ────────────────────────────────────────────────────────────
        var LIB        = {};
        var EXISTING   = #{existing.to_json};
        var wallCount  = 0;

        // ── Init ──────────────────────────────────────────────────────────────
        window.onload = function() {
          sketchup.get_library('');
          sketchup.get_existing('');
        };

        function receiveLibrary(lib) {
          LIB = lib;
          buildRevSelect();
          buildVarSelect();
          buildWallsFromExisting();
          recalc();
        }

        function receiveExisting(ex) {
          EXISTING = ex;
        }

        // ── Tipo de elemento ──────────────────────────────────────────────────
        function setTipo(tipo, btn) {
          document.getElementById('tipo').value = tipo;
          document.querySelectorAll('.tipo-btn').forEach(function(b){ b.classList.remove('active'); });
          btn.classList.add('active');
          // Mostra/esconde Le para pilares
          document.getElementById('pilar-le').style.display = tipo === 'pilar' ? 'block' : 'none';
        }

        // ── Abas ──────────────────────────────────────────────────────────────
        function showTab(id, el) {
          document.querySelectorAll('.panel').forEach(function(p){ p.classList.remove('active'); });
          document.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
          document.getElementById('panel-' + id).classList.add('active');
          el.classList.add('active');
        }

        // ── Dropdowns de biblioteca ───────────────────────────────────────────
        function buildRevSelect() {
          var sel = document.getElementById('l-rev');
          sel.innerHTML = '';
          var revs = (LIB['revestimentos'] || []);
          var curId = EXISTING['revestimento_id'] || 'sem_revestimento';
          revs.forEach(function(r) {
            var opt = document.createElement('option');
            opt.value = r['id'];
            opt.textContent = r['nome'] + ' (' + r['kN_m2'] + ' kN/m²)';
            if (r['id'] === curId) opt.selected = true;
            sel.appendChild(opt);
          });
          sel.onchange = recalc;
        }

        function buildVarSelect() {
          var sel = document.getElementById('l-var');
          sel.innerHTML = '';
          var vars = (LIB['variavel_nbr6120'] || []);
          var curId = EXISTING['variavel_id'] || '';
          vars.forEach(function(v) {
            var opt = document.createElement('option');
            opt.value = v['id'];
            opt.textContent = v['nome'] + ' — ' + v['kN_m2'] + ' kN/m²';
            if (v['id'] === curId) opt.selected = true;
            sel.appendChild(opt);
          });
          sel.onchange = recalc;
        }

        // ── Paredes ───────────────────────────────────────────────────────────
        function buildWallsFromExisting() {
          var walls = EXISTING['paredes'];
          if (!walls || !walls.length) { addWall(); return; }
          try {
            if (typeof walls === 'string') walls = JSON.parse(walls);
          } catch(e) { addWall(); return; }
          walls.forEach(function(w) { addWall(w['id'], w['comprimento_m']); });
        }

        function addWall(wallId, comp) {
          wallCount++;
          var list = document.getElementById('wall-list');
          var row  = document.createElement('div');
          row.className = 'wall-item';
          row.id = 'wall-row-' + wallCount;

          var sel = document.createElement('select');
          sel.id  = 'wall-sel-' + wallCount;
          (LIB['paredes'] || []).forEach(function(p) {
            var opt = document.createElement('option');
            opt.value = p['id'];
            opt.textContent = p['nome'].replace(/ \(.*/, '') + ' — ' + p['kN_m2'] + ' kN/m²';
            if (wallId && p['id'] === wallId) opt.selected = true;
            sel.appendChild(opt);
          });
          sel.onchange = recalc;

          var inp = document.createElement('input');
          inp.type = 'number'; inp.id = 'wall-len-' + wallCount;
          inp.value = comp || 1.0; inp.step = 0.1; inp.min = 0.1;
          inp.style.width = '70px'; inp.oninput = recalc;

          var lbl = document.createElement('span'); lbl.textContent = 'm';
          var rm  = document.createElement('button');
          rm.className = 'wall-rm'; rm.textContent = '×';
          var wid = wallCount;
          rm.onclick = function() {
            document.getElementById('wall-row-' + wid).remove();
            recalc();
          };

          row.appendChild(sel); row.appendChild(inp);
          row.appendChild(lbl); row.appendChild(rm);
          list.appendChild(row);
          recalc();
        }

        // ── Cálculo do resumo ─────────────────────────────────────────────────
        function recalc() {
          var hPared = parseFloat(document.getElementById('l-hpared').value) || 2.80;

          // Paredes
          var gParedes = 0;
          document.querySelectorAll('.wall-item').forEach(function(row) {
            var id  = row.id.replace('wall-row-', '');
            var sel = document.getElementById('wall-sel-' + id);
            var len = parseFloat(document.getElementById('wall-len-' + id).value) || 0;
            if (!sel) return;
            var wallId = sel.value;
            var wall   = (LIB['paredes'] || []).find(function(p){ return p['id'] === wallId; });
            if (wall) gParedes += wall['kN_m2'] * hPared * len;
          });

          // Revestimento — converte kN/m² → kN/m linear
          // Usa a largura tributária como 1m (o solver distribui pelas vigas)
          var revSel = document.getElementById('l-rev');
          var revId  = revSel ? revSel.value : '';
          var rev    = (LIB['revestimentos'] || []).find(function(r){ return r['id'] === revId; });
          var gRev   = rev ? parseFloat(rev['kN_m2']) : 0;

          // Variável
          var varSel = document.getElementById('l-var');
          var varId  = varSel ? varSel.value : '';
          var vObj   = (LIB['variavel_nbr6120'] || []).find(function(v){ return v['id'] === varId; });
          var qVar   = vObj ? parseFloat(vObj['kN_m2']) : 0;

          // Especiais
          var gEsp = parseFloat(document.getElementById('l-gesp').value) || 0;

          var gTot = gParedes + gRev + gEsp;

          document.getElementById('r-paredes').textContent = gParedes.toFixed(2) + ' kN/m';
          document.getElementById('r-rev').textContent     = gRev.toFixed(2)     + ' kN/m²';
          document.getElementById('r-esp').textContent     = gEsp.toFixed(2)     + ' kN/m';
          document.getElementById('r-var').textContent     = qVar.toFixed(2)     + ' kN/m²';
          document.getElementById('r-gtot').textContent    = gTot.toFixed(2)     + ' kN/m';
        }

        // ── Coleta de dados para salvar ───────────────────────────────────────
        function collectData() {
          var tipo = document.getElementById('tipo').value;
          var hPared = parseFloat(document.getElementById('l-hpared').value) || 2.80;

          // Paredes
          var walls = [];
          document.querySelectorAll('.wall-item').forEach(function(row) {
            var id  = row.id.replace('wall-row-', '');
            var sel = document.getElementById('wall-sel-' + id);
            var len = parseFloat(document.getElementById('wall-len-' + id).value) || 0;
            if (sel) walls.push({ id: sel.value, comprimento_m: len });
          });

          var revSel = document.getElementById('l-rev');
          var varSel = document.getElementById('l-var');

          return {
            tipo:                tipo,
            nome:                document.getElementById('g-nome').value,
            cobrimento_nominal:  document.getElementById('g-cnom').value,
            phi_longitudinal:    document.getElementById('g-phil').value,
            phi_estribo:         document.getElementById('g-phie').value,
            largura:             document.getElementById('g-bw').value,
            altura:              document.getElementById('g-h').value,
            comprimento_le_x:    document.getElementById('g-lex').value,
            comprimento_le_y:    document.getElementById('g-ley').value,
            // Cargas
            paredes:             JSON.stringify(walls),
            altura_parede_m:     hPared,
            revestimento_id:     revSel ? revSel.value : '',
            variavel_id:         varSel ? varSel.value : '',
            especiais_kN_m:      document.getElementById('l-gesp').value,
            // Vínculos
            vinculo_base:        document.getElementById('v-vinc').value,
            pavimento_hint:      document.getElementById('v-pav').value,
          };
        }

        function save() {
          sketchup.save_attributes(JSON.stringify(collectData()));
        }

        function copyLoads() {
          var d = collectData();
          var loads = {
            paredes:        d['paredes'],
            altura_parede_m:d['altura_parede_m'],
            revestimento_id:d['revestimento_id'],
            variavel_id:    d['variavel_id'],
            especiais_kN_m: d['especiais_kN_m'],
          };
          sketchup.copy_loads(JSON.stringify(loads));
        }

        function pasteLoads(loads) {
          if (!loads) return;
          if (loads['revestimento_id']) {
            var revSel = document.getElementById('l-rev');
            if (revSel) {
              for(var i=0;i<revSel.options.length;i++){
                if(revSel.options[i].value===loads['revestimento_id']){revSel.selectedIndex=i;break;}
              }
            }
          }
          if (loads['variavel_id']) {
            var varSel = document.getElementById('l-var');
            if (varSel) {
              for(var i=0;i<varSel.options.length;i++){
                if(varSel.options[i].value===loads['variavel_id']){varSel.selectedIndex=i;break;}
              }
            }
          }
          if (loads['especiais_kN_m'] !== undefined) {
            document.getElementById('l-gesp').value = loads['especiais_kN_m'];
          }
          if (loads['altura_parede_m']) {
            document.getElementById('l-hpared').value = loads['altura_parede_m'];
          }
          if (loads['paredes']) {
            document.getElementById('wall-list').innerHTML = '';
            wallCount = 0;
            try {
              var walls = typeof loads['paredes']==='string'
                ? JSON.parse(loads['paredes']) : loads['paredes'];
              walls.forEach(function(w){ addWall(w['id'], w['comprimento_m']); });
            } catch(e) { addWall(); }
          }
          recalc();
          showStatus('ok', '✓ Cargas coladas.');
        }

        function showStatus(cls, msg) {
          var s = document.getElementById('status');
          s.className     = cls;
          s.textContent   = msg;
          s.style.display = 'block';
          if (cls === 'ok') setTimeout(function(){ s.style.display='none'; }, 3000);
        }
        </script>
        </body>
        </html>
      HTML
    end

  end
end
