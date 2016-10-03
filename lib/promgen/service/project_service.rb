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
    class ProjectService
      extend Forwardable

      def initialize(logger:, project_repo:, config_writer:, rule_writer:)
        @logger = logger
        @project_repo = project_repo
        @config_writer = config_writer
        @rule_writer = rule_writer
      end

      def_delegators :@project_repo, :all, :insert, :update, :find, :find_by_name, :find_exporters, :update_line_notify_access_token

      def delete(*args)
        @project_repo.delete(*args)
        @config_writer.write
        @rule_writer.write
      end
    end
  end
end
