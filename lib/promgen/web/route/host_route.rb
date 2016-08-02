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
    # Add new host to the farm
    get '/project/:project_id/farm/:farm_id/host/add' do
      @farm = @farm_service.find(id: params[:farm_id])
      erb :add_host
    end

    post '/project/:project_id/farm/:farm_id/host/add' do
      names = params[:names].to_s
                            .split(/\n+/)
                            .map { |l| l.gsub(/^\s+|\s+$/, '') }
                            .select { |line| line !~ /^#/ && !line.empty? }
      farm = @farm_service.find(id: params[:farm_id])
      @host_service.insert_multi(names: names, farm_id: farm.id)
      @config_writer.write

      redirect "/project/#{@project.id}"
    end

    # Delete host
    post '/project/:project_id/farm/:farm_id/host/:host_name/delete' do
      @host_service.delete_by_name(name: params[:host_name])
      @config_writer.write
      redirect "/project/#{params[:project_id]}"
    end
  end
end
