from setuptools import setup, find_packages

setup(
    name='indico-chat-bot',
    version='0.2',
    license='ASL 2.0',
    long_description=open('README.md').read(),
    packages=find_packages(),
    install_requires=[
        'click',
        'pytz',
        'requests',
        'configparser',
        'loguru'
    ],
    extras_require={
        'redis': ['redis'],
        'test': ['pytest', 'pytest-cov', 'pytest-freezegun']
    },
    entry_points={
        'console_scripts': [
            'indico_chat_bot=indico_chat_bot.bot:cli'
        ]
    }
)
