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
Sequel.migration do
  change do
    drop_table :exporter

    create_table :server_directory do
      primary_key :id

      String :type, null: false
      String :params, null: false

      unique [:type, :params]
    end

    self[:server_directory].insert(
      type: 'Promgen::ServerDirectory::DB',
      params: '{}'
    )

    create_table :project_exporter do
      primary_key :id

      foreign_key :project_id, :project, null: false, on_delete: :cascade
      Integer :port, null: false
      String :job, null: false

      unique([:project_id, :port], :name => :unique_project_id_port)
    end

    alter_table(:rule) do
      add_foreign_key :project_id, :project, on_delete: :cascade
      set_column_not_null :project_id
      drop_foreign_key :farm_id
    end

    alter_table(:farm) do
      drop_column :source
    end

    alter_table(:host) do
      set_column_not_null :farm_id
    end

    alter_table(:project_farm) do
      add_column :farm_name, String
      drop_foreign_key :farm_id
      add_foreign_key :server_directory_id, :server_directory, on_delete: :cascade
      set_column_not_null :server_directory_id
      set_column_not_null :farm_name
      set_column_not_null :project_id

      add_index [:project_id, :farm_name], unique: true
    end
  end
end
