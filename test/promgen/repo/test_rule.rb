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
require 'test/unit'
require 'sequel'
require 'logger'

require 'promgen/test'
require 'promgen/repo/rule_repo'

class TestRule < Promgen::Test
  def setup
    super
    @repo = @app.rule_repo
    @db = @app.db
  end

  def test_register
    @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    assert_equal ['InstanceDown'], rule_alerts_by_service('hoge-service')
  end

  def test_update
    rule = @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.update(id: rule.id, service_id: service('hoge-service'), alert_clause: 'InstanceDown2', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"',
                 annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    assert_equal ['InstanceDown2'], rule_alerts_by_service('hoge-service')

    rule = @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    assert_equal service('hoge-service'), rule.service_id
    assert_equal 'InstanceDown', rule.alert_clause
    assert_equal 'up == 0', rule.if_clause
    assert_equal '5m', rule.for_clause
    assert_equal 'severity = "page"', rule.labels_clause
    assert_equal 'summary = "Instance {{ $labels.instance }} down"', rule.annotations_clause

    @repo.update(id: rule.id, service_id: service('fuga-RELEASE'), alert_clause: 'InstanceDown?', if_clause: 'up != 0', for_clause: '1m', labels_clause: 'severity = "error"',
                 annotations_clause: 'summary = "Instance {{ $labels.instance }} down?"')
    rule = @repo.find(id: rule.id)
    assert_equal service('fuga-RELEASE'), rule.service_id
    assert_equal 'InstanceDown?', rule.alert_clause
    assert_equal 'up != 0', rule.if_clause
    assert_equal '1m', rule.for_clause
    assert_equal 'severity = "error"', rule.labels_clause
  end

  def test_find_by_service_id
    @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown1', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown2', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('hoge-service'), alert_clause: 'InstanceDown3', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    assert_equal %w(InstanceDown1 InstanceDown2 InstanceDown3), rule_alerts_by_service('hoge-service')
  end

  def test_delete
    a1 = @repo.register(service_id: service('aaa-RELEASE'), alert_clause: 'InstanceDown1', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('aaa-RELEASE'), alert_clause: 'InstanceDown2', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('bbb-RELEASE'), alert_clause: 'InstanceDown3', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')

    @repo.delete(rule_id: a1.id)

    assert_equal ['InstanceDown2'], rule_alerts_by_service('aaa-RELEASE')
    assert_equal ['InstanceDown3'], rule_alerts_by_service('bbb-RELEASE')
  end

  def test_delete_by_service_id
    @repo.register(service_id: service('aaa-RELEASE'), alert_clause: 'InstanceDown1', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('aaa-RELEASE'), alert_clause: 'InstanceDown2', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
    @repo.register(service_id: service('bbb-RELEASE'), alert_clause: 'InstanceDown3', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')

    @repo.delete_by_service_id(service_id: service('aaa-RELEASE'))

    assert_equal 0, @repo.find_by_service_id(service_id: service('aaa-RELEASE')).length
    assert_equal 1, @repo.find_by_service_id(service_id: service('bbb-RELEASE')).length
  end

  def rule_alerts_by_service(service_name)
    @db[:rule].where(service_id: service(service_name))
              .map { |x| x[:alert_clause] }
  end
  private :rule_alerts_by_service

  def service(name)
    if @db[:service].where(name: name).count == 0
      @db[:service].insert(name: name)
    end
    @db[:service].where(name: name).first[:id]
  end
  private :service
end
