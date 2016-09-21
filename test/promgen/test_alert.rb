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
ENV['RACK_ENV'] = 'test'

require 'test/unit'
require 'logger'
require 'rack/test'
require 'webmock/test_unit'
require 'json'

require 'promgen'
require 'promgen/test'

class TestAlert < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.alert
  end

  def test_alert
    @app.project_repo.insert(service_id: @factory.service.id, name: 'mywebapp', hipchat_channel: '#foo')

    stub_request(:post, 'http://ikachan.localhost/notice')
      .to_return(status: 200, body: '', headers: {})

    post '/', JSON.generate(alerts: [
                              {
                                status: 'resolved',
                                labels: {
                                  alertname: 'InstanceDown',
                                  service: 'myservice',
                                  project: 'mywebapp',
                                  job: 'node',
                                  instance: 'testhost.localhost:9100',
                                  farm: 'foo-web'
                                },
                                generatorURL: 'http://prom.localhost/',
                                annotations: {
                                  description: 'testhost.localhost:9100 of job node has been down for more than 5 minutes.',
                                  summary: 'Instance testhost.localhost:9100 down'
                                }
                              }
                            ])

    @app.logger.info("response: #{last_response}")
    assert_equal 200, last_response.status
    assert_requested :post, 'http://ikachan.localhost/notice',
                     body: { 'channel' => '#foo',
                             'message' => %(
                                InstanceDown foo-web testhost.localhost:9100 node resolved
                                Instance testhost.localhost:9100 down
                                testhost.localhost:9100 of job node has been down for more than 5 minutes.

                                Prometheus: http://prom.localhost/
                                Alert Manager:
                                ).strip.gsub(/^ +/, ''),
                             'nickname' => 'promgen', 'color' => 'green' },
                     times: 1
  end

  def test_ikachan_alert_with_hipchat_privmsg
    ENV['HIPCHAT_PRIVMSG'] = '1'
    @app.project_repo.insert(service_id: @factory.service.id, name: 'mywebapp', hipchat_channel: '#foo')

    stub_request(:post, 'http://ikachan.localhost/privmsg')
      .to_return(status: 200, body: '', headers: {})

    post '/', JSON.generate(alerts: [
                              {
                                status: 'resolved',
                                labels: {
                                  alertname: 'InstanceDown',
                                  service: 'myservice',
                                  project: 'mywebapp',
                                  job: 'node',
                                  instance: 'testhost.localhost:9100',
                                  farm: 'foo-web'
                                },
                                generatorURL: 'http://prom.localhost/',
                                annotations: {
                                  description: 'testhost.localhost:9100 of job node has been down for more than 5 minutes.',
                                  summary: 'Instance testhost.localhost:9100 down'
                                }
                              }
                            ])

    @app.logger.info("response: #{last_response}")
    assert_equal 200, last_response.status
    assert_requested :post, 'http://ikachan.localhost/privmsg',
                     body: { 'channel' => '#foo',
                             'message' => %(
                                InstanceDown foo-web testhost.localhost:9100 node resolved
                                Instance testhost.localhost:9100 down
                                testhost.localhost:9100 of job node has been down for more than 5 minutes.

                                Prometheus: http://prom.localhost/
                                Alert Manager:
                                ).strip.gsub(/^ +/, ''),
                             'nickname' => 'promgen', 'color' => 'green' },
                     times: 1
  end

  def test_webhook_alert
    @app.project_repo.insert(service_id: @factory.service.id, name: 'mywebapp', webhook_url: 'http://webhook.localhost')

    stub_request(:post, 'http://webhook.localhost')
      .to_return(status: 200, body: '', headers: {})

    payload = {
      status: 'resolved',
      labels: {
        alertname: 'InstanceDown',
        service: 'myservice',
        project: 'mywebapp',
        job: 'node',
        instance: 'testhost.localhost:9100',
        farm: 'foo-web'
      },
      generatorURL: 'http://prom.localhost/',
      annotations: {
        description: 'testhost.localhost:9100 of job node has been down for more than 5 minutes.',
        summary: 'Instance testhost.localhost:9100 down'
      }
    }

    post '/', JSON.generate(alerts: [payload])

    @app.logger.info("response: #{last_response}")
    assert_equal 200, last_response.status

    assert_requested :post, 'http://webhook.localhost',
                     body: payload,
                     headers: {
                       'X-Promgen-Webhook-Type' => 'alert',
                       'Content-Type' => 'application/json'
                     },
                     times: 1
  end
end
