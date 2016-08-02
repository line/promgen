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
    # Farm registration form
    get '/project/:project_id/farm/register' do
      erb :register_farm
    end

    # Farm registration
    post '/project/:project_id/farm/register' do
      name = params[:name].to_s
      raise ArgumentError, 'Missing name' if name.nil? || name.empty?
      farm = @farm_service.find_or_create(name: name)

      server_directory = @server_directory_service.find_db
      @project_farm_service.link(
        project_id: @project.id,
        farm_name: farm.name,
        server_directory_id: server_directory.id
      )

      redirect "/project/#{@project.id}"
    end

    # Edit farm info
    get '/project/:project_id/farm/:farm_id/edit' do
      @farm = @farm_service.find(id: params[:farm_id])
      erb :edit_farm
    end

    post '/project/:project_id/farm/:farm_id/edit' do
      farm_id = params[:farm_id]
      name = params[:name]
      raise ArgumentError, 'Missing name' if name.nil? || name.empty?
      farm = @farm_service.find(id: farm_id)

      @farm_service.update(id: farm.id, name: name)

      redirect "/project/#{@project.id}"
    end
  end
end
