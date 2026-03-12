# calculadora_estrutural_loader.rb
# Arquivo carregador — deve ficar em: Plugins\calculadora_estrutural_loader.rb
# Os demais arquivos ficam em:         Plugins\calculadora_estrutural\

_dir = File.join(File.dirname(File.expand_path(__FILE__)), 'calculadora_estrutural')

require File.join(_dir, 'extension_main')
