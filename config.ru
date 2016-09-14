# frozen_string_literal: true
$LOAD_PATH.unshift(File.dirname(__FILE__) + '/lib/')
require 'rack/urlmap'

require 'promgen'

require 'rack/protection'
use Rack::Protection::XSSHeader
use Rack::Protection::FrameOptions

app = Promgen.build

use Rack::Static, urls: ['/css'], root: File.join(File.dirname(__FILE__), 'public')

run Rack::URLMap.new(
  # /metrics stub to allow prometheus to check 'up' status
  '/metrics' => proc { [200, { 'Content-Type' => 'text/plain' }, ['']] },
  '/alert/' => Rack::Auth::Basic.new(app.alert) do |username, password|
    username == 'promgen' && password == app.config['password']
  end,
  '/' => Rack::Protection::RemoteReferrer.new(app.web, allow_empty_referrer: false)
)
