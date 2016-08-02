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
      class Webhook
        def initialize(logger:, project_repo:)
          @logger = logger
          @project_repo = project_repo
        end

        def info
          'Webhook: enabled'
        end

        def send(data)
          data['alerts'].each do |alert|
            labels = alert['labels']
            project = @project_repo.find_by_name(name: labels['project'])
            if project && project.webhook_url
              webhook_url = project.webhook_url
              send_webhook(webhook_url, alert)
            else
              @logger.info "project:'#{labels['project']}' doesn't have a webhook configuration"
            end
          end
        end

        def send_webhook(webhook_url, payload)
          @logger.info "Sending webhook to #{webhook_url}"

          uri = URI.parse(webhook_url)
          request = Net::HTTP::Post.new(
            uri,
            'Content-Type' => 'application/json',
            'X-Promgen-Webhook-Type' => 'alert'
          )
          request.body = payload.to_json

          Net::HTTP.new(uri.host, uri.port).start do |http|
            resp = http.request(request)
            @logger.info("Sent webhook: #{webhook_url} : #{resp}")
          end
        end

        private :send_webhook
      end
    end
  end
end
