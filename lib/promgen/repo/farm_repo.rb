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
require 'net/http'
require 'uri'
require 'thread'

require 'promgen/host'
require 'promgen/farm'

class Promgen
  class Repo
    class FarmRepo
      def initialize(logger:, db:)
        @logger = logger
        @db = db
      end

      def valid_name?(name)
        name =~ /^[0-9a-zA-Z._-]+$/
      end

      # @return [Promgen::Farm]
      def find(id:)
        @db[:farm].where(id: id).map do |e|
          Promgen::Farm.new(e)
        end.first
      end

      def find_by_name(name:)
        @db[:farm].where(name: name).map do |e|
          Promgen::Farm.new(e)
        end.first
      end

      def insert(name:)
        @db[:farm].insert(name: name)
      end

      def all
        @db[:farm].order(Sequel.desc(:id)).map do |e|
          Promgen::Farm.new(e)
        end
      end

      def update(id:, name:)
        raise ArgumentError, "Invalid name: #{name}" unless valid_name?(name)
        @db[:farm].where(id: id).update(name: name)
      end

      def find_by_project_id(project_id:)
        @db['SELECT farm.*
            FROM farm
              INNER JOIN project_farm ON (project_farm.farm_name=farm.name)
            WHERE project_farm.project_id=?
            ORDER BY project_farm.id
            ', project_id].map do |e|
          Promgen::Farm.new(e)
        end
      end
    end
  end
end
