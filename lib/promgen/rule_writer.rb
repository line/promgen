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
require 'tempfile'
require 'open3'

class Promgen
  class RuleWriter
    def initialize(logger:, rule_path:, promtool_path:, rule_repo:, prometheus:, config:)
      raise ArgumentError, 'Destination path must not be null' unless rule_path
      @logger = logger
      @rule_path = rule_path
      @promtool_path = promtool_path
      @rule_repo = rule_repo
      @prometheus = prometheus
      @notify = config[:rule_writer][:notify] ||= []
    end

    def nil_or_empty?(s)
      s.nil? || s.empty?
    end
    private :nil_or_empty?

    def check_rule(alert_clause:, if_clause:, for_clause:, labels_clause:, annotations_clause:)
      Tempfile.open('prom.rule') do |tmp|
        File.open(tmp.path, 'w') do |file|
          file.puts('ALERT ' + alert_clause)
          file.puts('IF ' + if_clause)
          file.puts('FOR ' + for_clause) unless nil_or_empty?(for_clause)
          file.puts('LABELS ' + labels_clause) unless nil_or_empty?(labels_clause)
          file.puts('ANNOTATIONS ' + annotations_clause) unless nil_or_empty?(annotations_clause)
        end
        check_result = Open3.capture3(@promtool_path + ' check-rules ' + tmp.path)
        return check_result[2].to_i, check_result[1].split("\n")[1]
      end
    end

    def render
      sio = StringIO.new
      @rule_repo.all.each do |row|
        sio.puts('ALERT ' + row.values[:alert_clause])
        sio.puts('IF ' + row.values[:if_clause])
        sio.puts('FOR ' + row.values[:for_clause]) unless nil_or_empty?(row.values[:for_clause])
        sio.puts('LABELS ' + row.values[:labels_clause]) unless nil_or_empty?(row.values[:labels_clause])
        sio.puts('ANNOTATIONS ' + row.values[:annotations_clause]) unless nil_or_empty?(row.values[:annotations_clause])
      end
      sio.string
    end

    def write(notify: true)
      @logger.info("Writing #{@rule_path}")
      tmp = @rule_path + '.tmp'
      File.open(tmp, 'w') do |file|
        file.puts(render)
      end
      File.rename(tmp, @rule_path)

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
