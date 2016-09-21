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

require 'promgen'
require 'promgen/test'

class TestConfigWriter < Promgen::Test
  def test_render_data
    @app.server_directory_repo.find_db
    service = @app.service_repo.insert(
      name: 'foo'
    )
    project_id = @app.project_repo.insert(
      service_id: service.id,
      name: 'TestProj'
    )
    farm = @factory.farm(name: 'MyFarm')
    assert_not_nil farm

    @factory.host(farm_id: farm.id, name: 'MYHOST1')
    @factory.host(farm_id: farm.id, name: 'MYHOST2')

    @app.project_farm_repo.link(
      project_id: project_id,
      farm_name: farm.name,
      server_directory_id: @app.server_directory_repo.find_db.id
    )
    @app.project_exporter_repo.register(project_id: project_id, port: 9010, job: 'node')
    @app.project_exporter_repo.register(project_id: project_id, port: 9020, job: 'nginx', path: '/foo')

    data = @app.config_writer.render_data
    assert_equal [
      {
        labels: {
          service: 'foo',
          farm: 'MyFarm',
          job: 'node',
          project: 'TestProj'
        },
        targets: ['MYHOST1:9010', 'MYHOST2:9010']
      },
      {
        labels: {
          __metrics_path__: '/foo',
          service: 'foo',
          farm: 'MyFarm',
          job: 'nginx',
          project: 'TestProj'
        },
        targets: ['MYHOST1:9020', 'MYHOST2:9020']
      }
    ], data
  end
end
