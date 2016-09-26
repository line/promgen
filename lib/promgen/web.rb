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
require 'sinatra/base'
require 'sinatra/json'

require 'promgen/web/route/farm_route'
require 'promgen/web/route/project_route'
require 'promgen/web/route/status_route'
require 'promgen/web/route/server_directory_route'
require 'promgen/web/route/host_route'
require 'promgen/web/route/service_route'
require 'promgen/web/route/project_exporter_route'
require 'promgen/web/route/rule_route'
require 'promgen/web/route/audit_route'

require 'erubis'
require 'tilt/erubis'

class Promgen
  class Web < Sinatra::Base
    def initialize(
        farm_service:,
        host_service:,
        project_exporter_service:,
        rule_service:,
        config_writer:,
        rule_writer:,
        project_service:,
        project_farm_service:,
        prometheus:,
        alert_senders:,
        server_directory_service:,
        logger:,
        service_service:,
        audit_log_service:,

        config:
    )
      super()
      @farm_service = farm_service
      @host_service = host_service
      @project_exporter_service = project_exporter_service
      @rule_service = rule_service
      @project_service = project_service
      @project_farm_service = project_farm_service
      @config_writer = config_writer
      @rule_writer = rule_writer
      @prometheus = prometheus
      @alert_senders = alert_senders
      @server_directory_service = server_directory_service
      @logger = logger
      @service_service = service_service
      @audit_log_service = audit_log_service

      @default_exporters = config.fetch('default_exporters', node: 9100, nginx: 9113)
    end

    set :erb, escape_html: true
    set :root, File.join(File.dirname(__FILE__), '..', '..')

    helpers do
      def h(text)
        Rack::Utils.escape_html(text)
      end
    end

    before %r{/project/(?<path_project_id>[0-9]+)(?:/farm/(?<path_farm_id>[0-9]+))?(?<dest>/.*|)} do
      project_id = params['path_project_id']
      @project = @project_service.find(id: project_id)
      halt 404, 'Unknown project ID' unless @project
    end

    not_found do
      status 404
      erb :error_404
    end

    get '/' do
      redirect to('/service/')
    end
  end
end
