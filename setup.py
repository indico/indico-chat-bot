from setuptools import setup, find_packages

setup(
    name='indico-mattermost-bot',
    version='0.1',
    license='ASL 2.0',
    long_description=open('README.md').read(),
    packages=find_packages(),
    install_requires=[
        'click',
        'pytz',
        'requests',
        'configparser'
    ],
    entry_points={
        'console_scripts': [
            'indico-mm-bot=indico_mattermost_bot.bot:cli'
        ]
    }
)
