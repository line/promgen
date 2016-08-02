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

class TestStatus < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_service_list
    project = @factory.project
    @factory.project_exporter(project_id: project.id)
    @factory.project_farm(project_id: project.id)

    get '/service/'
    assert_equal 200, last_response.status
  end

  def test_register
    get '/service/register'
  end

  def test_register_post
    post '/service/register',
         name: 'foo'

    assert_equal 302, last_response.status

    services = @app.service_service.all
    assert_equal 1, services.length
    assert_equal 'foo', services[0].name
  end

  def test_service_delete_post
    service = @factory.service

    post "/service/#{service.id}/delete"

    assert_equal 302, last_response.status
  end
end
