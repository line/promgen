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

class Promgen
  class Web < Sinatra::Base
    def empty_to_nil(s)
      if s.nil?
        nil
      elsif s.empty?
        nil
      else
        s
      end
    end

    private :empty_to_nil

    get '/service/:service_id/project/create' do
      @service = @service_service.find(id: params[:service_id])
      erb :create_project
    end

    post '/service/:service_id/project/create' do
      @project_service.insert(
        service_id: params[:service_id],
        name: params[:name],
        hipchat_channel: empty_to_nil(params[:hipchat_channel]),
        mail_address: empty_to_nil(params[:mail_address]),
        webhook_url: empty_to_nil(params[:webhook_url])
      )

      redirect to('/service/')
    end

    get '/project/:project_id' do
      @project_farm = @project_farm_service.find_by_project_id(project_id: @project.id)
      if @project_farm
        @farm = @farm_service.find_by_name(name: @project_farm.farm_name)
        @server_directory = @server_directory_service.find(
          id: @project_farm.server_directory_id
        )
        if @server_directory.nil?
          raise "Invalid state: Unknown server directory id: #{farm.server_directory_id}"
        end
        @hosts = @server_directory.find_hosts(farm_name: @project_farm.farm_name)
      end

      @exporters = @project_exporter_service.find_by_project_id(project_id: @project.id)

      @server_directories = @server_directory_service.all

      erb :show_project
    end

    get '/project/:project_id/update' do
      erb :update_project
    end

    post '/project/:project_id/update' do
      @project_service.update(
        project_id: @project.id,
        name: params['name'],
        hipchat_channel: empty_to_nil(params['hipchat_channel']),
        mail_address: empty_to_nil(params['mail_address']),
        webhook_url: empty_to_nil(params['webhook_url'])
      )
      @config_writer.write
      redirect "/project/#{@project.id}"
    end

    get '/project/:project_id/link/:server_directory_id' do
      @server_directory = @server_directory_service.find(
        id: params[:server_directory_id].to_i
      )
      @farm_names = @server_directory.farm_names
      erb :link_project
    end
    post '/project/:project_id/delete' do
      @project_service.delete(id: @project.id)
      redirect '/service/'
    end

    post '/project/:project_id/link/:server_directory_id' do
      farm_name = params['farm_name']
      halt 400, 'Missing farm name' if farm_name.nil?
      @project_farm_service.link(
        project_id: @project.id,
        server_directory_id: params[:server_directory_id],
        farm_name: farm_name
      )
      @config_writer.write
      redirect "/project/#{@project.id}"
    end

    post '/project/:project_id/unlink/:project_farm_id' do
      project_farm_id = params['project_farm_id']
      project_farm = @project_farm_service.find(id: project_farm_id)
      halt 404, "Unknown project_farm_id: #{params[:project_farm_id]}" unless project_farm

      @project_farm_service.unlink(project_id: project_farm.project_id, farm_name: project_farm.farm_name)
      @config_writer.write

      redirect "/project/#{project_farm.project_id}"
    end
  end
end
