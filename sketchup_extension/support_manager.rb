# =============================================================================
# support_manager.rb  — v4.0
# Apoios gráficos no modelo SketchUp.
#
# Gera objetos 3D que representam tipos de vínculo estrutural:
#   🔺 Pirâmide  → Rótula (translação presa, rotação livre)
#   ⬛ Cubo      → Engastamento (todos os 6 graus fixos)
#   🟢 Cilindro  → Rolete (deslizamento em 1 eixo)
#
# Os objetos são ComponentDefinitions marcados com o dicionário "support_def".
# O exportador detecta apoios por proximidade ao nó de base do pilar (≤ 10cm).
# =============================================================================

module SupportManager

  INCH_TO_M  = 0.0254
  SUPPORT_DICT = "support_def"

  SUPPORT_TYPES = {
    "engastado"  => { label: "Engastamento",   color: [220, 38,  38],  size_m: 0.30 },
    "rotulado"   => { label: "Rótula",          color: [37,  99,  235], size_m: 0.30 },
    "rolete_x"   => { label: "Rolete (eixo X)", color: [22,  163, 74],  size_m: 0.30 },
    "rolete_y"   => { label: "Rolete (eixo Y)", color: [22,  163, 74],  size_m: 0.30 },
  }.freeze

  # ── Insere um apoio no ponto clicado ──────────────────────────────────────
  def self.insert_support(model, vinculo_type, position_pt = nil)
    cfg  = SUPPORT_TYPES[vinculo_type]
    return unless cfg

    position_pt ||= Geom::Point3d.new(0, 0, 0)
    defn_name    = "apoio_#{vinculo_type}"

    # Reutiliza definição existente ou cria nova
    defn = model.definitions[defn_name]
    defn = _create_definition(model, vinculo_type, cfg, defn_name) unless defn

    # Insere instância na posição
    t    = Geom::Transformation.translation(position_pt)
    inst = model.active_entities.add_instance(defn, t)
    inst.name = "#{cfg[:label]}"
    inst
  end

  # ── Encontra apoio próximo a um ponto ─────────────────────────────────────
  #
  # Usado pelo exportador para resolver vinculo_base a partir do modelo.
  # Retorna { "vinculo_type" => "engastado", "source" => "grafico" } ou nil.
  #
  def self.find_support_near(point_m, model, tol_m = 0.10)
    # Converte ponto de metros para polegadas SketchUp
    px = (point_m["x"] || 0.0) / INCH_TO_M
    py = (point_m["y"] || 0.0) / INCH_TO_M
    pz = (point_m["z"] || 0.0) / INCH_TO_M
    ref = Geom::Point3d.new(px, py, pz)

    best_dist = tol_m / INCH_TO_M
    best_type = nil

    model.definitions.each do |defn|
      next if defn.image?
      next unless defn.get_attribute(SUPPORT_DICT, "is_support")
      vtype = defn.get_attribute(SUPPORT_DICT, "vinculo_type")
      next unless vtype

      defn.instances.each do |inst|
        dist = inst.transformation.origin.distance(ref)
        if dist < best_dist
          best_dist = dist
          best_type = vtype
        end
      end
    end

    best_type ? { "vinculo_type" => best_type, "source" => "grafico" } : nil
  end

  # ── Cria a definição de um tipo de apoio ──────────────────────────────────
  def self._create_definition(model, vtype, cfg, defn_name)
    defn = model.definitions.add(defn_name)
    ents = defn.entities
    s    = cfg[:size_m] / INCH_TO_M   # tamanho em polegadas

    case vtype
    when "engastado"
      _build_engaste(ents, s, model)
    when "rotulado"
      _build_rotula(ents, s, model)
    when "rolete_x"
      _build_rolete(ents, s, model, :x)
    when "rolete_y"
      _build_rolete(ents, s, model, :y)
    end

    # Marca a definição como objeto de apoio
    defn.set_attribute(SUPPORT_DICT, "is_support",    true)
    defn.set_attribute(SUPPORT_DICT, "vinculo_type",  vtype)
    defn.set_attribute(SUPPORT_DICT, "label",         cfg[:label])

    defn
  end

  # ── Engaste: cubo sólido com diagonais nas faces (rigidez total) ─────────
  # Símbolo: bloco maciço = fixação em todas as direções
  def self._build_engaste(ents, s, model)
    r, g, b = SUPPORT_TYPES["engastado"][:color]
    mat      = _get_or_create_material(model, "apoio_engaste", r, g, b, 0.75)

    # Cubo
    pts_bot = [
      Geom::Point3d.new(0,   0,   0),
      Geom::Point3d.new(s,   0,   0),
      Geom::Point3d.new(s,   s,   0),
      Geom::Point3d.new(0,   s,   0)
    ]
    face_bot = ents.add_face(pts_bot)
    face_bot.pushpull(s)

    # Centraliza em X e Y, assenta em Z=0
    t = Geom::Transformation.translation(Geom::Vector3d.new(-s/2, -s/2, 0))
    ents.transform_entities(t, ents.to_a)

    # Aplica material ao sólido
    ents.grep(Sketchup::Face).each { |f| f.material = mat; f.back_material = mat }

    # Linhas de reforço diagonais na face superior (símbolo visual de engaste)
    top_z = s
    ents.add_line(
      Geom::Point3d.new(-s/2, -s/2, top_z),
      Geom::Point3d.new( s/2,  s/2, top_z)
    )
    ents.add_line(
      Geom::Point3d.new( s/2, -s/2, top_z),
      Geom::Point3d.new(-s/2,  s/2, top_z)
    )
  rescue => e
    # Falha silenciosa: cubo simples sem diagonais
  end

  # ── Rótula: pirâmide com vértice para cima ────────────────────────────────
  # Símbolo: vértice = ponto de contato = rotação livre
  def self._build_rotula(ents, s, model)
    r, g, b = SUPPORT_TYPES["rotulado"][:color]
    mat      = _get_or_create_material(model, "apoio_rotula", r, g, b, 0.75)

    half  = s / 2.0
    h     = s * 0.85  # altura da pirâmide

    # Base quadrada (centrada em 0,0,0)
    base = [
      Geom::Point3d.new(-half, -half, 0),
      Geom::Point3d.new( half, -half, 0),
      Geom::Point3d.new( half,  half, 0),
      Geom::Point3d.new(-half,  half, 0)
    ]
    apex = Geom::Point3d.new(0, 0, h)

    # 4 faces triangulares
    4.times do |i|
      a = base[i]
      b_pt = base[(i + 1) % 4]
      face = ents.add_face([a, b_pt, apex])
      face.material      = mat if face.is_a?(Sketchup::Face)
      face.back_material = mat if face.is_a?(Sketchup::Face)
    end

    # Face de base
    face_base = ents.add_face(base)
    face_base.material      = mat
    face_base.back_material = mat
  rescue => e
    nil
  end

  # ── Rolete: cilindro deitado sobre plataforma ─────────────────────────────
  # Símbolo: cilindro deitado indica direção de deslizamento
  def self._build_rolete(ents, s, model, axis)
    r, g, b = SUPPORT_TYPES["rolete_x"][:color]
    mat      = _get_or_create_material(model, "apoio_rolete", r, g, b, 0.75)

    radius  = s * 0.20
    length  = s * 0.80
    n_sides = 16
    half_l  = length / 2.0

    # Plataforma base (placa fina)
    plat_h  = s * 0.08
    plat_w  = s
    pts_plat = [
      Geom::Point3d.new(-plat_w/2, -plat_w/2, 0),
      Geom::Point3d.new( plat_w/2, -plat_w/2, 0),
      Geom::Point3d.new( plat_w/2,  plat_w/2, 0),
      Geom::Point3d.new(-plat_w/2,  plat_w/2, 0)
    ]
    fp = ents.add_face(pts_plat)
    fp.pushpull(plat_h)
    fp.material = mat rescue nil

    # Cilindro deitado acima da plataforma
    cyl_z = plat_h + radius + s * 0.02

    if axis == :x
      # Cilindro com eixo em X
      ctr   = Geom::Point3d.new(0,  0,  cyl_z)
      normal = Geom::Vector3d.new(1, 0, 0)
    else
      # Cilindro com eixo em Y
      ctr   = Geom::Point3d.new(0,  0,  cyl_z)
      normal = Geom::Vector3d.new(0, 1, 0)
    end

    circle_edges = ents.add_circle(ctr, normal, radius, n_sides)
    cyl_face     = circle_edges[0].faces.find { |f| f.normal.parallel?(normal) }
    if cyl_face
      cyl_face.pushpull(length)
      t_off = Geom::Transformation.translation(normal.transform(
        Geom::Transformation.scaling(-half_l)
      ))
      # Centraliza o cilindro
      cyl_grp_ents = ents.grep(Sketchup::Face).select { |f|
        (f.normal.parallel?(normal)) rescue false
      }
    end

    ents.grep(Sketchup::Face).each { |f| f.material = mat rescue nil }
  rescue => e
    nil
  end

  # ── Material com transparência ─────────────────────────────────────────────
  def self._get_or_create_material(model, name, r, g, b, alpha = 0.8)
    mat = model.materials[name]
    unless mat
      mat         = model.materials.add(name)
      mat.color   = Sketchup::Color.new(r, g, b)
      mat.alpha   = alpha
    end
    mat
  rescue
    nil
  end

  # ── Dialog picker para escolher tipo de apoio ─────────────────────────────
  def self.show_picker_dialog(model)
    dlg = UI::HtmlDialog.new(
      dialog_name:     "apoio_picker",
      preferences_key: "apoio_picker",
      width:  360,
      height: 280,
      resizable: false
    )
    dlg.set_html(picker_html)

    dlg.add_action_callback("insert_support") do |_ctx, vtype|
      dlg.close
      # Após fechar, usuário clica no modelo para posicionar
      _start_placement_tool(model, vtype)
    end

    dlg.add_action_callback("close") { |_ctx, _| dlg.close }
    dlg.show
  end

  def self._start_placement_tool(model, vtype)
    # Usa input box de ponto simplificado
    # Em produção seria ideal um Tool customizado com cursor
    pt_input = UI.inputbox(
      ["X (m)", "Y (m)", "Z (m)"],
      ["0.0",   "0.0",   "0.0"],
      "Posição do apoio (metros)"
    )
    return unless pt_input
    x_m, y_m, z_m = pt_input.map(&:to_f)
    x_in = x_m / INCH_TO_M
    y_in = y_m / INCH_TO_M
    z_in = z_m / INCH_TO_M
    pos  = Geom::Point3d.new(x_in, y_in, z_in)
    insert_support(model, vtype, pos)
    Sketchup.active_model.active_view.refresh
  end

  def self.picker_html
    entries = SUPPORT_TYPES.map do |vtype, cfg|
      r, g, b = cfg[:color]
      color   = "rgb(#{r},#{g},#{b})"
      <<~HTML
        <button class="sup-btn" onclick="sketchup.insert_support('#{vtype}')">
          <span class="swatch" style="background:#{color}"></span>
          <span class="lbl">#{cfg[:label]}</span>
        </button>
      HTML
    end.join("\n")

    <<~HTML
      <!DOCTYPE html><html lang="pt-BR"><head>
      <meta charset="UTF-8">
      <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;
          background:#0f1117;color:#e0e6f0;padding:20px}
        h1{font-size:14px;color:#60a5fa;margin-bottom:16px;font-weight:700}
        .sup-btn{display:flex;align-items:center;gap:10px;width:100%;
          padding:10px 14px;margin-bottom:8px;background:#141c2b;
          border:1px solid #1e2a3a;border-radius:6px;color:#e0e6f0;
          cursor:pointer;font-size:13px;text-align:left}
        .sup-btn:hover{border-color:#3b82f6;background:#1d3461}
        .swatch{width:18px;height:18px;border-radius:3px;flex-shrink:0}
        .lbl{font-weight:600}
        .footer{margin-top:12px;text-align:right}
        .btn-cancel{padding:7px 16px;background:#374151;border:none;
          border-radius:4px;color:#e0e6f0;cursor:pointer;font-size:12px}
      </style></head><body>
      <h1>🔧 Inserir Apoio</h1>
      #{entries}
      <div class="footer">
        <button class="btn-cancel" onclick="sketchup.close()">Cancelar</button>
      </div>
      </body></html>
    HTML
  end

end
