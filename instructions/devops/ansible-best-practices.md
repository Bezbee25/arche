# Ansible Best Practices

description: Ansible automation standards: idempotency, FQCN, Vault secrets, roles structure, validation pipeline
tags: devops, ansible, automation, configuration-management, idempotency, vault

Standards for idempotent, maintainable, and secure Ansible automation.

## Idempotency

- Always use idempotent modules over `shell`/`command`/`raw`:
  - Use `copy`, `template`, `file` instead of `shell: cp`
  - Use `package`, `apt`, `dnf` instead of `shell: apt-get install`
  - Use `service` instead of `shell: systemctl start`
- When `shell`/`command` is unavoidable, add `creates` or `changed_when`:
  ```yaml
  - name: Run migration
    command: python manage.py migrate
    changed_when: "'No migrations to apply' not in result.stdout"
  ```

## Module Naming

- Use fully qualified collection names (FQCN) to avoid ambiguity:
  ```yaml
  - ansible.builtin.copy:  # not just: copy:
  - ansible.posix.mount:
  - community.docker.docker_container:
  ```

## Secret Management

- Use Ansible Vault for all credentials and sensitive data
- Prefix vault variables with `vault_` and reference them in plain var files:
  ```yaml
  # vars/main.yml
  db_password: "{{ vault_db_password }}"

  # vars/vault.yml (encrypted)
  vault_db_password: "supersecret"
  ```
- Never commit unencrypted vault files
- Use `ansible-vault encrypt_string` for inline secrets

## Playbook Structure

```
roles/
  myapp/
    tasks/main.yml
    handlers/main.yml
    templates/
    files/
    vars/main.yml
    defaults/main.yml
    meta/main.yml
```

- Use roles for reusable configuration components
- Use `include_tasks` for conditional task inclusion
- Use `import_tasks` for static inclusion (better performance)

## Variables

- Use `snake_case` for all variable names
- Define defaults in `defaults/main.yml` (lowest precedence — overridable)
- Sort variables alphabetically within files
- Use `vars/main.yml` for role-specific non-overridable values

## Style & Formatting

- 2-space indentation throughout
- Quote all strings containing special characters
- Use block scalar (`|` or `>`) for multi-line strings
- Add `name:` to every task — descriptive, action-oriented names

## Validation Pipeline

```bash
# Syntax check
ansible-playbook site.yml --syntax-check

# Lint
ansible-lint site.yml

# Dry run with diff
ansible-playbook site.yml --check --diff -l staging

# Run
ansible-playbook site.yml -l staging
```

## Tags

- Add tags to tasks for selective execution:
  ```yaml
  - name: Install packages
    apt:
      name: nginx
    tags: [install, nginx]
  ```
- Use consistent tag taxonomy: `install`, `configure`, `deploy`, `cleanup`

## Handlers

- Use handlers for service restarts (only triggered when notified):
  ```yaml
  handlers:
    - name: restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
  ```
- Handlers run once at the end of a play, not immediately when notified

## Inventory

- Use dynamic inventory for cloud environments (AWS, Azure, GCP)
- Group hosts by role: `[webservers]`, `[databases]`, `[loadbalancers]`
- Use host and group variables directories: `host_vars/`, `group_vars/`
