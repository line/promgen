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

class TestProjectExporterRoute < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_register
    project = @factory.project

    get "/project/#{project.id}/exporter/register"

    assert_equal 200, last_response.status
  end

  def test_register_post
    project = @factory.project

    post "/project/#{project.id}/exporter/register",
         port: 9010,
         job: 'node'

    assert_equal 302, last_response.status

    exporters = @app.project_exporter_service.all
    assert_equal 1, exporters.length
    assert_equal 'node', exporters[0].job
    assert_equal 9010, exporters[0].port
    assert_nil exporters[0].path
  end

  def test_register_with_path_post
    project = @factory.project

    post "/project/#{project.id}/exporter/register",
         port: 9010,
         job: 'node',
         path: '/foo'

    assert_equal 302, last_response.status

    exporters = @app.project_exporter_service.all
    assert_equal 1, exporters.length
    assert_equal 'node', exporters[0].job
    assert_equal 9010, exporters[0].port
    assert_equal '/foo', exporters[0].path
  end

  def test_delete
    project = @factory.project
    project_exporter = @factory.project_exporter(project_id: project.id)

    post "/project/#{project.id}/exporter/#{project_exporter.port}/delete",
         path: project_exporter.path

    assert_equal 302, last_response.status
    assert_equal 0, @app.db[:project_exporter].where(id: project_exporter.id).count
  end
end
