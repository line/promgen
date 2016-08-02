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
    get '/server_directory/' do
      @server_directories = @server_directory_service.all
      erb :list_server_directory
    end

    get '/server_directory/register' do
      @types = @server_directory_service.types

      erb :register_server_directory
    end

    post '/server_directory/register' do
      type = params.delete('type')

      @server_directory_service.insert(
        type: type,
        params: params
      )

      redirect '/server_directory/'
    end

    get '/server_directory/:server_directory_id/update' do
      @server_directory = @server_directory_service.find(
        id: params[:server_directory_id]
      )

      erb :update_server_directory
    end

    post '/server_directory/:server_directory_id/update' do
      server_directory_id = params[:server_directory_id]
      @server_directory = @server_directory_service.update(
        id: server_directory_id,
        params: params
      )

      redirect '/server_directory/'
    end

    post '/server_directory/:server_directory_id/delete' do
      @server_directory_service.delete(
        server_directory_id: params[:server_directory_id]
      )
      redirect '/server_directory/'
    end

    get '/server_directory/:server_directory_id/farm_hosts' do
      @farm_name = params[:farm_name]
      raise ArgumentError, 'Missing farm name' if @farm_name.nil? || @farm_name.empty?
      server_directory_id = params[:server_directory_id]

      @server_directory = @server_directory_service.find(id: server_directory_id)
      @hosts = @server_directory.find_hosts(farm_name: @farm_name)

      erb :show_farm_host
    end
  end
end
