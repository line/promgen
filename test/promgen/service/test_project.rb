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
require 'promgen/test'

class TestProjectService < Promgen::Test
  def test_delete
    project_id = @factory.project.id
    farm = @factory.farm(name: 'iii-ALPHA')
    @app.project_farm_repo.link(project_id: project_id, farm_name: farm.name, server_directory_id: @app.server_directory_repo.find_db.id)
    @app.project_exporter_repo.register(project_id: project_id, port: 7777, job: 'bar')

    @app.project_service.delete(id: project_id)

    assert_equal nil, @app.project_repo.find(id: project_id)
    assert_equal false, @app.project_farm_repo.linked?(
      project_id: project_id,
      farm_name: farm.name,
      server_directory_id: @app.server_directory_repo.find_db.id
    )
    assert_equal [], @app.project_exporter_repo.find_by_project_id(project_id: project_id)
    assert_equal [], @app.project_exporter_repo.find_by_project_id(project_id: project_id)
  end
end
