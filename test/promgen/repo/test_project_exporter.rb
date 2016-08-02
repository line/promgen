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
require 'promgen/repo/project_exporter_repo'

class TestProjectExporter < Promgen::Test
  def setup
    super
    @repo = @app.project_exporter_repo
    @db = @app.db
  end

  def test_register
    @repo.register(project_id: project('hoge-RELEASE'), port: 9100, job: 'node')
    assert_equal [9100], project_exporter_ports_by_project('hoge-RELEASE')
  end

  def test_find_by_farm
    @repo.register(project_id: project('aaa-RELEASE'), port: 9100, job: 'node')
    @repo.register(project_id: project('aaa-RELEASE'), port: 9200, job: 'nginx')
    @repo.register(project_id: project('bbb-RELEASE'), port: 9300, job: 'node')

    assert_equal [9100, 9200], project_exporter_ports_by_project('aaa-RELEASE')
  end

  def test_delete
    @repo.register(project_id: project('aaa-RELEASE'), port: 9100, job: 'node')
    @repo.register(project_id: project('aaa-RELEASE'), port: 9200, job: 'nginx')
    @repo.register(project_id: project('bbb-RELEASE'), port: 9100, job: 'node')

    @repo.delete(project_id: project('aaa-RELEASE'), port: 9100)

    assert_equal [9200], project_exporter_ports_by_project('aaa-RELEASE')
    assert_equal [9100], project_exporter_ports_by_project('bbb-RELEASE')
  end

  def test_delete_by_farm_id
    @repo.register(project_id: project('aaa-RELEASE'), port: 9100, job: 'node')
    @repo.register(project_id: project('aaa-RELEASE'), port: 9200, job: 'nginx')
    @repo.register(project_id: project('bbb-RELEASE'), port: 9100, job: 'node')

    @repo.delete_by_project_id(project_id: project('aaa-RELEASE'))

    assert_equal 0, @repo.find_by_project_id(project_id: project('aaa-RELEASE')).length
    assert_equal 1, @repo.find_by_project_id(project_id: project('bbb-RELEASE')).length
  end

  def project_exporter_ports_by_project(farm_name)
    @db[:project_exporter].where(project_id: project(farm_name))
                          .order(:port)
                          .map { |x| x[:port] }
  end
  private :project_exporter_ports_by_project

  def project(name)
    if @db[:project].where(name: name).count == 0
      @db[:project].insert(service_id: @factory.service.id, name: name)
    end
    @db[:project].where(name: name).first[:id]
  end
  private :project
end
