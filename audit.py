#!/usr/bin/python

# Parses inventory audit logs in Ansible fact output format and templates
# them into readable text files.

# Author mjmaisey

import argparse
import ansible.runner
import ansible.inventory
import sys
import json
import jinja2
import os
import os.path
import getpass


def run_ansible(inventory, callback, module_name, module_args=''):

  ansible_runner = ansible.runner.Runner(inventory=inventory, pattern='*', forks=10, 
    module_name=module_name, module_args=module_args)
  results = ansible_runner.run()

  for (hostname, result) in results['contacted'].items():
      if not 'failed' in result:
          callback(hostname, result)


def collect_ansible_facts(inventory):

  host_facts = {}

  def callback(hostname, result):
    host_facts[hostname] = {'ansible_facts': result['ansible_facts']}

  print "Collecting ansible facts..."
  run_ansible(inventory, callback, 'setup')
  return host_facts


def collect_ubuntu_update_status(host_facts, inventory):

  def callback(hostname, result):
    outstanding_updates = {}
    lines = result['stdout'].splitlines()
    if len(lines) >= 3:
      outstanding_updates['all'] = lines[1].split()[0]
      outstanding_updates['security'] = lines[2].split()[0]
      host_facts[hostname]['outstanding_updates'] = outstanding_updates

  print "Collecting update status..."
  run_ansible(inventory, callback, 'command', '/usr/lib/update-notifier/update-motd-updates-available')


def write_facts(outputdir, host_facts):

  # Load output template
  env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
  template = env.get_template('host-template.j2')

  for hostname, facts in host_facts.iteritems():

    hostdir = os.path.join(outputdir, hostname)
    if not os.path.exists(hostdir):
      os.makedirs(hostdir)

    # Write facts to JSON file
    with open(os.path.join(hostdir, 'summary.json'), 'w') as json_file:
      json.dump(facts, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    # Write facts to text file using output template
    with open(os.path.join(hostdir, 'summary.txt'), 'w') as templated_file:
      templated_file.write(hostname)
      templated_file.write(template.render(facts))


def main():
  # Handle command line arguments
  parser = argparse.ArgumentParser(description='''Inventory audit tool''')
  parser.add_argument('inventory', help='''inventory file (in Ansible format)''')
  parser.add_argument('outputdir', help='''Output directory for results''')
  parser.add_argument()
  args = parser.parse_args()

  (sshpass, sudopass, su_pass, vault_pass) = utils.ask_passwords(ask_pass=args.ask_pass, ask_sudo_pass=args.ask_sudo_pass, ask_su_pass=args.ask_su_pass, ask_vault_pass=args.ask_vault_pass)

  # Collect basic ansible facts
  inventory = ansible.inventory.Inventory(args.inventory)
  host_facts = collect_ansible_facts(inventory)
  collect_ubuntu_update_status(host_facts, inventory)

  # Collect update status

  write_facts(args.outputdir, host_facts)

main()
