# The MIT License (MIT)
#
# Copyright (c) 2016 LINE Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# frozen_string_literal: true
require 'yaml'

module Injector
  def self.extended(obj)
    obj.class_eval do
      def initialize(config)
        @injector_config = Injector.indifferent_config(config)
      end

      def config
        @injector_config
      end

      def logger
        @injector_class_logger ||= Injector.build_logger(self, self.class)
      end

      def get_bean(clazz, config = {})
        Injector.get_bean(self, clazz, config)
      end
    end
  end

  def register(method_name, clazz = nil, &block)
    if clazz
      define_method(method_name) do
        Injector.cache(method_name, self) do
          config = self.config[method_name.to_s]

          if config
            Injector.get_bean(self, clazz, config)
          else
            Injector.get_bean(self, clazz)
          end
        end
      end
    elsif block
      define_method(method_name) do
        Injector.cache(method_name, self) do
          config = self.config[method_name]
          instance_exec(config || {}, &block)
        end
      end
    else
      raise ArgumentError, 'clazz must not be null'
    end
  end

  def register_multi(method_name, prefix, module_path)
    define_method(method_name) do
      Injector.cache(method_name, self) do
        # load modules
        $LOAD_PATH.each do |path|
          Dir[File.join(path, module_path, '*.rb')].each do |file|
            require file
          end
        end

        # create instances
        (config[method_name.to_s] || []).map do |conf|
          conf = conf.dup
          klass = conf.delete('module')
          unless klass
            raise "Missing 'module' key in configuration: #{method_name}: #{config[method_name]}"
          end
          klass_name = "#{prefix}::#{klass}"
          clazz = Object.const_get(klass_name)
          Injector.get_bean(self, clazz, conf)
        end
      end
    end
  end

  def config_key(key)
    @config_key = key
  end

  def build(config_file = (@config_key ? ENV[@config_key] : nil) || 'config.yml')
    config = YAML.load_file(config_file)
    new(config)
  end

  def self.cache(method_name, container, &block)
    if container.instance_variable_defined?("@injector_cache_#{method_name}")
      container.instance_variable_get("@injector_cache_#{method_name}")
    else
      obj = block.call
      container.instance_variable_set("@injector_cache_#{method_name}", obj)
      obj
    end
  end

  def self.get_bean(container, clazz, config = {})
    params = clazz.instance_method(:initialize).parameters

    opts = {}

    params.each do |param|
      # TODO: support :key
      case param[0]
      when :keyreq
        key = param[1]
        begin
          if key == :logger
            opts[key] = Injector.build_logger(container, clazz)
          elsif key == :container
            opts[key] = container
          elsif config[key]
            opts[key] = config[key]
          elsif container.respond_to?(key)
            opts[key] = container.send(key)
          else
            raise NoMethodError, "Cannot instantiate #{clazz}. There's no '#{key}' method in container. And there's no '#{key}' in configuration: #{config}"
          end
        end
      else
        raise "This container only supports keyword parameters: #{clazz}, #{param}"
      end
    end

    clazz.new(opts)
  end

  def self.build_logger(container, clazz)
    class_name = clazz.to_s.freeze
    logger = Logger.new(STDOUT)
    logger.level = (container.config[:logger] || {})[:level] || Logger::INFO
    logger.formatter = proc { |severity, _datetime, _progname, msg|
      "[#{severity}] [#{class_name}] #{msg}\n"
    }
    logger
  end

  # Enable string or symbol key access to the nested params hash.
  def self.indifferent_config(object)
    case object
    when Hash
      new_hash = Hash.new do |hash, key|
        hash[key.to_s] if key.instance_of?(Symbol)
      end
      object.each { |key, value| new_hash[key] = indifferent_config(value) }
      new_hash
    when Array
      object.map { |item| indifferent_config(item) }
    else
      object
    end
  end
end
