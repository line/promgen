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
    get '/service/' do
      @services = @service_service.all

      @service_id2projects = @project_service.all.group_by(&:service_id).each_with_object({}) do |row, memo|
        memo[row[0]] = row[1]
      end

      @project_id2exporters = @project_exporter_service.all.group_by(&:project_id).each_with_object({}) do |row, memo|
        memo[row[0]] = row[1]
      end

      @project_id2farm_name = @project_farm_service.all.each_with_object({}) do |project_farm, memo|
        memo[project_farm.project_id] = project_farm.farm_name
      end

      erb :list_services
    end

    get '/service/register' do
      erb :register_service
    end

    post '/service/register' do
      @service_service.insert(name: params[:name])
      redirect '/service/'
    end

    get '/service/:service_id' do
      @service = @service_service.find(id: params[:service_id])
      @service_id2projects = @project_service.all.group_by(&:service_id).each_with_object({}) do |row, memo|
        memo[row[0]] = row[1]
      end

      @project_id2exporters = @project_exporter_service.all.group_by(&:project_id).each_with_object({}) do |row, memo|
        memo[row[0]] = row[1]
      end

      @project_id2farm_name = @project_farm_service.all.each_with_object({}) do |project_farm, memo|
        memo[project_farm.project_id] = project_farm.farm_name
      end
      erb :show_service
    end

    post '/service/:service_id/delete' do
      @service_service.delete(id: params[:service_id])
      redirect back
    end

    get '/service/:service_id/rule' do
      @service = @service_service.find(id: params[:service_id])
      @rules = @rule_service.find_by_service_id(service_id: @service.id)
      erb :show_rule
    end
  end
end
