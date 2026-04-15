from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="netsurge-wireless-nms",
    version="1.0.0",
    author="Netsurge Wireless",
    author_email="support@netsurgewireless.com",
    description="Network Monitoring System with AI-powered device discovery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/netsurgewireless/Netsurge-Wireless-NMS",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "flask>=2.0.0",
        "pysnmp>=4.0",
        "cryptography>=41.0",
        "requests>=2.28",
        "apscheduler>=3.10",
        "paramiko>=3.0",
    ],
    extras_require={
        "desktop": [
            "Pillow>=9.0",
            "pystray>=0.19",
            "plyer>=2.1",
        ],
        "dev": [
            "pyinstaller>=5.0",
            "pytest>=7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "netsurge-server=src.server:main",
            "netsurge-client=src.client:main",
            "netsurge-launcher=src.desktop_launcher:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.txt", "*.md"],
    },
    zip_safe=False,
)
