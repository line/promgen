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

class TestFarmService < Promgen::Test
  def test_find_or_create
    farm1 = @app.farm_service.find_or_create(name: 'hoge-foo')
    farm2 = @app.farm_service.find_or_create(name: 'hoge-foo')

    assert_equal farm1.id, farm2.id
  end

  def test_update
    project = @factory.project()
    farm = @factory.farm()
    @app.project_farm_repo.link(farm_name: farm.name, project_id: project.id, server_directory_id: @app.server_directory_repo.find_db.id)

    @app.farm_service.update(id: farm.id, name: 'John')
    updated = @app.farm_repo.find(id: farm.id)
    assert_equal 'John', updated.name

    project_farm = @app.project_farm_repo.find_by_project_id(project_id: project.id)
    assert_equal 'John', project_farm.farm_name
  end
end
