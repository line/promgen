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
require 'promgen/repo/project_repo'

class TestProject < Promgen::Test
  setup do
    @repo = @app.project_repo
  end

  def test_create_and_lookup
    project_name = 'project-test'
    service = @app.service_repo.insert(name: 'foo')
    inserted_project_id = @repo.insert(service_id: service.id, name: project_name)

    project1 = @repo.find(id: inserted_project_id)
    project2 = @repo.find_by_name(name: project_name)

    assert_equal inserted_project_id, project1.id
    assert_equal project1.id, project2.id
  end

  def test_deletion
    inserted_project_id = @repo.insert(service_id: @factory.service.id, name: 'project-test')

    deleted_cnt = @repo.delete(id: inserted_project_id)
    assert_equal 1, deleted_cnt

    retrieved = @repo.find(id: inserted_project_id)
    assert_equal nil, retrieved
  end

  def test_find_exporters
    project_name = 'project-test'
    service = @app.service_repo.insert(name: 'foo')
    inserted_project_id = @repo.insert(service_id: service.id, name: project_name)
    @app.project_exporter_repo.register(project_id: inserted_project_id, port: 9100, job: 'node', path: '/foo')

    @repo.find_exporters.map do |row|
      assert_equal 'foo', row[:service]
      assert_equal 'project-test', row[:project]
      assert_equal 9100, row[:port]
      assert_equal 'node', row[:job]
      assert_equal '/foo', row[:path]
    end
  end
end
