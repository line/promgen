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
      class Alerta
        def initialize(alerta_url:, logger:)
          @url = alerta_url.gsub(%r{/$}, '') + '/webhooks/prometheus'
          @logger = logger
        end

        def info
          'Alerta: enabled'
        end

        def send(data)
          @logger.info "Sending Alerta to #{@url}"

          uri = URI.parse(@url)
          request = Net::HTTP::Post.new(uri, 'Content-Type' => 'application/json')
          request.body = data.to_json

          Net::HTTP.new(uri.host, uri.port).start do |http|
            resp = http.request(request)
            @logger.info("Sent Alerta: #{@url} : #{resp}")
          end
        end
      end
    end
  end
end
