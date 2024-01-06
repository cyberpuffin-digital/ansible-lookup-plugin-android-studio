#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Ansible lookup module for pulling latest Android Studio or CLI Tools information.
"""

import re
import sys
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.module_utils.urls import open_url

DOCUMENTATION = r"""
---
module: get_latest
author: Cyber Puffin
version_added: "2.15"
short_description: Lookup latest version and download URL for Android Studio or CLI tools.
description:
  - Pull and parse Android developer page for relevant version and download URLs.
  - Match OS and utility to determine appropriate URL.
options:
  target_os:
    description:
      - OS matching download link on android developer page.
      - Available options - chromeos, linux, mac, mac_arm, windows.
    type: str
    required: true
    default: linux
  utility:
    description: "Full studio or command line tools only (options: studio, cli)"
    type: str
    required: true
    default: studio
notes:
  - Source (https://github.com/cyberpuffin-digital/ansible-lookup-plugin-android-studio/)
  - Original source (https://raw.githubusercontent.com/snapcrafters/android-studio/master/get_latest.py)
  - Ansible documentation (https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html#lookup-plugins)
"""

EXAMPLES = r"""
- name: Get latest Android Studio info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'studio') }}"

- name: Split lookup results into dedicated variables
  ansible.builtin.set_fact:
    android_studio_version: "{{ android_studio_details | split(',') | first }}"
    android_studio_download: "{{ android_studio_details | split(',') | last }}"

- name: Get latest Android CLI tools info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'cli') }}"

- name: Get latest Android Studio info for Windows
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'windows', 'studio') }}"

- name: Get latest Android CLI tools info for Mac
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'mac', 'cli') }}"
"""

RETURN = r"""
version:
  description: Current version number for Studio or CLI tools.
  returned: success
  type: str
url:
  description: Download URL for Studio or CLI.
  returned: success
  type: str
"""

URL_STUDIO_HOME = 'https://developer.android.com/studio/index.html'

class LookupModule(LookupBase):
    """Ansible lookup module"""

    def __init__(self, target_os="linux", utility="studio", **kwargs):
        """Setup and initialize module"""
        super(LookupBase, self).__init__()

        self.display = Display()
        self.target_os = target_os
        self.utility = utility

    def get_match(self, html):
        """Scan page results for matching OS and utility."""
        matched = None
        match self.target_os:
            case "chromeos":
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*cros.deb)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-linux.*_latest.zip)"', html)
            case "linux":
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*linux.tar.gz)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-linux.*_latest.zip)"', html)
            case "mac":
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*mac.dmg)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-mac.*_latest.zip)"', html)
            case "mac_arm":
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*mac_arm.dmg)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-mac.*_latest.zip)"', html)
            case "windows":
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*windows.exe)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-win.*_latest.zip)"', html)
            case _:
                if self.utility == "studio":
                    matched = re.findall('"((https)?://.*linux.tar.gz)"', html)
                else:
                    matched = re.findall('"((https)?://.*commandlinetools-linux.*_latest.zip)"', html)

        return matched

    def print_msg(self, msg):
        """Output message based on how the script has been called."""
        if __package__ == "ansible.plugins.lookup":
            self.display.v(msg)
        else:
            print(msg)

    def run(self, terms=None, variables=None, **kwargs):
        """Ansible entry-point, runs lookup logic."""
        if terms and isinstance(terms, list):
            self.target_os = terms[0]
            self.utility = terms[1]
            self.print_msg(f"Scanning {URL_STUDIO_HOME} for {self.target_os} {self.utility}")

        # Download and scan Android Developer page
        resp = open_url(URL_STUDIO_HOME)
        matched = self.get_match(resp.read().decode())

        # Ensure unique and then convert to a list of easy access.
        links = list(set(matched))

        if len(links) == 0:
            raise AnsibleError("Url matching our query not found.")
        if len(links) > 1:
            raise AnsibleParserError(f"Expected one URL, found multiple: {links}")

        url = links[0][0]
        if self.utility == "studio":
            version = url.split('/')[-2]
        else:
            version = re.split(r"[-_]+", url)[-2]
        url = to_text(url)
        version = to_text(version)

        if version:
            self.print_msg(f"Version: {version}")

        if url:
            self.print_msg(f"URL: {url}")

        return [version, url]


match __name__:
    case '__main__':
        lookup_module = None
        match len(sys.argv):
            case 2:
                print(f"2 arguments found: {sys.argv}.")
                lookup_module = LookupModule(sys.argv[1])
            case 3:
                print(f"3 arguments found: {sys.argv}.")
                lookup_module = LookupModule(sys.argv[1], sys.argv[2])
            case _:
                print(f"{len(sys.argv)} arguments found: {sys.argv}.")
                lookup_module = LookupModule()
        print(' '.join(lookup_module.run()))
    case 'ansible.plugins.lookup.get_latest':
        print("Called by Ansible")
    case _:
        print(f"get_latest.py is being called in an unfamiliar way: {__name__}")

