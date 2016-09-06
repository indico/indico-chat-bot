from setuptools import setup

setup(
    name='indico-mattermost-bot',
    version='0.1',
    license='ASL 2.0',
    long_description=open('README.md').read(),
    install_requires=[
        'click',
        'pytz',
        'requests',
        'configparser'
    ]
)
