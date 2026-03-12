# =============================================================================
# extension_main.rb  — v4.0
# Extensão SketchUp: Calculadora Estrutural NBR 6118:2023
#
# Novidades v4.0:
#   • 📐 Revisar Geometria Extraída  (Módulo A1)
#       Auto-extrai b/h/L/tipo com score de confiança via StructuralExtractor.
#       Painel tabular com aprovação multi-seleção, edição inline e detecção
#       de nós possivelmente desconectados (5mm–30mm).
#   • 🎨 Atribuir Cargas à Seleção  (Módulo B1 + B2)
#       Paleta de 8 usos NBR 6120 + campo de carga pontual kN.
#       Multi-seleção: seleciona N elementos → clica uma cor → todos recebem.
#   • 🔧 Inserir Apoio  (Módulo C1)
#       Apoios gráficos gerados por Ruby API (pirâmide = rótula,
#       cubo = engaste, cilindro = rolete). Detectados por proximidade
#       na exportação, sem entrada manual de vínculo.
#   • Schema exportado: v3.1 (campos novos: extraction_score, carga_cor_id,
#       point_loads[], vinculo_source)
#
# Requer (mesmo diretório):
#   setup_attributes.rb   structural_exporter.rb
#   structural_extractor.rb  load_painter.rb  support_manager.rb
# =============================================================================

require 'json'

_ext_dir = File.dirname(File.expand_path(__FILE__))
require File.join(_ext_dir, 'structural_exporter')
require File.join(_ext_dir, 'setup_attributes')
require File.join(_ext_dir, 'structural_extractor')
require File.join(_ext_dir, 'load_painter')
require File.join(_ext_dir, 'support_manager')

