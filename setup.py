from setuptools import setup, find_packages

setup(
    name='ShelfCMS',
    version='0.3.9',
    url='https://github.com/iriahi/shelf-cms',
    license='BSD',
    author='Ismael Riahi',
    author_email='ismael@batb.fr',
    description='Enhancing flask microframework with beautiful admin and cms-like features',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Flask>=0.10',
        'Flask-Admin>=1.0.6',
	'Flask-WTF>=0.9',
	'Flask-SQLAlchemy>=1.0',
        'Flask-Login==0.2.9'
    ]
)
