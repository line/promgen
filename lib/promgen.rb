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
require 'logger'
require 'sequel'
require 'yaml'

require 'injector'

require 'promgen/alert'
require 'promgen/alert/sender/ikachan'
require 'promgen/alert/sender/mail'
require 'promgen/config_writer'
require 'promgen/rule_writer'
require 'promgen/migrator'
require 'promgen/repo/project_exporter_repo'
require 'promgen/repo/rule_repo'
require 'promgen/repo/farm_repo'
require 'promgen/repo/host_repo'
require 'promgen/repo/project_repo'
require 'promgen/repo/service_repo'
require 'promgen/repo/project_farm_repo'
require 'promgen/repo/server_directory_repo'
require 'promgen/repo/audit_repo'

require 'promgen/service/audit_service'
require 'promgen/service/farm_service'
require 'promgen/service/host_service'
require 'promgen/service/project_exporter_service'
require 'promgen/service/project_farm_service'
require 'promgen/service/project_service'
require 'promgen/service/rule_service'
require 'promgen/service/server_directory_service'
require 'promgen/service/service_service'

require 'promgen/web'
require 'promgen/api'
require 'promgen/prometheus'
require 'promgen/server_directory/db'

class Promgen
  extend Injector

  config_key 'PROMGEN_CONFIG'

  register :db do |config|
    dsn = config['dsn']
    raise 'Missing db.dsn in configuraiton' unless dsn
    logger.info("PROMGEN_DB: #{dsn} #{config}")
    @db ||= Sequel.connect(
      dsn,
      logger: config[:logging] ? logger : nil,
      sql_mode: dsn =~ /^mysql:/ ? [:traditional, :no_auto_value_on_zero, :only_full_group_by] : nil
    )
  end

  register :farm_repo,            Promgen::Repo::FarmRepo
  register :host_repo,            Promgen::Repo::HostRepo
  register :project_exporter_repo, Promgen::Repo::ProjectExporterRepo
  register :rule_repo,            Promgen::Repo::RuleRepo
  register :service_repo,         Promgen::Repo::ServiceRepo
  register :project_repo,         Promgen::Repo::ProjectRepo
  register :project_farm_repo,    Promgen::Repo::ProjectFarmRepo
  register :server_directory_repo, Promgen::Repo::ServerDirectoryRepo
  register :audit_log_repo, Promgen::Repo::AuditRepo

  register :farm_service, Promgen::Service::FarmService
  register :host_service, Promgen::Service::HostService
  register :project_exporter_service, Promgen::Service::ProjectExporterService
  register :project_farm_service, Promgen::Service::ProjectFarmService
  register :project_service, Promgen::Service::ProjectService
  register :rule_service, Promgen::Service::RuleService
  register :server_directory_service, Promgen::Service::ServerDirectoryService
  register :service_service, Promgen::Service::ServiceService
  register :audit_log_service, Promgen::Service::AuditService

  register :web,                  Promgen::Web
  register :api,                  Promgen::API
  register :config_writer,        Promgen::ConfigWriter
  register :rule_writer,          Promgen::RuleWriter
  register :alert,                Promgen::Alert
  register :migrator,             Promgen::Migrator
  register :prometheus,           Promgen::Prometheus

  register_multi :server_directories, 'Promgen::ServerDirectory', 'promgen/server_directory'
  register_multi :alert_senders, 'Promgen::Alert::Sender', 'promgen/alert/sender'
end
