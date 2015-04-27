#!/usr/bin/env python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: foreman_location
short_description:
- Manage Foreman Operatingsystems using Foreman API v2.
description:
- Create, update and and delete Foreman Operatingsystems using Foreman API v2
options:
  description:
    description: OS description
    required: false
    default: null
  name:
    description: OS name
    required: true
    default: null
    aliases: []
  major:
    description: OS major version
    required: true
    default: null
  minor:
    description: OS minor version
    required: false
    default: null
  release_name:
    description: Release name
    required: false
    default: null
  state:
    description: OS state
    required: false
    default: 'present'
    choices: ['present', 'absent']
  foreman_host:
    description: Hostname or IP address of Foreman system
    required: false
    default: 127.0.0.1
  foreman_port:
    description: Port of Foreman API
    required: false
    default: 443
  foreman_user:
    description: Username to be used to authenticate on Foreman
    required: true
    default: null
  foreman_pass:
    description: Password to be used to authenticate user on Foreman
    required: true
    default: null
notes:
- Requires the python-foreman package to be installed. See https://github.com/Nosmoht/python-foreman.
author: Thomas Krahn
'''

EXAMPLES = '''
- name: Ensure CoreOS 607.0.0
  foreman_operatingsystem:
    name: CoreOS 607.0.0
    architectures:
    - x86_64
    description: CoreOS Current stable
    media:
    - CoreOS mirror
    major: 607
    minor: 0.0
    partition_tables:
    - CoreOS default fake
    state: present
    foreman_host: 127.0.0.1
    foreman_port: 443
    foreman_user: admin
    foreman_pass: secret
'''

try:
    from foreman.foreman import *

    foremanclient_found = True
except ImportError:
    foremanclient_found = False


def list_to_dict_list(alist, key):
    result = []
    if alist:
        for item in alist:
            result.append({key: item})
    return result


def dict_list_to_list(alist, key):
    result = list()
    if alist:
        for item in alist:
            result.append(item.get(key, None))
    return result


def equal_dict_lists(l1, l2, compare_key='name'):
    s1 = set(dict_list_to_list(alist=l1, key=compare_key))
    s2 = set(dict_list_to_list(alist=l2, key=compare_key))
    return s1.issubset(s2) and s2.issubset(s1)


def get_resources(resource_type, resource_func, resource_names):
    result = []
    for item in resource_names:
        try:
            resource = resource_func(data=dict(name=item))
            if not resource:
                module.fail_json(
                    msg='Could not find resource type {resource_type} named {name}'.format(resource_type=resource_type,
                                                                                           name=item))
            result.append(dict(name=item, id=resource.get('id')))
        except ForemanError as e:
            module.fail_json(msg='Could not search resource type {resource_type} named {name}: {error}'.format(
                resource_type=resource_type, name=item, error=e.message))
    return result


def get_architectures(theforeman, architectures):
    return get_resources(resource_type='architecture',
                         resource_func=theforeman.search_architecture, resource_names=architectures)


def get_media(theforeman, media):
    return get_resources(resource_type='medium',
                         resource_func=theforeman.search_medium, resource_names=media)


def get_partition_tables(theforeman, partition_tables):
    return get_resources(resource_type='partition table',
                         resource_func=theforeman.search_partition_table, resource_names=partition_tables)


def ensure():
    comparable_keys = ['description', 'family', 'major', 'minor', 'release_name']
    architectures = module.params['architectures']
    description = module.params['description']
    family = module.params['family']
    major = module.params['major']
    media = module.params['media']
    minor = module.params['minor']
    name = module.params['name']
    partition_tables = module.params['partition_tables']
    release_name = module.params['release_name']
    state = module.params['state']

    foreman_host = module.params['foreman_host']
    foreman_port = module.params['foreman_port']
    foreman_user = module.params['foreman_user']
    foreman_pass = module.params['foreman_pass']

    theforeman = Foreman(hostname=foreman_host,
                         port=foreman_port,
                         username=foreman_user,
                         password=foreman_pass)

    data = {'name': name}

    try:
        os = theforeman.search_operatingsystem(data=data)
        if os:
            os = theforeman.get_operatingsystem(id=os.get('id'))
    except ForemanError as e:
        module.fail_json(msg='Could not get operatingsystem: {0}'.format(e.message))

    if state == 'absent':
        if os:
            try:
                os = theforeman.delete_operatingsystem(id=os.get('id'))
                return True, os
            except ForemanError as e:
                module.fail_json(msg='Could not delete operatingsystem: {0}'.format(e.message))

        return False, os

    data['architectures'] = get_architectures(theforeman=theforeman, architectures=architectures)
    data['description'] = description
    data['family'] = family
    data['major'] = major
    data['minor'] = minor
    data['media'] = get_media(theforeman=theforeman, media=media)
    data['ptables'] = get_partition_tables(theforeman=theforeman, partition_tables=partition_tables)
    data['release_name'] = release_name

    if not os:
        try:
            os = theforeman.create_operatingsystem(data=data)
            return True, os
        except ForemanError as e:
            module.fail_json(msg='Could not create operatingsystem: {0}'.format(e.message))

    if (not all(data[key] == os.get(key, data[key]) for key in comparable_keys)) or (
            not equal_dict_lists(l1=data.get('architectures', None), l2=os.get('architectures', None))) or (
            not equal_dict_lists(l1=data.get('media', None), l2=os.get('media', None))) or (
            not equal_dict_lists(l1=data.get('ptables', None), l2=os.get('ptables', None))):
        try:
            os = theforeman.update_operatingsystem(id=os.get('id'), data=data)
            return True, os
        except ForemanError as e:
            module.fail_json(msg='Could not update operatingsystem: {0}'.format(e.message))

    return False, os


def main():
    global module
    module = AnsibleModule(
        argument_spec=dict(
            architectures=dict(type='list', default=list()),
            description=dict(type='str', default=None),
            family=dict(type='str', default=None),
            major=dict(type='str', required=True),
            media=dict(type='list', default=list()),
            minor=dict(type='str', default=None),
            name=dict(type='str', required=True),
            partition_tables=dict(type='list', default=list()),
            release_name=dict(type='str', default=None),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            foreman_host=dict(type='str', default='127.0.0.1'),
            foreman_port=dict(type='str', default='443'),
            foreman_user=dict(type='str', required=True),
            foreman_pass=dict(type='str', required=True)
        ),
    )

    if not foremanclient_found:
        module.fail_json(msg='python-foreman module is required. See https://github.com/Nosmoht/python-foreman.')

    changed, os = ensure()
    module.exit_json(changed=changed, operatingsystem=os)

# import module snippets
from ansible.module_utils.basic import *

main()
