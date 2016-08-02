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

class Promgen
  class Factory
    # @param [Promgen::Repo::ServiceRepo] service_repo
    # @param [Promgen::Repo::ProjectRepo] project_repo
    # @param [Promgen::Service::FarmService] farm_service
    # @param [Promgen::Service::HostService] host_service
    # @param [Promgen::Repo::ProjectExporterRepo] project_exporter_repo
    # @param [Promgen::Repo::ServerDirectoryRepo] server_directory_repo
    # @param [Promgen::Repo::ProjectFarmRepo] project_farm_repo
    # @param [Promgen::Service::RuleService] rule_service
    def initialize(db:, service_repo:, project_repo:, farm_service:, host_service:, project_farm_repo:, project_exporter_repo:, server_directory_repo:, rule_service:)
      @db = db
      @random = Random.new
      @service_repo = service_repo
      @project_repo = project_repo
      @farm_service = farm_service
      @host_service = host_service
      @project_exporter_repo = project_exporter_repo
      @server_directory_repo = server_directory_repo
      @project_farm_repo = project_farm_repo
      @rule_service = rule_service
    end

    def service
      @service_repo.insert(name: "foo#{@random.rand}")
    end

    def project(service_id: service.id)
      id = @project_repo.insert(service_id: service_id, name: 'foo')
      @project_repo.find(id: id)
    end

    def project_exporter(project_id: project.id, port: @random.rand(1000), job: "job#{@random.rand}")
      id = @project_exporter_repo.register(project_id: project_id, port: port, job: job)
      @project_exporter_repo.find(id: id)
    end

    def project_farm(project_id: project.id, farm_name: farm.name, server_directory_id: @server_directory_repo.find_db.id)
      @project_farm_repo.link(project_id: project_id, server_directory_id: server_directory_id, farm_name: farm_name)
    end

    def farm(name: "farm-#{@random.rand}")
      @farm_service.find_or_create(name: name)
    end

    def host(farm_id: farm.id, name: "host-#{@random.rand}")
      id = @host_service.insert(farm_id: farm_id, name: name)
      @host_service.find(id: id)
    end

    def rule(service_id: service_id.id)
      rule = @rule_service.register(service_id: service_id, alert_clause: 'InstanceDown', if_clause: 'up == 0', for_clause: '5m', labels_clause: 'severity = "page"', annotations_clause: 'summary = "Instance {{ $labels.instance }} down"')
      @rule_service.find(id: rule.id)
    end
  end
end
