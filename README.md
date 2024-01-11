# ansible-lookup-plugin-android-studio
Ansible lookup plugin that started with Snapcraft's now defunct [get_latest.py](https://github.com/snapcrafters/android-studio/commit/921d05fcc21e8b789fdef7d65ccc4c96e484a9a4).  After multiple iterations there's hardly any resemblance left.

This plugin can be run in an Ansible playbook or from the command line to scan the [Android Developer](https://developer.android.com/studio/index.html) page for download details based on OS and Utility requested.  The downloaded page is parsed with some static regex and the results are returned as a list of dictionaries (should only be one, but Ansible demands a ~~blood sacrifice~~ List output, deprecating Dictionary outputs in 2.18).

# Examples

Call the lookup module from Ansible with the target os and utility specified
```yml
- name: Get latest Android Studio info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'studio') }}"

- name: Get latest Android CLI tools info for Linux
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'linux', 'cli') }}"

- name: Get latest Android Studio info for Windows
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'windows', 'studio') }}"

- name: Get latest Android CLI tools info for Mac
  ansible.builtin.set_fact:
    android_studio_details: "{{ lookup('get_latest', 'mac', 'cli')  }}"
```

Then use these details to determine if a download is necessary (NB: checksum is used to determine if download is necessary, but if `ansible.builtin.get_url`'s `dest` is a directory the file is downloaded each time for comparison \[[ref.](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/get_url_module.html#parameter-dest)\]).

```yml
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
```

# Returns

Technically the return is a List of Dictionaries, though there should only ever be one.  Ansible 2.18 deprecates lookup modules returning a Dictionary directly, but managing return elements based on order gets messy.

```yml
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
```
