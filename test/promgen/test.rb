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
ENV['RACK_ENV'] = 'test'

require 'test/unit'
require 'logger'
require 'rack/test'
require 'webmock/test_unit'

require 'promgen'
require 'promgen/factory'

class Promgen
  class ServerDirectory
    class PMC < Promgen::ServerDirectory::Base
      attr_reader :id, :url, :cache_lifetime

      def initialize(logger:, id:, url:, cache_lifetime:)
        @logger = logger
        @id = id
        @url = url
        @cache_lifetime = cache_lifetime
      end

      def self.properties
        [
          { name: :url },
          { name: :cache_lifetime }
        ]
      end
    end
  end
end

class Promgen
  class Test < Test::Unit::TestCase
    def setup
      @app = Promgen.new(
        'db' => {
          'dsn' => ENV['TEST_DSN'] || 'sqlite:/',
          'logging' => ENV['TEST_LOG'] || false
        },
        'logger' => {
          'level' => ENV['LOG_LEVEL'] || 'warn'
        },
        'config_writer' => {
          'path' => '/tmp/xxx.json',
          'notify' => ['http://promgen.localhost/api/v1/config']
        },
        'rule_writer' => {
          'rule_path' => '/tmp/xxx.rule',
          'promtool_path' => '/tmp/promtool',
          'notify' => ['http://promgen.localhost/api/v1/rules/']
        },
        'prometheus' => {
          'url' => 'http://prom.localhost'
        },
        'alert_senders' => [
          {
            'module' => 'Ikachan',
            'url' => 'http://ikachan.localhost/'
          },
          {
            'module' => 'Webhook'
          }
        ]
      )

      [:rule, :project_farm, :project_exporter, :project, :host, :server_directory, :farm, :service, :schema_info].each do |table|
        @app.db.drop_table? table
      end

      @app.migrator.run

      stub_request(:post, 'http://prom.localhost/-/reload').to_return(status: 200)
      stub_request(:post, 'http://promgen.localhost/api/v1/config').to_return(status: 200)
      stub_request(:post, 'http://promgen.localhost/api/v1/rules/').to_return(status: 200)

      @factory = @app.get_bean(Promgen::Factory)
    end
  end

  attr_reader :factory
end
