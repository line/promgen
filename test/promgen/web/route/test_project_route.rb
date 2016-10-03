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
require 'promgen/web/route/project_route'

class TestProjectRoute < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_project_create
    get "/service/#{@factory.service.id}/project/create"
    assert_equal 200, last_response.status
  end

  def test_project_create_post
    service = @factory.service

    post "/service/#{service.id}/project/create",
         'name' => 'hoge',
         'hipchat_channel' => '#foo',
         'mail_address' => 'a@a.localhost',
         'webhook_url' => 'http://webhook.localhost',
         'line_notify_access_token' => 'test_line_notify_access_token'

    assert_equal [
      { id: 1,
        service_id: service.id,
        name: 'hoge',
        hipchat_channel: '#foo',
        mail_address: 'a@a.localhost',
        webhook_url: 'http://webhook.localhost',
        line_notify_access_token: 'test_line_notify_access_token' }
    ], @app.project_repo.all.map(&:values)

    assert_equal 302, last_response.status
  end

  def test_project_show
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'foo')
    get "/project/#{project_id}"

    assert_equal 200, last_response.status
    assert_match(/foo/, last_response.body)

    farm = @factory.farm(name: 'iii-ALPHA')
    @app.project_farm_repo.link(project_id: project_id, farm_name: farm.name, server_directory_id: @app.server_directory_repo.find_db.id)

    get "/project/#{project_id}"
    assert_equal 200, last_response.status
    assert_match(/iii-ALPHA/, last_response.body)
  end

  def test_project_update
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'foo')
    get "/project/#{project_id}/update"

    assert_equal 200, last_response.status
    assert_match(/foo/, last_response.body)
  end

  def test_project_update_post
    service = @factory.service
    project_id = @app.project_repo.insert(service_id: service.id, name: 'foo')
    post "/project/#{project_id}/update",
         'name' => 'hoge',
         'hipchat_channel' => '#foo',
         'mail_address' => 'a@a.localhost',
         'webhook_url' => 'http://webhook.localhost',
         'line_notify_access_token' => 'test_line_notify_access_token'

    assert_equal [
      { id: 1, name: 'hoge', hipchat_channel: '#foo', mail_address: 'a@a.localhost', service_id: service.id, webhook_url: 'http://webhook.localhost', line_notify_access_token: 'test_line_notify_access_token' }
    ], @app.project_repo.all.map(&:values)

    assert_equal 302, last_response.status
  end

  def test_project_link
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'foo')
    server_directory = @app.server_directory_repo.find_db
    get "/project/#{project_id}/link/#{server_directory.id}"

    assert_equal 200, last_response.status
  end

  def test_project_link_post
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'foo')
    farm = @factory.farm(name: 'iii-ALPHA')
    server_directory = @app.server_directory_repo.find_db
    post "/project/#{project_id}/link/#{server_directory.id}",
         'farm_name' => farm.name

    assert_equal 302, last_response.status
    assert_equal [
      { farm_name: 'iii-ALPHA', id: 1, project_id: 1, server_directory_id: 1 }
    ], @app.project_farm_repo.all.map(&:values)
  end

  def test_project_unlink_post
    project_id = @app.project_repo.insert(service_id: @factory.service.id, name: 'foo')
    farm = @factory.farm(name: 'iii-ALPHA')
    @app.project_farm_repo.link(
      project_id: project_id,
      farm_name: farm.name,
      server_directory_id: @app.server_directory_repo.find_db.id
    )
    @app.project_exporter_repo.register(project_id: project_id, port: 7777, job: 'bar')

    post "/project/#{project_id}/unlink/#{farm.id}"

    assert_equal 0, @app.project_farm_repo.all.length
    assert_equal 302, last_response.status
  end

  def test_project_delete_post
    project_id = @factory.project.id
    farm = @factory.farm(name: 'iii-ALPHA')
    @app.project_farm_repo.link(project_id: project_id, farm_name: farm.name, server_directory_id: @app.server_directory_repo.find_db.id)
    @app.project_exporter_repo.register(project_id: project_id, port: 7777, job: 'bar')

    post "/project/#{project_id}/delete"

    assert_equal nil, @app.project_repo.find(id: project_id)
    assert_equal false, @app.project_farm_repo.linked?(
      project_id: project_id,
      farm_name: farm.name,
      server_directory_id: @app.server_directory_repo.find_db.id
    )
    assert_equal [], @app.project_exporter_repo.find_by_project_id(project_id: project_id)
    assert_equal 302, last_response.status
  end
end
