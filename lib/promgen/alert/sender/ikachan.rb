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
      class Ikachan
        def initialize(url:, logger:, project_repo:)
          @url = url.gsub(%r{/$}, '') + '/' + (ENV['HIPCHAT_PRIVMSG'] ? 'privmsg' : 'notice')
          @logger = logger
          @project_repo = project_repo
        end

        def info
          "ikachan: #{@url}"
        end

        def send(data)
          data['alerts'].each do |alert|
            labels = alert['labels']
            project = @project_repo.find_by_name(name: labels['project'])
            if project && project.hipchat_channel
              subject = "#{alert['labels']['alertname']} #{alert['labels']['farm']} #{alert['labels']['instance']} #{alert['labels']['job']} #{alert['status']}"
              body = "#{alert['annotations']['summary']}\n#{alert['annotations']['description']}"
              if alert['status'] == 'resolved'
                ikasan(project.hipchat_channel, subject + "\n" + body, 'green')
              else
                ikasan(project.hipchat_channel, subject + "\n" + body, 'red')
              end
            else
              @logger.info "project:'#{labels['project']}' doesn't have a hipchat channel configuration"
            end
          end
        end

        def ikasan(channel, message, color)
          @logger.info "Sending ikachan message: #{channel} #{message} #{color}"

          uri = URI.parse(@url)
          request = Net::HTTP::Post.new(uri.path)
          request.set_form_data(
            channel: channel,
            message: message,
            nickname: 'promgen',
            color: color
          )
          Net::HTTP.new(uri.host, uri.port).start do |http|
            resp = http.request(request)
            @logger.info("Sent request: #{channel} #{message}: #{resp}")
          end
        end
      end
    end
  end
end
