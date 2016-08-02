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
require 'promgen/test'

class TestWebRouteRuleController < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_rule_delete
    rule = @app.rule_repo.register(
      service_id: service('hoge-service'),
      alert_clause: 'InstanceDown',
      if_clause: 'up == 0',
      for_clause: '5m',
      labels_clause: 'severity = "page"',
      annotations_clause: 'summary = "Instance {{ $labels.instance }} down"'
    )
    post "/service/#{service('hoge-service')}/rule/#{rule.id}/delete"
    assert_equal 302, last_response.status
  end

  def service(name)
    if @app.db[:service].where(name: name).count == 0
      @app.db[:service].insert(name: name)
    end
    @app.db[:service].where(name: name).first[:id]
  end
  private :service
end
