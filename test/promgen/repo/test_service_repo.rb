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
require 'promgen/repo/service_repo'

class TestServiceRepo < Promgen::Test
  def setup
    super
  end

  def test_insert
    row = @app.service_repo.insert(name: 'foo')
    assert_equal 'foo', row.name
  end

  def test_find
    row = @app.service_repo.insert(name: 'foo')
    row2 = @app.service_repo.find(id: row.id)
    assert_equal row.id, row2.id
  end

  def test_all
    @app.service_repo.insert(name: 'foo')
    @app.service_repo.insert(name: 'bar')
    assert_equal 2, @app.service_repo.all.length
  end

  def test_delete
    service = @app.service_repo.insert(name: 'foo')
    project = @factory.project(service_id: service.id)
    farm = @factory.farm(name: 'foo')
    @app.project_farm_repo.link(
      project_id: project.id,
      server_directory_id: @app.server_directory_repo.find_db.id,
      farm_name: farm.name
    )

    @app.service_repo.delete(id: service.id)
    assert_nil @app.service_repo.find(id: service.id)
  end
end
