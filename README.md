# ansible-lookup-plugin-android-studio
Ansible lookup plugin based on Snapcraft's [get_latest.py](https://github.com/snapcrafters/android-studio/commit/921d05fcc21e8b789fdef7d65ccc4c96e484a9a4) script, modified for use in Ansible.

Lookup plugin downloads Android Developer page to scan for version information and download links for requested OS and utility.

# Example

```yml
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
```

# Returns

```yml
version:
  description: Current version number for Studio or CLI tools.
  returned: success
  type: str
url:
  description: Download URL for Studio or CLI.
  returned: success
  type: str
```

