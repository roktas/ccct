# frozen_string_literal: true
# vim: ft=ruby

Vagrant.configure('2') do |config|
  config.vm.box = 'windows/lab' # See .local/doc/development.md

  config.vm.provider 'virtualbox' do |virtualbox|
    virtualbox.gui = true

    virtualbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
  end

  config.vm.provision 'shell', inline: <<~'PROVISION'
    [Environment]::SetEnvironmentVariable('Path', $Env:Path + ';C:\vagrant\.local\bin;C:\vagrant\.local\tmp', 'User')
  PROVISION

  config.ssh.extra_args = ['-t', 'Set-Location \vagrant; powershell']
end
