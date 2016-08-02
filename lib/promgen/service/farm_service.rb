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

require 'promgen/host'
require 'promgen/farm'

require 'forwardable'

class Promgen
  class Service
    class FarmService
      extend Forwardable

      # @param [Promgen::Repo::FarmRepo] farm_repo
      # @param [Promgen::Repo::ProjectFarmRepo] project_farm_repo
      # @param [Promgen::Repo::ServerDirectoryRepo] server_directory_repo
      def initialize(logger:, farm_repo:, db:, project_farm_repo:, server_directory_repo:)
        @logger = logger
        @farm_repo = farm_repo
        @db = db
        @project_farm_repo = project_farm_repo
        @server_directory_repo = server_directory_repo
      end

      def_delegators :@farm_repo, :find, :find_by_name, :find_or_create, :all, :find_by_project_id

      def find_or_create(name:)
        raise ArgumentError, "Invalid name: #{name}" unless @farm_repo.valid_name?(name)

        farm = @farm_repo.find_by_name(name: name)
        return farm if farm

        farm_id = @farm_repo.insert(name: name)
        @farm_repo.find(id: farm_id)
      end

      def update(id:, name:)
        @db.transaction do
          farm = @farm_repo.find(id: id)
          @farm_repo.update(id: id, name: name)
          @project_farm_repo.update_farm_name(
            orig_farm_name: farm.name,
            new_farm_name: name,
            server_directory_id: @server_directory_repo.find_db.id
          )
        end
      end
    end
  end
end
