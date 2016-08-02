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
require 'json'

class Promgen
  class Repo
    class ServerDirectoryRepo
      def initialize(db:, logger:, container:)
        @db = db
        @logger = logger
        @container = container
      end

      def find(id:)
        @db[:server_directory]
          .where(id: id)
          .map { |e| instantiate(e) }
          .first
      end

      def insert(type:, params:)
        raise ArgumentError, "Type shouldn't be null" if type.nil?
        unless types.map(&:to_s).include?(type.to_s)
          raise ArgumentError, "Unknown type: #{type}"
        end

        id = @db[:server_directory].insert(
          type: type.to_s,
          params: JSON.generate(params)
        )
        @db[:server_directory]
          .where(id: id)
          .map { |e| instantiate(e) }
          .first
      end

      def update(id:, params:)
        sd = find(id: id)
        params = sd.class.properties
                   .map { |r| r[:name] }
                   .each_with_object({}) { |key, memo| memo[key] = params[key] }

        @db[:server_directory]
          .where(id: id)
          .update(params: JSON.generate(params))
      end

      def find_db
        sd = find_by_type(type: Promgen::ServerDirectory::DB.to_s)
        return sd if sd

        insert(type: Promgen::ServerDirectory::DB.to_s, params: {})
      end

      def find_by_type(type:)
        @db[:server_directory]
          .where(type: type)
          .map { |e| instantiate(e) }
          .first
      end

      def all
        @db[:server_directory].order(:id).map do |e|
          instantiate(e)
        end
      end

      def delete(server_directory_id:)
        @db[:server_directory].where(id: server_directory_id).delete
      end

      def types
        Promgen::ServerDirectory.constants
                                .select { |f| f != :Base }
                                .map { |f| "Promgen::ServerDirectory::#{f}" }
                                .map { |f| Object.const_get(f) }
      end

      def instantiate(e)
        klass = Object.const_get(e[:type])
        params = JSON.parse(e[:params]).inject({}) do |memo, (k, v)|
          memo[k.to_sym] = v
          memo
        end
        @container.get_bean(
          klass,
          {
            id: e[:id]
          }.merge(params)
        )
      end
    end
  end
end
