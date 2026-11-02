from setuptools import setup

package_name = 'avoider_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Deni',
    maintainer_email='denigo.dgo@gmail.com',
    description='Object avoidance node',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'avoider = avoider_pkg.avoider:main',
        ],
    },
)

