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

require 'promgen'

class TestAPI < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.api
  end

  def test_api
    get '/'
    assert_equal 200, last_response.status
  end

  def test_api_config
    get '/v1/config'
    assert_equal 200, last_response.status
  end

  def test_api_project
    get '/v1/project/'
    assert_equal 200, last_response.status
  end

  def test_api_project_show
    project_id = @factory.project.id
    get "/v1/project/#{project_id}"
    assert_equal 200, last_response.status
  end

  def test_api_farm
    get '/v1/farm/'
    assert_equal 200, last_response.status
  end

  def test_api_farm_show
    farm = @factory.farm(name: 'iii-ALPHA')
    get "/v1/farm/#{farm.id}"
    assert_equal 200, last_response.status
  end

  def test_api_server_directory_list
    get '/v1/server_directory/'
    assert_equal 200, last_response.status
  end

  def test_api_server_directory_types
    get '/v1/server_directory/type/'
    assert_equal 200, last_response.status
  end
end
