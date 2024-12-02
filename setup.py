from setuptools import setup, find_packages


TEST_DEPS = ["pytest", "pytest-cov", "pytest-freezegun"]

setup(
    name="indico-chat-bot",
    version="0.2",
    license="ASL 2.0",
    long_description=open("README.md").read(),
    packages=find_packages(),
    install_requires=["click", "pytz", "requests", "configparser", "loguru"],
    extras_require={"redis": ["redis"], "test": TEST_DEPS, "dev": TEST_DEPS + ["ruff"]},
    entry_points={"console_scripts": ["indico_chat_bot=indico_chat_bot.bot:cli"]},
)
