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
require 'mail'

class Promgen
  class Alert
    class Sender
      class MailNotify
        def initialize(smtp_server:, logger:, project_repo:)
          @smtp_server = smtp_server
          @logger = logger
          @project_repo = project_repo
        end

        def info
          "mail: #{@smtp_server}"
        end

        def send(data)
          data['alerts'].each do |alert|
            labels = alert['labels']
            project = @project_repo.find_by_name(name: labels['project'])
            if project && project.mail_address
              subject = "#{alert['labels']['alertname']} #{alert['labels']['farm']} #{alert['labels']['instance']} #{alert['labels']['job']} #{alert['status']}"
              body = %(
#{alert['annotations']['summary']}
#{alert['annotations']['description']}

Prometheus: #{alert['generatorURL']}
Alert Manager: #{data['externalURL']}
)
              send_mail(project.mail_address, subject, body)
            else
              @logger.info "project:'#{labels['project']}' doesn't have a mail address configuration"
            end
          end
        end

        def send_mail(mail_address, subject, body)
          @logger.info "Sending mail message: #{mail_address} #{subject} #{body}"
          m = Mail.new
          options = { address: @smtp_server }
          m.from = 'promgen'
          m.to = mail_address
          m.subject = subject
          m.body = body
          m.delivery_method(:smtp, options)
          m.deliver
        end
      end
    end
  end
end
