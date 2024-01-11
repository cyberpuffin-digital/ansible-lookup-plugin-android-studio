#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0103
"""
Ansible lookup module for pulling latest Android Studio or CLI Tools information.
"""

import argparse
import re

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
short_description: Lookup latest download information for Android Studio or CLI tools.
description:
  - Scrape Android developer page for requested download information.
options:
  target_os:
    description:
      - Download information for target Operating System.
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
  - Original source (https://github.com/snapcrafters/android-studio/commit/921d05fcc21e8b789fdef7d65ccc4c96e484a9a4)
  - Ansible documentation (https://docs.ansible.com/ansible/latest/dev_guide/developing_plugins.html#lookup-plugins)
"""

EXAMPLES = r"""
- name: Get latest Android Studio info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'studio') }}"

- name: Download Android Studio {{ android_studio_details.version }}
  ansible.builtin.get_url:
    url: "{{ android_studio_details.url }}"
    checksum: "sha256:{{ android_studio_details.checksum }}"
    dest: "{{ androidsdk_base_path }}/downloads/{{ android_studio_details.filename }}"
    mode: "0775"
  register: androidsdk_studio_archive

- name: Extract Android studio ({{ androidsdk_studio_archive.dest }})
  ansible.builtin.unarchive:
    src: "{{ androidsdk_studio_archive.dest }}"
    dest: "{{ androidsdk_base_path }}/"
    remote_src: true
  when: androidsdk_studio_archive is changed

- name: Link Android Studio startup script to system path
  ansible.builtin.file:
    path: "/usr/local/bin/android-studio.sh"
    src: "{{ androidsdk_base_path }}/android-studio/bin/studio.sh"
    state: link
  when: androidsdk_studio_archive is changed

- name: Get latest Android CLI tools info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'cli') }}"

- name: Get latest Android Studio info for Windows
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'windows', 'studio') }}"

- name: Get latest Android CLI tools info for Mac
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'mac', 'cli')  }}"
"""

RETURN = r"""
checksum:
  description: SHA-256 checksum for download package.
  returned: success
  type: str
filename:
  description: Download file name
  returned: success
  type: str
url:
  description: Download URL for Studio or CLI.
  returned: success
  type: str
version:
  description: Current version number for Studio or CLI tools.
  returned: success
  type: str
