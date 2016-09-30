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
require 'promgen/project'

class Promgen
  class Repo
    class ProjectRepo
      def initialize(db:, logger:)
        @db = db
        @logger = logger
      end

      def all
        @db[:project].order(:name).map do |e|
          Promgen::Project.new(e)
        end
      end

      def insert(service_id:, name:, hipchat_channel: nil, mail_address: nil, webhook_url: nil, access_token: nil)
        raise ArgumentError, 'service_id must not be null' if service_id.nil?
        @db[:project].insert(
          service_id: service_id,
          name: name,
          hipchat_channel: hipchat_channel,
          mail_address: mail_address,
          webhook_url: webhook_url,
          access_token: access_token
        )
      end

      def update(project_id:, name:, hipchat_channel:, mail_address:, webhook_url:, access_token:)
        @db[:project].where(id: project_id).update(
          name: name,
          hipchat_channel: hipchat_channel,
          mail_address: mail_address,
          webhook_url: webhook_url,
          access_token: access_token
        )
      end

      # @return [Promgen::Project]
      def find(id:)
        @db[:project].where(id: id).map do |e|
          Promgen::Project.new(e)
        end.first
      end

      def find_by_name(name:)
        @db[:project].where(name: name).map do |e|
          Promgen::Project.new(e)
        end.first
      end

      def delete(id:)
        @db[:project].where(id: id).delete
      end

      def find_exporters
        @db['
            SELECT project_exporter.port
              , project_exporter.job
              , project_exporter.path
              , project.name project
              , project_farm.farm_name farm
              , project_farm.server_directory_id server_directory_id
              , service.name service
            FROM project_exporter
              INNER JOIN project_farm ON (project_farm.project_id=project_exporter.project_id)
              INNER JOIN project ON (project.id=project_farm.project_id)
              INNER JOIN service ON (service.id=project.service_id)
          '].all
      end
    end
  end
end
