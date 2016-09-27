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
require 'promgen/host'

class Promgen
  class Repo
    class HostRepo
      def initialize(db:)
        @db = db
      end

      def find_by_farm_id(farm_id:)
        @db[:host].where(farm_id: farm_id).order(:name).map do |e|
          Promgen::Host.new(e)
        end
      end

      def find(id:)
        @db[:host].where(id: id).map do |e|
          Promgen::Host.new(e)
        end.first
      end

      def all
        @db[:host].order(:id).map do |e|
          Promgen::Host.new(e)
        end
      end

      def insert(farm_id:, name:)
        @db[:host].insert(
          farm_id: farm_id,
          name: name
        )
      end

      def insert_multi(farm_id:, names:)
        hosts = @db[:host].where(farm_id: farm_id).map do |e|
          e[:name]
        end

        # Filter out existing hosts and duplicates
        names = names.reject { |name| hosts.include? name }.to_set

        @db[:host].import(
          [:farm_id, :name],
          names.map { |name| [farm_id, name] }
        )
      end

      def delete(id:)
        @db[:host].where(id: id).delete
      end

      def delete_by_name(name:)
        @db[:host].where(name: name).delete
      end
    end
  end
end
