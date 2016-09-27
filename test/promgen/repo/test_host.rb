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

class TestHostRepo < Promgen::Test
  def test_find_or_create
    farm = @factory.farm
    @app.host_repo.insert_multi(farm_id: farm.id, names: %w(aaa bbb))

    assert_equal [
      { farm_id: farm.id, name: 'aaa' },
      { farm_id: farm.id, name: 'bbb' }
    ], @app.host_repo.all.map { |row| { farm_id: row.farm_id, name: row.name } }
  end

  def test_insert_multi
    farm = @factory.farm
    @app.host_repo.insert_multi(farm_id: farm.id, names: %w(aaa bbb))
    @app.host_repo.insert_multi(farm_id: farm.id, names: %w(aaa aaa bbb ccc ccc))

    assert_equal [
      { farm_id: farm.id, name: 'aaa' },
      { farm_id: farm.id, name: 'bbb' },
      { farm_id: farm.id, name: 'ccc' }
    ], @app.host_repo.all.map { |row| { farm_id: row.farm_id, name: row.name } }
  end

  def test_find
    host = @factory.host
    host2 = @app.host_repo.find(id: host.id)
    assert_equal host.name, host2.name
  end

  def test_delete
    host1 = @factory.host
    host2 = @factory.host
    @app.host_repo.delete(id: host1.id)
    assert_nil @app.host_repo.find(id: host1.id)
    assert_not_nil @app.host_repo.find(id: host2.id)
  end

  def test_delete_by_name
    host1 = @factory.host
    host2 = @factory.host
    @app.host_repo.delete_by_name(name: host1.name)
    assert_nil @app.host_repo.find(id: host1.id)
    assert_not_nil @app.host_repo.find(id: host2.id)
  end
end
