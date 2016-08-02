# frozen_string_literal: true
require 'rake/testtask'
require 'rubocop/rake_task'
require 'logger'

RuboCop::RakeTask.new

task default: [:test]

Rake::TestTask.new do |t|
  t.libs << 'test'
  t.ruby_opts = ['-r "./test/test_helper"'] if ENV['COVERAGE']
  t.test_files = FileList['test/**/test_*.rb']
  t.warning = false
  t.verbose = false
end

# rake db:migrate
# rake db:migrate[2]
namespace :db do
  desc 'Run migrations'
  task :migrate, [:version] do |_t, args|
    require 'sequel'
    Sequel.extension :migration
    logger = ENV['LOGGER'] ? Logger.new(STDOUT) : nil
    db = Sequel.connect(ENV.fetch('DATABASE_URL'), logger: logger)
    if args[:version]
      puts "Migrating to version #{args[:version]}"
      Sequel::Migrator.run(db, 'migrations', target: args[:version].to_i)
    else
      puts 'Migrating to latest'
      Sequel::Migrator.run(db, 'migrations')
    end
  end
end
