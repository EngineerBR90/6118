# =============================================================================
# structural_exporter.rb  — v3.1
# Extensão SketchUp: Exportador de Dados Estruturais para JSON
#
# Novidades v3.1 (em relação à v3.0):
#
#  NOVO 1 ── Leitura do StructuralExtractor (A1)
#    Usa no_inicio/no_fim calculados pelo eixo real da bbox em vez de
#    transformation.origin. Exporta extraction_score de cada elemento.
#
#  NOVO 2 ── Suporte a apoios gráficos (C1)
#    Detecta ComponentInstances com dict "support_def" próximos ao nó de base
#    de cada pilar (tolerância 10cm) e resolve vinculo_base automaticamente.
#    Exporta vinculo_source: "grafico" | "manual" | "auto".
#
#  NOVO 3 ── Cargas por cor (B1)
#    Lê carga_cor_id do dict e o exporta junto com revestimento/variável.
#
#  NOVO 4 ── Cargas pontuais (B2)
#    Lê point_loads_json do dict e exporta como array point_loads[].
#
#  MANTIDO ── Compatibilidade total com v3.0 no lado Python:
#    os campos novos são aditivos; o app.py lida com eles via json_importer v3.1.
#
# Schema exportado: v3.1
# =============================================================================

require 'json'

