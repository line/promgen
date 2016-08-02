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
    get '/project/:project_id/exporter/register' do
      erb :register_project_exporter
    end

    post '/project/:project_id/exporter/register' do
      port = params['port']
      job = params['job']

      @project_exporter_service.register(project_id: @project.id, port: port, job: job)
      @config_writer.write

      redirect "/project/#{@project.id}"
    end

    post '/project/:project_id/exporter/:port/delete' do
      port = params['port']

      @project_exporter_service.delete(project_id: @project.id, port: port)
      @config_writer.write

      redirect "/project/#{@project.id}"
    end
  end
end