module StructuralCalculatorExt

  DICT_NAME = "structural_data"

  # ── Menu ────────────────────────────────────────────────────────────────────
  def self.init
    unless file_loaded?(__FILE__)
      menu    = UI.menu("Extensions")
      sub     = menu.add_submenu("Calculadora Estrutural NBR 6118")

      sub.add_item("📤 Exportar Modelo → Python")           { MainDialog.show }
      sub.add_item("⚙️ Configurar Elemento Selecionado")    { SetupDialog.show }
      sub.add_separator

      sub.add_item("📐 Revisar Geometria Extraída")          { ReviewDialog.show }
      sub.add_item("🎨 Atribuir Cargas à Seleção")           { LoadPainter.show(Sketchup.active_model) }
      sub.add_item("🎨 Restaurar Cores Originais")           {
        LoadPainter.restore_colors(Sketchup.active_model)
        UI.messagebox("Cores originais restauradas.", MB_OK, "Calculadora Estrutural")
      }

      apoio_sub = sub.add_submenu("🔧 Inserir Apoio")
      SupportManager::SUPPORT_TYPES.each_key do |vtype|
        cfg = SupportManager::SUPPORT_TYPES[vtype]
        apoio_sub.add_item(cfg[:label]) {
          SupportManager._start_placement_tool(Sketchup.active_model, vtype)
        }
      end
      sub.add_separator

      sub.add_item("📋 Copiar config para seleção em lote") { BatchCopyDialog.show }
      sub.add_item("🔍 Verificar modelo antes de exportar") { ChecklistDialog.show }
      sub.add_item("📋 Listar Elementos no Console")        { list_console }

      file_loaded(__FILE__)
    end
  end

  # ── Utilitários de modelo ────────────────────────────────────────────────────
  def self.list_console
    count = 0
    Sketchup.active_model.definitions.each do |defn|
      next if defn.image?
      defn.instances.each do |inst|
        dict = inst.attribute_dictionary(DICT_NAME)
        next unless dict
        tipo = dict["tipo"].to_s
        next unless %w[viga pilar laje].include?(tipo)
        count += 1
        score = dict["extraction_score"]
        score_str = score ? " [#{(score.to_f * 100).round}%]" : ""
        puts "#{count}. [#{tipo.upcase}] #{dict['nome'] || inst.name}#{score_str}"
      end
    end
    puts count > 0 ? "\nTotal: #{count} elemento(s)" : "Nenhum elemento configurado."
  end

  def self.all_configured_instances
    result = []
    Sketchup.active_model.definitions.each do |defn|
      next if defn.image?
      defn.instances.each do |inst|
        dict = inst.attribute_dictionary(DICT_NAME)
        next unless dict
        next unless %w[viga pilar laje].include?(dict["tipo"].to_s)
        result << inst
      end
    end
    result
  end

  def self.check_model
    issues = []
    insts  = all_configured_instances
    nomes  = Hash.new(0)

    if insts.empty?
      return [{ level: "error", msg: "Nenhum elemento configurado no modelo." }]
    end

    insts.each do |inst|
      dict  = inst.attribute_dictionary(DICT_NAME)
      tipo  = dict["tipo"].to_s
      nome  = dict["nome"].to_s.strip
      eid   = dict["id"].to_s.strip
      score = dict["extraction_score"]

      issues << { level: "warning",
                  msg: "Elemento sem nome (id=#{eid || '?'})." } if nome.empty?
      nomes[nome] += 1 unless nome.empty?

      if score && score.to_f < 0.80
        issues << { level: "warning",
                    msg: "'#{nome}': score #{(score.to_f*100).round}% — revisar em 📐 Geometria." }
      end

      if tipo == "viga"
        cargas = dict.map { |k,v| [k,v] }.to_h
        has_load = !cargas["paredes_json"].to_s.empty? ||
                   !cargas["revestimento_tipo_id"].to_s.empty? ||
                   !cargas["variavel_tipo_id"].to_s.empty? ||
                   !cargas["carga_cor_id"].to_s.empty? ||
                   cargas["especiais_kN_m"].to_f > 0
        unless has_load
          issues << { level: "warning", msg: "Viga '#{nome}' sem cargas definidas." }
        end
      end

      if tipo == "pilar"
        vinc = dict["vinculo_base"].to_s
        # Verificar também se existe apoio gráfico próximo
        pos_ni_json = dict["no_inicio_json"].to_s
        has_grafic  = false
        unless pos_ni_json.empty?
          begin
            ni = JSON.parse(pos_ni_json)
            has_grafic = !!SupportManager.find_support_near(ni, Sketchup.active_model, 0.10)
          rescue; end
        end
        if vinc.empty? && !has_grafic
          issues << { level: "warning",
                      msg: "Pilar '#{nome}' sem vínculo de base. Será engastado." }
        end
      end
    end

    nomes.each do |nome, count|
      issues << { level: "error", msg: "Nome '#{nome}' duplicado em #{count} elementos." } if count > 1
    end

    issues
  end

  # ============================================================================
  # MÓDULO A1 — Painel de Revisão de Geometria
  # ============================================================================
  module ReviewDialog

    def self.show
      model   = Sketchup.active_model
      results = StructuralExtractor.extract_all(model)

      if results.empty?
        UI.messagebox(
          "Nenhum componente encontrado.\n" \
          "Os elementos estruturais devem ser Componentes ou Grupos no SketchUp.",
          MB_OK, "Revisar Geometria"
        )
        return
      end

      warnings = StructuralExtractor.find_near_disconnected(results)

      dlg = UI::HtmlDialog.new(
        dialog_name:     "calc_review_v4",
        preferences_key: "calc_review_v4",
        width: 780, height: 600, resizable: true
      )
      dlg.set_html(build_html(results, warnings))
      register_callbacks(dlg, model)
      dlg.show
    end

    def self.register_callbacks(dlg, model)
      dlg.add_action_callback("close") { |_,_| dlg.close }

      dlg.add_action_callback("confirm_all") do |_, json_str|
        begin
          confirmed = JSON.parse(json_str)
          StructuralExtractor.apply_confirmed(model, confirmed)
          dlg.execute_script("showStatus('✅ #{confirmed.length} elemento(s) confirmado(s). Ctrl+Z para desfazer.')")
        rescue => e
          dlg.execute_script("showStatus('❌ #{e.message.gsub("'","\\'")}')") 
        end
      end

      dlg.add_action_callback("refresh") do |_,_|
        dlg.close
        ReviewDialog.show
      end
    end

    def self.build_html(results, node_warnings)
      n_auto   = results.count { |r| !r["needs_review"] }
      n_review = results.count { |r|  r["needs_review"] }
      n_set    = results.count { |r|  r["already_set"]  }

      warn_html = ""
      if node_warnings.any?
        items = node_warnings.map { |w|
          "<div class='wi'>⚠️ <b>#{w['el_a']}</b>.#{w['end_a']} ↔ <b>#{w['el_b']}</b>.#{w['end_b']} — #{w['dist_mm']} mm</div>"
        }.join
        warn_html = "<div class='wbox'><b>⚠️ #{node_warnings.length} par(es) possivelmente desconectados</b>#{items}<div class='wh'>Use snap em vértice ou o botão Fundir Nós para corrigir.</div></div>"
      end

      rows_js = results.map(&:to_json).join(",\n")

      <<~HTML
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <style>
          *{box-sizing:border-box;margin:0;padding:0}
          body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:12px;
            background:#0f1117;color:#e0e6f0;display:flex;flex-direction:column;height:100vh}
          .hdr{padding:11px 16px;background:#141c2b;border-bottom:1px solid #1e2a3a}
          .hdr h1{font-size:13px;color:#60a5fa;font-weight:700}
          .hdr p{font-size:10px;color:#6b7fa0;margin-top:2px}
          .met{display:flex;gap:6px;padding:8px 16px;border-bottom:1px solid #1e2a3a}
          .chip{background:#141c2b;border:1px solid #1e2a3a;border-radius:5px;
            padding:5px 12px;text-align:center;min-width:74px}
          .chip .n{font-size:16px;font-weight:700;line-height:1}
          .chip .l{font-size:9px;color:#6b7fa0;margin-top:1px}
          .wbox{margin:8px 16px;padding:8px 11px;background:#2d2006;
            border:1px solid #d97706;border-radius:5px;font-size:10px;color:#fde68a}
          .wi{padding:2px 0;line-height:1.4}
          .wh{color:#a0814d;font-style:italic;margin-top:4px}
          .tw{flex:1;overflow:auto;padding:0 16px 8px}
          table{width:100%;border-collapse:collapse;margin-top:8px}
          th{background:#141c2b;color:#6b7fa0;font-size:9px;font-weight:700;
            text-transform:uppercase;letter-spacing:.5px;padding:6px 7px;
            border-bottom:1px solid #1e2a3a;text-align:left;white-space:nowrap}
          td{padding:4px 7px;border-bottom:1px solid #141c2b;vertical-align:middle}
          tr:hover td{background:#141c2b}
          .sb{display:inline-block;padding:2px 6px;border-radius:8px;
            font-size:9px;font-weight:700;color:#0f1117}
          select.ts{background:#0f1117;border:1px solid #1e2a3a;border-radius:3px;
            color:#e0e6f0;padding:2px 4px;font-size:10px;width:66px}
          input.di{background:#0f1117;border:1px solid #1e2a3a;border-radius:3px;
            color:#e0e6f0;padding:2px 4px;font-size:10px;text-align:right}
          .ok{color:#22c55e}.warn{color:#f59e0b}.ab{font-size:8px;padding:1px 4px;
            background:#1d3461;color:#60a5fa;border-radius:3px;margin-left:3px}
          .ft{padding:9px 16px;border-top:1px solid #1e2a3a;background:#0f1117;
            display:flex;justify-content:space-between;align-items:center}
          .st{font-size:11px;color:#34d399;flex:1;padding-right:10px}
          .br{display:flex;gap:7px}
          button{padding:7px 14px;border:none;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer}
          .bc{background:#3b82f6;color:#fff}.bc:hover{background:#2563eb}
          .bx{background:#1a2235;color:#8a9bbf;border:1px solid #1e2a3a}
          .br2{background:#141c2b;color:#6b7fa0;border:1px solid #1e2a3a}
          .chk{width:13px;height:13px;cursor:pointer}
        </style></head><body>
        <div class="hdr">
          <h1>📐 Revisar Geometria Extraída</h1>
          <p>Geometria calculada da bounding box. Score ≥ 80% aprovado automaticamente. Edite campos se necessário.</p>
        </div>
        <div class="met">
          <div class="chip"><div class="n ok">#{n_auto}</div><div class="l">Auto ✅</div></div>
          <div class="chip"><div class="n warn">#{n_review}</div><div class="l">Revisar ⚠️</div></div>
          <div class="chip"><div class="n" style="color:#60a5fa">#{n_set}</div><div class="l">Já config.</div></div>
          <div class="chip"><div class="n">#{results.length}</div><div class="l">Total</div></div>
        </div>
        #{warn_html}
        <div class="tw">
          <table>
            <thead><tr>
              <th><input type="checkbox" id="ca" onchange="toggleAll(this)" class="chk"></th>
              <th>Nome</th><th>Tipo</th><th>bw cm</th><th>h cm</th><th>L m</th>
              <th>Score</th><th>Status</th>
            </tr></thead>
            <tbody id="tb"></tbody>
          </table>
        </div>
        <div class="ft">
          <span class="st" id="st">Edite se necessário e confirme.</span>
          <div class="br">
            <button class="br2" onclick="sketchup.refresh('')">↻ Reler</button>
            <button class="bc" onclick="confirmSel()">✅ Confirmar selecionados</button>
            <button class="bx" onclick="sketchup.close()">✕ Fechar</button>
          </div>
        </div>
        <script>
          var D=[#{rows_js}];
          function build(){
            var tb=document.getElementById('tb');tb.innerHTML='';
            D.forEach(function(r,i){
              var sc=r.score;
              var col=sc>=0.90?'#22c55e':sc>=0.80?'#84cc16':sc>=0.60?'#f59e0b':'#ef4444';
              var si=r.needs_review?"<span class='warn'>⚠️ Revisar</span>":"<span class='ok'>✅ Auto</span>";
              var ab=r.already_set?"<span class='ab'>configurado</span>":"";
              var ts='<select class="ts" onchange="D['+i+'].tipo_infer=this.value">';
              ['viga','pilar','laje'].forEach(function(t){ts+='<option'+(r.tipo_infer===t?' selected':'')+'>'+t+'</option>';});
              ts+='</select>';
              var ck=!r.needs_review?'checked':'';
              tb.innerHTML+='<tr>'+
                '<td><input type="checkbox" class="chk rc" data-i="'+i+'" '+ck+'></td>'+
                '<td>'+r.name_su+ab+'</td>'+
                '<td>'+ts+'</td>'+
                '<td><input class="di" type="number" step="0.5" style="width:50px" value="'+r.b_cm+'" onchange="D['+i+'].b_cm=+this.value"></td>'+
                '<td><input class="di" type="number" step="0.5" style="width:50px" value="'+r.h_cm+'" onchange="D['+i+'].h_cm=+this.value"></td>'+
                '<td><input class="di" type="number" step="0.01" style="width:58px" value="'+r.L_m+'" onchange="D['+i+'].L_m=+this.value"></td>'+
                '<td><span class="sb" style="background:'+col+'">'+Math.round(sc*100)+'%</span></td>'+
                '<td>'+si+'</td></tr>';
            });
          }
          function toggleAll(c){document.querySelectorAll('.rc').forEach(function(x){x.checked=c.checked;});}
          function confirmSel(){
            var sel=[];
            document.querySelectorAll('.rc').forEach(function(c){
              if(c.checked)sel.push(D[+c.getAttribute('data-i')]);
            });
            if(!sel.length){document.getElementById('st').textContent='⚠️ Nada selecionado.';return;}
            document.getElementById('st').textContent='Gravando…';
            sketchup.confirm_all(JSON.stringify(sel));
          }
          function showStatus(m){document.getElementById('st').textContent=m;}
          build();
        </script>
        </body></html>
      HTML
    end
  end

  # ============================================================================
  # ChecklistDialog (v4.0 — inclui alerta de score)
  # ============================================================================
  module ChecklistDialog
    def self.show
      issues = StructuralCalculatorExt.check_model
      insts  = StructuralCalculatorExt.all_configured_instances
      dlg = UI::HtmlDialog.new(
        dialog_name: "calc_checklist_v4", preferences_key: "calc_checklist_v4",
        width: 520, height: 500, resizable: true
      )
      dlg.set_html(build_html(insts.size, issues))
      dlg.add_action_callback("close") { |_,_| dlg.close }
      dlg.show
    end

    def self.build_html(total, issues)
      n_ok   = [0, total - issues.count { |i| i[:level] == "error" }].max
      n_warn = issues.count { |i| i[:level] == "warning" }
      n_err  = issues.count { |i| i[:level] == "error" }
      sc     = n_err > 0 ? "#ef4444" : (n_warn > 0 ? "#f59e0b" : "#22c55e")
      sl     = n_err > 0 ? "Problemas encontrados" : (n_warn > 0 ? "Avisos" : "Modelo OK")
      rows   = issues.empty? ?
        "<div class='item ok'>✅ Tudo certo. Pronto para exportar!</div>" :
        issues.map { |i|
          icon = i[:level]=="error" ? "❌" : "⚠️"
          cls  = i[:level]=="error" ? "item err" : "item warn"
          "<div class='#{cls}'>#{icon} #{i[:msg]}</div>"
        }.join
      <<~HTML
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <style>
          *{box-sizing:border-box;margin:0;padding:0}
          body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:13px;
            background:#0f1117;color:#e0e6f0;padding:20px}
          .hdr{border-bottom:1px solid #1e2a3a;padding-bottom:14px;margin-bottom:16px}
          .hdr h1{color:#60a5fa;font-size:15px;font-weight:700}
          .hdr p{color:#6b7fa0;font-size:11px;margin-top:3px}
          .met{display:flex;gap:8px;margin-bottom:16px}
          .chip{flex:1;background:#141c2b;border:1px solid #1e2a3a;border-radius:6px;padding:10px;text-align:center}
          .chip .n{font-size:22px;font-weight:700;line-height:1}
          .chip .l{font-size:10px;color:#6b7fa0;margin-top:3px}
          .sb{padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px;
            font-weight:700;color:#{sc};background:#{sc}22;border:1px solid #{sc}55}
          .item{padding:8px 12px;border-radius:5px;font-size:12px;margin-bottom:6px;line-height:1.5}
          .ok  {background:#052e16;border:1px solid #16a34a;color:#4ade80}
          .warn{background:#2d2006;border:1px solid #d97706;color:#fbbf24}
          .err {background:#2d0a0a;border:1px solid #dc2626;color:#f87171}
          .br{display:flex;gap:8px;margin-top:18px}
          button{flex:1;padding:9px;border:none;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer}
          .bx{background:#1a2235;color:#8a9bbf;border:1px solid #1e2a3a}
        </style></head><body>
        <div class="hdr"><h1>🔍 Verificação do Modelo</h1><p>#{total} elemento(s) configurado(s)</p></div>
        <div class="met">
          <div class="chip"><div class="n" style="color:#34d399">#{total}</div><div class="l">Total</div></div>
          <div class="chip"><div class="n" style="color:#22c55e">#{n_ok}</div><div class="l">OK</div></div>
          <div class="chip"><div class="n" style="color:#f59e0b">#{n_warn}</div><div class="l">Avisos</div></div>
          <div class="chip"><div class="n" style="color:#ef4444">#{n_err}</div><div class="l">Erros</div></div>
        </div>
        <div class="sb">#{sl}</div>
        <div>#{rows}</div>
        <div class="br"><button class="bx" onclick="sketchup.close()">✕ Fechar</button></div>
        </body></html>
      HTML
    end
  end

  # ============================================================================
  # BatchCopyDialog (v4.0 — inclui carga_cor_id na cópia)
  # ============================================================================
  module BatchCopyDialog
    def self.show
      model = Sketchup.active_model
      insts = model.selection.select { |e|
        e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
      }
      if insts.size < 2
        UI.messagebox("Selecione 2+ componentes. O 1º é a fonte.", MB_OK, "Copiar em lote")
        return
      end
      src = insts.first; targets = insts[1..]
      src_dict = src.attribute_dictionary(DICT_NAME)
      unless src_dict
        UI.messagebox("1º componente sem atributos. Configure-o primeiro.", MB_OK, "Copiar em lote")
        return
      end
      load_keys = %w[
        paredes_json altura_parede_m revestimento_tipo_id variavel_tipo_id
        revestimento_kN_m2 variavel_kN_m2 revestimento_nome variavel_nome
        especiais_kN_m carga_cor_id vinculo_base pavimento_hint
      ]
      dlg = UI::HtmlDialog.new(
        dialog_name: "calc_batch_v4", preferences_key: "calc_batch_v4",
        width: 500, height: 420, resizable: false
      )
      src_nome  = (src_dict["nome"] || src.name || "Fonte").to_s
      tgt_nomes = targets.map { |t|
        d = t.attribute_dictionary(DICT_NAME)
        d ? (d["nome"] || t.name || "?").to_s : "(sem config)"
      }
      dlg.set_html(build_html(src_nome, tgt_nomes))
      dlg.add_action_callback("close") { |_,_| dlg.close }
      dlg.add_action_callback("execute_copy") do |_,_|
        begin
          model.start_operation("Copiar cargas em lote", true)
          n = 0
          targets.each do |tgt|
            td = tgt.attribute_dictionary(DICT_NAME, true)
            load_keys.each { |k| v=src_dict[k]; td[k]=v unless v.nil? }
            tgt.material = src.material if src.material
            n += 1
          end
          model.commit_operation
          dlg.execute_script("showDone(#{n})")
        rescue => e
          model.abort_operation rescue nil
          dlg.execute_script("showErr('#{e.message.gsub("'","\\'")}')") 
        end
      end
      dlg.show
    end

    def self.build_html(src_nome, tgt_nomes)
      items = tgt_nomes.map { |n| "<div class='ti'>📦 #{n}</div>" }.join
      <<~HTML
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <style>
          *{box-sizing:border-box;margin:0;padding:0}
          body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:13px;
            background:#0f1117;color:#e0e6f0;padding:20px}
          .hdr{border-bottom:1px solid #1e2a3a;padding-bottom:12px;margin-bottom:16px}
          .hdr h1{color:#60a5fa;font-size:15px;font-weight:700}
          .sl{font-size:10px;font-weight:700;color:#6b7fa0;text-transform:uppercase;
            letter-spacing:.8px;margin:12px 0 6px}
          .sb{background:#1d3461;border:1px solid #3b82f6;border-radius:6px;
            padding:10px 12px;color:#60a5fa;font-size:13px;font-weight:600}
          .ar{text-align:center;color:#6b7fa0;font-size:18px;margin:8px 0}
          .tl{background:#0a0e17;border:1px solid #1e2a3a;border-radius:6px;
            padding:8px;max-height:150px;overflow-y:auto}
          .ti{padding:4px 8px;font-size:12px;color:#9ab0cc;border-bottom:1px solid #1e2a3a}
          .ti:last-child{border-bottom:none}
          .nt{font-size:11px;color:#6b7fa0;margin-top:10px;line-height:1.6}
          .br{display:flex;gap:8px;margin-top:16px}
          button{flex:1;padding:9px;border:none;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer}
          .brun{background:#3b82f6;color:#fff}.brun:hover{background:#2563eb}
          .bx{background:#1a2235;color:#8a9bbf;border:1px solid #1e2a3a}
          #d,#e{display:none;margin-top:10px;padding:9px;border-radius:5px;font-size:12px}
          #d{background:#052e16;border:1px solid #16a34a;color:#4ade80}
          #e{background:#2d0a0a;border:1px solid #dc2626;color:#f87171}
        </style></head><body>
        <div class="hdr"><h1>📋 Copiar cargas em lote</h1></div>
        <div class="sl">Fonte</div><div class="sb">⚙️ #{src_nome}</div>
        <div class="ar">↓</div>
        <div class="sl">Destinos (#{tgt_nomes.size})</div>
        <div class="tl">#{items}</div>
        <div class="nt">✔ Copiados: paredes, revestimento, variável, cor, vínculo.<br>
        ✘ Não copiados: nome, geometria, φ.</div>
        <div id="d"></div><div id="e"></div>
        <div class="br">
          <button class="brun" onclick="sketchup.execute_copy('')">✅ Executar</button>
          <button class="bx" onclick="sketchup.close()">✕ Cancelar</button>
        </div>
        <script>
          function showDone(n){var d=document.getElementById('d');d.style.display='block';d.textContent='✓ Copiado para '+n+' elemento(s).';}
          function showErr(m){var e=document.getElementById('e');e.style.display='block';e.textContent='❌ '+m;}
        </script></body></html>
      HTML
    end
  end

  # ============================================================================
  # MainDialog — Exportação (v4.0, schema 3.1)
  # ============================================================================
  module MainDialog

    def self.show
      dlg = UI::HtmlDialog.new(
        dialog_name: "calc_export_v4", preferences_key: "calc_export_v4",
        width: 660, height: 630, resizable: true
      )
      dlg.set_html(build_html)
      register_callbacks(dlg)
      dlg.show
    end

    def self.register_callbacks(dlg)
      dlg.add_action_callback("close") { |_,_| dlg.close }

      dlg.add_action_callback("count_elements") do |_,_|
        dlg.execute_script("updateCounts(#{count_by_type.to_json})")
      end

      dlg.add_action_callback("run_checklist") do |_,_|
        issues = StructuralCalculatorExt.check_model
        dlg.execute_script("receiveChecklist(#{issues.to_json})")
      end

      dlg.add_action_callback("export_data") do |_, params_json|
        begin
          params   = JSON.parse(params_json)
          exporter = StructuralExporter::Exporter.new(Sketchup.active_model)
          exporter.set_global_parameters(
            params["concreto"], params["aco"],
            params["combinacao"], params["agressividade"]
          )
          desktop   = File.expand_path("~/Desktop")
          timestamp = Time.now.strftime("%Y%m%d_%H%M%S")
          filepath  = File.join(desktop, "estrutural_#{timestamp}.json")
          n = exporter.export_to_json(filepath)
          if n > 0
            msg = "✅ #{n} elemento(s) exportado(s)!\\n📁 #{File.basename(filepath)}\\n📂 #{desktop}"
            dlg.execute_script("showResult('success','#{esc(msg)}')")
          else
            dlg.execute_script("showResult('warn','⚠️ Nenhum elemento encontrado.')")
          end
        rescue => e
          dlg.execute_script("showResult('error','Erro: #{esc(e.message)}')")
        end
      end
    end

    def self.count_by_type
      c = { "total"=>0, "viga"=>0, "pilar"=>0, "laje"=>0 }
      Sketchup.active_model.definitions.each do |defn|
        next if defn.image?
        defn.instances.each do |inst|
          dict = inst.attribute_dictionary(DICT_NAME)
          next unless dict
          t = dict["tipo"].to_s.downcase
          next unless c.key?(t)
          c[t]+=1; c["total"]+=1
        end
      end
      c
    end

    def self.esc(s)
      s.to_s.gsub("\\","\\\\\\\\").gsub("'","\\'").gsub("\n","\\n").gsub("\r","")
    end

    def self.build_html
      <<~HTML
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
        <style>
          *{box-sizing:border-box;margin:0;padding:0}
          body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:13px;
            background:#0f1117;color:#e0e6f0;padding:22px}
          .hdr{padding-bottom:14px;margin-bottom:18px;border-bottom:1px solid #1e2a3a}
          .hdr h1{color:#60a5fa;font-size:16px;font-weight:700}
          .hdr p{color:#6b7fa0;font-size:11px;margin-top:3px}
          .badge{display:inline-block;background:#1d3461;color:#60a5fa;border:1px solid #2a4a7f;
            border-radius:4px;padding:2px 8px;font-size:10px;margin-right:5px}
          .sl{font-size:10px;font-weight:700;color:#6b7fa0;text-transform:uppercase;
            letter-spacing:.8px;margin:16px 0 8px}
          .counts{display:flex;gap:8px;margin-bottom:4px}
          .chip{flex:1;background:#141c2b;border:1px solid #1e2a3a;border-radius:6px;padding:10px 8px;text-align:center}
          .chip .num{font-size:24px;font-weight:700;color:#60a5fa;line-height:1}
          .chip .lbl{font-size:10px;color:#6b7fa0;margin-top:4px}
          #clbox{background:#0a0e17;border:1px solid #1e2a3a;border-radius:6px;
            padding:10px;min-height:60px;margin-bottom:4px}
          .ci{padding:5px 8px;border-radius:4px;font-size:12px;margin-bottom:4px;line-height:1.5}
          .cok {background:#052e16;color:#4ade80}
          .cwn {background:#2d2006;color:#fbbf24}
          .cer {background:#2d0a0a;color:#f87171}
          .cidl{color:#6b7fa0;font-size:12px;text-align:center;padding:10px}
          .fg{display:grid;grid-template-columns:1fr 1fr;gap:10px}
          .fgg label{display:block;font-size:11px;color:#8a9bbf;margin-bottom:4px}
          select{width:100%;padding:7px 10px;background:#141c2b;border:1px solid #1e2a3a;
            border-radius:5px;color:#e0e6f0;font-size:12px;cursor:pointer}
          select:focus{outline:none;border-color:#3b82f6}
          .br{display:flex;gap:10px;margin-top:20px}
          button{flex:1;padding:10px;border:none;border-radius:5px;font-size:12px;font-weight:700;cursor:pointer}
          .bck{background:#1d3461;color:#60a5fa;border:1px solid #2a4a7f}
          .bex{background:#3b82f6;color:#fff}.bex:hover{background:#2563eb}
          .bcl{background:#1a2235;color:#8a9bbf;border:1px solid #1e2a3a}
          #res{display:none;margin-top:14px;padding:10px 14px;border-radius:6px;
            font-size:12px;line-height:1.7;white-space:pre-line}
          #res.success{background:#052e16;border:1px solid #16a34a;color:#4ade80}
          #res.warn   {background:#2d2006;border:1px solid #d97706;color:#fbbf24}
          #res.error  {background:#2d0a0a;border:1px solid #dc2626;color:#f87171}
          .rfb{background:none;border:none;color:#6b7fa0;font-size:11px;cursor:pointer;margin-left:6px}
          .rfb:hover{color:#60a5fa}
        </style></head>
        <body>
        <div class="hdr">
          <h1>🏗️ Exportar Modelo Estrutural</h1>
          <p>Gera JSON v3.1 com geometria extraída, cargas por cor e apoios gráficos</p>
          <div style="margin-top:7px">
            <span class="badge">NBR 6118:2023</span>
            <span class="badge">v4.0</span>
            <span class="badge">Schema v3.1</span>
          </div>
        </div>
        <div class="sl">Elementos no modelo <button class="rfb" onclick="refreshCounts()">↻</button></div>
        <div class="counts">
          <div class="chip"><div class="num" id="ct">—</div><div class="lbl">Total</div></div>
          <div class="chip"><div class="num" id="cv">—</div><div class="lbl">Vigas</div></div>
          <div class="chip"><div class="num" id="cp">—</div><div class="lbl">Pilares</div></div>
          <div class="chip"><div class="num" id="cl">—</div><div class="lbl">Lajes</div></div>
        </div>
        <div class="sl">Verificação <button class="rfb" onclick="runChk()">↻</button></div>
        <div id="clbox"><div class="cidl">Clique ↻ ou em Verificar.</div></div>
        <div class="sl">Parâmetros globais</div>
        <div class="fg">
          <div class="fgg"><label>Classe do Concreto</label>
            <select id="sc"><option>C20</option><option>C25</option><option selected>C30</option>
            <option>C35</option><option>C40</option><option>C45</option><option>C50</option>
            <option>C55</option><option>C60</option><option>C70</option><option>C80</option><option>C90</option></select></div>
          <div class="fgg"><label>Tipo de Aço</label>
            <select id="sa"><option>CA-25</option><option selected>CA-50</option><option>CA-60</option></select></div>
          <div class="fgg"><label>Combinação de Ações</label>
            <select id="scb"><option value="normal" selected>Normal</option>
            <option value="especial">Especial</option><option value="excepcional">Excepcional</option></select></div>
          <div class="fgg"><label>Classe de Agressividade</label>
            <select id="sag"><option value="I">I — Fraca</option><option value="II" selected>II — Moderada</option>
            <option value="III">III — Forte</option><option value="IV">IV — Muito Forte</option></select></div>
        </div>
        <div class="br">
          <button class="bck" onclick="runChk()">🔍 Verificar</button>
          <button class="bex" onclick="exportData()">📤 Exportar JSON</button>
          <button class="bcl" onclick="sketchup.close()">✕ Fechar</button>
        </div>
        <div id="res"></div>
        <script>
          window.onload=function(){refreshCounts();runChk();};
          function refreshCounts(){
            ['ct','cv','cp','cl'].forEach(function(k){document.getElementById(k).textContent='…';});
            sketchup.count_elements('');
          }
          function updateCounts(c){
            document.getElementById('ct').textContent=c['total'];
            document.getElementById('cv').textContent=c['viga'];
            document.getElementById('cp').textContent=c['pilar'];
            document.getElementById('cl').textContent=c['laje'];
          }
          function runChk(){
            document.getElementById('clbox').innerHTML="<div class='cidl'>Verificando…</div>";
            sketchup.run_checklist('');
          }
          function receiveChecklist(issues){
            var b=document.getElementById('clbox');
            if(!issues.length){b.innerHTML="<div class='ci cok'>✅ Modelo pronto.</div>";return;}
            var h='';
            issues.forEach(function(i){
              var c=i.level==='error'?'cer':'cwn';
              h+="<div class='ci "+c+"'>"+(i.level==='error'?'❌':'⚠️')+" "+i.msg+"</div>";
            });
            b.innerHTML=h;
          }
          function exportData(){
            sketchup.export_data(JSON.stringify({
              concreto:document.getElementById('sc').value,
              aco:document.getElementById('sa').value,
              combinacao:document.getElementById('scb').value,
              agressividade:document.getElementById('sag').value
            }));
          }
          function showResult(t,m){
            var el=document.getElementById('res');
            el.className=t;el.textContent=m.replace(/\\n/g,'\n');el.style.display='block';
            if(t==='success')setTimeout(refreshCounts,400);
          }
        </script>
        </body></html>
      HTML
    end
  end

end

StructuralCalculatorExt.init
