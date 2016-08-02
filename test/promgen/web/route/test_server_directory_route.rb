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

class TestServerDirectoryRoute < Promgen::Test
  include Rack::Test::Methods

  def app
    @app.web
  end

  def test_server_directory_list
    @app.server_directory_repo.find_db

    get '/server_directory/'
    assert_equal 200, last_response.status
  end

  def test_server_directory_register
    get '/server_directory/register'

    assert_equal 200, last_response.status
  end

  def test_server_directory_register_post
    post '/server_directory/register',
         type: 'Promgen::ServerDirectory::PMC',
         url: 'http://pmc.localhost/',
         cache_lifetime: '30s'

    assert_equal 302, last_response.status
  end

  def test_server_directory_update
    sd = @app.server_directory_repo.find_db

    get "/server_directory/#{sd.id}/update"

    assert_equal 200, last_response.status
  end

  def test_server_directory_delete
    sd = @app.server_directory_repo.find_db

    post "/server_directory/#{sd.id}/delete"

    assert_equal 302, last_response.status

    assert @app.server_directory_repo.find(id: sd.id).nil?
  end

  def test_server_directory_get_hosts_of_farm
    farm = @factory.farm(name: 'aaa-BETA')
    sd = @app.server_directory_repo.find_db

    get "/server_directory/#{sd.id}/farm_hosts?farm_name=#{farm.name}"

    assert_equal 200, last_response.status
  end
end