module StructuralExporter

  INCH_TO_CM   = 2.54
  INCH_TO_M    = 0.0254
  DICT_NAME    = "structural_data"
  VALID_TIPOS  = %w[viga pilar laje].freeze
  FLOOR_TOL_M  = 0.10
  SUPPORT_TOL_M = 0.10   # raio de busca de apoio gráfico em torno do nó de base

  class Exporter

    def initialize(model)
      @model         = model
      @elements      = []
      @global_params = {}
    end

    def set_global_parameters(concreto, aco, combinacao, agressividade, tol_nos = 0.005)
      @global_params = {
        "classe_concreto"      => concreto,
        "tipo_aco"             => aco,
        "tipo_combinacao"      => combinacao,
        "classe_agressividade" => agressividade,
        "tolerancia_nos_m"     => tol_nos.to_f
      }
    end

    # ── Coleta todos os elementos estruturais ────────────────────────────────
    def collect_structural_elements
      @elements   = []
      visited_ids = {}

      @model.definitions.each do |definition|
        next if definition.image?
        definition.instances.each do |instance|
          next if visited_ids[instance.entityID]
          visited_ids[instance.entityID] = true
          # Pular objetos de apoio e cargas pontuais
          next if instance.definition.get_attribute("support_def", "is_support")
          next if instance.definition.get_attribute("load_point_def", "is_load_point")
          data = extract_element_data(instance)
          @elements << data if data
        end
      end

      _assign_pavimento_hints!
      _assign_vinculos_graficos!
      @elements
    end

    # ── Extrai dados de um componente ────────────────────────────────────────
    def extract_element_data(instance)
      dict = instance.attribute_dictionary(DICT_NAME)
      return nil unless dict

      tipo = dict["tipo"].to_s.strip.downcase
      return nil unless VALID_TIPOS.include?(tipo)

      nome = dict["nome"].to_s.strip
      nome = instance.name.to_s if nome.empty?

      {
        "id"                 => dict["id"] || _generate_id(tipo),
        "tipo"               => tipo,
        "nome"               => nome,
        "extraction_score"   => _read_score(dict),
        "pavimento_hint"     => 0,
        "geometria"          => extract_geometry(instance, tipo, dict),
        "posicao"            => extract_position(instance, tipo, dict),
        "cargas"             => extract_cargas(dict, tipo),
        "parametros_calculo" => extract_calculation_parameters(dict, tipo)
      }
    end

    # ── Geometria ────────────────────────────────────────────────────────────
    #
    # Prioridade:
    #   1. Valores manuais do dict (dict["largura"], dict["altura"]) se
    #      dict["largura_manual"] = true  (usuário sobrescreveu via dialog)
    #   2. Valores extraídos pelo StructuralExtractor (gravados no dict em
    #      extraction_score, no_inicio_json, no_fim_json)
    #   3. Fallback: bounding box (lógica v3.0)
    #
    def extract_geometry(instance, tipo, dict)
      # Lê dimensões do dict se existirem (preenchidas pelo extrator ou manualmente)
      b_dict = dict["largura"]
      h_dict = dict["altura"]

      if b_dict && h_dict && b_dict.to_f > 0
        # Já está no dict — usar diretamente
        b_cm = b_dict.to_f
        h_cm = h_dict.to_f
        l_m  = _read_L_from_dict_or_bbox(instance, tipo, dict)
        return build_geom_hash(tipo, b_cm, h_cm, l_m)
      end

      # Fallback: bbox (idêntico ao v3.0)
      extract_geometry_bbox(instance, tipo)
    end

    def extract_geometry_bbox(instance, tipo)
      b    = instance.bounds
      dx   = (b.max.x - b.min.x).abs.to_f
      dy   = (b.max.y - b.min.y).abs.to_f
      dz   = (b.max.z - b.min.z).abs.to_f

      case tipo
      when "viga"
        horiz_max = [dx, dy].max
        horiz_min = [dx, dy].min
        {
          "comprimento" => (horiz_max * INCH_TO_M).round(3),
          "largura"     => (horiz_min * INCH_TO_CM).round(1),
          "altura"      => (dz        * INCH_TO_CM).round(1)
        }
      when "pilar"
        b_in = [dx, dy].min
        h_in = [dx, dy].max
        {
          "comprimento" => (dz   * INCH_TO_M).round(3),
          "largura"     => (b_in * INCH_TO_CM).round(1),
          "altura"      => (h_in * INCH_TO_CM).round(1)
        }
      when "laje"
        {
          "comprimento" => (dx * INCH_TO_M).round(3),
          "largura"     => (dy * INCH_TO_M).round(3),
          "altura"      => (dz * INCH_TO_CM).round(1)
        }
      end
    end

    def build_geom_hash(tipo, b_cm, h_cm, l_m)
      case tipo
      when "viga"
        { "comprimento" => l_m.round(3), "largura" => b_cm.round(1), "altura" => h_cm.round(1) }
      when "pilar"
        { "comprimento" => l_m.round(3), "largura" => b_cm.round(1), "altura" => h_cm.round(1) }
      when "laje"
        { "comprimento" => l_m.round(3), "largura" => b_cm.round(1), "altura" => h_cm.round(1) }
      end
    end

    # ── Posição 3D ────────────────────────────────────────────────────────────
    #
    # Prioridade:
    #   1. no_inicio_json / no_fim_json do dict (calculados pelo extrator via eixo bbox)
    #   2. Fallback: transformation.origin + bbox extent (lógica v3.0)
    #
    def extract_position(instance, tipo, dict)
      ni_json = dict["no_inicio_json"].to_s
      nf_json = dict["no_fim_json"].to_s

      if !ni_json.empty? && !nf_json.empty?
        begin
          ni = JSON.parse(ni_json)
          nf = JSON.parse(nf_json)
          return { "no_inicio" => ni, "no_fim" => nf }
        rescue JSON::ParserError
          # fallthrough
        end
      end

      # Fallback: lógica v3.0
      extract_position_v30(instance, tipo)
    end

    def extract_position_v30(instance, tipo)
      t  = instance.transformation
      ox = t.origin.x.to_f * INCH_TO_M
      oy = t.origin.y.to_f * INCH_TO_M
      oz = t.origin.z.to_f * INCH_TO_M

      b     = instance.bounds
      dx    = (b.max.x - b.min.x).abs.to_f
      dy    = (b.max.y - b.min.y).abs.to_f
      dz    = (b.max.z - b.min.z).abs.to_f

      case tipo
      when "viga"
        if dx >= dy
          { "no_inicio" => _pt(ox, oy, oz),
            "no_fim"    => _pt(ox + dx * INCH_TO_M, oy, oz) }
        else
          { "no_inicio" => _pt(ox, oy, oz),
            "no_fim"    => _pt(ox, oy + dy * INCH_TO_M, oz) }
        end
      when "pilar"
        { "no_inicio" => _pt(ox, oy, oz),
          "no_fim"    => _pt(ox, oy, oz + dz * INCH_TO_M) }
      when "laje"
        { "no_inicio" => _pt(ox, oy, oz),
          "no_fim"    => _pt(ox + dx * INCH_TO_M, oy + dy * INCH_TO_M, oz) }
      end
    end

    # ── Cargas ────────────────────────────────────────────────────────────────
    def extract_cargas(dict, tipo)
      cargas = { "pp_automatico" => true }

      # Carga por cor (B1) — presente para todos os tipos
      cor_id = dict["carga_cor_id"].to_s
      cargas["carga_cor_id"] = cor_id unless cor_id.empty?

      # Cargas pontuais (B2) — presente para vigas principalmente
      pl_raw = dict["point_loads_json"].to_s
      unless pl_raw.empty?
        begin
          pl_arr = JSON.parse(pl_raw)
          cargas["point_loads"] = pl_arr if pl_arr.is_a?(Array) && !pl_arr.empty?
        rescue JSON::ParserError
        end
      end

      case tipo
      when "viga"
        # Paredes
        paredes_raw = dict["paredes_json"]
        if paredes_raw && !paredes_raw.to_s.strip.empty?
          begin
            cargas["paredes"] = JSON.parse(paredes_raw.to_s)
          rescue JSON::ParserError
            cargas["paredes"] = []
          end
        else
          cargas["paredes"] = []
        end

        # Revestimento
        rev_id  = dict["revestimento_tipo_id"].to_s
        rev_val = (dict["revestimento_kN_m2"] || 0.0).to_f
        cargas["revestimento"] = rev_id.empty? ? nil : {
          "tipo_id" => rev_id,
          "nome"    => dict["revestimento_nome"].to_s,
          "kN_m2"   => rev_val
        }

        # Carga variável
        var_id  = dict["variavel_tipo_id"].to_s
        var_val = (dict["variavel_kN_m2"] || 0.0).to_f
        cargas["variavel"] = var_id.empty? ? nil : {
          "tipo_id" => var_id,
          "nome"    => dict["variavel_nome"].to_s,
          "kN_m2"   => var_val
        }

        # Cargas especiais
        cargas["especiais_kN_m"] = (dict["especiais_kN_m"] || 0.0).to_f

      when "laje"
        rev_id  = dict["revestimento_tipo_id"].to_s
        rev_val = (dict["revestimento_kN_m2"] || 0.0).to_f
        cargas["revestimento"] = rev_id.empty? ? nil : {
          "tipo_id" => rev_id, "nome" => dict["revestimento_nome"].to_s, "kN_m2" => rev_val
        }
        var_id  = dict["variavel_tipo_id"].to_s
        var_val = (dict["variavel_kN_m2"] || 0.0).to_f
        cargas["variavel"] = var_id.empty? ? nil : {
          "tipo_id" => var_id, "nome" => dict["variavel_nome"].to_s, "kN_m2" => var_val
        }

      when "pilar"
        nil  # pilares só têm pp_automatico + point_loads opcionais
      end

      cargas
    end

    # ── Parâmetros de cálculo (inalterado da v3.0) ───────────────────────────
    def extract_calculation_parameters(dict, tipo)
      params = {}
      params["cobrimento_nominal"] = (dict["cobrimento_nominal"] || 30.0).to_f
      params["phi_estribo"]        = (dict["phi_estribo"]        ||  8.0).to_f
      params["phi_longitudinal"]   = (dict["phi_longitudinal"]   || 20.0).to_f

      case tipo
      when "viga"
        params["momento_fletor_Md"]            = (dict["momento_fletor_Md"]            || 0.0).to_f
        params["modo_flexao"]                  =  dict["modo_flexao"]                  || "Calcular As"
        params["num_barras_flexao"]            = (dict["num_barras_flexao"]            || 4).to_i
        params["as_fornecida_flexao"]          = (dict["as_fornecida_flexao"]          || 0.0).to_f
        params["forca_cortante_Vd"]            = (dict["forca_cortante_Vd"]            || 0.0).to_f
        params["as_longitudinal_cisalhamento"] = (dict["as_longitudinal_cisalhamento"] || 0.0).to_f
        params["modelo_cisalhamento"]          =  dict["modelo_cisalhamento"]          || "Modelo I — Treliça 45°"
        params["angulo_theta_cisalhamento"]    = (dict["angulo_theta_cisalhamento"]    || 45).to_i
        params["num_ramos_estribo"]            = (dict["num_ramos_estribo"]            || 2).to_i
        params["as_tracao_els"]                = (dict["as_tracao_els"]                || 0.0).to_f
        params["as_compressao_els"]            = (dict["as_compressao_els"]            || 0.0).to_f
        params["momento_caracteristico_Mk"]    = (dict["momento_caracteristico_Mk"]    || 0.0).to_f
        params["uso_elemento_els"]             =  dict["uso_elemento_els"]             || "Viga de piso — estrutura geral (L/250)"
        params["num_barras_fissuras"]          = (dict["num_barras_fissuras"]          || 4).to_i
        params["momento_servico_Ms"]           = (dict["momento_servico_Ms"]           || 0.0).to_f
        params["wk_limite_fissuras"]           =  dict["wk_limite_fissuras"]           || "CAA II — wk ≤ 0,3 mm"
      when "pilar"
        params["forca_normal_Nd"]  = (dict["forca_normal_Nd"]  || 0.0).to_f
        params["momento_Mdx"]      = (dict["momento_Mdx"]      || 0.0).to_f
        params["momento_Mdy"]      = (dict["momento_Mdy"]      || 0.0).to_f
        params["comprimento_le_x"] = (dict["comprimento_le_x"] || 0.0).to_f
        params["comprimento_le_y"] = (dict["comprimento_le_y"] || 0.0).to_f
        params["_vinculo_base"]    = dict["vinculo_base"] || "engastado"
        params["_vinculo_source"]  = dict["vinculo_source"] || "manual"
      when "laje"
        params["momento_fletor_Md"]         = (dict["momento_fletor_Md"]         || 0.0).to_f
        params["as_tracao_els"]             = (dict["as_tracao_els"]             || 0.0).to_f
        params["as_compressao_els"]         = (dict["as_compressao_els"]         || 0.0).to_f
        params["momento_caracteristico_Mk"] = (dict["momento_caracteristico_Mk"] || 0.0).to_f
        params["uso_elemento_els"]          =  dict["uso_elemento_els"]          || "Laje de piso (L/250)"
        params["num_barras_fissuras"]       = (dict["num_barras_fissuras"]       || 4).to_i
        params["momento_servico_Ms"]        = (dict["momento_servico_Ms"]        || 0.0).to_f
        params["wk_limite_fissuras"]        =  dict["wk_limite_fissuras"]        || "CAA II — wk ≤ 0,3 mm"
      end

      params
    end

    # ── Detecção de pavimentos ────────────────────────────────────────────────
    def _assign_pavimento_hints!
      return if @elements.empty?
      z_values = @elements.map { |el|
        pos = el["posicao"]
        pos ? pos["no_inicio"]["z"] : 0.0
      }
      z_levels = []
      z_values.sort.uniq.each do |z|
        existing = z_levels.find { |zl| (zl - z).abs <= FLOOR_TOL_M }
        if existing
          idx = z_levels.index(existing)
          z_levels[idx] = (existing + z) / 2.0
        else
          z_levels << z
        end
      end
      z_levels.sort!
      @elements.each do |el|
        pos = el["posicao"]
        z   = pos ? pos["no_inicio"]["z"] : 0.0
        idx = z_levels.index { |zl| (zl - z).abs <= FLOOR_TOL_M }
        el["pavimento_hint"] = idx || 0
      end

      # Vinculo_base de pilares para nível raiz
      @elements.each do |el|
        next unless el["tipo"] == "pilar"
        params = el["parametros_calculo"] || {}
        el["vinculo_base"]   = params.delete("_vinculo_base") || "engastado"
        el["vinculo_source"] = params.delete("_vinculo_source") || "manual"
      end
    end

    # ── Vinculo gráfico: detecta apoio próximo ao no_inicio de cada pilar ─────
    def _assign_vinculos_graficos!
      @elements.each do |el|
        next unless el["tipo"] == "pilar"
        pos = el["posicao"]
        next unless pos

        ni = pos["no_inicio"]
        result = SupportManager.find_support_near(ni, @model, SUPPORT_TOL_M)
        if result
          el["vinculo_base"]   = result["vinculo_type"]
          el["vinculo_source"] = "grafico"
        end
      end
    end

    # ── Exportação para JSON ──────────────────────────────────────────────────
    def export_to_json(filepath)
      collect_structural_elements if @elements.empty?

      data = {
        "schema_version"        => "3.1",
        "exportado_em"          => Time.now.strftime("%Y-%m-%dT%H:%M:%S"),
        "global_parameters"     => @global_params,
        "elementos_estruturais" => @elements
      }

      File.open(filepath, "w:UTF-8") { |f| f.write(JSON.pretty_generate(data)) }
      puts "✓ Exportado v3.1: #{filepath}"
      puts "  Elementos: #{@elements.length}"
      _print_floor_summary
      @elements.length
    end

    def validate_json(filepath)
      data   = JSON.parse(File.read(filepath, encoding: "UTF-8"))
      errors = []

      %w[classe_concreto tipo_aco tipo_combinacao classe_agressividade].each do |k|
        errors << "global_parameters.#{k} ausente" unless data.dig("global_parameters", k)
      end

      (data["elementos_estruturais"] || []).each_with_index do |el, i|
        %w[id tipo nome geometria].each do |k|
          errors << "elemento[#{i}].#{k} ausente" unless el[k]
        end
        unless VALID_TIPOS.include?(el["tipo"].to_s)
          errors << "elemento[#{i}].tipo inválido: '#{el['tipo']}'"
        end
        if ["3.0","3.1"].include?(data["schema_version"])
          unless el["posicao"]&.dig("no_inicio") && el["posicao"]&.dig("no_fim")
            errors << "elemento[#{i}] (#{el['nome']}): posicao ausente"
          end
        end
      end

      if errors.empty?
        puts "✓ JSON v#{data['schema_version']} válido!"; true
      else
        puts "✗ #{errors.length} erro(s):"; errors.each { |e| puts "  - #{e}" }; false
      end
    end

    private

    def _pt(x, y, z)
      { "x" => x.round(4), "y" => y.round(4), "z" => z.round(4) }
    end

    def _generate_id(tipo)
      "#{tipo}-#{Time.now.to_i}-#{rand(1000..9999)}"
    end

    def _read_score(dict)
      s = dict["extraction_score"]
      s ? s.to_f.round(3) : nil
    end

    def _read_L_from_dict_or_bbox(instance, tipo, dict)
      # Se tiver no_inicio_json e no_fim_json pode calcular L
      ni_json = dict["no_inicio_json"].to_s
      nf_json = dict["no_fim_json"].to_s
      if !ni_json.empty? && !nf_json.empty?
        begin
          ni = JSON.parse(ni_json)
          nf = JSON.parse(nf_json)
          dx = (nf["x"] - ni["x"]) ** 2
          dy = (nf["y"] - ni["y"]) ** 2
          dz = (nf["z"] - ni["z"]) ** 2
          return Math.sqrt(dx + dy + dz).round(4)
        rescue
        end
      end
      # Fallback bbox
      b  = instance.bounds
      dx = (b.max.x - b.min.x).abs.to_f
      dy = (b.max.y - b.min.y).abs.to_f
      dz = (b.max.z - b.min.z).abs.to_f
      case tipo
      when "pilar" then dz * INCH_TO_M
      else [dx, dy].max * INCH_TO_M
      end
    end

    def _print_floor_summary
      floors = @elements.group_by { |el| el["pavimento_hint"] }
      puts "  Pavimentos detectados:"
      floors.sort.each do |idx, els|
        z = els.first.dig("posicao", "no_inicio", "z") || 0.0
        puts "    Pavimento #{idx} (Z≈#{z.round(2)}m): #{els.length} elementos"
      end
    end

  end
end
