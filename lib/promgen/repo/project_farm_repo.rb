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
require 'promgen/project_farm'

class Promgen
  class Repo
    class ProjectFarmRepo
      def initialize(db:, logger:)
        @db = db
        @logger = logger
      end

      def link(project_id:, server_directory_id:, farm_name:)
        raise ArgumentError, 'farm name must not be null' if farm_name.nil?
        if server_directory_id.nil?
          raise ArgumentError, 'server_directory_id must not be null'
        end
        unless @db[:project_farm].where(project_id: project_id, server_directory_id: server_directory_id, farm_name: farm_name).count == 0
          return
        end

        id = @db[:project_farm].insert(
          project_id: project_id,
          server_directory_id: server_directory_id,
          farm_name: farm_name
        )
        find(id: id)
      end

      def find(id:)
        @db[:project_farm].where(id: id).map do |e|
          Promgen::ProjectFarm.new(e)
        end.first
      end

      def find_by_project_id(project_id:)
        @db[:project_farm].where(project_id: project_id).map do |e|
          Promgen::ProjectFarm.new(e)
        end.first
      end

      def find_by_farm_name(farm_name:)
        @db[:project_farm].where(farm_name: farm_name).map do |e|
          Promgen::ProjectFarm.new(e)
        end.first
      end

      def linked?(project_id:, farm_name:, server_directory_id:)
        @db[:project_farm].where(
          project_id: project_id,
          farm_name: farm_name,
          server_directory_id: server_directory_id
        ).count > 0
      end

      def unlink(project_id:, farm_name:)
        @db[:project_farm].where(
          project_id: project_id,
          farm_name: farm_name
        ).delete
      end

      def all
        @db[:project_farm].order(:id).map do |e|
          Promgen::ProjectFarm.new(e)
        end
      end

      def update_farm_name(orig_farm_name:, new_farm_name:, server_directory_id:)
        @db[:project_farm].where(farm_name: orig_farm_name, server_directory_id: server_directory_id)
                          .update(farm_name: new_farm_name)
      end
    end
  end
end
