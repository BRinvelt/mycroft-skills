"""Write a YAML file for the Voight-Kampff test setup script.

Voight-Kampff is the name of the integration test suite for mycroft-core and
mycroft-skills.  The test setup script installs the skills to include in the
test and copies their feature files over to core for inclusion in the tests.
"""
from argparse import ArgumentParser
from os import environ

import requests
from github import Github


def parse_command_line():
    """Get the values of the command line arguments."""
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "--pull-request",
        default=None,
        help='The Pull Request to be tested.'
    )
    arg_parser.add_argument(
        "--platform",
        default='mycroft_mark_1',
        help='The Pull Request to be tested.'
    )

    return arg_parser.parse_args()


def get_pull_request_diff(args):
    """Get the difference between the base branch and the modified branch."""
    pr_number = int(args.pull_request.strip('PR-'))
    g = Github(environ['GITHUB_API_KEY'])
    repo = g.get_repo('MycroftAI/mycroft-skills')
    pr = repo.get_pull(pr_number)
    pr_diff = requests.get(pr.diff_url)

    return pr_diff.text.split('\n')


def get_pull_request_submodule(pull_request_diff):
    """Determine the submodule name of the skill added/modified in the PR"""
    diff_file_name = None
    skill_submodule_path = None
    for line in pull_request_diff:
        #  The line indicating the file being compared looks like this:
        #    diff --git a/<file name> b/<file name>
        if line.startswith('diff --git a/'):
            words = line.split()
            diff_file_name = words[2].lstrip('a/').rstrip(' b/')
        # If a file contains a subproject commit hash it represents a skill
        if line.startswith('+Subproject commit '):
            skill_submodule_path = diff_file_name
            break

    return skill_submodule_path


def get_skill_author(skill_submodule_path, pull_request_diff):
    """Get the author of the Skill repo associated with the submodule.

    This first searches the .gitmodules file and then falls back to the diff.

    A submodule definition consists of 3 lines:
        [submodule "camera"]
            path = camera
            url = https://github.com/MycroftAI/skill-camera
    """
    skill_url = None
    with open('.gitmodules') as f:
        for line in f:
            if line.strip() == f'path = {skill_submodule_path}':
                skill_url = f.readline().split(' = ')[1]
                break

    if skill_url is None:
        for idx, line in enumerate(pull_request_diff):
            if line == f'+[submodule "{skill_submodule_path}"]':
                skill_url = pull_request_diff[idx + 2].split(' = ')[1]
                break
        else:
            raise Exception(f'{skill_submodule_path} not found')

    skill_author = skill_url.split('/')[3]
    return skill_author


def write_test_config_file(submodule, skill_author):
    """Write a YAML file for the integration test setup script."""
    with open('test_skill.yml', 'w') as config_file:
        config_file.write('test_skills:\n')
        config_file.write(' '.join(['-', submodule, '-u', skill_author, '\n']))


def main():
    args = parse_command_line()
    pull_request_diff = get_pull_request_diff(args)
    skill_submodule_path = get_pull_request_submodule(pull_request_diff)
    if skill_submodule_path is None:
        # Not every PR into this repository will be a change to a skill. 
        # If no Skill submodule was found, use the "hello world" Skill.
        skill_submodule_path = 'skill-hello-world'
        skill_author = 'MycroftAI'
    else:
        skill_author = get_skill_author(skill_submodule_path, pull_request_diff)
    write_test_config_file(skill_submodule_path, skill_author)


if __name__ == '__main__':
    main()
