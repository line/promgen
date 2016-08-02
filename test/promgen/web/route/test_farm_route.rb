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

class TestWebRouteFarm < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_farm_register
    project_id = @factory.project.id
    get "/project/#{project_id}/farm/register"
    assert_equal 200, last_response.status
  end

  def test_farm_register_post
    project_id = @factory.project.id

    post "/project/#{project_id}/farm/register",
         'name' => 'myfarm'

    assert_equal 302, last_response.status
  end

  def test_farm_edit
    project_id = @factory.project.id
    farm = @factory.farm
    get "/project/#{project_id}/farm/#{farm.id}/edit"
    assert_equal 200, last_response.status
  end

  def test_farm_edit_post
    project_id = @factory.project.id
    farm = @factory.farm
    post "/project/#{project_id}/farm/#{farm.id}/edit",
         'name' => 'hoge'

    assert_equal 302, last_response.status

    assert_equal 'hoge', @app.farm_repo.find(id: farm.id).name
  end
end
