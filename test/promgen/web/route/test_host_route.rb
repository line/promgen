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

require 'promgen/test'

class TestWebRouteFarm < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_add_host
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'john')
    farm = @factory.farm(name: 'iii-ALPHA')
    get "/project/#{project_id}/farm/#{farm.id}/host/add"
    assert_equal 200, last_response.status
  end

  def test_add_host_post
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'john')
    farm = @factory.farm(name: 'iii-ALPHA')

    post "/project/#{project_id}/farm/#{farm.id}/host/add",
         'names' => "hogehoge-1\nhogehoge-2\n# hogehoge\nhogehoge-3"

    assert_equal 302, last_response.status

    assert_equal [
      { farm_id: farm.id, name: 'hogehoge-1' },
      { farm_id: farm.id, name: 'hogehoge-2' },
      { farm_id: farm.id, name: 'hogehoge-3' }
    ], @app.host_repo.all.map { |row| { farm_id: row.farm_id, name: row.name } }
  end

  def test_delete
    project = @factory.project
    farm = @factory.farm
    @factory.project_farm(project_id: project.id, farm_name: farm.name)
    host = @factory.host(farm_id: farm.id)

    post "/project/#{project.id}/farm/#{farm.id}/host/#{host.name}/delete"

    assert_nil @app.host_repo.find(id: host.id)
  end
end
