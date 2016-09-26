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
require 'json'

class Promgen
  class ConfigWriter
    # @param [Promgen::ServerLoader::Base] server_directory_repo
    def initialize(logger:, path:, host_repo:, prometheus:, project_repo:, server_directory_repo:, config:)
      raise ArgumentError, 'Destination path must not be null' unless path
      @logger = logger
      @destpath = path
      @host_repo = host_repo
      @prometheus = prometheus
      @project_repo = project_repo
      @server_directory_repo = server_directory_repo
      @notify = config[:config_writer][:notify]
    end

    def render
      JSON.generate(render_data, indent: '  ', object_nl: "\n", array_nl: "\n")
    end

    def render_data
      # {:port=>3251, :job=>"hoge", :project=>"myproj", :farm=>"my-app", :host=>"example.localhost", :service=>"my-service"}
      @project_repo.find_exporters.map do |row|
        repo = @server_directory_repo.find(
          id: row[:server_directory_id]
        )
        row[:hosts] = repo.find_hosts(farm_name: row[:farm])
        row
      end.group_by do |row|
        {
          service: row[:service],
          project: row[:project],
          farm: row[:farm],
          job: row[:job]
        }.merge(row[:path] ? { __metrics_path__: row[:path] } : {})
      end.map do |row|
        {
          targets: row[1].map do |r|
            r[:hosts].map do |host|
              "#{host}:#{r[:port]}"
            end
          end.flatten,
          labels: row[0]
        }
      end
    end

    def write(notify: true)
      @logger.info("Writing #{@destpath}")
      tmp = @destpath + '.tmp'
      File.write(tmp, render)
      File.rename(tmp, @destpath)

      if notify
        @notify.each do |url|
          uri = URI(url)
          res = Net::HTTP.post_form(uri, {})
          @logger.info("Posted notification to: #{uri}: #{res.body}")
        end
      end

      @prometheus.reload
    end
  end
end
