from setuptools import setup
setup(
    name='ShelfCMS',
    version='0.1',
    url='https://github.com/iriahi/shelf-cms',
    license='BSD',
    author='Ismael Riahi',
    author_email='ismael@batb.fr',
    description='Enhancing flask microframework with beautiful admin and cms-like features',
    packages=['shelf','shelf.admin'],
    zip_safe=False,
    install_requires=[
        'Flask>=0.10',
        'Flask-Admin>=1.0.6'
    ]
)