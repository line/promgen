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

require 'erubis'

class Promgen
  class API < Sinatra::Base
    def initialize(
        config_writer:,
        rule_writer:,

        farm_service:,
        host_service:,
        project_exporter_service:,
        project_farm_service:,
        project_service:,
        server_directory_service:,

        logger:
    )
      super()
      @config_writer = config_writer
      @rule_writer = rule_writer

      @farm_service = farm_service
      @host_service = host_service
      @project_exporter_service = project_exporter_service
      @project_farm_service = project_farm_service
      @project_service = project_service
      @server_directory_service = server_directory_service

      @logger = logger
    end

    set :erb, escape_html: true
    set :root, File.join(File.dirname(__FILE__), '..', '..')

    get '/' do
      erb :api
    end

    get '/v1/config' do
      @config_writer.render
    end

    post '/v1/config' do
      @config_writer.write(notify: false)
      'ok'
    end

    get '/v1/project/' do
      json(projects: @project_service.all.map(&:values))
    end

    get '/v1/project/:project_id' do
      project = @project_service.find(id: params[:project_id])
      halt 404 unless project
      val = { project: project.values }
      val[:project][:exporters] = @project_exporter_service.find_by_project_id(
        project_id: project.id
      ).map(&:values)
      project_farm = @project_farm_service.find_by_project_id(
        project_id: project.id
      )
      if project_farm
        val[:project][:farm] = project_farm.farm_name
        server_directory = @server_directory_service.find(id: project_farm.server_directory_id)
        val[:project][:hosts] = server_directory.find_hosts(farm_name: project_farm.farm_name)
      end
      json(val)
    end

    get '/v1/farm/' do
      json(farms: @farm_service.all.map(&:values))
    end

    get '/v1/farm/:farm_id' do
      farm_id = params['farm_id'].to_i
      farm = @farm_service.find(id: farm_id)
      halt 404 unless farm

      val = { farm: farm.values }
      val[:farm][:hosts] = @host_service.find_by_farm_id(farm_id: farm_id).map(&:values)

      json(val)
    end

    get '/v1/rule/' do
      content_type 'text/plain'
      @rule_writer.render
    end

    post '/v1/rule/' do
      @rule_writer.write(notify: false)
      'ok'
    end

    get '/v1/server_directory/' do
      json(server_directories: @server_directory_service.all.map(&:values))
    end

    get '/v1/server_directory/type/' do
      types = @server_directory_service.types
                                       .map(&:values)
      json(types: types)
    end
  end
end
