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
require 'promgen/repo/rule_repo'

class TestServiceDirectory < Promgen::Test
  def setup
    super
    @repo = @app.server_directory_repo
    @db = @app.db
  end

  def test_insert
    @repo.insert(
      type: 'Promgen::ServerDirectory::PMC',
      params: {
        url: 'http://pmc.localhost/',
        cache_lifetime: '1h'
      }
    )

    assert_equal [
      {
        type: 'Promgen::ServerDirectory::DB'
      },
      {
        type: 'Promgen::ServerDirectory::PMC',
        cache_lifetime: '1h',
        url: 'http://pmc.localhost/'
      }
    ], @repo.all.map(&:values)
  end

  def test_insert_fail
    caught = nil
    begin
      @repo.insert(
        type: 'String',
        params: {}
      )
    rescue ArgumentError => e
      caught = e
    end
    assert_not_nil caught
  end

  def test_delete
    @app.db[:server_directory].delete

    sd1 = @repo.insert(
      type: 'Promgen::ServerDirectory::PMC',
      params: {
        url: 'http://pmc.localhost/',
        cache_lifetime: '1h'
      }
    )
    sd2 = @repo.insert(
      type: 'Promgen::ServerDirectory::PMC',
      params: {
        url: 'http://pmc2.localhost/',
        cache_lifetime: '1h'
      }
    )
    @repo.delete(server_directory_id: sd2.id)

    assert_equal [sd1.id], @repo.all.map(&:id)
  end
end
