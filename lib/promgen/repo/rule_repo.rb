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
# configuration for prometheus

require 'promgen/rule'

class Promgen
  class Repo
    class RuleRepo
      def initialize(logger:, db:)
        raise ArgumentError, 'DB must not be null' if db.nil?
        @logger = logger
        @db = db
      end

      def find_by_service_id(service_id:)
        @db[:rule].where(service_id: service_id).order(:alert_clause).map do |e|
          Promgen::Rule.new(e)
        end
      end

      def find(id:)
        @db[:rule].where(id: id).map do |e|
          Promgen::Rule.new(e)
        end.first
      end

      def register(service_id:, alert_clause:, if_clause:, for_clause:, labels_clause:, annotations_clause:)
        raise ArgumentError, 'alert_clause must not be null' if alert_clause.nil?
        raise ArgumentError, 'alert_clause must not be empty' if alert_clause == ''
        raise ArgumentError, 'if_clause must not be null' if if_clause.nil?
        raise ArgumentError, 'if_clause must not be empty' if if_clause == ''

        @logger.info "Registering #{service_id}, #{alert_clause}, #{if_clause}, #{for_clause}, #{labels_clause}, #{annotations_clause}"
        rule = @db[:rule].where(service_id: service_id, alert_clause: alert_clause).first
        if rule.nil?
          id = @db[:rule].insert(service_id: service_id, alert_clause: alert_clause, if_clause: if_clause, for_clause: for_clause, labels_clause: labels_clause, annotations_clause: annotations_clause)
          find(id: id)
        else
          rule
        end
      end

      def update(id:, service_id:, alert_clause:, if_clause:, for_clause:, labels_clause:, annotations_clause:)
        raise ArgumentError, 'alert_clause must not be null' if alert_clause.nil?
        raise ArgumentError, 'alert_clause must not be empty' if alert_clause == ''
        raise ArgumentError, 'if_clause must not be null' if if_clause.nil?
        raise ArgumentError, 'if_clause must not be empty' if if_clause == ''

        @db[:rule].where(id: id).update(
          service_id: service_id,
          alert_clause: alert_clause,
          if_clause: if_clause,
          for_clause: for_clause,
          labels_clause: labels_clause,
          annotations_clause: annotations_clause
        )
      end

      def all
        @db[:rule].order(:service_id).map do |e|
          Promgen::Rule.new(e)
        end
      end

      def find_rules
        @db['
            SELECT rule.alert_clause
              , rule.if_clause
              , rule.for_clause
              , rule.labels_clause
              , rule.annotations_clause
              , service.id service_id
              , service.name service_name
            FROM rule
              INNER JOIN service ON (rule.service_id=service.id)
          '].all
      end

      def delete(rule_id:)
        @logger.info "removing rule id:#{rule_id}"

        @db[:rule].where('id=?', rule_id).delete
      end

      def delete_by_service_id(service_id:)
        @db[:rule].where(service_id: service_id).delete
      end
    end
  end
end
