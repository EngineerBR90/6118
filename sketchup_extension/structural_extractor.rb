# =============================================================================
# structural_extractor.rb  — v4.0
# Auto-extração de geometria, classificação e score de confiança.
#
# Funcionalidades:
#   • Lê bounding box de cada ComponentInstance/Group
#   • Determina eixo principal (maior dimensão) e seção transversal (b × h)
#   • Classifica como viga/pilar/laje por razão de esbeltez e orientação
#   • Gera score de confiança 0–1 (threshold: 0.80)
#   • Detecta pares de nós possivelmente desconectados (5mm < dist < 30mm)
#   • Calcula no_inicio/no_fim pelo centróide das faces extremas da bbox
# =============================================================================

require 'json'

module StructuralExtractor

  INCH_TO_M    = 0.0254
  INCH_TO_CM   = 2.54
  DICT_NAME    = "structural_data"
  SCORE_AUTO   = 0.80   # threshold para aprovação automática
  TOL_FUSED    = 0.005  # nós fundidos se distância < 5mm
  TOL_WARN     = 0.030  # alerta se distância < 30mm (provavelmente deveria ser 1 nó)
  SUPPORT_DICT = "support_def"
  LOAD_PT_DICT = "load_point_def"

  # ── Extrai todos os elementos estruturais do modelo ────────────────────────
  def self.extract_all(model)
    results   = []
    visited   = {}

    model.definitions.each do |defn|
      next if defn.image?
      defn.instances.each do |inst|
        next if visited[inst.entityID]
        visited[inst.entityID] = true
        # Ignorar objetos de apoio e cargas pontuais (têm dict próprio)
        next if inst.definition.get_attribute(SUPPORT_DICT, "is_support")
        next if inst.definition.get_attribute(LOAD_PT_DICT, "is_load_point")
        r = extract_one(inst)
        results << r if r
      end
    end

    results
  end

  # ── Extrai dados de um componente ─────────────────────────────────────────
  def self.extract_one(inst)
    bb = inst.bounds
    dx = (bb.max.x - bb.min.x).abs.to_f   # extensão X em polegadas
    dy = (bb.max.y - bb.min.y).abs.to_f
    dz = (bb.max.z - bb.min.z).abs.to_f

    # Descarta objetos com bounding box trivial (linhas, pontos)
    return nil if [dx, dy, dz].max < (0.01 / INCH_TO_M)

    dims = { x: dx, y: dy, z: dz }

    # Eixo principal = maior dimensão
    principal_axis = dims.max_by { |_k, v| v }[0]
    l_in           = dims[principal_axis]
    sec_dims       = dims.reject { |k, _| k == principal_axis }.values.sort
    b_in, h_in     = sec_dims[0], sec_dims[1]   # b ≤ h

    l_m  = l_in  * INCH_TO_M
    b_cm = b_in  * INCH_TO_CM
    h_cm = h_in  * INCH_TO_CM

    # Classificação
    tipo, score = classify(principal_axis, l_m, b_cm, h_cm)

    # Nós pelo centróide das faces extremas
    ctr = bb.center
    ni, nf = endpoints(bb, ctr, principal_axis)

    # Nome do componente SketchUp
    name_su = inst.definition.name.to_s
    name_su = inst.name.to_s if name_su.strip.empty?

    # Verificar se já foi configurado manualmente
    dict         = inst.attribute_dictionary(DICT_NAME)
    already_set  = dict && dict["tipo"] && !dict["tipo"].to_s.strip.empty?

    {
      "entity_id"    => inst.entityID,
      "name_su"      => name_su,
      "tipo_infer"   => tipo,
      "score"        => score.round(3),
      "needs_review" => score < SCORE_AUTO,
      "already_set"  => already_set || false,
      "b_cm"         => b_cm.round(1),
      "h_cm"         => h_cm.round(1),
      "l_m"          => l_m.round(4),
      "principal_axis"=> principal_axis.to_s,
      "no_inicio"    => pt_h(ni),
      "no_fim"       => pt_h(nf)
    }
  rescue => e
    nil
  end

  # ── Classificação com score ────────────────────────────────────────────────
  def self.classify(axis, l_m, b_cm, h_cm)
    is_vert  = (axis == :z)
    max_sec  = [b_cm, h_cm].max
    ratio    = max_sec > 0 ? l_m / (max_sec / 100.0) : 1.0

    if is_vert
      # Pilar: eixo vertical
      if ratio > 4.0
        ["pilar", 0.97]
      elsif ratio > 2.5
        ["pilar", 0.88]
      elsif ratio > 1.5
        ["pilar", 0.72]
      else
        # Cubo / bloco — ambíguo
        ["pilar", 0.50]
      end
    else
      # Horizontal: viga ou laje
      h_m = h_cm / 100.0
      if ratio > 5.0
        ["viga", 0.97]
      elsif ratio > 3.0
        ["viga", 0.90]
      elsif ratio > 2.0
        ["viga", 0.80]
      elsif h_m < 0.20 && ratio > 1.0
        # Laje: muito plano
        ["laje", 0.85]
      elsif ratio > 1.0
        ["viga", 0.65]
      else
        ["viga", 0.50]
      end
    end
  end

  # ── Calcula no_inicio e no_fim pelo centróide das faces extremas ───────────
  def self.endpoints(bb, ctr, axis)
    cx = ctr.x.to_f
    cy = ctr.y.to_f
    cz = ctr.z.to_f

    case axis
    when :x
      ni = [bb.min.x.to_f, cy, cz]
      nf = [bb.max.x.to_f, cy, cz]
    when :y
      ni = [cx, bb.min.y.to_f, cz]
      nf = [cx, bb.max.y.to_f, cz]
    when :z
      ni = [cx, cy, bb.min.z.to_f]
      nf = [cx, cy, bb.max.z.to_f]
    end

    [ni.map { |v| v * INCH_TO_M }, nf.map { |v| v * INCH_TO_M }]
  end

  # ── Detecta nós possivelmente desconectados ────────────────────────────────
  #
  # Percorre todos os endpoints dos resultados e encontra pares onde a
  # distância é maior que TOL_FUSED (5mm) mas menor que TOL_WARN (30mm).
  # Esses são candidatos a "deveria ser um nó mas não está conectado".
  #
  def self.find_near_disconnected(results)
    # Coleta todos os endpoints com referência ao elemento
    pts = []
    results.each do |r|
      ni = r["no_inicio"]
      nf = r["no_fim"]
      pts << { pt: [ni["x"], ni["y"], ni["z"]], el: r["name_su"], end: "inicio" }
      pts << { pt: [nf["x"], nf["y"], nf["z"]], el: r["name_su"], end: "fim"    }
    end

    warnings = []
    pts.length.times do |i|
      (i + 1).upto(pts.length - 1) do |j|
        a, b = pts[i], pts[j]
        # Mesmos elemento e ponto → ignora
        next if a[:el] == b[:el] && a[:end] == b[:end]

        dist = Math.sqrt(
          (a[:pt][0] - b[:pt][0])**2 +
          (a[:pt][1] - b[:pt][1])**2 +
          (a[:pt][2] - b[:pt][2])**2
        )
        if dist > TOL_FUSED && dist < TOL_WARN
          warnings << {
            "el_a"   => a[:el],
            "end_a"  => a[:end],
            "el_b"   => b[:el],
            "end_b"  => b[:end],
            "dist_mm"=> (dist * 1000).round(1)
          }
        end
      end
    end
    warnings
  end

  # ── Aplica resultados de volta ao modelo (grava atributos) ─────────────────
  #
  # Chamado após o usuário confirmar no painel de revisão.
  # data = array de hashes: [{entity_id, tipo, b_cm, h_cm, l_m, no_inicio, no_fim}]
  #
  def self.apply_confirmed(model, confirmed_data)
    confirmed_data.each do |d|
      inst = find_by_entity_id(model, d["entity_id"].to_i)
      next unless inst

      model.start_operation("Auto-configurar elemento", true)
      dict = inst.attribute_dictionary(DICT_NAME, true)

      # JS envia "tipo_infer" (nome do campo no hash do extrator);
      # aceita também "tipo" para compatibilidade futura.
      tipo_val = d["tipo_infer"] || d["tipo"]
      if tipo_val && !tipo_val.to_s.strip.empty?
        dict["tipo"] = tipo_val.to_s.strip unless dict["tipo"] && !dict["tipo"].to_s.strip.empty?
      end

      dict["extraction_score"] = d["score"].to_f

      # Geometria: preenche se vazio
      unless dict["largura_manual"]
        dict["largura"] = d["b_cm"].to_f if d["b_cm"].to_f > 0
        dict["altura"]  = d["h_cm"].to_f if d["h_cm"].to_f > 0
      end

      # Nó de início/fim: sempre atualiza do extrator
      dict["no_inicio_json"] = d["no_inicio"].to_json rescue nil
      dict["no_fim_json"]    = d["no_fim"].to_json    rescue nil

      # Nome padrão se vazio
      if !dict["nome"] || dict["nome"].to_s.strip.empty?
        dict["nome"] = d["name_su"].to_s
      end

      # ID único se ainda não tiver
      if !dict["id"] || dict["id"].to_s.strip.empty?
        dict["id"] = "#{tipo_val}-#{inst.entityID}"
      end

      model.commit_operation
    end
  end

  # ── Busca instância por entityID ───────────────────────────────────────────
  def self.find_by_entity_id(model, eid)
    model.definitions.each do |defn|
      next if defn.image?
      defn.instances.each do |inst|
        return inst if inst.entityID == eid
      end
    end
    nil
  end

  # ── Auxiliar: hash de ponto ────────────────────────────────────────────────
  def self.pt_h(arr)
    { "x" => arr[0].round(4), "y" => arr[1].round(4), "z" => arr[2].round(4) }
  end

end
