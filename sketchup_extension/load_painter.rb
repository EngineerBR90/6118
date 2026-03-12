# =============================================================================
# load_painter.rb  — v4.0
# Atribuição visual de cargas por paleta de cores.
#
# Fluxo:
#   1. Usuário seleciona N componentes no modelo
#   2. Aciona Extensions → 🎨 Atribuir cargas à seleção
#   3. Dialog mostra a paleta (8 usos + carga pontual)
#   4. Clique numa cor → todos os N elementos recebem aquela carga
#   5. Elementos mudam de cor imediatamente (feedback visual)
#   6. Atributos gravados: carga_cor_id, revestimento_tipo_id, variavel_tipo_id
# =============================================================================

require 'json'

module LoadPainter

  DICT_NAME = "structural_data"

  # Paleta: id → {label, cor RGB, revestimento_id, variavel_id}
  PALETTE = {
    "dormitorio"  => {
      label:    "Dormitório",
      r: 59,  g: 130, b: 246,   # azul
      rev_id:  "ceramica_contrapiso_5cm",
      var_id:  "residencial_dormitorio",
      q_knm2:  1.5
    },
    "sala_circ"   => {
      label:    "Sala / Circulação",
      r: 34,  g: 197, b: 94,    # verde
      rev_id:  "ceramica_contrapiso_5cm",
      var_id:  "residencial_sala_cozinha",
      q_knm2:  2.0
    },
    "cozinha"     => {
      label:    "Cozinha / Lavanderia",
      r: 234, g: 179, b: 8,     # amarelo
      rev_id:  "ceramica_contrapiso_5cm",
      var_id:  "residencial_sala_cozinha",
      q_knm2:  2.0
    },
    "escritorio"  => {
      label:    "Escritório",
      r: 249, g: 115, b: 22,    # laranja
      rev_id:  "porcelanato_contrapiso_5cm",
      var_id:  "comercial_escritorio",
      q_knm2:  2.0
    },
    "cob_acesso"  => {
      label:    "Cobertura acessível",
      r: 239, g: 68,  b: 68,    # vermelho
      rev_id:  "impermeabilizacao",
      var_id:  "cobertura_acessivel",
      q_knm2:  2.0
    },
    "cob_fechado" => {
      label:    "Cobertura fechada",
      r: 156, g: 163, b: 175,   # cinza
      rev_id:  "sem_revestimento",
      var_id:  "cobertura_nao_acessivel",
      q_knm2:  0.5
    },
    "garagem"     => {
      label:    "Garagem",
      r: 120, g: 53,  b: 15,    # marrom
      rev_id:  "impermeabilizacao",
      var_id:  "garagem",
      q_knm2:  3.0
    },
    "maquinas"    => {
      label:    "Área técnica / Máquinas",
      r: 30,  g: 41,  b: 59,    # preto azulado
      rev_id:  "sem_revestimento",
      var_id:  "area_tecnica",
      q_knm2:  5.0
    }
  }.freeze

  # ── Abre o dialog de paleta ────────────────────────────────────────────────
  def self.show(model)
    sel = model.selection.select { |e|
      e.is_a?(Sketchup::ComponentInstance) || e.is_a?(Sketchup::Group)
    }

    if sel.empty?
      UI.messagebox(
        "Selecione um ou mais elementos estruturais e tente novamente.",
        MB_OK, "Atribuir Cargas"
      )
      return
    end

    dlg = UI::HtmlDialog.new(
      dialog_name:     "load_painter_v4",
      preferences_key: "load_painter_v4",
      width:  420,
      height: 500,
      resizable: false
    )
    dlg.set_html(build_html(sel.length))
    register_callbacks(dlg, model, sel)
    dlg.show
  end

  # ── Callbacks ─────────────────────────────────────────────────────────────
  def self.register_callbacks(dlg, model, instances)
    dlg.add_action_callback("close") { |_ctx, _| dlg.close }

    dlg.add_action_callback("apply_color") do |_ctx, cor_id|
      begin
        n = apply_to_instances(model, instances, cor_id)
        dlg.execute_script("showStatus('✅ #{n} elemento(s) atualizados com \"#{PALETTE[cor_id]&.dig(:label) || cor_id}\"')")
      rescue => e
        msg = e.message.gsub("'", "\\'")
        dlg.execute_script("showStatus('❌ Erro: #{msg}')")
      end
    end

    dlg.add_action_callback("add_point_load") do |_ctx, data_json|
      begin
        data = JSON.parse(data_json)
        n    = apply_point_load(model, instances, data)
        dlg.execute_script("showStatus('✅ Carga pontual de #{data['Fy']} kN adicionada a #{n} elemento(s)')")
      rescue => e
        msg = e.message.gsub("'", "\\'")
        dlg.execute_script("showStatus('❌ Erro: #{msg}')")
      end
    end
  end

  # ── Aplica cor e cargas a uma lista de instâncias ─────────────────────────
  def self.apply_to_instances(model, instances, cor_id)
    cfg = PALETTE[cor_id]
    return 0 unless cfg

    mat = _get_or_create_material(
      model, "carga_#{cor_id}", cfg[:r], cfg[:g], cfg[:b]
    )

    n = 0
    instances.each do |inst|
      next unless inst.is_a?(Sketchup::ComponentInstance) ||
                  inst.is_a?(Sketchup::Group)

      model.start_operation("Atribuir carga: #{cfg[:label]}", true)

      # Material visual
      inst.material = mat

      # Atributos de carga
      dict = inst.attribute_dictionary(DICT_NAME, true)
      dict["carga_cor_id"]        = cor_id
      dict["revestimento_tipo_id"] = cfg[:rev_id]
      dict["variavel_tipo_id"]    = cfg[:var_id]
      dict["variavel_kN_m2"]      = cfg[:q_knm2]
      # Nome amigável para o dialog ⚙️
      dict["variavel_nome"]       = cfg[:label]
      dict["revestimento_nome"]   = cfg[:rev_id].gsub("_", " ").capitalize

      model.commit_operation
      n += 1
    end
    n
  end

  # ── Adiciona carga pontual a instâncias ───────────────────────────────────
  #
  # data = { "Fy" => kN_value, "x_rel" => 0.5, "descricao" => "..." }
  # As cargas pontuais são acumuladas num array JSON no atributo "point_loads_json"
  #
  def self.apply_point_load(model, instances, data)
    fy    = data["Fy"].to_f
    x_rel = [[data["x_rel"].to_f, 0.0].max, 1.0].min
    desc  = data["descricao"].to_s.strip

    return 0 if fy == 0.0

    n = 0
    instances.each do |inst|
      next unless inst.is_a?(Sketchup::ComponentInstance) ||
                  inst.is_a?(Sketchup::Group)

      model.start_operation("Carga pontual #{fy} kN", true)
      dict = inst.attribute_dictionary(DICT_NAME, true)

      # Lê array existente
      existing_raw = dict["point_loads_json"].to_s
      existing     = existing_raw.empty? ? [] : (JSON.parse(existing_raw) rescue [])

      # Adiciona nova carga
      existing << {
        "x_rel"     => x_rel.round(4),
        "Fy"        => fy,
        "descricao" => desc
      }

      dict["point_loads_json"] = existing.to_json
      model.commit_operation
      n += 1
    end
    n
  end

  # ── Restaura cores originais de todos os elementos ─────────────────────────
  def self.restore_colors(model)
    model.definitions.each do |defn|
      next if defn.image?
      defn.instances.each do |inst|
        dict = inst.attribute_dictionary(DICT_NAME)
        next unless dict
        inst.material = nil
      end
    end
  end

  # ── Material ──────────────────────────────────────────────────────────────
  def self._get_or_create_material(model, name, r, g, b)
    mat = model.materials[name]
    unless mat
      mat       = model.materials.add(name)
      mat.color = Sketchup::Color.new(r, g, b)
      mat.alpha = 0.85
    end
    mat
  rescue
    nil
  end

  # ── HTML do dialog ─────────────────────────────────────────────────────────
  def self.build_html(n_selected)
    swatches = PALETTE.map do |cor_id, cfg|
      r, g, b = cfg[:r], cfg[:g], cfg[:b]
      <<~HTML
        <button class="swatch-btn" onclick="applyColor('#{cor_id}')"
          style="--swatch:rgb(#{r},#{g},#{b})">
          <span class="dot"></span>
          <span class="lbl">#{cfg[:label]}</span>
          <span class="q">Q = #{cfg[:q_knm2]} kN/m²</span>
        </button>
      HTML
    end.join("\n")

    <<~HTML
      <!DOCTYPE html><html lang="pt-BR"><head>
      <meta charset="UTF-8">
      <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:13px;
          background:#0f1117;color:#e0e6f0;display:flex;flex-direction:column;height:100vh}
        .hdr{padding:14px 18px;border-bottom:1px solid #1e2a3a;background:#141c2b}
        .hdr h1{font-size:14px;color:#60a5fa;font-weight:700}
        .hdr p{font-size:11px;color:#6b7fa0;margin-top:2px}
        .body{flex:1;overflow-y:auto;padding:14px 18px}
        .section-label{font-size:10px;font-weight:700;color:#6b7fa0;
          text-transform:uppercase;letter-spacing:.8px;margin:12px 0 6px}
        .swatch-btn{display:flex;align-items:center;gap:10px;width:100%;
          padding:9px 12px;margin-bottom:6px;background:#141c2b;
          border:1px solid #1e2a3a;border-radius:6px;color:#e0e6f0;
          cursor:pointer;text-align:left}
        .swatch-btn:hover{border-color:var(--swatch);background:#1a2235}
        .dot{width:14px;height:14px;border-radius:3px;background:var(--swatch);flex-shrink:0}
        .lbl{flex:1;font-weight:600;font-size:12px}
        .q{font-size:10px;color:#6b7fa0;white-space:nowrap}
        .sep{border:none;border-top:1px solid #1e2a3a;margin:12px 0}
        .pt-row{display:grid;grid-template-columns:1fr 80px 80px;gap:6px;margin-bottom:6px}
        .pt-row input{padding:6px 8px;background:#141c2b;border:1px solid #1e2a3a;
          border-radius:4px;color:#e0e6f0;font-size:12px;width:100%}
        .btn-pt{padding:8px 12px;background:#7c3aed;border:none;border-radius:4px;
          color:#fff;cursor:pointer;font-size:12px;font-weight:600;width:100%;margin-top:2px}
        .btn-pt:hover{background:#6d28d9}
        .status{padding:10px 18px;font-size:12px;color:#34d399;
          border-top:1px solid #1e2a3a;background:#0f1117;min-height:38px}
        .footer{display:flex;justify-content:space-between;padding:10px 18px;
          border-top:1px solid #1e2a3a;background:#0f1117}
        .btn-restore{padding:7px 12px;background:#374151;border:none;
          border-radius:4px;color:#e0e6f0;cursor:pointer;font-size:12px}
        .btn-close{padding:7px 16px;background:#1d3461;border:1px solid #3b82f6;
          border-radius:4px;color:#60a5fa;cursor:pointer;font-size:12px;font-weight:600}
      </style></head><body>
      <div class="hdr">
        <h1>🎨 Atribuir Cargas</h1>
        <p>#{n_selected} elemento(s) selecionado(s) — clique em uma categoria para aplicar</p>
      </div>

      <div class="body">
        <div class="section-label">Tipo de uso / ocupação (NBR 6120)</div>
        #{swatches}

        <hr class="sep">

        <div class="section-label">📍 Carga pontual (kN)</div>
        <div class="pt-row">
          <input id="pt-desc"  placeholder="Descrição (ex.: reservatório)" />
          <input id="pt-fy"    type="number" placeholder="kN" step="0.1" />
          <input id="pt-xrel"  type="number" placeholder="x/L (0-1)" step="0.05" value="0.5" />
        </div>
        <button class="btn-pt" onclick="addPointLoad()">➕ Adicionar carga pontual</button>
      </div>

      <div class="status" id="status">—</div>

      <div class="footer">
        <button class="btn-restore" onclick="sketchup.apply_color('__restore__')">
          Restaurar cores originais
        </button>
        <button class="btn-close" onclick="sketchup.close()">Fechar</button>
      </div>

      <script>
        function applyColor(id) {
          if (id === '__restore__') {
            sketchup.apply_color('__restore__');
            return;
          }
          sketchup.apply_color(id);
        }
        function addPointLoad() {
          const desc  = document.getElementById('pt-desc').value.trim();
          const fy    = parseFloat(document.getElementById('pt-fy').value);
          const x_rel = parseFloat(document.getElementById('pt-xrel').value);
          if (isNaN(fy) || fy === 0) {
            showStatus('⚠️ Informe um valor de força em kN.');
            return;
          }
          sketchup.add_point_load(JSON.stringify({ Fy: fy, x_rel: x_rel || 0.5, descricao: desc }));
        }
        function showStatus(msg) {
          document.getElementById('status').textContent = msg;
        }
      </script>
      </body></html>
    HTML
  end

end