"""

URL_STUDIO_HOME = 'https://developer.android.com/studio/index.html'

class LookupModule(LookupBase):
    """Android Studio download information lookup module"""

    def __init__(self, target_os="linux", utility="studio", **kwargs):
        """Setup and initialize module"""
        self.target_os = target_os
        self.utility = utility

        if self.is_called_by_ansible():
            super(LookupBase, self).__init__()
            self.display = Display()

    def get_checksum(self, html):
        """Scan page results for OS + utility checksum."""
        checksum = "Unavailable"
        matched = self.match_checksum(html)

        if len(matched) == 0:
            err_msg = f"Unable to find checksum for {self.utility} on {self.target_os}."
            if self.is_called_by_ansible():
                raise AnsibleError(err_msg)
            raise LookupError(err_msg)

        if len(matched) > 1:
            err_msg = f"Expected one checksum, found multiple: {matched}"
            if self.is_called_by_ansible():
                raise AnsibleParserError(err_msg)
            raise LookupError(err_msg)

        checksum = to_text(matched[0])

        return checksum

    def get_url(self, html):
        """Scan page results for OS + utility to find download URL."""
        matched = self.match_url(html)
        filename = "Unavailable"
        url = "Unavailable"
        version = "Unavailable"

        if len(matched) == 0:
            err_msg = f"Unable to find URL matching OS {self.target_os} and utility {self.utility}"
            if self.is_called_by_ansible():
                raise AnsibleError(err_msg)
            raise LookupError(err_msg)

        # Deduplicate matched URLs
        matched = list(dict.fromkeys(matched))

        if len(matched) > 1:
            err_msg = f"Expected one URL, found multiple: {matched}"
            if self.is_called_by_ansible():
                raise AnsibleParserError(err_msg)
            raise LookupError(err_msg)

        url = to_text(matched[0])
        filename = to_text(re.split(r"/", url)[-1])
        version = to_text(re.split(r"[-_]+", url)[-2])

        return filename, url, version

    def is_called_by_ansible(self):
        """Running inside Ansible?"""
        return __package__ == "ansible.plugins.lookup"

    def match_checksum(self, html):
        """Regex rules for finding the SHA-256 checksum."""
        # pylint: disable=too-many-return-statements, line-too-long

        if self.utility == "studio":
            match self.target_os:
                case "chromeos":
                    return re.findall(
                        r'android-studio-.*-cros\.deb</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "linux":
                    return re.findall(
                        r'android-studio-.*-linux.tar.gz</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "mac":
                    return re.findall(
                        r'android-studio-.*-mac.dmg</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "mac_arm":
                    return re.findall(
                        r'android-studio-.*-mac_arm.dmg</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "windows":
                    return re.findall(
                        r'android-studio-.*-windows.exe</button>\s*<br>\n\s+Recommended\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
        else:
            match self.target_os:
                case "chromeos":
                    return re.findall(
                        r'commandlinetools-linux-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "linux":
                    return re.findall(
                        r'commandlinetools-linux-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "mac":
                    return re.findall(
                        r'commandlinetools-mac-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "mac_arm":
                    return re.findall(
                        r'commandlinetools-mac-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )
                case "windows":
                    return re.findall(
                        r'commandlinetools-win-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                        html
                    )

        if self.utility == "studio":
            return re.findall(
                r'android-studio-.*-linux.tar.gz</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
                html
            )

        return re.findall(
            r'commandlinetools-linux-.*_latest.zip</button>\n\s+</td>\n\s+<td>.*</td>\n\s+<td>([0-9a-f]{64})</td>',
            html
        )

    def match_url(self, html):
        """Regex rules for finding the download URL."""
        # pylint: disable=too-many-return-statements

        if self.utility == "studio":
            match self.target_os:
                case "chromeos":
                    return re.findall(r'(https?://.*cros\.deb)', html)
                case "linux":
                    return re.findall(r'(https?://.*linux\.tar\.gz)', html)
                case "mac":
                    return re.findall(r'(https?://.*mac\.dmg)', html)
                case "mac_arm":
                    return re.findall(r'(https?://.*mac_arm\.dmg)', html)
                case "windows":
                    return re.findall(r'(https?://.*windows\.exe)', html)
        else:
            match self.target_os:
                case "chromeos":
                    return re.findall(
                        r'(https?://.*commandlinetools-linux.*_latest\.zip)', html
                    )
                case "linux":
                    return re.findall(
                        r'(https?://.*commandlinetools-linux.*_latest\.zip)', html
                    )
                case "mac":
                    return re.findall(r'(https?://.*commandlinetools-mac.*_latest\.zip)', html)
                case "mac_arm":
                    return re.findall(r'(https?://.*commandlinetools-mac.*_latest\.zip)', html)
                case "windows":
                    return re.findall(r'(https?://.*commandlinetools-win.*_latest\.zip)', html)

        if self.utility == "studio":
            return re.findall(r'(https?://.*linux\.tar\.gz)', html)

        return re.findall(r'(https?://.*commandlinetools-linux.*_latest\.zip)', html)

    def print_msg(self, msg):
        """Output message based on how the script has been called."""
        if self.is_called_by_ansible():
            self.display.v(to_text(msg))
        else:
            print(msg)

    def run(self, terms=None, variables=None, **kwargs):
        """Ansible entry-point, runs lookup logic."""
        if terms and isinstance(terms, list):
            self.target_os = terms[0]
            self.utility = terms[1]
            self.print_msg(f"Scanning {URL_STUDIO_HOME} for {self.target_os} {self.utility}")

        # Grab Android Developer Page
        html = open_url(URL_STUDIO_HOME).read().decode()

        # Scan html for requested information
        filename, url, version = self.get_url(html)

        return_dict = {
            "checksum": self.get_checksum(html),
            "filename": filename,
            "url": url,
            "version": version
        }

        self.print_msg(return_dict)

        # Lookup modules require lists and deprecate dictionary returns as of 2.18
        # May be a bit of a hack, but encapsulate the return dictionary in a list
        # to keep key names.
        return [return_dict]

match __name__:
    case '__main__': # Script called directly
        parser = argparse.ArgumentParser(
            description="""
            Get Download URL, version, and checksum from Android
            developer site for chosen OS and Utility.
            """
        )
        parser.add_argument(
            '-o', '--os', help="Operating System to filter on.",
            choices=['chromeos', 'linux', 'mac', 'mac_arm', 'windows'], default="linux",

        )
        parser.add_argument(
            '-u', '--utility', choices=['studio', 'cli'], default="studio",
            help="Command line utilities or full studio suite."
        )
        args = parser.parse_args()

        lookup_module = LookupModule(args.os, args.utility)
        lookup_module.run()
    case 'ansible.plugins.lookup.get_latest': # Script called by Ansible
        print("Called by Ansible")
    case _: # Not sure
        print(f"get_latest.py is being called in an unfamiliar way: {__name__}")
