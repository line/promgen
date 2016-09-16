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

require 'promgen/project_exporter'

class Promgen
  class Repo
    class ProjectExporterRepo
      def initialize(logger:, db:)
        raise ArgumentError, 'DB must not be null' if db.nil?
        @logger = logger
        @db = db
      end

      def find(id:)
        @db[:project_exporter].where(id: id).map do |e|
          Promgen::ProjectExporter.new(e)
        end.first
      end

      def find_by_project_id(project_id:)
        @db['SELECT project_exporter.*
            FROM project_exporter
            WHERE project_exporter.project_id=?', project_id].map do |e|
          Promgen::ProjectExporter.new(e)
        end
      end

      def all
        @db[:project_exporter].order(:project_id, :port).map do |e|
          Promgen::ProjectExporter.new(e)
        end
      end

      def register(project_id:, port:, job:, path: nil)
        raise ArgumentError, 'port must not be null' if port.nil?
        raise ArgumentError, 'port must not be empty' if port == ''
        raise ArgumentError, 'job must not be null' if job.nil?
        raise ArgumentError, 'job must not be empty' if job == ''

        port = port.to_i

        @logger.info "Registering #{project_id}, #{port}, #{job}, #{path}"
        if @db[:project_exporter].where(project_id: project_id, port: port, path:path).count == 0
          @db[:project_exporter].insert(project_id: project_id,
                                        port: port,
                                        job: job,
                                        path: path)
        end
      end

      def delete(project_id:, port:, path:)
        @logger.info "removing #{port}, #{path} from #{project_id}"

        @db[:project_exporter].where(project_id: project_id, port: port, path: path).delete
      end

      def delete_by_project_id(project_id:)
        @db[:project_exporter].where(project_id: project_id).delete
      end
    end
  end
end
