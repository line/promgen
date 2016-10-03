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

class Promgen
  class Alert
    class Sender
      class LineNotify
        def initialize(url:, logger:, project_repo:)
          @url = url
          @logger = logger
          @project_repo = project_repo
        end

        def info
          "LineNotify: #{@line_notify_access_token}"
        end

        def send(data)
          data['alerts'].each do |alert|
            labels = alert['labels']
            project = @project_repo.find_by_name(name: labels['project'])
            if project && project.line_notify_access_token
              subject = "#{alert['labels']['alertname']} #{alert['labels']['farm']} #{alert['labels']['instance']} #{alert['labels']['job']} #{alert['status']}"
              body = %(
                #{alert['annotations']['summary']}
                #{alert['annotations']['description']}

                Prometheus: #{alert['generatorURL']}
                Alert Manager: #{data['externalURL']}
                ).strip.gsub(/^ +/, '')
              send_linenotify(project.line_notify_access_token, subject + "\n" + body)
            else
              @logger.info "project:'#{labels['project']}' doesn't have a access token configuration"
            end
          end
        end

        def send_linenotify(line_notify_access_token, message)
          @logger.info "Sending line message: #{line_notify_access_token} #{message}"

          uri = URI.parse(@url)
          request = Net::HTTP::Post.new(uri.path)
          request['Authorization'] = "Bearer #{line_notify_access_token}"
          request['Content­-Type'] = 'application/x-www-form-urlencoded'
          request.set_form_data(
            message: message
          )
          http = Net::HTTP.new(uri.host, uri.port)
          http.use_ssl = true
          http.verify_mode = OpenSSL::SSL::VERIFY_NONE
          resp = http.request(request)
          @logger.info("Sent request: #{line_notify_access_token} #{message}: #{resp}")
        end
      end
    end
  end
end
