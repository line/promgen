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
    get '/rule/' do
      @rules = @rule_service.find_rules.map
      erb :list_rule
    end

    get '/service/:service_id/rule/register' do
      @service = @service_service.find(id: params[:service_id])
      erb :register_rule
    end

    post '/service/:service_id/rule/register' do
      alert_clause = params['alert']
      if_clause = params['if']
      for_clause = params['for']
      labels_clause = params['labels']
      annotations_clause = params['annotations']

      exit_code, @err = @rule_writer.check_rule(alert_clause: alert_clause, if_clause: if_clause, for_clause: for_clause, labels_clause: labels_clause, annotations_clause: annotations_clause)
      if exit_code != 0
        erb :error
      else
        @rule_service.register(service_id: params[:service_id], alert_clause: alert_clause, if_clause: if_clause, for_clause: for_clause, labels_clause: labels_clause, annotations_clause: annotations_clause)
        @rule_writer.write

        @service = @service_service.find(id: params[:service_id])
        @audit_log_service.log(entry: "Registered rules for #{@service.name}")

        redirect "/service/#{params[:service_id]}/rule"
      end
    end

    get '/service/:service_id/rule/:rule_id/update' do
      @service = @service_service.find(id: params[:service_id])
      @rule = @rule_service.find(id: params[:rule_id])
      halt 404 unless @rule
      erb :update_rule
    end

    post '/service/:service_id/rule/:rule_id/update' do
      rule = @rule_service.find(id: params[:rule_id])
      alert_clause = params['alert']
      if_clause = params['if']
      for_clause = params['for']
      labels_clause = params['labels']
      annotations_clause = params['annotations']

      exit_code, @err = @rule_writer.check_rule(alert_clause: alert_clause, if_clause: if_clause, for_clause: for_clause, labels_clause: labels_clause, annotations_clause: annotations_clause)
      if exit_code != 0
        erb :error
      else

        @rule_service.update(id: rule.id, service_id: params[:service_id], alert_clause: alert_clause, if_clause: if_clause, for_clause: for_clause, labels_clause: labels_clause, annotations_clause: annotations_clause)
        @rule_writer.write

        @service = @service_service.find(id: params[:service_id])
        @audit_log_service.log(entry: "Updated rules for #{@service.name}")

        redirect "/service/#{params[:service_id]}/rule"
      end
    end

    post '/service/:service_id/rule/:rule_id/delete' do
      rule_id = params['rule_id']
      halt 400 if rule_id.nil?

      @rule_service.delete(rule_id: rule_id)
      @rule_writer.write

      @service = @service_service.find(id: params[:service_id])
      @audit_log_service.log(entry: "Deleted rule for #{@service.name}")

      redirect back
    end
  end
end
